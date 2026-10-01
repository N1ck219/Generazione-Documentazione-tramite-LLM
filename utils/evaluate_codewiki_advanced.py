"""
evaluate_codewiki_advanced.py
-----------------------------
Metriche "avanzate" della pipeline della tesi applicate alla documentazione
CodeWiki di TinyXML-2, con la stessa configurazione usata da utils/benchmark_eval.py:

  - Code Retrieval (MRR, Hit@1/3/5)  stesso corpus della pipeline (function_name+signature
                                      distinti di TinyXML-2), nessuna chiamata LLM
  - CodeBERTScore F1                  microsoft/codebert-base, nessuna chiamata LLM
  - LLM-as-a-Judge                    GeminiJudgeEvaluator, gemini-3.5-flash-lite, T=0.4,
                                      5 round x prospettive A (Faithfulness) e B (Alignment)
  - Round-Trip Differential Testing   RoundTripEvaluator con GeminiLLMProvider (rpm 15)

Non applicabili a CodeWiki (riportate come N/A nel confronto):
  - Param F1 / Return match: richiedono tag @param/@return, assenti nella prosa CodeWiki
  - Hallucination rate: deriva dagli errori del Verifier Doxygen della pipeline

Input : compare_CodeWiki/codewiki_mapped_functions.json + codewiki_metrics_results.json
Output: compare_CodeWiki/codewiki_advanced_results.json  (cache incrementale per funzione)

Ogni step completato viene salvato subito: rilanciando lo script si riprende da dove
si era interrotto, senza ripagare le chiamate gia' fatte. Se il testo CodeWiki di una
funzione cambia, i suoi risultati vengono ricalcolati.

Le righe del DB (firma, codice, GT) sono selezionate con la stessa funzione usata da
benchmark_eval.py --functions, quindi coincidono con quelle valutate dalla pipeline.

Utilizzo:
  .venv/Scripts/python utils/evaluate_codewiki_advanced.py [--steps retrieval,codebert,judge,roundtrip]
                                                           [--rounds 5] [--limit N] [--mock]
"""

import os
import sys
import json
import sqlite3
import hashlib
import argparse
from typing import Dict, List, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.evaluate_codewiki_metrics import group_by_db_function, MAPPED_JSON, OUT_RESULTS, DB_PATH, TARGET_LIBRARY

ADV_RESULTS      = os.path.join(ROOT_DIR, "compare_CodeWiki", "codewiki_advanced_results.json")
ADV_RESULTS_MOCK = os.path.join(ROOT_DIR, "compare_CodeWiki", "codewiki_advanced_results_mock.json")

# Stessa configurazione di utils/benchmark_eval.py
LLM_MODEL         = "gemini-3.5-flash-lite"
JUDGE_TEMPERATURE = 0.4
RPM_LIMIT         = 15
ALL_STEPS         = ["retrieval", "codebert", "judge", "roundtrip"]


def _doc_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _save(cache: Dict, path: str):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        # default=list: il round-trip restituisce alcuni set (es. passed_test_names)
        json.dump(cache, f, ensure_ascii=False, indent=2, default=list)
    os.replace(tmp, path)


def load_codewiki_docs() -> Dict[str, str]:
    """{function_name: testo CodeWiki aggregato} per le funzioni valutate nelle metriche NLP."""
    with open(MAPPED_JSON, encoding="utf-8") as f:
        mapped = json.load(f)
    with open(OUT_RESULTS, encoding="utf-8") as f:
        evaluated = {r["function_name"] for r in json.load(f) if r["evaluated"]}
    groups = group_by_db_function([r for r in mapped if r.get("matched")])
    return {g["db_function_name"]: g["codewiki_doc"] for g in groups if g["db_function_name"] in evaluated}


def load_pipeline_rows(names: List[str]) -> Dict[str, Dict]:
    """Stesse righe DB che benchmark_eval.py usa con --functions (variante .cpp preferita)."""
    from utils.benchmark_eval import get_benchmark_candidates
    rows = get_benchmark_candidates(TARGET_LIBRARY, len(names), function_names=names)
    return {r["function_name"]: r for r in rows}


def load_retrieval_corpus() -> List[Dict[str, str]]:
    """Stesso corpus di retrieval costruito da benchmark_eval.py per una singola libreria."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT DISTINCT function_name, signature FROM benchmark_functions WHERE LOWER(library) = LOWER(?)",
        (TARGET_LIBRARY,),
    ).fetchall()
    conn.close()
    return [{"name": r[0], "signature": r[1] or ""} for r in rows]


# ── Step ──────────────────────────────────────────────────────────────────────

def step_retrieval(cache: Dict, docs: Dict[str, str], path: str):
    from utils.benchmark_metrics import calculate_code_retrieval_mrr
    corpus = load_retrieval_corpus()
    todo = [n for n in docs if "retrieval" not in cache[n]]
    print(f"[retrieval] {len(todo)} funzioni (corpus: {len(corpus)} voci)")
    for name in todo:
        cache[name]["retrieval"] = calculate_code_retrieval_mrr(docs[name], name, corpus)
    _save(cache, path)


def step_codebert(cache: Dict, docs: Dict[str, str], rows: Dict[str, Dict], path: str):
    from utils.benchmark_metrics import calculate_batch_bert_scores
    todo = [n for n in docs if "codebert" not in cache[n]]
    print(f"[codebert] {len(todo)} funzioni")
    if not todo:
        return
    refs = [rows[n]["cleaned_doc"] for n in todo]
    cands = [docs[n] for n in todo]
    scores = calculate_batch_bert_scores(refs, cands, model_type="microsoft/codebert-base")
    for name, s in zip(todo, scores):
        cache[name]["codebert"] = s
    _save(cache, path)


def step_judge(cache: Dict, docs: Dict[str, str], rows: Dict[str, Dict], path: str, rounds: int, mock: bool):
    from utils.llm_judge import GeminiJudgeEvaluator
    judge = GeminiJudgeEvaluator(model_name=LLM_MODEL, api_key=os.getenv("GEMINI_API_KEY"), temperature=JUDGE_TEMPERATURE)
    if mock:
        # Il judge legge comunque GEMINI_API_KEY dall'ambiente: lo forziamo offline
        judge.api_keys, judge.client = [], None
        if hasattr(judge, "model"):
            del judge.model
    todo = [n for n in docs if "judge" not in cache[n]]
    print(f"[judge] {len(todo)} funzioni x {rounds} round x 2 prospettive")
    for i, name in enumerate(todo, 1):
        row = rows[name]
        print(f"  [{i}/{len(todo)}] {name}")
        res = judge.run_multi_round_evaluation(
            func_name=name,
            signature=row["signature"],
            source_code=row["source_code"],
            ground_truth=row["cleaned_doc"],
            generated_doc=docs[name],
            rounds=rounds,
        )
        cache[name]["judge"] = res
        _save(cache, path)


def step_roundtrip(cache: Dict, docs: Dict[str, str], rows: Dict[str, Dict], path: str, mock: bool):
    from src.llm_provider import GeminiLLMProvider, MockLLMProvider
    from utils.roundtrip_eval import RoundTripEvaluator
    if mock:
        llm = MockLLMProvider()
    else:
        llm = GeminiLLMProvider(model_name=LLM_MODEL, api_key=os.getenv("GEMINI_API_KEY"), rpm_limit=RPM_LIMIT)
    evaluator = RoundTripEvaluator(llm_provider=llm)
    if mock:
        # RoundTripEvaluator usa un proprio client Gemini (letto dall'ambiente): nessuna chiamata in mock
        evaluator._call_gemini = lambda prompt: ""
    todo = [n for n in docs if "roundtrip" not in cache[n]]
    print(f"[roundtrip] {len(todo)} funzioni")
    for i, name in enumerate(todo, 1):
        row = rows[name]
        print(f"  [{i}/{len(todo)}] {name}", end="", flush=True)
        res = evaluator.evaluate_function_roundtrip(
            name, row["signature"], docs[name],
            source_code=row["source_code"], library=TARGET_LIBRARY,
        )
        ex = res["execution"]
        diff = ex.get("differential", {}).get("differential_agreement_rate", "N/A")
        print(f"  pass={ex['pass_rate']}%  dual agreement={diff}%")
        cache[name]["roundtrip"] = res
        _save(cache, path)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(steps: List[str], rounds: int = 5, limit: int = None, mock: bool = False) -> str:
    path = ADV_RESULTS_MOCK if mock else ADV_RESULTS
    if not mock and any(s in steps for s in ("judge", "roundtrip")):
        from dotenv import load_dotenv  # carica .env come la pipeline
        load_dotenv()
        key = os.getenv("GEMINI_API_KEY")
        if not key or key == "YOUR_GEMINI_API_KEY_HERE":
            raise SystemExit("[ERRORE] GEMINI_API_KEY non configurata: judge/roundtrip richiedono l'API (o usa --mock).")

    docs = load_codewiki_docs()
    names = sorted(docs)[:limit] if limit else sorted(docs)
    docs = {n: docs[n] for n in names}
    rows = load_pipeline_rows(names)
    missing = [n for n in names if n not in rows]
    if missing:
        print(f"[WARN] Funzioni senza riga nel DB, escluse: {missing}")
        docs = {n: d for n, d in docs.items() if n in rows}

    cache: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
    for name, doc in docs.items():
        h = _doc_hash(doc)
        if cache.get(name, {}).get("doc_hash") != h:
            # Nuova funzione o testo CodeWiki cambiato: si ricalcola tutto
            cache[name] = {"doc_hash": h, "db_id": rows[name]["id"], "codewiki_doc": doc}

    print(f"Funzioni CodeWiki: {len(docs)}  |  step: {', '.join(steps)}  |  output: {os.path.relpath(path, ROOT_DIR)}")
    if "retrieval" in steps:
        step_retrieval(cache, docs, path)
    if "codebert" in steps:
        step_codebert(cache, docs, rows, path)
    if "judge" in steps:
        step_judge(cache, docs, rows, path, rounds, mock)
    if "roundtrip" in steps:
        step_roundtrip(cache, docs, rows, path, mock)
    _save(cache, path)
    return path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Judge, round-trip, retrieval e CodeBERTScore sulla documentazione CodeWiki")
    parser.add_argument("--steps", default=",".join(ALL_STEPS),
                        help=f"Step da eseguire, separati da virgola (default: {','.join(ALL_STEPS)})")
    parser.add_argument("--rounds", type=int, default=5, help="Round per prospettiva del judge (default: 5, come la pipeline)")
    parser.add_argument("--limit", type=int, default=None, help="Solo le prime N funzioni (test rapido)")
    parser.add_argument("--mock", action="store_true",
                        help="Nessuna chiamata API; risultati in un file separato (_mock) per non sporcare quelli reali")
    args = parser.parse_args()
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = set(steps) - set(ALL_STEPS)
    if unknown:
        parser.error(f"step sconosciuti: {sorted(unknown)}")
    path = run(steps, args.rounds, args.limit, args.mock)
    print(f"\nRisultati salvati in: {path}")


if __name__ == "__main__":
    main()
