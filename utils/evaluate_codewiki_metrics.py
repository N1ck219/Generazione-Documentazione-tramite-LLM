"""
evaluate_codewiki_metrics.py
-----------------------------
Calcola e confronta le metriche di qualita' della documentazione prodotta da
CodeWiki rispetto al Ground Truth presente nel benchmark.db, per una libreria alla volta
(cartella compare_CodeWiki/<Libreria>/).

Legge: compare_CodeWiki/<Libreria>/codewiki_mapped_functions.json
       (generato da utils/parse_codewiki_to_benchmark.py)

Produce:
  - compare_CodeWiki/<Libreria>/codewiki_metrics_results.json   (dati per funzione)
  - compare_CodeWiki/<Libreria>/codewiki_metrics_summary.json   (aggregati finali)
  - compare_CodeWiki/<Libreria>/codewiki_metrics_report.md      (report leggibile per la tesi)
  - compare_CodeWiki/<Libreria>/codewiki_function_list.txt      (funzioni documentate da CodeWiki,
                                                      input per benchmark_eval.py --functions)
  - compare_CodeWiki/<Libreria>/charts/*.png + codewiki_vs_pipeline_report.md
                                                     (grafici e confronto con la pipeline,
                                                      vedi utils/plot_codewiki_comparison.py)

Unita' di valutazione: la funzione unica del DB ("ClassName::MethodName" in C++, nome della
funzione in C).
Le varianti .h/.cpp della stessa funzione condividono il Ground Truth e
vengono contate una sola volta. Se CodeWiki descrive la stessa funzione in
piu' punti, le descrizioni testuali distinte vengono concatenate.
Le menzioni provenienti solo dai diagrammi Mermaid non hanno testo
descrittivo: contano per la "Mention Coverage" ma sono escluse dalle metriche.

Metriche calcolate (solo sulle funzioni con testo CodeWiki e Ground Truth):
  - SBERT Cosine Similarity        (semantica densa, all-MiniLM-L6-v2)
  - BERTScore F1                   (allineamento token contestuali, bert-base-uncased)
  - ROUGE-L F1                     (Longest Common Subsequence)
  - TF-IDF Cosine Similarity       (similarita' vettoriale lessicale)
  - METEOR Score                   (sinonimi + stemming via NLTK WordNet)
  - BLEURT estimate                (0.65*SBERT + 0.25*ROUGE-L + 0.10*BP)
  - Actionability Score            (completezza operativa; su doc CodeWiki)
  - Edge Case Coverage             (guardie NULL/zero/vuoto menzionate)
  - Error Documentation Rate       (rami di errore documentati)
  - Semantic Concept Checklist     (concetti tecnici chiave coperti)
  - Documented Coverage            (% funzioni DB con testo CodeWiki)
  - Mention Coverage               (% funzioni DB almeno menzionate, Mermaid incluso)

Utilizzo:
  .venv/Scripts/python utils/evaluate_codewiki_metrics.py [-l LIBRERIA] [--no-bert] [--limit N]
  (per eseguire l'intero confronto su piu' librerie usa compare_codewiki.py)
  (usare il venv del progetto: senza sentence_transformers / bert_score le
   metriche SBERT e BERTScore ricadono silenziosamente su un'approssimazione)

Opzioni:
  --no-bert   Salta BERTScore (piu' lento, richiede bert_score installato)
  --limit N   Valuta solo le prime N funzioni documentate (per test rapidi)
  --no-plots  Non genera grafici e confronto con la pipeline
  --full      Calcola anche judge, round-trip, retrieval e CodeBERTScore su CodeWiki
              (chiamate API reali; risultati in cache, ripresa automatica)
  --pipeline-report PATH / --pipeline-mode MODE   vedi plot_codewiki_comparison.py
"""

import os
import sys
import json
import sqlite3
import argparse
from typing import Dict, List, Any

# Root del progetto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.codewiki_config import DB_PATH, lib_paths, resolve_library
from utils.benchmark_metrics import (
    calculate_sbert_similarity,
    calculate_batch_bert_scores,
    calculate_rouge_l,
    calculate_tfidf_cosine,
    calculate_meteor_score,
    calculate_bleurt_score,
    calculate_brevity_penalty,
    parse_doxygen_block,
    calculate_actionability_score,
    calculate_error_documentation_rate,
    calculate_edge_case_coverage,
    evaluate_semantic_checklist,
)

COMPARISON_KEYS = [
    "rouge_l", "tfidf_cosine", "length_ratio", "brevity_penalty",
    "sbert_similarity", "meteor_score", "bleurt_estimate",
    "concept_checklist_score", "bertscore_f1",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0

def std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = avg(values)
    return round((sum((v - m) ** 2 for v in values) / len(values)) ** 0.5, 4)

def pct(n: int, total: int) -> str:
    return f"{n / total * 100:.1f}%" if total > 0 else "N/A"

def bar(value: float, width: int = 20) -> str:
    """Barra ASCII proporzionale al valore [0.0, 1.0]."""
    filled = int(round(value * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def load_db_function_names(db_path: str, library: str) -> Dict[str, int]:
    """Restituisce {nome_funzione_unico: numero di righe DB (varianti .h/.cpp)}."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT function_name, COUNT(*) FROM benchmark_functions "
        "WHERE LOWER(library) = LOWER(?) GROUP BY function_name",
        (library,),
    ).fetchall()
    conn.close()
    return {name: count for name, count in rows}


# ── Raggruppamento per funzione DB ────────────────────────────────────────────

def group_by_db_function(records: List[Dict]) -> List[Dict]:
    """
    Aggrega le menzioni CodeWiki matchate per funzione DB unica.
    Il testo candidato e' la concatenazione delle descrizioni testuali
    (doc_source == "bullet") distinte; le menzioni Mermaid non contribuiscono.
    """
    groups: Dict[str, Dict] = {}
    for r in records:
        name = r["db_function_name"]
        g = groups.get(name)
        if g is None:
            g = groups[name] = {
                "db_function_name": name,
                "db_ids": r.get("db_ids") or [r.get("db_id")],
                "cleaned_doc": r.get("cleaned_doc", "") or "",
                "source_code": r.get("source_code", "") or "",
                "parameters": r.get("parameters", []) or [],
                "return_type": r.get("return_type", "") or "",
                "codewiki_mentions": [],
                "match_strategies": [],
                "source_files": [],
                "_texts": [],
            }
        g["codewiki_mentions"].append(r["function_name"])
        if r["match_strategy"] not in g["match_strategies"]:
            g["match_strategies"].append(r["match_strategy"])
        if r["source_file"] not in g["source_files"]:
            g["source_files"].append(r["source_file"])
        text = (r.get("codewiki_doc") or "").strip()
        if r.get("doc_source") == "bullet" and text and text not in g["_texts"]:
            g["_texts"].append(text)

    out = []
    for g in groups.values():
        g["codewiki_doc"] = " ".join(g.pop("_texts"))
        g["has_codewiki_text"] = bool(g["codewiki_doc"])
        out.append(g)
    return out


# ── Valutazione per singola funzione ─────────────────────────────────────────

def evaluate_single(group: Dict) -> Dict[str, Any]:
    """
    Calcola tutte le metriche locali per una singola funzione DB.

    reference = cleaned_doc (Ground Truth originale della libreria)
    candidate = codewiki_doc (testo CodeWiki aggregato per la funzione)
    """
    reference = group["cleaned_doc"]
    candidate = group["codewiki_doc"]
    source_code = group["source_code"]
    parameters = group["parameters"]

    has_gt = bool(reference.strip())
    evaluated = has_gt and group["has_codewiki_text"]

    result: Dict[str, Any] = {
        "function_name": group["db_function_name"],
        "db_ids": group["db_ids"],
        "codewiki_mentions": group["codewiki_mentions"],
        "match_strategies": group["match_strategies"],
        "source_files": group["source_files"],
        "has_ground_truth": has_gt,
        "has_codewiki_text": group["has_codewiki_text"],
        "evaluated": evaluated,
        "codewiki_doc_length": len(candidate.split()),
        "gt_doc_length": len(reference.split()) if has_gt else 0,
    }

    if not evaluated:
        # Solo menzione (Mermaid) o GT mancante: nessuna metrica calcolabile
        for k in COMPARISON_KEYS + ["actionability_score", "error_doc_rate", "edge_case_coverage"]:
            result[k] = None
        return result

    # ── Livello Lessicale & Sequenziale ──────────────────────────────────────
    result["rouge_l"]         = calculate_rouge_l(reference, candidate)
    result["tfidf_cosine"]    = calculate_tfidf_cosine(reference, candidate)
    bp_info                   = calculate_brevity_penalty(reference, candidate)
    result["length_ratio"]    = bp_info["length_ratio"]
    result["brevity_penalty"] = bp_info["brevity_penalty"]

    # ── Livello Semantico Denso ───────────────────────────────────────────────
    result["sbert_similarity"] = calculate_sbert_similarity(reference, candidate)
    result["meteor_score"]     = calculate_meteor_score(reference, candidate)
    result["bleurt_estimate"]  = calculate_bleurt_score(reference, candidate)

    # ── Semantic Concept Checklist ────────────────────────────────────────────
    checklist = evaluate_semantic_checklist(reference, candidate)
    result["concept_checklist_score"] = checklist["checklist_score"]
    result["concept_ref_active"]      = checklist["ref_concepts"]
    result["concept_matched"]         = checklist["matched_concepts"]

    # BERTScore: compilato in batch
    result["bertscore_f1"] = None

    # ── Metriche su doc CodeWiki (indipendenti dal GT) ────────────────────────
    # La doc CodeWiki non e' in formato Doxygen: il testo libero viene trattato
    # come "brief" per una valutazione parziale dell'Actionability.
    parsed_cw = parse_doxygen_block(candidate)
    if not parsed_cw["brief"]:
        parsed_cw["brief"] = candidate[:300]

    result["actionability_score"] = calculate_actionability_score(parsed_cw, parameters)

    # EDR ed ECC richiedono il codice sorgente. Se il codice non contiene rami
    # di errore / guardie la metrica non e' applicabile (None): le funzioni di
    # libreria restituirebbero 1.0 per vacuita', gonfiando la media.
    edr = calculate_error_documentation_rate(
        source_code,
        documented_returns=parsed_cw.get("returns", []),
        details_text=candidate
    )
    result["has_code_error_branch"] = edr["has_code_error"]
    result["error_doc_rate"] = edr["score"] if edr["has_code_error"] else None

    ecc = calculate_edge_case_coverage(source_code, candidate)
    result["code_guard_count"]   = ecc["code_guard_count"]
    result["edge_case_coverage"] = ecc["coverage"] if ecc["code_guard_count"] > 0 else None

    return result


# ── Calcolo batch BERTScore ───────────────────────────────────────────────────

def fill_bert_scores(results: List[Dict], groups_by_name: Dict[str, Dict]) -> List[Dict]:
    """Calcola BERTScore in batch su tutte le coppie (GT, CodeWiki doc) valutate."""
    idxs = [i for i, r in enumerate(results) if r["evaluated"]]
    if not idxs:
        return results

    print(f"  [BERTScore] Calcolo su {len(idxs)} coppie (bert-base-uncased)...")
    refs  = [groups_by_name[results[i]["function_name"]]["cleaned_doc"] for i in idxs]
    cands = [groups_by_name[results[i]["function_name"]]["codewiki_doc"] for i in idxs]

    bert_scores = calculate_batch_bert_scores(refs, cands, model_type="bert-base-uncased")
    for i, bs in zip(idxs, bert_scores):
        results[i]["bertscore_f1"] = bs["f1"]

    return results


# ── Aggregazione statistica ───────────────────────────────────────────────────

def compute_summary(
    results: List[Dict],
    db_names: Dict[str, int],
    all_records: List[Dict],
) -> Dict[str, Any]:
    """Calcola le statistiche aggregate su tutte le funzioni valutate."""
    total_db = len(db_names)
    evaluated = [r for r in results if r["evaluated"]]
    n_eval = len(evaluated)
    n_mentioned = len(results)
    unmatched = [r for r in all_records if not r.get("matched")]

    def col(key: str) -> List[float]:
        return [r[key] for r in evaluated if r.get(key) is not None]

    strategy_counts: Dict[str, int] = {}
    for r in all_records:
        s = r.get("match_strategy", "none")
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    summary = {
        "total_db_rows": sum(db_names.values()),
        "total_db_functions": total_db,
        "total_codewiki_mentions": len(all_records),
        "total_codewiki_unmatched": len(unmatched),
        "unmatched_mentions": sorted({r["function_name"] for r in unmatched}),
        "match_strategy_counts": strategy_counts,
        "total_db_mentioned": n_mentioned,
        "total_db_documented": n_eval,
        "total_db_mentioned_only": n_mentioned - n_eval,
        "documented_coverage_rate": round(n_eval / total_db, 4) if total_db > 0 else 0.0,
        "mention_coverage_rate": round(n_mentioned / total_db, 4) if total_db > 0 else 0.0,
        "uncovered_db_functions": sorted(set(db_names) - {r["function_name"] for r in results}),
    }

    for key, label in [
        ("sbert_similarity",        "SBERT Cosine Similarity"),
        ("bertscore_f1",            "BERTScore F1"),
        ("rouge_l",                 "ROUGE-L"),
        ("tfidf_cosine",            "TF-IDF Cosine"),
        ("meteor_score",            "METEOR"),
        ("bleurt_estimate",         "BLEURT Estimate"),
        ("concept_checklist_score", "Semantic Concept Checklist"),
        ("actionability_score",     "Actionability Score"),
        ("error_doc_rate",          "Error Documentation Rate"),
        ("edge_case_coverage",      "Edge Case Coverage"),
        ("length_ratio",            "Length Ratio (CodeWiki/GT)"),
    ]:
        vals = col(key)
        summary[key] = {
            "label": label,
            "n": len(vals),
            "mean": avg(vals) if vals else None,
            "std": std(vals) if vals else None,
            "min": round(min(vals), 4) if vals else None,
            "max": round(max(vals), 4) if vals else None,
        }

    return summary


# ── Generazione report Markdown ───────────────────────────────────────────────

def fmt(v) -> str:
    return f"{v:.4f}" if v is not None else "N/A"


def uncovered_by_class(names: List[str]) -> str:
    """Riassume le funzioni non coperte per classe, es. 'XMLDocument (25), XMLHandle (12)'."""
    counts: Dict[str, int] = {}
    for n in names:
        cls = n.split("::")[0] if "::" in n else "(free functions)"
        counts[cls] = counts.get(cls, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    return ", ".join(f"`{c}` ({k})" for c, k in ordered)


def generate_markdown_report(summary: Dict, results: List[Dict], library: str) -> str:
    """Genera un report Markdown leggibile con i risultati per la tesi."""
    n_db       = summary["total_db_functions"]
    n_rows     = summary["total_db_rows"]
    n_mentions = summary["total_codewiki_mentions"]
    n_unmatch  = summary["total_codewiki_unmatched"]
    n_ment     = summary["total_db_mentioned"]
    n_doc      = summary["total_db_documented"]
    n_only     = summary["total_db_mentioned_only"]
    uncovered  = summary["uncovered_db_functions"]

    lines = [
        f"# Valutazione Metriche: CodeWiki vs Ground Truth ({library})",
        "",
        "> **Script**: `utils/evaluate_codewiki_metrics.py`  ",
        f"> **Libreria target**: {library}  ",
        f"> **Funzioni uniche nel DB**: {n_db} ({n_rows} righe, varianti header/implementazione)  ",
        f"> **Menzioni di metodi in CodeWiki**: {n_mentions}  ",
        f"> **Funzioni DB con testo CodeWiki valutato**: {n_doc} ({pct(n_doc, n_db)} del DB)  ",
        "",
        "---",
        "",
        "## 1. Copertura API",
        "",
        "| Metrica | Valore |",
        "|---------|--------|",
        f"| Funzioni uniche DB {library} | {n_db} |",
        f"| Menzioni di metodi nei Markdown CodeWiki | {n_mentions} |",
        f"| Menzioni senza corrispondenza nel DB | {n_unmatch} |",
        f"| Funzioni DB menzionate (testo o diagramma Mermaid) | {n_ment} |",
        f"| └── di cui solo nel diagramma Mermaid (senza testo) | {n_only} |",
        f"| **Documented Coverage** (funzioni con testo descrittivo) | **{pct(n_doc, n_db)}** ({n_doc}/{n_db}) |",
        f"| Mention Coverage | {pct(n_ment, n_db)} ({n_ment}/{n_db}) |",
        f"| Funzioni DB non coperte | {len(uncovered)} |",
        "",
        "Strategie di matching (per menzione): " + ", ".join(
            f"`{k}`={v}" for k, v in sorted(summary["match_strategy_counts"].items())
        ) + ".",
        "",
        "---",
        "",
        "## 2. Metriche di Qualita' della Documentazione",
        "",
        f"*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n={n_doc})*",
        "",
        "| Metrica | n | Media | Std | Min | Max |",
        "|---------|---|-------|-----|-----|-----|",
    ]

    metric_keys = [
        "sbert_similarity", "bertscore_f1", "rouge_l", "tfidf_cosine",
        "meteor_score", "bleurt_estimate", "concept_checklist_score",
        "actionability_score", "error_doc_rate", "edge_case_coverage",
        "length_ratio",
    ]
    for key in metric_keys:
        s = summary[key]
        lines.append(
            f"| {s['label']} | {s['n']} | {fmt(s['mean'])} | {fmt(s['std'])} | {fmt(s['min'])} | {fmt(s['max'])} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Distribuzione SBERT per Funzione",
        "",
        f"*(Tutte le {n_doc} funzioni valutate, ordinate per SBERT decrescente)*",
        "",
        "| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |",
        "|-------------|-------------------|-------|---------|--------|---------------|",
    ]

    evaluated_sorted = sorted(
        [r for r in results if r["evaluated"]],
        key=lambda r: r["sbert_similarity"],
        reverse=True,
    )
    for r in evaluated_sorted:
        mentions = ", ".join(sorted(set(r["codewiki_mentions"])))
        lines.append(
            f"| `{r['function_name']}` | {mentions} | {fmt(r['sbert_similarity'])} | "
            f"{fmt(r['rouge_l'])} | {fmt(r['meteor_score'])} | {fmt(r['actionability_score'])} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Interpretazione e Limiti",
        "",
        f"- **Documented Coverage del {pct(n_doc, n_db)}**: CodeWiki documenta a livello di modulo,",
        "  non per singola funzione. Le funzioni non coperte, per classe, sono:",
        f"  {uncovered_by_class(uncovered)}.",
        f"  Altre {n_only} funzioni compaiono solo come firma nei diagrammi Mermaid, senza testo descrittivo.",
        "",
        "- **Unita' di conteggio**: nel DB molte funzioni compaiono due volte (dichiarazione nell'header e",
        "  definizione nel file di implementazione) con lo stesso Ground Truth; il conteggio usa le funzioni uniche.",
        "  Le descrizioni CodeWiki multiple di una stessa funzione sono concatenate.",
        "",
        "- **Matching conservativo**: sono ammessi solo match esatti sul nome canonico, la rimozione",
        "  del namespace iniziale (`fmt::format` -> `format`) e, per i metodi ereditati/ridefiniti,",
        "  il match con la dichiarazione della classe base (es. `XMLDocument::Accept` ->",
        "  `XMLNode::Accept`). Nessun matching fuzzy ne' per solo nome di metodo.",
        "",
        "- **EDR / ECC**: calcolati solo sulle funzioni il cui codice (file di implementazione se disponibile)",
        "  contiene rami di errore o guardie su casi limite (colonna *n*); altrove non applicabili.",
        "",
        "- **Actionability Score**: la documentazione CodeWiki e' in prosa libera senza tag Doxygen",
        "  (`@param [in/out]`, `@return`, `@pre`). Questo abbassa strutturalmente l'Actionability Score",
        "  rispetto alla pipeline della tesi, che genera commenti Doxygen formali e verificati.",
        "",
        "- **Granularita'**: SBERT/METEOR confrontano brevi snippet (tipicamente 1-2 frasi, spesso",
        "  condivisi da un gruppo di metodi, es. \"Methods for traversing the DOM tree\") con la",
        "  `cleaned_doc` originale, piu' lunga e specifica: i valori tendono ad essere moderati.",
        "",
        "---",
        "*Report generato automaticamente da `utils/evaluate_codewiki_metrics.py`*",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(library: str, no_bert: bool = False, limit: int = None, no_plots: bool = False,
        full: bool = False, pipeline_report: str = None, pipeline_mode: str = "multiagent") -> bool:
    """Valuta le metriche NLP di CodeWiki per `library`. Restituisce False se l'input manca."""
    canonical = resolve_library(library)
    if canonical is None:
        print(f"[ERRORE] '{library}' non e' presente in {DB_PATH}")
        return False
    library = canonical
    paths = lib_paths(library)

    print("=" * 65)
    print("  evaluate_codewiki_metrics.py")
    print(f"  Libreria: {library}")
    print(f"  Input   : {paths.mapped_json}")
    print(f"  Output  : {paths.dir}")
    print("=" * 65)
    print()

    if not os.path.exists(paths.mapped_json):
        print(f"[ERRORE] File non trovato: {paths.mapped_json}")
        print(f"  Esegui prima: python utils/parse_codewiki_to_benchmark.py -l {library}")
        return False

    with open(paths.mapped_json, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    db_names = load_db_function_names(DB_PATH, library)

    matched_records = [r for r in all_records if r.get("matched")]
    groups = group_by_db_function(matched_records)
    documented = [g for g in groups if g["has_codewiki_text"] and g["cleaned_doc"].strip()]

    print(f"Funzioni uniche nel DB          : {len(db_names)}  ({sum(db_names.values())} righe)")
    print(f"Menzioni CodeWiki nel JSON      : {len(all_records)}")
    print(f"  matchate / senza match        : {len(matched_records)} / {len(all_records) - len(matched_records)}")
    print(f"Funzioni DB menzionate          : {len(groups)}")
    print(f"Funzioni DB con testo CodeWiki  : {len(documented)}")
    print()

    if limit:
        keep = {g["db_function_name"] for g in documented[:limit]}
        groups = [g for g in groups if g["db_function_name"] in keep or not g["has_codewiki_text"]]
        print(f"[--limit] Valuto solo le prime {limit} funzioni documentate.")
        print()

    # ── Fase 1: Metriche per funzione ─────────────────────────────────────────
    print(f"[1/4] Calcolo metriche per {len(groups)} funzioni DB menzionate...")
    results = []
    for i, g in enumerate(groups, 1):
        r = evaluate_single(g)
        results.append(r)
        sbert = fmt(r["sbert_similarity"]) if r["evaluated"] else "-- (solo menzione)"
        print(f"  [{i:3d}/{len(groups)}] {g['db_function_name']:45s} SBERT={sbert}")
    print()

    # ── Fase 2: BERTScore in batch ─────────────────────────────────────────────
    if not no_bert:
        print("[2/4] Calcolo BERTScore in batch...")
        results = fill_bert_scores(results, {g["db_function_name"]: g for g in groups})
    else:
        print("[2/4] BERTScore saltato (--no-bert).")
    print()

    # ── Fase 3: Aggregazione e report ──────────────────────────────────────────
    print("[3/4] Aggregazione risultati e generazione report...")

    summary = compute_summary(results, db_names, all_records)
    md_report = generate_markdown_report(summary, results, library)

    with open(paths.results_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Risultati per funzione: {paths.results_json}")

    with open(paths.summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  Sommario aggregato    : {paths.summary_json}")

    with open(paths.report_md, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"  Report Markdown       : {paths.report_md}")

    # Elenco funzioni documentate: permette di eseguire la pipeline sullo stesso insieme
    with open(paths.function_list, "w", encoding="utf-8") as f:
        f.write(f"# Funzioni {library} documentate da CodeWiki (generato da evaluate_codewiki_metrics.py)\n")
        f.write(f"# Uso: python utils/benchmark_eval.py -l {library} -m multiagent --functions <questo file>\n")
        for r in sorted(results, key=lambda r: r["function_name"]):
            if r["evaluated"]:
                f.write(r["function_name"] + "\n")
    print(f"  Elenco funzioni       : {paths.function_list}")
    print()

    n_evaluated = sum(1 for r in results if r["evaluated"])
    if n_evaluated == 0:
        print("[WARN] Nessuna funzione con testo CodeWiki e Ground Truth: grafici e confronto saltati.")
        no_plots = True

    # ── Fase 3b: Metriche avanzate (judge, round-trip, retrieval, CodeBERTScore) ─
    if full and not limit and n_evaluated:
        print("[3b] Metriche avanzate CodeWiki (judge, round-trip, retrieval, CodeBERTScore)...")
        from utils.evaluate_codewiki_advanced import run as run_advanced, ALL_STEPS
        run_advanced(library, ALL_STEPS)
        print()

    # ── Fase 4: Grafici e confronto con la pipeline ───────────────────────────
    if not no_plots and not limit:
        print("[4/4] Generazione grafici e confronto con la pipeline...")
        from utils.plot_codewiki_comparison import generate_all_charts
        for p in generate_all_charts(library, pipeline_report, pipeline_mode):
            print(f"  -> {os.path.relpath(p, ROOT_DIR)}")
        print()

    # ── Stampa sommario a video ───────────────────────────────────────────────
    n_db = summary["total_db_functions"]
    print("=" * 65)
    print(f"  SOMMARIO FINALE - {library}")
    print("=" * 65)
    print(f"  Documented Coverage   : {summary['documented_coverage_rate']*100:.1f}%  "
          f"({summary['total_db_documented']}/{n_db})")
    print(f"  Mention Coverage      : {summary['mention_coverage_rate']*100:.1f}%  "
          f"({summary['total_db_mentioned']}/{n_db})")
    print()

    for key in ["sbert_similarity", "bertscore_f1", "rouge_l", "meteor_score",
                "bleurt_estimate", "actionability_score",
                "concept_checklist_score", "error_doc_rate", "edge_case_coverage"]:
        s = summary[key]
        if s["mean"] is not None:
            print(f"  {s['label']:<35s}: {s['mean']:.4f}  {bar(s['mean'])}")
        else:
            print(f"  {s['label']:<35s}: N/A")

    print("=" * 65)
    print()
    print("Fatto! Apri il report Markdown per i dettagli:")
    print(f"  {paths.report_md}")
    print()
    return True


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Valuta le metriche della documentazione CodeWiki vs Ground Truth per una libreria"
    )
    parser.add_argument(
        "-l", "--library", default="TinyXML-2",
        help="Libreria da valutare (default: TinyXML-2)"
    )
    parser.add_argument(
        "--no-bert", action="store_true",
        help="Salta il calcolo BERTScore (piu' lento, richiede bert_score)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limita la valutazione alle prime N funzioni documentate (test rapido)"
    )
    parser.add_argument(
        "--no-plots", action="store_true",
        help="Non genera i grafici e il confronto con la pipeline"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Calcola anche judge, round-trip, retrieval e CodeBERTScore (chiamate API reali, "
             "vedi utils/evaluate_codewiki_advanced.py)"
    )
    parser.add_argument(
        "--pipeline-report", default=None,
        help="eval_report_*.json della pipeline da confrontare (default: tutti i run in results/)"
    )
    parser.add_argument(
        "--pipeline-mode", default="multiagent", choices=["multiagent", "single", "any"],
        help="Modalita' della pipeline da confrontare (default: multiagent)"
    )
    args = parser.parse_args()
    ok = run(args.library, args.no_bert, args.limit, args.no_plots, args.full,
             args.pipeline_report, args.pipeline_mode)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
