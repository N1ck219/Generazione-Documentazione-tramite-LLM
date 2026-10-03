"""
compare_codewiki.py
-------------------
Punto di ingresso unico del confronto  documentazione CodeWiki  vs  pipeline della tesi.

Per ogni libreria scelta (default: tutte quelle con documentazione CodeWiki in
compare_CodeWiki/<Libreria>/ e righe in dataset/benchmark.db) esegue in sequenza:

  1. parse     mappa la documentazione CodeWiki sulle funzioni del benchmark.db
               (utils/parse_codewiki_to_benchmark.py)
  2. metrics   metriche NLP/statiche di CodeWiki vs Ground Truth
               (utils/evaluate_codewiki_metrics.py)
  3. pipeline  genera la documentazione con la pipeline della tesi (multi-agente) e calcola
               tutti i benchmark: NLP, judge, retrieval, CodeBERTScore, round-trip
               (utils/benchmark_eval.py). Riprende da dove si era interrotto: le funzioni
               gia' presenti nei run in results/ non vengono rigenerate (--force-pipeline per
               rifarle).
  4. advanced  judge, round-trip, retrieval e CodeBERTScore sulla documentazione CodeWiki,
               con la stessa configurazione della pipeline
               (utils/evaluate_codewiki_advanced.py, cache incrementale)
  5. compare   grafici e report del confronto, piu' un riepilogo tra librerie
               (utils/plot_codewiki_comparison.py)

Output: compare_CodeWiki/<Libreria>/ (mapping, metriche, grafici, codewiki_vs_pipeline_report.md)
e compare_CodeWiki/SUMMARY.md (riepilogo di tutte le librerie).

Esempi:
  .venv/Scripts/python compare_codewiki.py                    # tutte le librerie, tutti gli step
  .venv/Scripts/python compare_codewiki.py -l cJSON sds       # solo alcune librerie
  .venv/Scripts/python compare_codewiki.py --list             # librerie disponibili
  .venv/Scripts/python compare_codewiki.py --dry-run          # mostra il piano senza eseguire
  .venv/Scripts/python compare_codewiki.py -l cJSON --steps parse,metrics   # solo la parte offline
  .venv/Scripts/python compare_codewiki.py --pipeline-scope codewiki        # pipeline solo sulle
                                                              # funzioni documentate da CodeWiki

Scope della pipeline (--pipeline-scope):
  all       (default) documenta con la pipeline tutte le funzioni della libreria con Ground Truth;
            il confronto usa poi l'intersezione con le funzioni documentate da CodeWiki.
  codewiki  documenta solo le funzioni che CodeWiki documenta (meno chiamate API).

Gli step "pipeline" e "advanced" usano l'API Gemini (GEMINI_API_KEY in .env). Con --mock non
viene fatta nessuna chiamata: lo step "pipeline" e' saltato (un run finto inquinerebbe i risultati
reali in results/) e "advanced" scrive in un file separato (_mock).
"""

import os
import sys
import time
import json
import math
import argparse
import subprocess
import traceback
from typing import Dict, List, Optional

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.codewiki_config import (
    COMPARE_ROOT,
    DB_PATH,
    db_libraries,
    discover_libraries,
    lib_paths,
    resolve_library,
)

ALL_STEPS = ["parse", "metrics", "pipeline", "advanced", "compare"]
API_STEPS = {"pipeline", "advanced"}
DEFAULT_BATCH_SIZE = 12


# ── Utilita' ──────────────────────────────────────────────────────────────────

def banner(text: str, char: str = "="):
    print("\n" + char * 70)
    print(f"  {text}")
    print(char * 70)


def db_function_names(library: str) -> List[str]:
    """Nomi unici delle funzioni della libreria che hanno un Ground Truth nel DB."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT DISTINCT function_name FROM benchmark_functions "
            "WHERE LOWER(library) = LOWER(?) AND length(cleaned_doc) > 0 ORDER BY function_name",
            (library,),
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def read_function_list(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def split_batches(names: List[str], batch_size: int) -> List[List[str]]:
    """Batch di dimensione bilanciata (nessun batch da una sola funzione se evitabile)."""
    if not names:
        return []
    n_batches = max(1, math.ceil(len(names) / batch_size))
    size = math.ceil(len(names) / n_batches)
    return [names[i:i + size] for i in range(0, len(names), size)]


def require_api_key():
    """Interrompe subito se manca la chiave Gemini: senza, benchmark_eval ripiegherebbe sul Mock."""
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT_DIR, ".env"))
    except ImportError:
        pass
    key = os.getenv("GEMINI_API_KEY")
    if not key or key == "YOUR_GEMINI_API_KEY_HERE":
        raise SystemExit(
            "[ERRORE] GEMINI_API_KEY non configurata (file .env o variabile d'ambiente).\n"
            "  Gli step 'pipeline' e 'advanced' richiedono l'API Gemini.\n"
            "  Usa --steps parse,metrics,compare per la sola parte offline, oppure --mock."
        )


# ── Step ──────────────────────────────────────────────────────────────────────

def step_parse(library: str, args) -> Optional[str]:
    from utils.parse_codewiki_to_benchmark import run
    if run(library) is None:
        raise RuntimeError("parsing CodeWiki fallito")
    return "ok"


def step_metrics(library: str, args) -> Optional[str]:
    from utils.evaluate_codewiki_metrics import run
    # I grafici si generano nello step 'compare', dopo pipeline e metriche avanzate
    if not run(library, no_bert=args.no_bert, no_plots=True):
        raise RuntimeError("metriche CodeWiki fallite")
    return "ok"


def pipeline_targets(library: str, args) -> List[str]:
    """Funzioni da documentare con la pipeline (esclude quelle gia' presenti nei run)."""
    paths = lib_paths(library)
    if args.pipeline_scope == "all":
        wanted = db_function_names(library)
    else:
        wanted = read_function_list(paths.function_list)
        if not wanted:
            raise RuntimeError(f"elenco funzioni CodeWiki assente o vuoto ({paths.function_list}): "
                               "esegui prima lo step 'metrics'")
    if args.force_pipeline:
        return wanted
    from utils.plot_codewiki_comparison import load_pipeline_records
    done = set(load_pipeline_records(library, None, args.mode))
    return [n for n in wanted if n not in done]


def _has_judge_fallback(obj) -> bool:
    """True se nel report compaiono risposte di ripiego del judge (quota API esaurita o errore)."""
    if isinstance(obj, dict):
        return any(_has_judge_fallback(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_judge_fallback(v) for v in obj)
    if isinstance(obj, str):
        low = obj.lower()
        return "default fallback" in low or "evaluation error" in low or (
            "resource_exhausted" in low and "429" in low)
    return False


JUDGE_KEYS = ("judge_score_a", "judge_std_a", "judge_score_b", "judge_std_b", "judge_combined")
MAX_DEGRADED_FRACTION = 0.6


def quarantine_if_degraded(library: str, before: set) -> Optional[str]:
    """
    Controlla il run appena creato in cerca di punteggi di ripiego del judge (chiamate fallite,
    di solito per quota API esaurita: "Default fallback." / "Evaluation error", punteggio 3.0).
      - pochi record toccati (<= 60%): si tolgono solo i punteggi del judge di quei record
        (restano documentazione, metriche NLP e round-trip) e si segnala "judge_invalid";
      - molti record toccati: il report intero e' inaffidabile, viene rinominato .invalid e le sue
        funzioni verranno rigenerate al prossimo lancio.
    Restituisce il percorso del run scartato, altrimenti None.
    """
    base = os.path.join(ROOT_DIR, "results", f"benchmark_{library.lower()}")
    if not os.path.isdir(base):
        return None
    for d in sorted(set(os.listdir(base)) - before):
        report = os.path.join(base, d, "eval_report_multiagent.json")
        if not (d.startswith("run_") and os.path.exists(report)):
            continue
        with open(report, encoding="utf-8") as f:
            data = json.load(f)
        affected = [r for r in data if _has_judge_fallback(r)]
        if not affected:
            continue
        latest = os.path.join(base, "latest", "eval_report_multiagent.json")
        if len(affected) / max(len(data), 1) > MAX_DEGRADED_FRACTION:
            os.replace(report, report + ".invalid")
            if os.path.exists(latest):
                os.replace(latest, latest + ".invalid")
            return os.path.join(base, d)
        for r in affected:
            for k in JUDGE_KEYS:
                r.get("metrics", {}).pop(k, None)
            r["judge_invalid"] = True
        for path in (report, latest):
            if os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[WARN] {library}: judge con chiamate fallite su {len(affected)}/{len(data)} funzioni "
              f"({', '.join(r['function_name'] for r in affected)}): punteggi del judge esclusi, "
              "resto del run mantenuto.")
    return None


def step_pipeline(library: str, args) -> Optional[str]:
    if args.mock:
        return "saltato (--mock: un run finto inquinerebbe results/)"
    paths = lib_paths(library)
    targets = pipeline_targets(library, args)
    if not targets:
        return "nulla da fare (tutte le funzioni gia' documentate dalla pipeline)"

    batches = split_batches(targets, args.batch_size)
    print(f"Funzioni da documentare con la pipeline ({args.mode}): {len(targets)} "
          f"in {len(batches)} batch  [scope: {args.pipeline_scope}]")

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    failed = 0
    for i, batch in enumerate(batches, 1):
        list_file = paths.pipeline_function_list
        with open(list_file, "w", encoding="utf-8") as f:
            f.write(f"# Funzioni {library} da documentare con la pipeline (batch {i}/{len(batches)}, "
                    f"generato da compare_codewiki.py)\n")
            f.write("\n".join(batch) + "\n")
        cmd = [sys.executable, os.path.join(ROOT_DIR, "utils", "benchmark_eval.py"),
               "-l", library, "-m", args.mode, "--functions", list_file,
               "--roundtrip" if not args.no_roundtrip else "--no-roundtrip"]
        banner(f"[{library}] pipeline: batch {i}/{len(batches)} ({len(batch)} funzioni)", "-")
        base = os.path.join(ROOT_DIR, "results", f"benchmark_{library.lower()}")
        before = set(os.listdir(base)) if os.path.isdir(base) else set()
        rc = subprocess.run(cmd, cwd=ROOT_DIR, env=env).returncode
        bad = quarantine_if_degraded(library, before) if rc == 0 else None
        if bad:
            raise RuntimeError(
                f"il run {os.path.relpath(bad, ROOT_DIR)} contiene punteggi di ripiego del judge "
                "(quota API probabilmente esaurita): report scartato (.invalid), "
                "rilancia quando la quota si e' ripristinata")
        if rc != 0:
            failed += 1
            print(f"[ERRORE] benchmark_eval.py terminato con codice {rc} sul batch {i}/{len(batches)}. "
                  "I batch completati sono salvati: rilanciando si riprende da qui.")
            break
    if failed:
        raise RuntimeError("pipeline interrotta (riesegui per riprendere dai batch mancanti)")
    return f"{len(targets)} funzioni documentate"


def step_advanced(library: str, args) -> Optional[str]:
    from utils.evaluate_codewiki_advanced import run, ALL_STEPS as ADV_STEPS
    path = run(library, ADV_STEPS, rounds=args.rounds, mock=args.mock)
    return os.path.relpath(path, ROOT_DIR)


def step_compare(library: str, args) -> Optional[str]:
    from utils.plot_codewiki_comparison import generate_all_charts
    out = generate_all_charts(library, None, args.mode)
    for p in out:
        print(f"  -> {os.path.relpath(p, ROOT_DIR)}")
    return f"{len(out)} file generati"


STEP_FUNCS = {
    "parse": step_parse,
    "metrics": step_metrics,
    "pipeline": step_pipeline,
    "advanced": step_advanced,
    "compare": step_compare,
}


# ── Riepilogo tra librerie ────────────────────────────────────────────────────

def _load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_global_summary(libraries: List[str], status: Dict[str, Dict[str, str]]) -> str:
    """compare_CodeWiki/SUMMARY.md con i risultati chiave di ogni libreria presente su disco."""
    def f(v):
        return f"{v:.3f}" if isinstance(v, (int, float)) else "N/A"

    rows_cov, rows_cmp = [], []
    for lib in libraries:
        paths = lib_paths(lib)
        cw = _load_json(paths.summary_json)
        cmp_ = _load_json(paths.cmp_json)
        if cw:
            rows_cov.append(
                f"| {lib} | {cw['total_db_functions']} | {cw['total_db_mentioned']} | "
                f"{cw['total_db_documented']} | {cw['documented_coverage_rate'] * 100:.1f}% |")
        if cmp_:
            by = {m["metric"]: m for m in cmp_["metrics"]}
            def cell(key):
                m = by.get(key)
                if not m or not m["n"]:
                    return "N/A"
                return f"{f(m['pipeline_mean'])} / {f(m['codewiki_mean'])}"
            rows_cmp.append(
                f"| {lib} | {cmp_['n_common']} | {cell('sbert_similarity')} | {cell('bertscore_f1')} | "
                f"{cell('meteor_score')} | {cell('judge_combined')} | {cell('roundtrip_pass_rate')} | "
                f"{cell('retrieval_rr')} |")

    lines = [
        "# Confronto CodeWiki vs pipeline della tesi - riepilogo per libreria",
        "",
        f"> Generato da `compare_codewiki.py` il {time.strftime('%Y-%m-%d %H:%M')}. "
        "Dettagli, grafici e report completi in `compare_CodeWiki/<Libreria>/`.",
        "",
        "## Copertura di CodeWiki",
        "",
        "| Libreria | Funzioni DB | Menzionate | Con testo descrittivo | Documented coverage |",
        "|----------|-------------|------------|-----------------------|---------------------|",
        *rows_cov,
        "",
        "## Pipeline vs CodeWiki (medie sulle funzioni in comune, formato `pipeline / CodeWiki`)",
        "",
        "| Libreria | n | SBERT | BERTScore F1 | METEOR | Judge combinato (1-5) | Round-trip pass % | Retrieval MRR |",
        "|----------|---|-------|--------------|--------|-----------------------|-------------------|---------------|",
        *rows_cmp,
        "",
        "## Stato dell'ultima esecuzione",
        "",
        "| Libreria | " + " | ".join(ALL_STEPS) + " |",
        "|----------|" + "|".join("---" for _ in ALL_STEPS) + "|",
    ]
    for lib in libraries:
        st = status.get(lib, {})
        lines.append(f"| {lib} | " + " | ".join(st.get(s, "-") for s in ALL_STEPS) + " |")
    lines.append("")

    path = os.path.join(COMPARE_ROOT, "SUMMARY.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="Confronto documentazione CodeWiki vs pipeline della tesi, su una o piu' librerie",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Esempi:")[1].split("Scope della pipeline")[0],
    )
    ap.add_argument("-l", "--libraries", nargs="+", default=None, metavar="LIB",
                    help="Librerie da processare (default: tutte quelle con CodeWiki e righe nel DB)")
    ap.add_argument("--list", action="store_true", help="Elenca le librerie disponibili ed esce")
    ap.add_argument("--dry-run", action="store_true", help="Mostra il piano di esecuzione senza eseguire nulla")
    ap.add_argument("--steps", default=",".join(ALL_STEPS),
                    help=f"Step da eseguire, separati da virgola (default: {','.join(ALL_STEPS)})")
    ap.add_argument("--pipeline-scope", choices=["all", "codewiki"], default="all",
                    help="Funzioni da documentare con la pipeline: 'all' = tutte quelle della libreria "
                         "(default), 'codewiki' = solo quelle documentate da CodeWiki")
    ap.add_argument("-m", "--mode", choices=["multiagent", "single"], default="multiagent",
                    help="Modalita' della pipeline della tesi (default: multiagent)")
    ap.add_argument("--force-pipeline", action="store_true",
                    help="Rigenera la documentazione anche per le funzioni gia' presenti nei run in results/")
    ap.add_argument("--no-roundtrip", action="store_true",
                    help="Nello step pipeline salta il Round-Trip Differential Testing")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                    help=f"Funzioni per batch nello step pipeline; ogni batch e' salvato a parte, cosi' "
                         f"un'interruzione non perde tutto (default: {DEFAULT_BATCH_SIZE})")
    ap.add_argument("--rounds", type=int, default=5, help="Round del judge per prospettiva (default: 5)")
    ap.add_argument("--no-bert", action="store_true", help="Salta BERTScore nelle metriche CodeWiki")
    ap.add_argument("--mock", action="store_true",
                    help="Nessuna chiamata API (salta lo step pipeline; advanced scrive su file _mock)")
    ap.add_argument("--stop-on-error", action="store_true",
                    help="Si ferma al primo errore invece di passare alla libreria successiva")
    return ap.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    found = discover_libraries()
    available = found["ready"]

    if args.list:
        banner("Librerie disponibili")
        for lib in available:
            n = len(db_function_names(lib))
            print(f"  {lib:<14s} {n:>4d} funzioni con Ground Truth nel DB   ({lib_paths(lib).dir})")
        for d in found["no_db"]:
            print(f"  {d:<14s}  --  CodeWiki presente ma nessuna riga in benchmark.db (non confrontabile)")
        return

    # Librerie scelte
    if args.libraries:
        libraries = []
        for name in args.libraries:
            canon = resolve_library(name)
            if canon is None:
                raise SystemExit(f"[ERRORE] Libreria '{name}' non presente in benchmark.db. "
                                 f"Disponibili: {', '.join(db_libraries())}")
            if canon not in available:
                raise SystemExit(f"[ERRORE] Nessuna documentazione CodeWiki in compare_CodeWiki/{canon}/")
            libraries.append(canon)
    else:
        libraries = list(available)
    if not libraries:
        raise SystemExit("[ERRORE] Nessuna libreria da processare.")

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = set(steps) - set(ALL_STEPS)
    if unknown:
        raise SystemExit(f"[ERRORE] Step sconosciuti: {sorted(unknown)}. Validi: {', '.join(ALL_STEPS)}")
    steps = [s for s in ALL_STEPS if s in steps]  # ordine canonico

    banner("CONFRONTO CODEWIKI vs PIPELINE DELLA TESI")
    print(f"  Librerie : {', '.join(libraries)}")
    print(f"  Step     : {', '.join(steps)}")
    print(f"  Pipeline : modalita' {args.mode}, scope {args.pipeline_scope}"
          f"{', round-trip OFF' if args.no_roundtrip else ''}{', MOCK' if args.mock else ''}")
    if found["no_db"] and not args.libraries:
        print(f"  Saltate  : {', '.join(found['no_db'])} (CodeWiki presente ma nessuna riga in benchmark.db)")

    if args.dry_run:
        banner("PIANO (dry-run, nulla viene eseguito)", "-")
        for lib in libraries:
            line = f"  {lib:<14s} {len(db_function_names(lib)):>4d} funzioni con GT nel DB"
            if "pipeline" in steps and not args.mock:
                if args.pipeline_scope == "all" or read_function_list(lib_paths(lib).function_list):
                    line += f"  |  da documentare con la pipeline: {len(pipeline_targets(lib, args))}"
                else:
                    line += "  |  pipeline: elenco funzioni CodeWiki disponibile dopo lo step 'metrics'"
            print(line)
        if (set(steps) & API_STEPS) and not args.mock:
            print("\n  Gli step pipeline/advanced richiedono GEMINI_API_KEY (chiamate API a pagamento).")
        return

    if set(steps) & API_STEPS and not args.mock:
        require_api_key()

    status: Dict[str, Dict[str, str]] = {lib: {} for lib in libraries}
    t_all = time.time()
    for lib in libraries:
        banner(f"LIBRERIA: {lib}")
        for step in steps:
            if step == "pipeline" and args.mock:
                status[lib][step] = "saltato (mock)"
                print(f"\n>>> [{lib}] {step}: saltato (--mock)")
                continue
            banner(f"[{lib}] step: {step}", "-")
            t0 = time.time()
            try:
                msg = STEP_FUNCS[step](lib, args)
                status[lib][step] = f"ok ({time.time() - t0:.0f}s)" + (f" - {msg}" if msg and msg != "ok" else "")
            except (Exception, SystemExit) as e:
                status[lib][step] = "ERRORE"
                if isinstance(e, SystemExit):
                    print(str(e))
                else:
                    traceback.print_exc()
                print(f"[ERRORE] [{lib}] step '{step}' fallito: {e if not isinstance(e, SystemExit) else 'vedi sopra'}")
                if args.stop_on_error:
                    write_global_summary(available, status)
                    raise SystemExit(1)
                # Gli step successivi dipendono da quelli precedenti: si passa alla libreria dopo
                break

    path = write_global_summary(available, status)

    # Risultati complessivi tra librerie (grafici + OVERALL_REPORT.md), solo da file gia' prodotti
    if "compare" in steps:
        try:
            from utils.plot_codewiki_overall import generate_overall
            for p in generate_overall():
                print(f"  -> {os.path.relpath(p, ROOT_DIR)}")
        except Exception as e:  # il riepilogo complessivo non deve far fallire l'esecuzione
            print(f"[WARN] risultati complessivi non generati: {e}")

    banner(f"COMPLETATO in {(time.time() - t_all) / 60:.1f} min")
    for lib in libraries:
        print(f"  {lib:<14s} " + "  ".join(f"{s}={status[lib].get(s, '-').split(' ')[0]}" for s in steps))
    print(f"\n  Riepilogo tra librerie: {os.path.relpath(path, ROOT_DIR)}")
    if any("ERRORE" in v for st in status.values() for v in st.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
