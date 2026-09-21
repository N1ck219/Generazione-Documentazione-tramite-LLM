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
import ast
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
from src.context_scaffold import (
    infer_library_name,
    format_ast_context_for_prompt,
    get_library_runtime_scaffold,
)
from utils.roundtrip_error_analysis import (
    analyze_roundtrip_errors,
    save_roundtrip_error_report,
)


def classify_function_type(func_name: str, signature: str) -> str:
    """
    Classifica deterministicamente una funzione C/C++ in una delle 3 categorie tassonomiche:
    1. 'Stateful / Object-Graph': Metodi di classe C++ (::) o funzioni che operano su grafi/strutture complesse.
    2. 'Pointer / Buffer-Driven': Funzioni con puntatori a buffer, stringhe mutabili o puntatori void.
    3. 'Stateless / Primitive': Funzioni pure senza stato, operanti su tipi scalari o primitive.
    """
    is_class_method = "::" in func_name
    sig_lower = signature.lower()
    
    # Se è un metodo membro di classe C++ o manipola esplicitamente alberi di nodi (cJSON, XMLNode, AST)
    if is_class_method or any(t in sig_lower for t in ["cjson *", "xmlnode", "xmlattribute", "xmldocument", "xmlhandle"]):
        return "Stateful / Object-Graph"
    
    # Se manipola puntatori di memoria, buffer o I/O
    if any(p in signature for p in ["*", "buf", "char *", "void *", "size_t"]):
        return "Pointer / Buffer-Driven"
    
    # Altrimenti pura/stateless
    return "Stateless / Primitive"


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

    def synthesize_code_from_doc(self, func_name: str, signature: str, docstring: str, library: str = "", context_scaffold: str = "") -> str:
        """
        Passaggio 1: Rigenera il codice Python della funzione basandosi sulla documentazione generata
        e sullo Scaffold di Contesto Esterno (definizioni dei tipi, enum e helper della libreria).
        Supporta sia funzioni C libere che metodi di classi C++ (es. Class::Method).
        """
        is_method = "::" in func_name
        class_name = func_name.split("::")[0] if is_method else None
        method_name = func_name.split("::")[1] if is_method else func_name

        c_instructions = ""
        if is_method:
            c_instructions = f"""
NOTE: The target is a C++ class method `{method_name}` inside class `{class_name}`.
1. Define the class `{class_name}` (or extend/reuse the existing scaffold class).
2. CONSTRUCTOR COMPATIBILITY: Include a flexible constructor:
   `def __init__(self, *args, **kwargs):`
   It MUST safely accept ANY positional and keyword arguments (e.g. `doc`, `name`, `attributes`, `hasBOM`, etc.) without raising TypeError! Provide sensible defaults for all internal attributes.
3. Implement the method `def {method_name}(self, ...):` strictly adhering to the documentation and signature.
4. SIGNATURE ENFORCEMENT: Keep the exact parameter names and order specified in the C++ signature `{signature}`.
5. Also implement minimal getter/setter or state properties if mentioned in the docstring (e.g. `SetAttribute(name, val)`, `Attribute(name)`, `Parse(text)`).
6. OUTPUT POINTER CONVENTION: If the method takes an output pointer parameter (e.g. `int64_t * value`, `const char ** value`, or `type *`), support accepting a mutable container (like a single-element list `value: list`, updating `value[0] = result` or `value.append(result)`).
7. Define any return codes, enums, or constants mentioned in the docstring or context scaffold at module top level or class level.
8. Provide self-contained helper functions/classes if referenced (e.g. if XMLUtil.ToStr or ToInt is used, define a simple mock XMLUtil class).
"""
        else:
            c_instructions = f"""
NOTE: The target is a C free function.
1. Implement the Python function `def {func_name}(...):` strictly matching the inputs, return values, and behavior described in the documentation.
2. SIGNATURE ENFORCEMENT: The function parameters MUST strictly match the exact names and order of `{signature}`. Do NOT rename, reorder, or drop documented parameters.
3. OUTPUT POINTER CONVENTION: If the C function takes an output pointer parameter (e.g. `int * out`, `const char ** parse_end`, `int * count`), support accepting a mutable list container (e.g. `if isinstance(out, list): out[0] = ...`) or returning the appropriate value.
4. STRUCT MOCK TOLERANCE: If defining mock struct/helper classes (e.g. `cJSON`, `printbuffer`), ALWAYS use `def __init__(self, *args, **kwargs)` with `.get()` so constructor calls with different argument naming conventions (e.g. `type` vs `cjson_type`, dict vs object) never raise TypeError or AttributeError.
5. Define any constants, enums, or error codes mentioned in the documentation or context scaffold at the module top level.
"""

        context_section = ""
        if context_scaffold:
            context_section = f"""
=== EXTERNAL CONTEXT & ENVIRONMENT SPECIFICATIONS ===
The target function belongs to library `{library or 'C/C++ Component'}`.
Here are the relevant type definitions, enums, struct members, and constants extracted from its header:
{context_scaffold}
Use the struct fields, constants, and return codes defined above to satisfy callers and unit tests.
"""

        prompt = f"""You are an expert Software Engineer writing self-contained Python code strictly based on technical documentation.
Do not invent features not described in the docstring.

Target Symbol: `{func_name}`
C/C++ Signature: `{signature}`

=== TECHNICAL DOCUMENTATION (SPECIFICATION) ===
{docstring}
{context_section}
=== IMPLEMENTATION REQUIREMENTS ===
{c_instructions}
- Ensure the code is 100% self-contained, syntactically valid Python 3.
- STRICTLY FORBIDDEN: Do NOT import or use `ctypes` or `ctypes.CDLL(None)`. Implement pure Python logic or pure Python mocks for memory allocation (e.g. bytearray or integer IDs).
- Return ONLY valid Python code inside a single ```python ... ``` block without conversational filler.
"""
        response = self._call_gemini(prompt)
        match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
        code = match.group(1).strip() if match else response.strip()

        # Validazione sintattica con ast.parse
        try:
            ast.parse(code)
            return code
        except SyntaxError as e:
            # Tentativo di recupero tramite LLM fornendo l'errore di sintassi
            fix_prompt = f"""The following Python code has a SyntaxError: {e}.
Please fix the syntax error and return the corrected, complete, self-contained Python code in a single ```python ... ``` block.

Code:
{code}
"""
            fixed_response = self._call_gemini(fix_prompt)
            fixed_match = re.search(r"```python\s*(.*?)\s*```", fixed_response, re.DOTALL)
            fixed_code = fixed_match.group(1).strip() if fixed_match else fixed_response.strip()
            try:
                ast.parse(fixed_code)
                return fixed_code
            except SyntaxError:
                return code

    def synthesize_reference_from_code(self, func_name: str, signature: str, source_code: str, library: str = "", context_scaffold: str = "") -> str:
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

        context_section = ""
        if context_scaffold:
            context_section = f"""
=== EXTERNAL CONTEXT & ENVIRONMENT SPECIFICATIONS ===
Library: `{library or 'C/C++ Component'}`
Type definitions, enums, struct members, and macros from header:
{context_scaffold}
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
{context_section}
=== IMPLEMENTATION REQUIREMENTS ===
{c_instructions}
- Ensure the code is 100% self-contained, syntactically valid Python 3.
- STRICTLY FORBIDDEN: Do NOT import or use `ctypes` or `ctypes.CDLL(None)`. Implement pure Python logic or pure Python mocks for memory allocation.
- Return ONLY valid Python code inside a single ```python ... ``` block without conversational filler.
"""
        response = self._call_gemini(prompt)
        match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
        code = match.group(1).strip() if match else response.strip()

        try:
            ast.parse(code)
            return code
        except SyntaxError as e:
            fix_prompt = f"""The following Python code has a SyntaxError: {e}.
Please fix the syntax error and return the corrected, complete, self-contained Python code in a single ```python ... ``` block.

Code:
{code}
"""
            fixed_response = self._call_gemini(fix_prompt)
            fixed_match = re.search(r"```python\s*(.*?)\s*```", fixed_response, re.DOTALL)
            fixed_code = fixed_match.group(1).strip() if fixed_match else fixed_response.strip()
            try:
                ast.parse(fixed_code)
                return fixed_code
            except SyntaxError:
                return code

    def generate_pytest_suite(self, func_name: str, signature: str, docstring: str, library: str = "", context_scaffold: str = "", num_tests: Optional[int] = None) -> str:
        """
        Passaggio 2: Genera una suite di test Pytest esaustiva derivata dai contratti
        specificati nella documentazione tecnica e dalle definizioni AST dello scaffold (Pure Black-Box Testing).
        """
        is_method = "::" in func_name
        class_name = func_name.split("::")[0] if is_method else None
        method_name = func_name.split("::")[1] if is_method else func_name

        invocation_guidance = ""
        if is_method:
            invocation_guidance = f"""
- The target is a class method `{method_name}` of `{class_name}`.
- ISOLATED UNIT TESTING: Instantiate the target object `{class_name}` directly: `obj = {class_name}()` or `obj = {class_name}(...)` using primitive test arguments. Do NOT construct complex multi-object graphs or parse documents from other classes unless strictly necessary.
- BLACK-BOX RULE: Test ONLY public documented behavior, return values, and error contracts.
- DO NOT access or assert on private internal fields (e.g. NEVER assert `obj._attributes`, `obj.child`, `obj.valuestring`, etc.), as internal representations may vary across implementations.
- If the method takes an output pointer parameter (e.g. `const char ** value`), pass a mutable list `val = [None]` and verify the assigned result via `val[0]`.
"""
        else:
            invocation_guidance = f"""
- The target is a free function `{func_name}`.
- Call `{func_name}(...)` directly inside the tests matching the documented signature arguments.
- STRING AND BUFFER ARGUMENTS: If the function accepts C string/buffer pointers (e.g. `const char *`, `sds`, `bytes`), pass standard Python strings or bytes matching the docstring specification (e.g. `"hello"` or `b"hello"`).
- If the function accepts an output pointer parameter (e.g. `int * out` or `const char ** return_parse_end`), pass a mutable list `out = [0]` or `out = [None]` to receive the result.
- For struct/buffer parameters (e.g. `cJSON *`, `printbuffer *`, `http_parser *`), instantiate or use standard objects/constructors if needed.
"""

        if num_tests and num_tests > 0:
            quantity_instruction = f"1. Write exactly {num_tests} standalone pytest test functions (named `test_semantic_1_...`, `test_semantic_2_...`, etc.)."
        else:
            quantity_instruction = """1. ADAPTIVE TEST COUNT: Decide autonomously how many tests are needed (typically between 4 and 10) to thoroughly cover the specification without redundancy.
   - Name each standard semantic test starting with `test_semantic_...`."""

        context_section = ""
        if context_scaffold:
            context_section = f"""
=== LIBRARY DEFINITIONS & CONSTANTS ===
Library: `{library or 'C/C++ Component'}`
{context_scaffold}
Use the documented public constants or enum return codes from above when verifying return values in test assertions.
"""

        prompt = f"""You are a Senior QA Automation & Verification Engineer writing a comprehensive pytest test suite.
You are given the specification and C/C++ signature of: `{func_name}`.

=== FUNCTION SPECIFICATION (DOCUMENTATION) ===
Target Symbol: `{func_name}`
C/C++ Signature: `{signature}`

{docstring}
{context_section}
=== CRITICAL RULES ===
{quantity_instruction}
2. Test categories to cover:
   - Happy path / normal execution matching documented behavior.
   - Edge cases (e.g. None input, empty string, boundary numbers, 0, negative values).
   - Return type and error contract checks strictly according to the docstring.
3. EXCEPTION HANDLING & CONTRACT STRICTNESS (ANTI-DID-NOT-RAISE RULE):
   - NEVER assert that a function raises an exception (e.g. NEVER use `with pytest.raises(...)`) unless the documentation EXPLICITLY states that it raises an exception, throws, or aborts.
   - If the function documentation specifies that invalid input returns an error code (e.g. -1, False, NULL, None, or a specific enum), test that it RETURNS that error value: `assert result == ...` or `assert result is None`. Do NOT expect it to raise an exception!
4. SIGNATURE ENFORCEMENT:
   - When calling `{func_name}`, you MUST strictly match the exact parameter names, types, and order from `{signature}`.
   - Do NOT pass invented arguments or miss documented positional arguments.
5. AUTOMATED FUZZ / PROPERTY-BASED TEST (Hypothesis):
   - In addition to the semantic tests, include 1 or 2 property-based test functions named `test_auto_property_...` using `from hypothesis import given, strategies as st, settings`.
   - Use `@settings(max_examples=50, deadline=None)` on each property test.
   - Pass random inputs from appropriate strategies (e.g. `st.integers()`, `st.text()`, `st.none()`).
   - If using `st.floats()`, NEVER pass `allow_inf=False` (it is deprecated/invalid in modern Hypothesis). Use `allow_infinity=False` or simply `st.floats(allow_nan=False, allow_infinity=False)`.
6. NEVER USE OR ASSUME PYTEST FIXTURES. Semantic test functions MUST have zero parameters: `def test_semantic_name():`. Property tests use `@given(...)`.
7. DO NOT IMPORT the function or class from any external module (e.g. NEVER write `from implementation import ...` or `import implementation`). The code under test will be injected automatically into the global scope.
8. STRICTLY FORBIDDEN: DO NOT import or use `ctypes` or `ctypes.CDLL(None)` in the test suite. All mocks and test inputs must be pure Python objects/primitives.
9. All objects, instances, and inputs MUST be created directly inside each test function.
10. PURE BLACK-BOX TESTING: Test strictly through the public interface, parameters, and return values. Do NOT test internal private variables or mock object properties.
{invocation_guidance}
Return ONLY executable Python code inside a single ```python ... ``` block.
"""
        response = self._call_gemini(prompt)
        match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
        raw_test = match.group(1).strip() if match else response.strip()
        # Rimuove import errati generati dal modello (es. from implementation import ..., import implementation)
        cleaned_lines = []
        for line in raw_test.splitlines():
            if re.match(r"^\s*(from|import)\s+implementation\b", line):
                continue
            # Sostituisce eventuali allow_inf= con allow_infinity= per robustezza
            line = re.sub(r"\ballow_inf\s*=", "allow_infinity=", line)
            # Rimuove parametrizzazioni errate su st.text con argomenti non supportati se presenti
            cleaned_lines.append(line)
        cleaned_test = "\n".join(cleaned_lines).strip()

        try:
            ast.parse(cleaned_test)
            return cleaned_test
        except SyntaxError as e:
            fix_prompt = f"""The following pytest test suite has a SyntaxError: {e}.
Please fix the syntax error and return the corrected, complete Python test code in a single ```python ... ``` block.

Code:
{cleaned_test}
"""
            fixed_response = self._call_gemini(fix_prompt)
            fixed_match = re.search(r"```python\s*(.*?)\s*```", fixed_response, re.DOTALL)
            fixed_test = fixed_match.group(1).strip() if fixed_match else fixed_response.strip()
            fixed_lines = [re.sub(r"\ballow_inf\s*=", "allow_infinity=", l) for l in fixed_test.splitlines() if not re.match(r"^\s*(from|import)\s+implementation\b", l)]
            return "\n".join(fixed_lines).strip()

    def run_differential_test(self, synthesized_code: str, test_code: str, reference_code: str = "", runtime_scaffold: str = "", timeout_sec: int = 25) -> Dict[str, Any]:
        """
        Passaggio 3: Esegue i test generati con pytest su un file temporaneo isolato.
        Inietta lo scaffold runtime prima del codice sintetizzato/reference per prevenire NameError.
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

# --- External Environment & Runtime Scaffold Mocks ---
{runtime_scaffold}

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

    def evaluate_function_roundtrip(self, func_name: str, signature: str, docstring: str, source_code: str = "", library: str = "", num_tests: Optional[int] = None) -> Dict[str, Any]:
        """Esegue l'intero ciclo di valutazione Round-Trip su una singola funzione con Dual Differential Testing e Context Scaffold."""
        # 0. Risoluzione della libreria e dello Scaffold di Contesto Esterno
        inferred_lib = infer_library_name(func_name, signature, given_library=library)
        ast_ctx = format_ast_context_for_prompt(inferred_lib, func_name, root_dir=ROOT_DIR)
        runtime_scaff = get_library_runtime_scaffold(inferred_lib)

        # 1. Sintesi da sola Documentazione + Contesto Esterno AST
        synth_code = self.synthesize_code_from_doc(func_name, signature, docstring, library=inferred_lib, context_scaffold=ast_ctx)
        
        # 2. Sintesi/Traduzione Reference dal Codice Sorgente Reale C/C++ + Contesto Esterno AST
        ref_code = ""
        if source_code:
            ref_code = self.synthesize_reference_from_code(func_name, signature, source_code, library=inferred_lib, context_scaffold=ast_ctx)

        # 3. Generazione della Suite di Test Black-Box (basata su docstring, signature e costanti esterne)
        test_suite = self.generate_pytest_suite(func_name, signature, docstring, library=inferred_lib, context_scaffold=ast_ctx, num_tests=num_tests)
        
        # 4. Esecuzione Differenziale su entrambe le implementazioni (con Runtime Mock Scaffold iniettato)
        test_results = self.run_differential_test(synth_code, test_suite, reference_code=ref_code, runtime_scaffold=runtime_scaff)

        # 5. Tassonomia della funzione
        category = classify_function_type(func_name, signature)

        return {
            "function_name": func_name,
            "library": inferred_lib,
            "signature": signature,
            "function_type": category,
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
    parser.add_argument("-o", "--output-suffix", default="", help="Suffisso per i file di output (es. 'single' o 'multiagent')")
    parser.add_argument("-r", "--random", action="store_true", help="Campionamento casuale uniforme tra le funzioni del file")
    parser.add_argument("-s", "--seed", type=int, default=None, help="Seed per la riproducibilità del campionamento casuale")
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
    if args.random:
        import random
        rng = random.Random(args.seed) if args.seed is not None else random.Random(42)
        sample_size = min(args.limit, len(eval_data))
        candidates = rng.sample(eval_data, sample_size)
    else:
        candidates = eval_data[:args.limit]

    test_mode_str = f"Fisso ({args.tests_per_func} test)" if args.tests_per_func > 0 else "Adattivo Libero (Gemini) + Auto-Property (Hypothesis)"
    print("=" * 65)
    print(f"  ROUND-TRIP DIFFERENTIAL TESTING (Dual Execution)")
    print(f"  Campione: {len(candidates)} funzioni da: {os.path.basename(json_path)}")
    print(f"  Regime Test: {test_mode_str}")
    print(f"  Verifica: Sintesi da Doc vs Reference da Sorgente Reale C/C++ (con Context Scaffold)")
    print("=" * 65)

    summary_results = []
    num_tests_arg = args.tests_per_func if args.tests_per_func > 0 else None
    for idx, item in enumerate(candidates, 1):
        fname = item["function_name"]
        sig = item["signature"]
        doc = f"{item['generated_summary']}\n{item['generated_doxygen']}"
        source_code = item.get("source_code", "")
        lib_name = item.get("library", "")

        # Fallback al database se source_code o library non erano salvati nel JSON
        if db_conn:
            try:
                cur = db_conn.cursor()
                if "id" in item:
                    cur.execute("SELECT source_code, library FROM benchmark_functions WHERE id=? LIMIT 1", (item["id"],))
                    row = cur.fetchone()
                    if row:
                        if not source_code and row[0]:
                            source_code = row[0]
                        if not lib_name and row[1]:
                            lib_name = row[1]
                if not source_code:
                    cur.execute("SELECT source_code, library FROM benchmark_functions WHERE function_name=? LIMIT 1", (fname,))
                    row = cur.fetchone()
                    if row:
                        if not source_code and row[0]:
                            source_code = row[0]
                        if not lib_name and row[1]:
                            lib_name = row[1]
            except Exception:
                pass

        print(f"\n[{idx}/{len(candidates)}] Dual Testing: {fname} (Lib: {lib_name or 'Auto'})...")
        res = evaluator.evaluate_function_roundtrip(fname, sig, doc, source_code=source_code, library=lib_name, num_tests=num_tests_arg)
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

    # Analisi diagnostica delle tipologie di errore
    error_analysis = analyze_roundtrip_errors(summary_results)

    # Salvataggio dei risultati ed esportazione del grafico
    target_dir = os.path.dirname(json_path)
    suffix = f"_{args.output_suffix}" if args.output_suffix else ""
    output_json = os.path.join(target_dir, f"roundtrip_results{suffix}.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "avg_pass_rate": avg_pass_rate,
            "avg_differential_agreement": avg_diff_rate,
            "error_analysis": {
                "summary": error_analysis["summary"],
                "categories": error_analysis["categories"],
                "subtypes": error_analysis["subtypes"]
            },
            "results": summary_results
        }, f, indent=2)
    print(f"[OK] Risultati dettagliati salvati in: {output_json}")

    # Salva report diagnostico errori in formato Markdown
    error_report_path = os.path.join(target_dir, f"roundtrip_error_report{suffix}.md")
    save_roundtrip_error_report(
        error_analysis,
        output_md_path=error_report_path,
        title=f"Round-Trip Error Diagnostic Report{f' ({args.output_suffix})' if args.output_suffix else ''}"
    )
    print(f"[OK] Report diagnostico errori salvato in: {error_report_path}")

    # Salva anche il file delle impostazioni del roundtrip
    rt_config_path = os.path.join(target_dir, f"roundtrip_config{suffix}.json")
    with open(rt_config_path, "w", encoding="utf-8") as f:
        json.dump({
            "json_source": args.json,
            "limit": args.limit,
            "tests_per_func": args.tests_per_func,
            "output_suffix": args.output_suffix,
            "avg_pass_rate": avg_pass_rate,
            "avg_differential_agreement": avg_diff_rate
        }, f, indent=2)

    # Statistiche disaggregate per categoria tassonomica
    cat_stats = {}
    for r in summary_results:
        c = r.get("function_type", "Stateless / Primitive")
        if c not in cat_stats:
            cat_stats[c] = {"doc_rates": [], "diff_rates": []}
        cat_stats[c]["doc_rates"].append(r["execution"]["pass_rate"])
        if "differential" in r["execution"]:
            cat_stats[c]["diff_rates"].append(r["execution"]["differential"]["differential_agreement_rate"])

    if cat_stats:
        print("\n  ANALISI DISAGGREGATA PER CATEGORIA:")
        for c, st in cat_stats.items():
            avg_d = round(sum(st["doc_rates"]) / len(st["doc_rates"]), 1) if st["doc_rates"] else 0.0
            avg_df = round(sum(st["diff_rates"]) / len(st["diff_rates"]), 1) if st["diff_rates"] else 0.0
            print(f"  - [{c}] ({len(st['doc_rates'])} func): Doc Pass: {avg_d}% | Dual Agreement: {avg_df}%")

    if error_analysis.get("categories"):
        print("\n  DIAGNOSTICA TIPOLOGIE DI ERRORE RISCONTRATE:")
        for cat_info in error_analysis["categories"]:
            print(f"  - {cat_info['category']}: {cat_info['count']} fallimenti ({cat_info['percentage']}%)")

    try:
        from utils.plot_roundtrip import generate_roundtrip_charts
        formatted_for_plot = [
            {
                "name": r["function_name"],
                "function_type": r.get("function_type", "Stateless / Primitive"),
                "pass_rate": r["execution"]["pass_rate"],
                "diff_agreement": r["execution"].get("differential", {}).get("differential_agreement_rate", 0.0),
                "passed": r["execution"]["passed"],
                "total": r["execution"]["total_tests"]
            }
            for r in summary_results
        ]
        out_png = os.path.join(target_dir, f"eval_chart_roundtrip{suffix}.png")
        generate_roundtrip_charts(
            formatted_for_plot,
            out_png,
            avg_pass_rate=avg_pass_rate,
            avg_differential_agreement=avg_diff_rate
        )
        print(f"[OK] Grafico Round-Trip generato con successo in: {out_png}")
    except Exception as e:
        print(f"[WARN] Impossibile generare il grafico Round-Trip: {e}")

    # Genera grafico diagnostico dedicato agli errori
    try:
        from utils.plot_roundtrip_errors import generate_roundtrip_error_charts
        err_chart_name = f"eval_chart_roundtrip_errors{suffix}.png"
        err_chart_path = os.path.join(target_dir, err_chart_name)
        generate_roundtrip_error_charts(error_analysis, err_chart_path)
        print(f"[OK] Grafico Diagnostico Errori generato in: {err_chart_path}")

        # Riscrivi il report markdown con l'immagine inclusa
        save_roundtrip_error_report(
            error_analysis,
            output_md_path=error_report_path,
            title=f"Round-Trip Error Diagnostic Report{f' ({args.output_suffix})' if args.output_suffix else ''}",
            chart_filename=err_chart_name
        )
    except Exception as e:
        print(f"[WARN] Impossibile generare il grafico degli errori: {e}")


if __name__ == "__main__":
    main()

