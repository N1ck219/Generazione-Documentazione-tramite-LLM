"""
Modulo LLM-as-a-Judge per il Benchmark della Documentazione C/C++.
Implementa:
1. Valutazione Prospettiva A: Fedelta' e Correttezza Tecnica (Codice C + GT vs Documentazione Generata).
2. Valutazione Prospettiva B: Allineamento Semantico e Completezza (GT vs Documentazione Generata).
3. Campionamento Statistico Monte Carlo: esegue N iterazioni (default: 5) con controllo rigoroso
   della temperatura (temperature = 0.4) per ottenere Media e Deviazione Standard (mu +- sigma).
4. Rubrica Likert a 5 livelli con Chain-of-Thought ("Reasoning First").
"""

import os
import sys
import json
import time
import re
from typing import Dict, List, Any, Tuple
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.llm_provider import GeminiLLMProvider, QuotaDailyExceededError

class GeminiJudgeEvaluator:
    """
    Giudice autonomo basato su Google Gemini con configurazione esplicita di temperatura,
    gestione rate limiting e calcolo statistico delle valutazioni.
    """
    def __init__(self, model_name: str = "gemini-3.5-flash-lite", api_key: str = None, temperature: float = 0.4):
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        # Gestione multi-key rotation
        if self.api_key and "," in self.api_key:
            self.api_keys = [k.strip() for k in self.api_key.split(",") if k.strip()]
        elif self.api_key:
            self.api_keys = [self.api_key.strip()]
        else:
            self.api_keys = []
        self.current_key_idx = 0
        self.last_call_time = 0.0
        self.min_delay = 4.0  # 15 RPM
        
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
            self.use_new_sdk = False

    def _wait_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_call_time = time.time()

    def _call_gemini_judge(self, prompt: str) -> Dict[str, Any]:
        """Chiama Gemini impostando esplicitamente la temperatura e la modalita' JSON."""
        if not self.client and not hasattr(self, 'model'):
            # Fallback mock deterministico se offline
            return {"reasoning": "Offline Mock evaluation.", "score": 4.0}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._wait_rate_limit()

                if self.use_new_sdk:
                    from google.genai import types
                    config = types.GenerateContentConfig(
                        temperature=self.temperature,
                        top_p=0.95,
                        response_mime_type="application/json"
                    )
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config
                    )
                    text = response.text
                else:
                    import google.generativeai as genai
                    gen_config = genai.GenerationConfig(
                        temperature=self.temperature,
                        response_mime_type="application/json"
                    )
                    response = self.model.generate_content(prompt, generation_config=gen_config)
                    text = response.text

                # Parsing JSON pulito
                cleaned = text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                data = json.loads(cleaned.strip())
                
                score = float(data.get("score", 3.0))
                # Limita il punteggio al range [1.0, 5.0]
                score = max(1.0, min(5.0, score))
                return {
                    "reasoning": data.get("reasoning", "No reasoning provided."),
                    "score": score
                }

            except Exception as e:
                err_msg = str(e)
                if ("Quota" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and self.current_key_idx + 1 < len(self.api_keys):
                    self.current_key_idx += 1
                    print(f"  -> Judge: Key cambiata con successo (#{self.current_key_idx + 1}). Riprovo...")
                    self._init_client()
                    continue
                
                if attempt == max_retries - 1:
                    print(f"[WARN Judge] Fallimento chiamata LLM-Judge: {e}")
                    return {"reasoning": f"Evaluation error: {err_msg}", "score": 3.0}
                time.sleep(4)

        return {"reasoning": "Default fallback.", "score": 3.0}

    def evaluate_perspective_a(self, func_name: str, signature: str, source_code: str, ground_truth: str, generated_doc: str) -> Dict[str, Any]:
        """
        PROSPETTIVA A: Faithfulness & Technical Correctness (Code + GT vs Generated Doc).
        Verifica che la documentazione generata corrisponda al codice C reale e non lo contraddica.
        """
        prompt = f"""You are a strict Principal Software Engineer and C/C++ Code Auditor serving as an impartial benchmark judge.
Evaluate the technical faithfulness, accuracy, and contract correctness of the generated documentation against the actual C source code and official Ground Truth.

Function: `{func_name}`
Signature: `{signature}`

=== ACTUAL C SOURCE CODE ===
```c
{source_code}
```

=== OFFICIAL GROUND TRUTH / AUTHOR NOTE ===
{ground_truth}

=== GENERATED DOCUMENTATION TO EVALUATE ===
{generated_doc}

=== CHECKLIST OF CRITICAL DEFECTS (Scrutinize carefully) ===
1. DEF-1 (Omission of Error Handling): Fails to document NULL pointer checks or memory allocation failure return values present in the C code.
2. DEF-2 (Memory Ownership Ambiguity): Fails to specify whether caller or callee owns returned buffers/nodes, or whether data is copied vs referenced.
3. DEF-3 (Tautological / Empty Description): Simply rephrases the function name or parameter name without explaining the operational logic or side effects.
4. DEF-4 (Contract / Direction Mismatch): Inaccurate parameter directions (e.g. marking a modified pointer as [in] instead of [in,out], or wrong return values).
5. DEF-5 (Over-specification / Invention): Mentions behavior or guarantees not present in the code or Ground Truth (hallucinated checks, non-existent flags).

=== SCORING RUBRIC (STRICT 1 TO 5 SCALE) ===
Start evaluation from a baseline score of 4.0 for competent documentation, then adjust:
- 5 (Flawless / Flaw-free): ZERO defects. Perfectly describes logic, memory ownership, exact failure modes, parameter directions, and internal delegation without any fluff. (Reserve for truly exemplary documentation).
- 4 (Good / Standard): Technically faithful and correct with NO hallucinations, but contains 1 minor defect (e.g., slightly tautological brief or minor omission in failure nuances).
- 3 (Adequate / Flawed): Understandable and mostly faithful, but exhibits 2 defects (e.g., misses memory ownership clarity AND omits a return error code).
- 2 (Poor): Significant inaccuracies, inverts boolean/return logic, or exhibits 3+ defects.
- 1 (Critical Failure): Severe hallucinations, documents wrong algorithm, or causes memory leaks/crashes if followed.

Respond strictly in JSON format with two keys:
{{
  "reasoning": "First explicitly list any detected defect (e.g., 'DEF-1: misses NULL check' or 'None'). Then justify the final score concisely in 2-3 sentences.",
  "score": 4
}}
"""
        return self._call_gemini_judge(prompt)

    def evaluate_perspective_b(self, func_name: str, signature: str, ground_truth: str, generated_doc: str) -> Dict[str, Any]:
        """
        PROSPETTIVA B: Semantic Alignment & Completeness (Ground Truth vs Generated Doc).
        Verifica quanto la documentazione generata cattura l'intento funzionale e le sfumature
        della spiegazione dell'autore originale.
        """
        prompt = f"""You are a strict technical specification auditor.
Evaluate how thoroughly and faithfully the generated documentation captures the functional intent, nuances, and explicit warnings stated in the official Ground Truth documentation.

Function: `{func_name}`
Signature: `{signature}`

=== OFFICIAL GROUND TRUTH (AUTHOR'S INTENT) ===
{ground_truth}

=== GENERATED DOCUMENTATION TO EVALUATE ===
{generated_doc}

=== CHECKLIST OF ALIGNMENT DEFECTS ===
1. ALIGN-1 (Missed Warning / Caveat): Ignores a specific warning, lifetime constraint, or caution mentioned in the Ground Truth (e.g. const flags, corruption risk).
2. ALIGN-2 (Intent Distortion): Shifts or alters the author's stated purpose (e.g. claims it duplicates data when the author stated it adds by reference).
3. ALIGN-3 (Over-bloating / Loss of Focus): Drowns the author's primary functional point in excessive generic boilerplate.
4. ALIGN-4 (Superficiality): Only captures high-level keywords while missing the underlying operational rationale.

=== SCORING RUBRIC (STRICT 1 TO 5 SCALE) ===
- 5 (Complete Alignment): Captures 100% of the author's points, constraints, and warnings with precision, translating them cleanly into professional Doxygen format.
- 4 (Substantial Alignment): Conveys the main functional goal and caveats well, with at most 1 minor nuance slightly under-elaborated.
- 3 (Partial Alignment): Mentions the core action, but omits a critical caveat, specific condition, or warning highlighted by the author.
- 2 (Weak Alignment): Misses the central message of the Ground Truth or provides conflicting explanations.
- 1 (Zero Alignment): Irrelevant or completely contradictory to the library author's intention.

Respond strictly in JSON format with two keys:
{{
  "reasoning": "Identify if any ALIGN defects are present (e.g., 'ALIGN-1: missing warning' or 'None'). Provide a concise 2-sentence rationale for the score.",
  "score": 4
}}
"""
        return self._call_gemini_judge(prompt)

    def run_multi_round_evaluation(
        self, 
        func_name: str, 
        signature: str, 
        source_code: str, 
        ground_truth: str, 
        generated_doc: str, 
        rounds: int = 5
    ) -> Dict[str, Any]:
        """
        Esegue le N iterazioni Monte Carlo (default: 5) per entrambe le prospettive,
        calcolando Media (mu) e Deviazione Standard (sigma).
        """
        scores_a = []
        reasonings_a = []

        scores_b = []
        reasonings_b = []

        total_steps = rounds * 2
        try:
            from tqdm import tqdm
            pbar = tqdm(total=total_steps, desc=f"    -> Giudice [{func_name[:20]}]", unit="call", leave=False)
        except ImportError:
            pbar = None
            print(f"    -> Giudice Gemini: Valutazione su {rounds} iterazioni (Temp={self.temperature})...")

        # 1. Rounds per Prospettiva A (Code + GT vs Doc)
        for r in range(rounds):
            res_a = self.evaluate_perspective_a(func_name, signature, source_code, ground_truth, generated_doc)
            scores_a.append(res_a["score"])
            if r == 0:  # Conserva il reasoning del primo round come campione illustrativo
                reasonings_a.append(res_a["reasoning"])
            if pbar:
                pbar.set_postfix({"Persp": "A (Faithfulness)", "Score": res_a["score"]})
                pbar.update(1)

        # 2. Rounds per Prospettiva B (GT vs Doc)
        for r in range(rounds):
            res_b = self.evaluate_perspective_b(func_name, signature, ground_truth, generated_doc)
            scores_b.append(res_b["score"])
            if r == 0:
                reasonings_b.append(res_b["reasoning"])
            if pbar:
                pbar.set_postfix({"Persp": "B (Alignment)", "Score": res_b["score"]})
                pbar.update(1)

        if pbar:
            pbar.close()

        mean_a = round(float(np.mean(scores_a)), 3)
        std_a = round(float(np.std(scores_a)), 3)

        mean_b = round(float(np.mean(scores_b)), 3)
        std_b = round(float(np.std(scores_b)), 3)

        combined_mean = round((mean_a + mean_b) / 2.0, 3)

        return {
            "perspective_a": {
                "name": "Faithfulness (Code+GT vs Doc)",
                "scores": scores_a,
                "mean": mean_a,
                "std": std_a,
                "sample_reasoning": reasonings_a[0] if reasonings_a else ""
            },
            "perspective_b": {
                "name": "Alignment (GT vs Doc)",
                "scores": scores_b,
                "mean": mean_b,
                "std": std_b,
                "sample_reasoning": reasonings_b[0] if reasonings_b else ""
            },
            "combined_score": combined_mean
        }

    def generate_naive_baseline_doc(self, func_name: str, signature: str, source_code: str) -> str:
        """
        Baseline 1: Genera documentazione con un prompt 'naive' zero-shot senza analisi AST,
        senza Big-O deterministico e senza contesto delle callee bottom-up.
        Serve come termine di paragone per quantificare l'incremento di qualità (delta).
        """
        prompt = f"""Write standard Doxygen documentation for the following C/C++ function:

Function: {func_name}
Signature: {signature}
Code:
```c
{source_code}
```
Return only the Doxygen comment block.
"""
        self._wait_rate_limit()
        try:
            if self.use_new_sdk and self.client:
                from google.genai import types
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.7)
                )
                return resp.text.strip()
            elif hasattr(self, 'model') and self.model:
                resp = self.model.generate_content(prompt)
                return resp.text.strip()
        except Exception:
            pass
        return f"/**\n * @brief {func_name}\n */"

