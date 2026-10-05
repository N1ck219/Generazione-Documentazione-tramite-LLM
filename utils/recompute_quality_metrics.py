"""
recompute_quality_metrics.py
----------------------------
Ricalcola Actionability, EDR, ECC e METEOR sui report di benchmark gia' salvati in results/benchmark_*/,
senza richiamare nessun LLM, e rigenera report Markdown e grafici che le contengono.

Serve dopo una correzione delle definizioni di queste tre metriche: la documentazione generata, il
Judge e il Round-Trip restano quelli del run originale; cambiano solo i valori deterministici
calcolati dal testo della documentazione e dal sorgente.

  - Actionability: direzione dei parametri solo se esplicita, componente @return basata sul tipo di
    ritorno dell'AST (letto da dataset/benchmark.db), tag @pre/@post letti dal parser.
  - EDR / ECC: None quando non applicabili (nessun ramo di errore / nessuna guardia nel sorgente).

Uso:
  .venv/Scripts/python utils/recompute_quality_metrics.py             # tutti i run in results/
  .venv/Scripts/python utils/recompute_quality_metrics.py -l cjson    # solo results/benchmark_cjson
  .venv/Scripts/python utils/recompute_quality_metrics.py --dry-run   # mostra le variazioni, non scrive
"""

import os
import sys
import json
import glob
import sqlite3
import argparse
from typing import Dict, Any, List, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.benchmark_metrics import (
    parse_doxygen_block,
    calculate_actionability_score,
    calculate_error_documentation_rate,
    calculate_edge_case_coverage,
    calculate_meteor_score,
    generate_benchmark_charts,
)

DB_PATH = os.path.join(ROOT_DIR, "dataset", "benchmark.db")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
MODIFIED_KEYS = ("actionability_score", "error_documentation_score", "edge_case_coverage", "meteor_score")


def load_db_items() -> Dict[str, Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    items = {}
    for row in conn.execute("SELECT id, return_type, parameters FROM benchmark_functions"):
        try:
            params = json.loads(row["parameters"]) if row["parameters"] else []
        except json.JSONDecodeError:
            params = []
        items[row["id"]] = {"return_type": row["return_type"] or "", "parameters": params}
    conn.close()
    return items


def recompute_record(rec: Dict[str, Any], db_items: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Aggiorna rec["metrics"] in place e restituisce i nuovi valori delle tre metriche."""
    doxygen = rec.get("generated_doxygen", "") or ""
    code = rec.get("source_code", "") or ""
    parsed = parse_doxygen_block(doxygen)

    item = db_items.get(rec.get("id"))
    if item is not None:
        formal_params, return_type = item["parameters"], item["return_type"]
    else:
        # Record non piu' presente nel DB (run storici): nomi dei parametri dal report, tipo ignoto
        formal_params = [{"name": n} for n in rec.get("parsed_components", {}).get("ast_params", [])]
        return_type = None

    edr = calculate_error_documentation_rate(code, parsed.get("returns", []), parsed.get("details", ""))
    ecc = calculate_edge_case_coverage(code, doxygen)
    new = {
        "actionability_score": calculate_actionability_score(parsed, formal_params, return_type),
        "error_documentation_score": edr["score"] if edr["has_code_error"] else None,
        "edge_case_coverage": ecc["coverage"] if ecc["code_guard_count"] > 0 else None,
        # METEOR tra Ground Truth e descrizione generata, come in benchmark_eval.py
        "meteor_score": calculate_meteor_score(rec.get("ground_truth", "") or "", rec.get("generated_description", "") or ""),
    }
    rec["metrics"].update(new)
    rec["metrics"].pop("bleurt_score", None)  # metrica rimossa dal benchmark (era una stima euristica)
    return new


def _mean(values: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def regenerate_run_outputs(run_dir: str, mode: str, results: List[Dict[str, Any]]):
    """Rigenera report Markdown e grafici che dipendono dalle tre metriche, come fa benchmark_eval."""
    from utils.benchmark_eval import write_markdown_report
    from utils.plot_advanced_benchmark import generate_all_advanced_charts
    from utils.roundtrip_error_analysis import analyze_roundtrip_errors

    with open(os.path.join(run_dir, "execution_config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    library = cfg.get("library", "")

    chart_path = os.path.join(run_dir, f"eval_charts_{mode}.png")
    generate_benchmark_charts(results, chart_path, library_name=library)
    advanced_paths = generate_all_advanced_charts(
        eval_results=results, run_dir=run_dir, mode_name=mode, library_name=library
    )

    rt_path = os.path.join(run_dir, "roundtrip_results.json")
    roundtrip_summary, rt_error_analysis = None, None
    if os.path.exists(rt_path):
        with open(rt_path, encoding="utf-8") as f:
            roundtrip_summary = json.load(f)
        rt_error_analysis = analyze_roundtrip_errors(roundtrip_summary.get("results", []))
    rt_chart = os.path.join(run_dir, "eval_chart_roundtrip.png")

    write_markdown_report(
        os.path.join(run_dir, f"eval_report_{mode}.md"),
        library,
        mode,
        results,
        chart_filename=os.path.basename(chart_path),
        roundtrip_summary=roundtrip_summary,
        rt_chart_filename=os.path.basename(rt_chart) if roundtrip_summary and os.path.exists(rt_chart) else "",
        reproduction_command=cfg.get("reproduction_command", ""),
        advanced_chart_filenames=[os.path.basename(p) for p in advanced_paths if os.path.exists(p)],
        rt_error_analysis=rt_error_analysis,
    )


def process_report(json_path: str, db_items: Dict[str, Dict[str, Any]], dry_run: bool) -> Optional[Dict[str, Any]]:
    run_dir = os.path.dirname(json_path)
    mode = os.path.basename(json_path)[len("eval_report_"):-len(".json")]
    with open(json_path, encoding="utf-8") as f:
        results = json.load(f)
    if not isinstance(results, list) or not results:
        return None

    before = {k: _mean([r["metrics"].get(k) for r in results]) for k in MODIFIED_KEYS}
    n_edr_before = sum(1 for r in results if r["metrics"].get("error_documentation_score") is not None)
    for rec in results:
        recompute_record(rec, db_items)
    after = {k: _mean([r["metrics"].get(k) for r in results]) for k in MODIFIED_KEYS}
    n_edr = sum(1 for r in results if r["metrics"].get("error_documentation_score") is not None)
    n_ecc = sum(1 for r in results if r["metrics"].get("edge_case_coverage") is not None)

    if not dry_run:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        regenerate_run_outputs(run_dir, mode, results)

    return {"path": os.path.relpath(json_path, ROOT_DIR), "n": len(results), "before": before, "after": after,
            "n_edr": n_edr, "n_ecc": n_ecc, "n_edr_before": n_edr_before}


def fmt(v: Optional[float]) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def require_real_meteor():
    """calculate_meteor_score ripiega in silenzio su 0.5*SBERT + 0.5*ROUGE-L se le risorse NLTK mancano."""
    try:
        from nltk.translate.meteor_score import single_meteor_score
        from nltk.tokenize import word_tokenize
        single_meteor_score(word_tokenize("checks the item"), word_tokenize("verifies the item"))
    except Exception as e:
        sys.exit(f"Risorse NLTK mancanti (punkt_tab, wordnet, omw-1.4): METEOR userebbe il ripiego. {type(e).__name__}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-l", "--library", default=None, help="Cartella results/benchmark_<library> da elaborare (default: tutte)")
    ap.add_argument("--dry-run", action="store_true", help="Calcola e mostra le variazioni senza scrivere nulla")
    args = ap.parse_args()

    pattern = os.path.join(RESULTS_DIR, f"benchmark_{args.library.lower() if args.library else '*'}", "*", "eval_report_*.json")
    paths = sorted(glob.glob(pattern))
    if not paths:
        print("Nessun report trovato.")
        return

    require_real_meteor()
    db_items = load_db_items()
    print(f"{'report':<70} {'n':>3}  {'AS prima->dopo':>16}  {'EDR prima->dopo':>16}  {'ECC prima->dopo':>16}  {'METEOR prima->dopo':>18}")
    for p in paths:
        try:
            info = process_report(p, db_items, args.dry_run)
        except Exception as e:  # un run storico incompleto non deve fermare gli altri
            print(f"{os.path.relpath(p, ROOT_DIR):<70} ERRORE: {type(e).__name__}: {e}")
            continue
        if info is None:
            continue
        b, a = info["before"], info["after"]
        print(f"{info['path']:<70} {info['n']:>3}  "
              f"{fmt(b['actionability_score'])}->{fmt(a['actionability_score']):>7}  "
              f"{fmt(b['error_documentation_score'])}->{fmt(a['error_documentation_score']):>7} (n={info['n_edr']})  "
              f"{fmt(b['edge_case_coverage'])}->{fmt(a['edge_case_coverage']):>7} (n={info['n_ecc']})  "
              f"{fmt(b['meteor_score'])}->{fmt(a['meteor_score']):>7}")
    if args.dry_run:
        print("\n[dry-run] nessun file scritto.")


if __name__ == "__main__":
    main()
