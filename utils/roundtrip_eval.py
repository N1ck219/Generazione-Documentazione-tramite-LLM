"""
Modulo di Round-Trip Differential Testing (Doc-to-Code Synthesis & Test Execution).

Flusso di valutazione:
1. Prende la documentazione generata dall'LLM (senza mostrare il codice sorgente originale).
2. Chiede a un LLM "Coder" di rigenerare la funzione basandosi ESCLUSIVAMENTE sulla docstring e sulla firma.
3. Chiede a un LLM "Tester" di generare una suite di casi di test (Pytest) che copre casi normali ed edge-cases.
4. Esegue sia l'implementazione ricreata sia una reference logic verificando il Pass Rate % dei test.
"""

import os
import sys
import json
import time
import re
import tempfile
import subprocess
import sqlite3
from typing import Dict, List, Any, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.llm_provider import GeminiLLMProvider


class RoundTripEvaluator:
    """
    Orchestra la sintesi di codice a partire dalla docstring e ne valida
    l'equivalenza comportamentale mediante generazione ed esecuzione di test pytest.
    """
    def __init__(self, model_name: str = "gemini-3.5-flash-lite", api_key: str = None, llm_provider: Optional[Any] = None):
        self.llm_provider = llm_provider
        self.model_name = getattr(llm_provider, "model_name", model_name)
        self.api_key = getattr(llm_provider, "api_key", api_key) or os.getenv("GEMINI_API_KEY")
        if self.api_key and "," in self.api_key:
            self.api_keys = [k.strip() for k in self.api_key.split(",") if k.strip()]
        elif self.api_key:
            self.api_keys = [self.api_key.strip()]
        else:
            self.api_keys = []
        self.current_key_idx = 0
        self.last_call_time = 0.0
        self.min_delay = 4.0
        self._init_client()

    def _init_client(self):
        if not self.api_keys:
            self.client = None
            self.use_new_sdk = False
            return
        active_key = self.api_keys[self.current_key_idx]
        try:
            from google import genai
            self.client = genai.Client(api_key=active_key)
            self.use_new_sdk = True
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=active_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.client = self.model
            self.use_new_sdk = False

    def _wait_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_call_time = time.time()

    def _call_gemini(self, prompt: str) -> str:
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._wait_rate_limit()
                if self.use_new_sdk:
                    from google.genai import types
                    config = types.GenerateContentConfig(temperature=0.2)
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config
                    )
                    return response.text
                else:
                    response = self.model.generate_content(prompt)
                    return response.text
            except Exception as e:
                err_msg = str(e)
                if ("Quota" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and self.current_key_idx + 1 < len(self.api_keys):
                    self.current_key_idx += 1
                    print(f"  -> RoundTrip: Key cambiata con successo (#{self.current_key_idx + 1}). Riprovo...")
                    self._init_client()
                    continue
                if attempt == max_retries - 1:
                    print(f"[WARN RoundTrip] Fallimento chiamata Gemini: {e}")
                    return ""
                time.sleep(4)
        return ""

    def synthesize_code_from_doc(self, func_name: str, signature: str, docstring: str) -> str:
        """
        Passaggio 1: Rigenera il codice Python della funzione basandosi SOLO sulla documentazione generata.
        Supporta sia funzioni C libere che metodi di classi C++ (es. Class::Method).
        """
        is_method = "::" in func_name
        class_name = func_name.split("::")[0] if is_method else None
        method_name = func_name.split("::")[1] if is_method else func_name

        c_instructions = ""
        if is_method:
            c_instructions = f"""
NOTE: The target is a C++ class method `{method_name}` inside class `{class_name}`.
1. Define the class `{class_name}`.
2. Include a simple constructor `def __init__(self, ...):` with default/optional arguments so the object can be instantiated easily in unit tests.
3. Implement the method `def {method_name}(self, ...):` strictly adhering to the documentation and signature.
4. Also implement minimal getter/setter or state properties if mentioned in the docstring.
5. Define any return codes, enums, or constants mentioned in the docstring (e.g., XML_SUCCESS = 0, XML_WRONG_ATTRIBUTE_TYPE = 1) at the module top level or class level.
6. Provide self-contained helper functions/classes if referenced (e.g. if XMLUtil.ToStr or ToInt is used, define a simple mock XMLUtil class).
"""
        else:
            c_instructions = f"""
NOTE: The target is a C free function.
1. Implement the Python function `def {func_name}(...):` strictly matching the inputs, return values, and behavior described in the documentation.
2. Define any constants, enums, or error codes mentioned in the documentation at the module top level.
"""

        prompt = f"""You are an expert Software Engineer writing self-contained Python code strictly based on technical documentation.
Do not invent features not described in the docstring.

Target Symbol: `{func_name}`
C/C++ Signature: `{signature}`

=== TECHNICAL DOCUMENTATION (SPECIFICATION) ===
{docstring}

=== IMPLEMENTATION REQUIREMENTS ===
{c_instructions}
- Ensure the code is 100% self-contained, syntactically valid Python.
- Do NOT use external C libraries or require uninstalled third-party packages.
- Return ONLY valid Python code inside a single ```python ... ``` block without conversational filler.
"""
        response = self._call_gemini(prompt)
        match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def synthesize_reference_from_code(self, func_name: str, signature: str, source_code: str) -> str:
        """
        Passaggio 1-REF: Traduce la funzione C/C++ originale direttamente in Python (Ground Truth Reference).
        Questa implementazione rappresenta il vero comportamento del sorgente (senza guardare la documentazione).
        """
        is_method = "::" in func_name
        class_name = func_name.split("::")[0] if is_method else None
        method_name = func_name.split("::")[1] if is_method else func_name

        c_instructions = ""
        if is_method:
            c_instructions = f"""
NOTE: The target is a C++ class method `{method_name}` inside class `{class_name}`.
1. Define the class `{class_name}`.
2. Include a constructor `def __init__(self, ...):` with default/optional arguments so the object can be instantiated easily in unit tests.
3. Faithfully translate the C++ method logic `{method_name}` into Python.
4. Define any return codes, enums, or constants used in the C++ code at module or class level.
5. Provide minimal mock helpers for external class methods if needed (e.g. XMLUtil).
"""
        else:
            c_instructions = f"""
NOTE: The target is a C free function.
1. Translate the C function `{func_name}` faithfully into Python `def {func_name}(...):`.
2. Define any constants, enums, or macros present in the C source code at module top level.
"""

        prompt = f"""You are an expert C/C++ to Python Transpiler.
Translate the following original C/C++ source code into clean, self-contained, idiomatic Python.
Do NOT use external C libraries.
The Python code MUST reproduce the exact same logical behavior, return values, and side-effects as the original C/C++ implementation.

Target Symbol: `{func_name}`
C/C++ Signature: `{signature}`

=== ORIGINAL C/C++ SOURCE CODE (GROUND TRUTH) ===
```c
{source_code}
```

=== IMPLEMENTATION REQUIREMENTS ===
{c_instructions}
- Ensure the code is 100% self-contained, syntactically valid Python.
- Return ONLY valid Python code inside a single ```python ... ``` block without conversational filler.
"""
        response = self._call_gemini(prompt)
        match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def generate_pytest_suite(self, func_name: str, docstring: str, synth_code: str = "", num_tests: Optional[int] = None) -> str:
        """
        Passaggio 2: Genera una suite di test Pytest esaustiva derivata dai contratti specificati nella documentazione.
        Se num_tests è None o <= 0, Gemini ha piena libertà adattiva per decidere quanti test servono.
        Inoltre, istruisce Gemini a includere un test basato su Hypothesis per il property/fuzz testing.
        """
        is_method = "::" in func_name
        class_name = func_name.split("::")[0] if is_method else None
        method_name = func_name.split("::")[1] if is_method else func_name

        invocation_guidance = ""
        if is_method:
            invocation_guidance = f"""
- The target is a class method `{method_name}` of `{class_name}`.
- In each test function, instantiate the object directly: `obj = {class_name}(...)` and then call `obj.{method_name}(...)`.
- Check the exact signature of `__init__` and `{method_name}` in the SYNTHESIZED IMPLEMENTATION below. Do not pass wrong number of arguments to `__init__` or `{method_name}`.
- Do NOT call unmentioned methods that are not implemented in the provided code.
"""
        else:
            invocation_guidance = f"""
- The target is a free function `{func_name}`.
- Call `{func_name}(...)` directly inside the tests matching its arguments.
"""

        synth_section = ""
        if synth_code:
            synth_section = f"""
=== SYNTHESIZED IMPLEMENTATION UNDER TEST ===
```python
{synth_code}
```
"""

        if num_tests and num_tests > 0:
            quantity_instruction = f"1. Write exactly {num_tests} standalone pytest test functions (named `test_semantic_1_...`, `test_semantic_2_...`, etc.)."
        else:
            quantity_instruction = """1. ADAPTIVE TEST COUNT: Decide autonomously how many tests are needed (typically between 4 and 12) to thoroughly cover the specification without redundancy.
   - Name each standard semantic test starting with `test_semantic_...`."""

        prompt = f"""You are a Senior QA Automation & Verification Engineer writing a comprehensive pytest test suite.
You are given the specification of: `{func_name}` and its synthesized implementation.

=== FUNCTION SPECIFICATION ===
{docstring}
{synth_section}
=== CRITICAL RULES ===
{quantity_instruction}
2. Test categories to cover:
   - Happy path / normal execution matching documented behavior.
   - Edge cases (e.g. None input, empty string, boundary numbers, 0, negative values).
   - Return type and error contract checks strictly according to the docstring.
3. AUTOMATED FUZZ / PROPERTY-BASED TEST (Hypothesis):
   - In addition to the semantic tests, include 1 or 2 property-based test functions named `test_auto_property_...` using `from hypothesis import given, strategies as st, settings`.
   - Use `@settings(max_examples=50, deadline=None)` on each property test.
   - Pass random inputs from appropriate strategies (e.g. `st.integers()`, `st.text()`, `st.none()`) to verify that the implementation does not crash unexpectedly or violate fundamental contracts.
4. NEVER USE OR ASSUME PYTEST FIXTURES. Semantic test functions MUST have zero parameters: `def test_semantic_name():`. Property tests use `@given(...)`.
5. All objects, instances, and inputs MUST be created directly inside each test function.
6. Strictly respect the constructor and method arguments of the synthesized implementation shown above.
{invocation_guidance}
Return ONLY executable Python code inside a single ```python ... ``` block.
"""
        response = self._call_gemini(prompt)
        match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def run_differential_test(self, synthesized_code: str, test_code: str, reference_code: str = "", timeout_sec: int = 25) -> Dict[str, Any]:
        """
        Passaggio 3: Esegue i test generati con pytest su un file temporaneo isolato.
        Se reference_code è fornito, esegue sia la suite sul codice sintetizzato da docstring,
        sia sul codice di riferimento originale (Dual Differential Execution), calcolando l'accordo differenziale.
        """
        def _exec_suite(code_under_test: str) -> Dict[str, Any]:
            full_code = f"""# Auto-generated Round-Trip Differential Test
import pytest
try:
    from hypothesis import given, strategies as st, settings
except ImportError:
    pass

# --- Code Under Test ---
{code_under_test}

# --- Test Suite ---
{test_code}
"""
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                tmp_path = tmp.name
                tmp.write(full_code)

            venv_pytest = os.path.join(ROOT_DIR, ".venv", "Scripts", "pytest.exe")
            pytest_cmd = venv_pytest if os.path.exists(venv_pytest) else "pytest"

            try:
                res = subprocess.run(
                    [pytest_cmd, tmp_path, "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                stdout = res.stdout
                passed_match = re.search(r"(\d+)\s+passed", stdout)
                failed_match = re.search(r"(\d+)\s+failed", stdout)
                error_match = re.search(r"(\d+)\s+error", stdout)

                passed = int(passed_match.group(1)) if passed_match else 0
                failed = int(failed_match.group(1)) if failed_match else 0
                errors = int(error_match.group(1)) if error_match else 0
                total = passed + failed + errors

                pass_rate = round((passed / total) * 100.0, 1) if total > 0 else 0.0

                semantic_passed = len(re.findall(r"test_semantic[^\s]+ PASSED", stdout))
                semantic_failed = len(re.findall(r"test_semantic[^\s]+ (FAILED|ERROR)", stdout))
                auto_passed = len(re.findall(r"test_auto[^\s]+ PASSED", stdout))
                auto_failed = len(re.findall(r"test_auto[^\s]+ (FAILED|ERROR)", stdout))

                # Estrazione per-test del risultato (per confronto differenziale)
                passed_test_names = set(re.findall(r"(test_[^\s]+)\s+PASSED", stdout))

                return {
                    "total_tests": total,
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "pass_rate": pass_rate,
                    "semantic_tests": {
                        "passed": semantic_passed,
                        "failed": semantic_failed,
                        "total": semantic_passed + semantic_failed
                    },
                    "auto_property_tests": {
                        "passed": auto_passed,
                        "failed": auto_failed,
                        "total": auto_passed + auto_failed
                    },
                    "passed_test_names": passed_test_names,
                    "is_success": (res.returncode == 0 and passed > 0),
                    "test_output": stdout[-1500:] if len(stdout) > 1500 else stdout
                }
            except subprocess.TimeoutExpired:
                return {
                    "total_tests": 0, "passed": 0, "failed": 0, "errors": 1,
                    "pass_rate": 0.0, "passed_test_names": set(), "is_success": False, "test_output": "Execution timed out."
                }
            except Exception as e:
                return {
                    "total_tests": 0, "passed": 0, "failed": 0, "errors": 1,
                    "pass_rate": 0.0, "passed_test_names": set(), "is_success": False, "test_output": str(e)
                }
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

        # 1. Esecuzione sul codice sintetizzato da Documentazione (Doc-Driven)
        synth_exec = _exec_suite(synthesized_code)

        # 2. Se è disponibile il codice di riferimento originale (Code-Driven), eseguiamo anche quello
        differential_info = {}
        if reference_code:
            ref_exec = _exec_suite(reference_code)
            # Calcolo dell'accordo differenziale test-per-test
            total_tests = max(synth_exec["total_tests"], ref_exec["total_tests"])
            if total_tests > 0:
                synth_passed = synth_exec.get("passed_test_names", set())
                ref_passed = ref_exec.get("passed_test_names", set())
                # Un test è in accordo se passa su entrambi o fallisce su entrambi
                agreement_count = sum(1 for t in (synth_passed | ref_passed) if (t in synth_passed and t in ref_passed))
                # Se entrambi passano lo stesso test, agreement è positivo
                diff_agreement_rate = round((agreement_count / total_tests) * 100.0, 1)
            else:
                diff_agreement_rate = 0.0

            differential_info = {
                "reference_pass_rate": ref_exec["pass_rate"],
                "reference_passed": ref_exec["passed"],
                "reference_total": ref_exec["total_tests"],
                "differential_agreement_rate": diff_agreement_rate,
                "both_passed_count": len(synth_exec.get("passed_test_names", set()) & ref_exec.get("passed_test_names", set()))
            }
            synth_exec["differential"] = differential_info

        # Pulizia del set non serializzabile in JSON
        synth_exec.pop("passed_test_names", None)
        return synth_exec

    def evaluate_function_roundtrip(self, func_name: str, signature: str, docstring: str, source_code: str = "", num_tests: Optional[int] = None) -> Dict[str, Any]:
        """Esegue l'intero ciclo di valutazione Round-Trip su una singola funzione con Dual Differential Testing."""
        # 1. Sintesi da sola Documentazione
        synth_code = self.synthesize_code_from_doc(func_name, signature, docstring)
        
        # 2. Sintesi/Traduzione Reference dal Codice Sorgente Reale C/C++
        ref_code = ""
        if source_code:
            ref_code = self.synthesize_reference_from_code(func_name, signature, source_code)

        # 3. Generazione della Suite di Test
        test_suite = self.generate_pytest_suite(func_name, docstring, synth_code=synth_code, num_tests=num_tests)
        
        # 4. Esecuzione Differenziale su entrambe le implementazioni
        test_results = self.run_differential_test(synth_code, test_suite, reference_code=ref_code)

        return {
            "function_name": func_name,
            "signature": signature,
            "synthesized_code": synth_code,
            "reference_code": ref_code,
            "test_suite": test_suite,
            "execution": test_results
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Round-Trip Differential Testing: Doc-to-Code Synthesis & Pytest Execution")
    parser.add_argument("-j", "--json", default="results/benchmark_cjson/eval_report_single.json", help="Percorso del file eval_report.json da testare")
    parser.add_argument("-n", "--limit", type=int, default=3, help="Numero di funzioni da sottoporre a test comportamentale (default: 3)")
    parser.add_argument("-t", "--tests-per-func", type=int, default=0, help="Numero di test semantici da generare (default: 0 = adattivo libero a cura di Gemini)")
    args = parser.parse_args()

    json_path = os.path.join(ROOT_DIR, args.json) if not os.path.isabs(args.json) else args.json
    if not os.path.exists(json_path):
        print(f"[ERRORE] File non trovato: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    # Connessione opzionale a benchmark.db per recuperare il source_code reale se assente nel json
    db_conn = None
    try:
        db_path = os.path.join(ROOT_DIR, "dataset", "benchmark.db")
        if os.path.exists(db_path):
            db_conn = sqlite3.connect(db_path)
    except Exception:
        pass

    evaluator = RoundTripEvaluator()
    candidates = eval_data[:args.limit]

    test_mode_str = f"Fisso ({args.tests_per_func} test)" if args.tests_per_func > 0 else "Adattivo Libero (Gemini) + Auto-Property (Hypothesis)"
    print("=" * 65)
    print(f"  ROUND-TRIP DIFFERENTIAL TESTING (Dual Execution)")
    print(f"  Campione: {len(candidates)} funzioni da: {os.path.basename(json_path)}")
    print(f"  Regime Test: {test_mode_str}")
    print(f"  Verifica: Sintesi da Doc vs Reference da Sorgente Reale C/C++")
    print("=" * 65)

    summary_results = []
    num_tests_arg = args.tests_per_func if args.tests_per_func > 0 else None
    for idx, item in enumerate(candidates, 1):
        fname = item["function_name"]
        sig = item["signature"]
        doc = f"{item['generated_summary']}\n{item['generated_doxygen']}"
        source_code = item.get("source_code", "")

        # Fallback al database se source_code non era salvato nel JSON
        if not source_code and db_conn:
            try:
                cur = db_conn.cursor()
                if "id" in item:
                    cur.execute("SELECT source_code FROM benchmark_functions WHERE id=? LIMIT 1", (item["id"],))
                    row = cur.fetchone()
                    if row and row[0]:
                        source_code = row[0]
                if not source_code:
                    cur.execute("SELECT source_code FROM benchmark_functions WHERE function_name=? LIMIT 1", (fname,))
                    row = cur.fetchone()
                    if row and row[0]:
                        source_code = row[0]
            except Exception as e:
                pass

        print(f"\n[{idx}/{len(candidates)}] Dual Testing: {fname}...")
        res = evaluator.evaluate_function_roundtrip(fname, sig, doc, source_code=source_code, num_tests=num_tests_arg)
        exec_res = res["execution"]
        sem = exec_res.get("semantic_tests", {})
        auto = exec_res.get("auto_property_tests", {})
        diff = exec_res.get("differential", {})

        breakdown_str = f" [Sem: {sem.get('passed', 0)}/{sem.get('total', 0)} | Auto: {auto.get('passed', 0)}/{auto.get('total', 0)}]" if sem or auto else ""
        diff_str = f" | Dual Agreement: {diff.get('differential_agreement_rate', 'N/A')}% (Ref Pass: {diff.get('reference_pass_rate', 'N/A')}%)" if diff else ""
        print(f"  -> Pass Rate Doc: {exec_res['pass_rate']}% ({exec_res['passed']}/{exec_res['total_tests']} test passati){breakdown_str}{diff_str}")
        summary_results.append(res)

    if db_conn:
        db_conn.close()

    avg_pass_rate = round(sum(r["execution"]["pass_rate"] for r in summary_results) / len(summary_results), 1) if summary_results else 0.0
    diff_rates = [r["execution"]["differential"]["differential_agreement_rate"] for r in summary_results if "differential" in r["execution"]]
    avg_diff_rate = round(sum(diff_rates) / len(diff_rates), 1) if diff_rates else 0.0

    print("\n" + "=" * 65)
    print(f"  VALUTAZIONE ROUND-TRIP DIFFERENTIAL COMPLETATA!")
    print(f"  Pass Rate Medio Sintesi da Doc (Self-Consistency): {avg_pass_rate}%")
    if diff_rates:
        print(f"  Dual Agreement Medio (Doc vs Reference C/C++ Reale): {avg_diff_rate}%")
    print("=" * 65)

    # Salvataggio dei risultati ed esportazione del grafico
    target_dir = os.path.dirname(json_path)
    output_json = os.path.join(target_dir, "roundtrip_results.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "avg_pass_rate": avg_pass_rate,
            "avg_differential_agreement": avg_diff_rate,
            "results": summary_results
        }, f, indent=2)
    print(f"[OK] Risultati dettagliati salvati in: {output_json}")

    try:
        from utils.plot_roundtrip import generate_roundtrip_charts
        formatted_for_plot = [
            {
                "name": r["function_name"],
                "pass_rate": r["execution"]["pass_rate"],
                "passed": r["execution"]["passed"],
                "total": r["execution"]["total_tests"]
            }
            for r in summary_results
        ]
        out_png = os.path.join(target_dir, "roundtrip_charts.png")
        generate_roundtrip_charts(formatted_for_plot, out_png, avg_pass_rate=avg_pass_rate)
        print(f"[OK] Grafico Round-Trip generato con successo in: {out_png}")
    except Exception as e:
        print(f"[WARN] Impossibile generare il grafico: {e}")


if __name__ == "__main__":
    main()

