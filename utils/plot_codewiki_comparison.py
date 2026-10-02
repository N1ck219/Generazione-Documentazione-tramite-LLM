"""
plot_codewiki_comparison.py
---------------------------
Grafici delle metriche CodeWiki e confronto affiancato con la pipeline della tesi
di una libreria.

Legge:
  - compare_CodeWiki/<Libreria>/codewiki_metrics_results.json   (da evaluate_codewiki_metrics.py)
  - results/**/eval_report_*.json                    (run della pipeline della tesi)
  - dataset/benchmark.db                             (codice sorgente canonico per EDR/ECC)

Produce in compare_CodeWiki/<Libreria>/charts/:
  Solo CodeWiki
    cw_metrics_summary.png        media +- std di ogni metrica
    cw_metrics_distributions.png  distribuzione per funzione di ogni metrica
    cw_coverage_by_class.png      copertura API per classe (testo / solo Mermaid / assente)
    cw_length_ratio.png           rapporto di lunghezza CodeWiki/GT
  CodeWiki vs Pipeline (solo sulle funzioni valutate da entrambi i sistemi)
    cmp_metrics_bars.png          medie affiancate per metrica
    cmp_distributions.png         distribuzioni affiancate per metrica
    cmp_paired_functions.png      confronto per funzione (SBERT, BERTScore, METEOR)
    cmp_advanced_metrics.png      judge, round-trip, retrieval, CodeBERTScore (se calcolati
                                  per CodeWiki con utils/evaluate_codewiki_advanced.py)
  e il report compare_CodeWiki/<Libreria>/codewiki_vs_pipeline_report.md (+ .json).

Equita' del confronto:
  - Le metriche semantiche della pipeline sono quelle salvate nei suoi report:
    stesse funzioni di utils/benchmark_metrics.py, calcolate su @brief+@details vs GT.
  - EDR ed ECC vengono ricalcolate per entrambi i sistemi sullo stesso codice
    (file di implementazione se disponibile) e sono "non applicabili" quando il codice non ha
    rami di errore / guardie, invece di valere 1.0 per vacuita'.
  - Per ogni funzione si usa il run piu' recente della pipeline che la contiene.

Utilizzo:
  .venv/Scripts/python utils/plot_codewiki_comparison.py [-l LIBRERIA] [--pipeline-report PATH]
                                                         [--pipeline-mode multiagent|single|any]
"""

import os
import sys
import json
import glob
import argparse
from typing import Dict, List, Any, Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.benchmark_metrics import (
    parse_doxygen_block,
    calculate_error_documentation_rate,
    calculate_edge_case_coverage,
)
from utils.parse_codewiki_to_benchmark import (
    load_benchmark_functions,
    group_db_functions,
)
from utils.codewiki_config import DB_PATH, RESULTS_DIR, LibraryPaths, lib_paths, resolve_library

# Metriche in scala [0, 1] (stesso asse). length_ratio ha scala diversa: grafico a parte.
METRICS = [
    ("sbert_similarity",        "SBERT"),
    ("bertscore_f1",            "BERTScore F1"),
    ("bleurt_estimate",         "BLEURT (stima)"),
    ("meteor_score",            "METEOR"),
    ("tfidf_cosine",            "TF-IDF cosine"),
    ("rouge_l",                 "ROUGE-L"),
    ("concept_checklist_score", "Concept checklist"),
    ("actionability_score",     "Actionability"),
    ("error_doc_rate",          "Error doc. rate"),
    ("edge_case_coverage",      "Edge case coverage"),
]

# Chiave metrica canonica -> chiave nel report della pipeline
PIPELINE_KEYS = {
    "sbert_similarity":        "sbert_similarity",
    "bertscore_f1":            "bert_score_f1",
    "bleurt_estimate":         "bleurt_score",
    "meteor_score":            "meteor_score",
    "tfidf_cosine":            "tfidf_similarity",
    "rouge_l":                 "rouge_l",
    "concept_checklist_score": "concept_checklist_score",
    "actionability_score":     "actionability_score",
    "length_ratio":            "length_ratio",
}

# Metriche avanzate (scale diverse: un pannello per metrica, ciascuno con il proprio asse).
# (chiave, etichetta, limiti asse, estrattore dal record pipeline, estrattore dalla cache CodeWiki)
def _dig(d: Dict, *path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


ADV_METRICS = [
    ("codebert_f1", "CodeBERTScore F1", (0, 1),
     lambda r: _dig(r, "metrics", "codebert_score_f1"), lambda c: _dig(c, "codebert", "f1")),
    ("retrieval_rr", "Retrieval MRR", (0, 1),
     lambda r: _dig(r, "metrics", "retrieval_rr"), lambda c: _dig(c, "retrieval", "reciprocal_rank")),
    ("hit_at_1", "Retrieval Hit@1", (0, 1),
     lambda r: _dig(r, "metrics", "hit_at_1"), lambda c: _dig(c, "retrieval", "hit_at_1")),
    ("hit_at_5", "Retrieval Hit@5", (0, 1),
     lambda r: _dig(r, "metrics", "hit_at_5"), lambda c: _dig(c, "retrieval", "hit_at_5")),
    ("judge_a", "Judge A - Faithfulness", (1, 5),
     lambda r: _dig(r, "metrics", "judge_score_a"), lambda c: _dig(c, "judge", "perspective_a", "mean")),
    ("judge_b", "Judge B - Alignment", (1, 5),
     lambda r: _dig(r, "metrics", "judge_score_b"), lambda c: _dig(c, "judge", "perspective_b", "mean")),
    ("judge_combined", "Judge combinato", (1, 5),
     lambda r: _dig(r, "metrics", "judge_combined"), lambda c: _dig(c, "judge", "combined_score")),
    ("roundtrip_pass_rate", "Round-trip pass rate (%)", (0, 100),
     lambda r: _dig(r, "roundtrip", "execution", "pass_rate"),
     lambda c: _dig(c, "roundtrip", "execution", "pass_rate")),
    ("roundtrip_dual_agreement", "Dual agreement (%)", (0, 100),
     lambda r: _dig(r, "roundtrip", "execution", "differential", "differential_agreement_rate"),
     lambda c: _dig(c, "roundtrip", "execution", "differential", "differential_agreement_rate")),
]

# Metriche della pipeline che non hanno senso sulla prosa CodeWiki
NOT_APPLICABLE = [
    ("param_f1", "Param F1", "richiede tag @param, assenti in CodeWiki"),
    ("return_match", "Return match", "richiede tag @return, assenti in CodeWiki"),
    ("hallucination_rate", "Hallucination rate", "deriva dal Verifier Doxygen della pipeline"),
]


# ── Stile (palette categorica di riferimento, slot in ordine fisso) ───────────
C_PIPELINE = "#2a78d6"   # slot 1 - pipeline della tesi
C_CODEWIKI = "#eb6834"   # slot 2 - CodeWiki
C_MERMAID  = "#1baf7a"   # slot 3 - solo menzione Mermaid
C_NEUTRAL  = "#c9c8c2"   # non coperto (neutro, non e' una serie)
INK        = "#0b0b0b"
INK_2      = "#52514e"
GRID       = "#e6e5e0"
SURFACE    = "#ffffff"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK_2,
    "ytick.color": INK,
    "font.size": 10,
    "legend.frameon": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def _style_value_axis(ax, axis: str = "x", limit=(0, 1.0)):
    """Griglia recessiva sull'asse dei valori, baseline a zero."""
    if axis == "x":
        ax.set_xlim(*limit)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.spines["left"].set_visible(False)
    else:
        ax.set_ylim(*limit)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.spines["bottom"].set_visible(False)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _values(rows: List[Dict], key: str) -> List[float]:
    return [r[key] for r in rows if r.get(key) is not None]


# ── Caricamento dati pipeline ─────────────────────────────────────────────────

def _run_timestamp(report_path: str) -> str:
    cfg = os.path.join(os.path.dirname(report_path), "execution_config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                return json.load(f).get("timestamp", "")
        except (json.JSONDecodeError, OSError):
            pass
    return os.path.basename(os.path.dirname(report_path))


def load_pipeline_records(library: str, report_path: Optional[str], mode: str) -> Dict[str, Dict]:
    """
    Restituisce {function_name: record pipeline} per la libreria (record il cui id e' nel DB
    tra le righe della libreria).
    Senza report esplicito scandisce tutti i run in results/ (escluse le cartelle
    'latest', duplicati dell'ultimo run) e tiene il record piu' recente per funzione.
    """
    if report_path:
        paths = [report_path]
    else:
        pattern = "eval_report_*.json" if mode == "any" else f"eval_report_{mode}.json"
        paths = [
            p for p in glob.glob(os.path.join(RESULTS_DIR, "**", pattern), recursive=True)
            if os.path.basename(os.path.dirname(p)) != "latest"
        ]

    library_ids = {fn["db_id"] for fn in load_benchmark_functions(DB_PATH, library)}
    best: Dict[str, Dict] = {}
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, list):
            continue
        ts = _run_timestamp(p)
        for r in data:
            if not isinstance(r, dict) or r.get("id") not in library_ids:
                continue
            name = r.get("function_name")
            if name and (name not in best or ts > best[name]["_ts"]):
                best[name] = dict(r, _ts=ts, _report=os.path.relpath(p, ROOT_DIR))
    return best


def pipeline_metrics(rec: Dict, canonical_code: str) -> Dict[str, Any]:
    """Converte un record della pipeline nelle chiavi metriche canoniche."""
    m = rec.get("metrics", {})
    out = {k: m.get(pk) for k, pk in PIPELINE_KEYS.items()}

    doxygen = rec.get("generated_doxygen", "") or ""
    parsed = parse_doxygen_block(doxygen)
    edr = calculate_error_documentation_rate(canonical_code, parsed.get("returns", []), parsed.get("details", ""))
    ecc = calculate_edge_case_coverage(canonical_code, doxygen)
    out["error_doc_rate"] = edr["score"] if edr["has_code_error"] else None
    out["edge_case_coverage"] = ecc["coverage"] if ecc["code_guard_count"] > 0 else None
    for key, _, _, from_pipeline, _ in ADV_METRICS:
        out[key] = from_pipeline(rec)
    for key, _, _ in NOT_APPLICABLE:
        out[key] = m.get(key)
    out["function_name"] = rec["function_name"]
    out["run"] = rec["_report"]
    return out


def codewiki_advanced_metrics(cache_entry: Optional[Dict]) -> Dict[str, Any]:
    """Metriche avanzate CodeWiki dalla cache di evaluate_codewiki_advanced.py (None se assenti)."""
    return {key: (from_cw(cache_entry) if cache_entry else None) for key, _, _, _, from_cw in ADV_METRICS}


def codewiki_metrics_on_canonical_code(cw: Dict, canonical_code: str, cw_doc: str) -> Dict[str, Any]:
    """Ricalcola EDR/ECC CodeWiki sullo stesso codice canonico usato per la pipeline."""
    out = dict(cw)
    edr = calculate_error_documentation_rate(canonical_code, [], cw_doc)
    ecc = calculate_edge_case_coverage(canonical_code, cw_doc)
    out["error_doc_rate"] = edr["score"] if edr["has_code_error"] else None
    out["edge_case_coverage"] = ecc["coverage"] if ecc["code_guard_count"] > 0 else None
    return out


# ── Grafici solo CodeWiki ─────────────────────────────────────────────────────

def plot_cw_summary(rows: List[Dict], library: str, path: str):
    labels, means, stds, ns = [], [], [], []
    for key, label in METRICS:
        vals = _values(rows, key)
        labels.append(f"{label}  (n={len(vals)})")
        means.append(np.mean(vals) if vals else 0.0)
        stds.append(np.std(vals) if vals else 0.0)
        ns.append(len(vals))

    fig, ax = plt.subplots(figsize=(8, 5.2))
    y = np.arange(len(labels))[::-1]
    ax.barh(y, means, height=0.6, color=C_CODEWIKI, edgecolor=SURFACE, linewidth=2)
    # Deviazione standard troncata al dominio [0, 1] delle metriche
    lo = [m - max(0.0, m - sd) for m, sd in zip(means, stds)]
    hi = [min(1.0, m + sd) - m for m, sd in zip(means, stds)]
    ax.errorbar(means, y, xerr=[lo, hi], fmt="none", ecolor=INK_2, elinewidth=1, capsize=3)
    for yi, m, h, n in zip(y, means, hi, ns):
        ax.text(m + h + 0.02, yi, f"{m:.2f}" if n else "n/a", va="center", fontsize=9, color=INK)
    ax.set_yticks(y, labels)
    _style_value_axis(ax, "x", (0, 1.1))
    ax.set_xlabel("Media (barre di errore: deviazione standard, troncata a [0, 1])")
    ax.set_title(f"CodeWiki vs Ground Truth - metriche medie ({library})")
    fig.savefig(path)
    plt.close(fig)


def plot_cw_distributions(rows: List[Dict], path: str):
    data, labels = [], []
    for key, label in METRICS:
        vals = _values(rows, key)
        if vals:
            data.append(vals)
            labels.append(f"{label}  (n={len(vals)})")

    fig, ax = plt.subplots(figsize=(8, 5.6))
    pos = np.arange(len(data))[::-1]
    ax.boxplot(
        data, positions=pos, vert=False, widths=0.55, showfliers=False,
        patch_artist=True,
        boxprops=dict(facecolor="#f8d9cc", edgecolor=C_CODEWIKI, linewidth=1.2),
        medianprops=dict(color=C_CODEWIKI, linewidth=2),
        whiskerprops=dict(color=INK_2, linewidth=1), capprops=dict(color=INK_2, linewidth=1),
    )
    rng = np.random.default_rng(0)
    for p, vals in zip(pos, data):
        ax.scatter(vals, p + rng.uniform(-0.18, 0.18, len(vals)), s=10, color=C_CODEWIKI,
                   alpha=0.55, linewidths=0, zorder=3)
    ax.set_yticks(pos, labels)
    _style_value_axis(ax, "x", (-0.02, 1.02))
    ax.set_xlabel("Punteggio per funzione")
    ax.set_title("CodeWiki - distribuzione delle metriche per funzione")
    fig.savefig(path)
    plt.close(fig)


def plot_cw_coverage(summary: Dict, rows: List[Dict], path: str):
    """Barre impilate per classe: con testo / solo Mermaid / non coperte."""
    def cls(name: str) -> str:
        return name.split("::")[0] if "::" in name else "(free)"

    classes: Dict[str, List[int]] = {}
    for r in rows:
        c = classes.setdefault(cls(r["function_name"]), [0, 0, 0])
        c[0 if r["evaluated"] else 1] += 1
    for name in summary.get("uncovered_db_functions", []):
        classes.setdefault(cls(name), [0, 0, 0])[2] += 1

    order = sorted(classes, key=lambda c: -sum(classes[c]))
    doc = np.array([classes[c][0] for c in order])
    mer = np.array([classes[c][1] for c in order])
    unc = np.array([classes[c][2] for c in order])

    fig, ax = plt.subplots(figsize=(8, 0.5 * len(order) + 1.6))
    y = np.arange(len(order))[::-1]
    kw = dict(height=0.6, edgecolor=SURFACE, linewidth=2)
    ax.barh(y, doc, color=C_CODEWIKI, label="Con testo descrittivo", **kw)
    ax.barh(y, mer, left=doc, color=C_MERMAID, label="Solo diagramma Mermaid", **kw)
    ax.barh(y, unc, left=doc + mer, color=C_NEUTRAL, label="Non coperte", **kw)
    for yi, d, t in zip(y, doc, doc + mer + unc):
        ax.text(t + 0.3, yi, f"{d}/{t} con testo", va="center", fontsize=9, color=INK_2)
    ax.set_yticks(y, order)
    _style_value_axis(ax, "x", (0, max(doc + mer + unc) * 1.3))
    ax.set_xlabel("Funzioni uniche nel DB")
    tot = summary["total_db_functions"]
    ax.set_title(
        f"Copertura API di CodeWiki per classe - {summary['total_db_documented']}/{tot} con testo, "
        f"{summary['total_db_mentioned']}/{tot} menzionate"
    )
    ax.legend(loc="lower right", ncol=1, fontsize=9)
    fig.savefig(path)
    plt.close(fig)


def plot_length_ratio(cw_rows: List[Dict], pl_rows: Optional[List[Dict]], path: str):
    """Rapporto di lunghezza (scala diversa dalle altre metriche: grafico separato)."""
    series = [("CodeWiki", _values(cw_rows, "length_ratio"), C_CODEWIKI)]
    if pl_rows:
        series.insert(0, ("Pipeline tesi", _values(pl_rows, "length_ratio"), C_PIPELINE))
    fig, ax = plt.subplots(figsize=(8, 1.2 + 0.8 * len(series)))
    rng = np.random.default_rng(1)
    for i, (label, vals, color) in enumerate(series[::-1]):
        ax.scatter(vals, i + rng.uniform(-0.15, 0.15, len(vals)), s=14, color=color, alpha=0.6, linewidths=0)
        if vals:
            ax.plot([np.median(vals)] * 2, [i - 0.3, i + 0.3], color=INK, linewidth=2)
    ax.axvline(1.0, color=INK_2, linewidth=1, linestyle="--")
    ax.set_yticks(range(len(series)), [f"{s[0]} (n={len(s[1])})" for s in series[::-1]])
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Lunghezza doc generata / lunghezza GT (scala log; tratto nero = mediana, "
                  "tratteggio = stessa lunghezza del GT)")
    ax.set_title("Rapporto di lunghezza rispetto al Ground Truth")
    fig.savefig(path)
    plt.close(fig)


# ── Grafici di confronto ──────────────────────────────────────────────────────

def paired_values(cw: List[Dict], pl: List[Dict], key: str):
    """Coppie (cw, pl) sulle funzioni in cui la metrica e' definita per entrambi."""
    pl_by = {r["function_name"]: r for r in pl}
    pairs = [
        (c[key], pl_by[c["function_name"]][key])
        for c in cw
        if c["function_name"] in pl_by and c.get(key) is not None and pl_by[c["function_name"]].get(key) is not None
    ]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def wilcoxon_p(a: List[float], b: List[float]) -> Optional[float]:
    """Wilcoxon signed-rank (test appaiato). None se n < 6 o differenze tutte nulle."""
    if len(a) < 6 or all(x == y for x, y in zip(a, b)):
        return None
    from scipy.stats import wilcoxon
    return float(wilcoxon(a, b).pvalue)


def plot_cmp_bars(stats: List[Dict], n_pairs: int, library: str, path: str):
    fig, ax = plt.subplots(figsize=(8.5, 6))
    y = np.arange(len(stats))[::-1]
    h = 0.36
    pl = [s["pipeline_mean"] if s["n"] else 0 for s in stats]
    cw = [s["codewiki_mean"] if s["n"] else 0 for s in stats]
    ax.barh(y + h / 2, pl, height=h, color=C_PIPELINE, edgecolor=SURFACE, linewidth=2, label="Pipeline tesi")
    ax.barh(y - h / 2, cw, height=h, color=C_CODEWIKI, edgecolor=SURFACE, linewidth=2, label="CodeWiki")
    for yi, s, a, b in zip(y, stats, pl, cw):
        if not s["n"]:
            ax.text(0.01, yi, "non applicabile su queste funzioni", va="center", fontsize=8, color=INK_2)
            continue
        ax.text(a + 0.01, yi + h / 2, f"{a:.2f}", va="center", fontsize=8, color=INK)
        ax.text(b + 0.01, yi - h / 2, f"{b:.2f}", va="center", fontsize=8, color=INK)
    labels = []
    for s in stats:
        star = " *" if s["p_value"] is not None and s["p_value"] < 0.05 else ""
        labels.append(f"{s['label']}{star}  (n={s['n']})")
    ax.set_yticks(y, labels)
    _style_value_axis(ax, "x", (0, 1.08))
    ax.set_xlabel("Media sulle funzioni valutate da entrambi i sistemi"
                  "   (* = differenza significativa, Wilcoxon p < 0.05)")
    ax.set_title(f"Pipeline tesi vs CodeWiki - metriche medie ({n_pairs} funzioni {library} in comune)", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9, borderaxespad=0.2)
    fig.savefig(path)
    plt.close(fig)


def plot_cmp_distributions(cw: List[Dict], pl: List[Dict], path: str):
    keys = [(k, l) for k, l in METRICS]
    ncols = 5
    nrows = int(np.ceil(len(keys) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(13, 3.0 * nrows), sharey=True)
    rng = np.random.default_rng(2)
    for ax, (key, label) in zip(axes.flat, keys):
        a, b = paired_values(cw, pl, key)
        ax.set_title(f"{label} (n={len(a)})", fontsize=10)
        _style_value_axis(ax, "y", (-0.03, 1.03))
        if not a:
            ax.set_xticks([0, 1], ["Pipeline", "CodeWiki"])
            ax.text(0.5, 0.5, "n/a", ha="center", transform=ax.transAxes, color=INK_2)
            continue
        for x, vals, color in [(0, b, C_PIPELINE), (1, a, C_CODEWIKI)]:
            ax.boxplot([vals], positions=[x], widths=0.5, showfliers=False,
                       medianprops=dict(color=color, linewidth=2),
                       boxprops=dict(color=color), whiskerprops=dict(color=INK_2), capprops=dict(color=INK_2))
            ax.scatter(x + rng.uniform(-0.12, 0.12, len(vals)), vals, s=10, color=color, alpha=0.6, linewidths=0, zorder=3)
        ax.set_xticks([0, 1], ["Pipeline", "CodeWiki"])
        ax.set_xlim(-0.6, 1.6)
    for ax in list(axes.flat)[len(keys):]:
        ax.set_visible(False)
    fig.suptitle("Distribuzioni per metrica - stesse funzioni per entrambi i sistemi",
                 x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_cmp_paired(cw: List[Dict], pl: List[Dict], path: str):
    """Dumbbell per funzione: SBERT, BERTScore, METEOR affiancati, ordinati per delta SBERT."""
    pl_by = {r["function_name"]: r for r in pl}
    common = [c for c in cw if c["function_name"] in pl_by and c.get("sbert_similarity") is not None]
    common.sort(key=lambda c: (pl_by[c["function_name"]].get("sbert_similarity") or 0) - c["sbert_similarity"])
    panels = [("sbert_similarity", "SBERT"), ("bertscore_f1", "BERTScore F1"), ("meteor_score", "METEOR")]

    fig, axes = plt.subplots(1, 3, figsize=(13, 0.32 * len(common) + 1.8), sharey=True)
    y = np.arange(len(common))
    for ax, (key, label) in zip(axes, panels):
        for yi, c in zip(y, common):
            a, b = c.get(key), pl_by[c["function_name"]].get(key)
            if a is None or b is None:
                continue
            ax.plot([a, b], [yi, yi], color=GRID, linewidth=2, zorder=1)
            ax.scatter([b], [yi], s=36, color=C_PIPELINE, edgecolor=SURFACE, linewidth=1.5, zorder=3)
            ax.scatter([a], [yi], s=36, color=C_CODEWIKI, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.set_title(label, fontsize=10)
        _style_value_axis(ax, "x", (0, 1.0))
    axes[0].set_yticks(y, [c["function_name"] for c in common], fontsize=8)
    axes[0].scatter([], [], s=36, color=C_PIPELINE, label="Pipeline tesi")
    axes[0].scatter([], [], s=36, color=C_CODEWIKI, label="CodeWiki")
    fig.legend(loc="upper right", ncol=2, fontsize=9)
    fig.suptitle("Confronto per funzione (ordinate per vantaggio SBERT della pipeline)",
                 x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path)
    plt.close(fig)


def plot_cmp_advanced(cw: List[Dict], pl: List[Dict], path: str) -> bool:
    """Small multiples: un pannello per metrica avanzata (asse proprio), media + punti per funzione."""
    panels = [(k, l, lim) for k, l, lim, _, _ in ADV_METRICS if paired_values(cw, pl, k)[0]]
    if not panels:
        return False
    ncols = 3
    nrows = int(np.ceil(len(panels) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 3.2 * nrows), squeeze=False)
    rng = np.random.default_rng(3)
    for ax, (key, label, lim) in zip(axes.flat, panels):
        a, b = paired_values(cw, pl, key)
        p = wilcoxon_p(a, b)
        star = " *" if p is not None and p < 0.05 else ""
        ax.set_title(f"{label}{star} (n={len(a)})", fontsize=10)
        base = lim[0]
        for x, vals, color in [(0, b, C_PIPELINE), (1, a, C_CODEWIKI)]:
            m = float(np.mean(vals))
            ax.bar(x, m - base, bottom=base, width=0.55, color=color, alpha=0.85, edgecolor=SURFACE, linewidth=2)
            ax.scatter(x + rng.uniform(-0.15, 0.15, len(vals)), vals, s=10, color=INK_2, alpha=0.5, linewidths=0, zorder=3)
            # Valore medio alla base della barra (in alto collide con i punti delle funzioni)
            pad = (lim[1] - lim[0]) * 0.03
            inside = m - base > (lim[1] - lim[0]) * 0.12
            ax.text(x, base + pad if inside else m + pad, f"{m:.2f}" if lim[1] <= 5 else f"{m:.0f}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold",
                    color=SURFACE if inside else INK, zorder=4)
        ax.set_xticks([0, 1], ["Pipeline", "CodeWiki"])
        ax.set_xlim(-0.6, 1.6)
        _style_value_axis(ax, "y", (lim[0], lim[1] + (lim[1] - lim[0]) * 0.1))
    for ax in list(axes.flat)[len(panels):]:
        ax.set_visible(False)
    fig.suptitle("Metriche avanzate - stesse funzioni per entrambi i sistemi  "
                 "(barra = media, punti = singole funzioni, * = Wilcoxon p < 0.05)",
                 x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path)
    plt.close(fig)
    return True


# ── Report di confronto ───────────────────────────────────────────────────────

def compare_stats(cw: List[Dict], pl: List[Dict]) -> List[Dict]:
    stats = []
    advanced = [(k, l) for k, l, _, _, _ in ADV_METRICS]
    for key, label in METRICS + [("length_ratio", "Length ratio")] + advanced:
        a, b = paired_values(cw, pl, key)
        stats.append({
            "metric": key,
            "label": label,
            "group": "advanced" if (key, label) in advanced else "nlp",
            "n": len(a),
            "codewiki_mean": round(float(np.mean(a)), 4) if a else None,
            "pipeline_mean": round(float(np.mean(b)), 4) if b else None,
            "delta": round(float(np.mean(b) - np.mean(a)), 4) if a else None,
            "p_value": wilcoxon_p(a, b) if key != "length_ratio" else None,
        })
    return stats


def write_comparison_report(paths: LibraryPaths, stats: List[Dict], cw_common: List[Dict], pl_common: List[Dict],
                            n_cw_eval: int, missing: List[str], runs: List[str],
                            extra_lines: Optional[List[str]] = None):
    library = paths.library
    def f(v, nd=4):
        return f"{v:.{nd}f}" if v is not None else "N/A"

    n = len(cw_common)
    lines = [
        f"# Confronto: Pipeline della tesi vs CodeWiki ({library})",
        "",
        "> **Script**: `utils/plot_codewiki_comparison.py`  ",
        f"> **Funzioni confrontate**: {n} (valutate da entrambi i sistemi) su {n_cw_eval} documentate da CodeWiki  ",
        f"> **Run della pipeline usati**: {', '.join(f'`{r}`' for r in runs) or 'nessuno'}  ",
        "",
    ]
    if n < 20:
        lines += [
            f"> ⚠️ **Campione ridotto (n={n})**: le differenze non sono statisticamente affidabili.",
            "> Per un confronto completo eseguire la pipeline sulle stesse funzioni di CodeWiki:",
            f"> `.venv/Scripts/python utils/benchmark_eval.py -l {library} -m multiagent "
            f"--functions compare_CodeWiki/{os.path.basename(paths.dir)}/codewiki_function_list.txt`",
            "",
        ]
    lines += [
        "## Metriche medie sulle funzioni in comune",
        "",
        "| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |",
        "|---------|---|----------|----------|--------------------------|------------|",
    ]
    def table_rows(group: str):
        for s in stats:
            if s["group"] != group:
                continue
            p = "n<6" if s["p_value"] is None and 0 < s["n"] < 6 else f(s["p_value"])
            lines.append(f"| {s['label']} | {s['n']} | {f(s['pipeline_mean'])} | {f(s['codewiki_mean'])} | "
                         f"{f(s['delta'])} | {p} |")

    table_rows("nlp")
    lines += [
        "",
        "## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)",
        "",
    ]
    if not any(s["n"] for s in stats if s["group"] == "advanced"):
        lines += [
            "*Non ancora calcolate per CodeWiki: eseguire*",
            f"`.venv/Scripts/python utils/evaluate_codewiki_advanced.py -l {library}`",
            "*(oppure `evaluate_codewiki_metrics.py --full`).*",
        ]
    else:
        lines += [
            "| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |",
            "|---------|---|----------|----------|--------------------------|------------|",
        ]
        table_rows("advanced")
    lines += [
        "",
        "Metriche della pipeline non applicabili a CodeWiki:",
        "",
        "| Metrica | Pipeline | Motivo |",
        "|---------|----------|--------|",
    ]
    for key, label, reason in NOT_APPLICABLE:
        vals = [r[key] for r in pl_common if r.get(key) is not None]
        lines.append(f"| {label} | {f(float(np.mean(vals))) if vals else 'N/A'} | {reason} |")
    lines += [
        "",
        "## Dettaglio per funzione (SBERT)",
        "",
        "| Funzione | Pipeline | CodeWiki | Run pipeline |",
        "|----------|----------|----------|--------------|",
    ]
    pl_by = {r["function_name"]: r for r in pl_common}
    for c in sorted(cw_common, key=lambda c: c["function_name"]):
        p = pl_by[c["function_name"]]
        lines.append(f"| `{c['function_name']}` | {f(p.get('sbert_similarity'))} | "
                     f"{f(c.get('sbert_similarity'))} | `{p['run']}` |")
    lines += extra_lines or []
    lines += [
        "",
        "## Note metodologiche",
        "",
        "- Le metriche semantiche della pipeline sono quelle salvate nei suoi report (stesse funzioni",
        "  di `utils/benchmark_metrics.py`, calcolate su `@brief` + `@details` vs GT); per CodeWiki",
        "  il candidato e' il testo dei bullet Markdown associati alla funzione.",
        "- EDR ed ECC sono ricalcolate per entrambi i sistemi sullo stesso codice (file di",
        "  implementazione se presente) e considerate solo dove il codice contiene rami di errore / guardie.",
        "- Il test di Wilcoxon (appaiato, a due code) e' riportato solo per n >= 6.",
        "- Judge e round-trip CodeWiki usano la stessa configurazione della pipeline",
        "  (gemini-3.5-flash-lite, judge T=0.4 con 5 round per prospettiva, `RoundTripEvaluator`),",
        "  le stesse righe del DB (firma, codice, GT) e come documentazione il testo CodeWiki.",
        f"  Retrieval: stesso corpus {library} della pipeline; query = testo della documentazione.",
        f"- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: {len(missing)}.",
        "",
        "*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*",
    ]
    with open(paths.cmp_report, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_all_charts(library: str, pipeline_report: Optional[str] = None,
                        pipeline_mode: str = "multiagent") -> List[str]:
    canonical = resolve_library(library)
    if canonical is None:
        raise SystemExit(f"[ERRORE] '{library}' non e' presente in {DB_PATH}")
    library = canonical
    paths = lib_paths(library)
    for needed in (paths.results_json, paths.summary_json, paths.mapped_json):
        if not os.path.exists(needed):
            raise SystemExit(f"[ERRORE] File non trovato: {needed}\n"
                             f"  Esegui prima evaluate_codewiki_metrics.py -l {library}")

    os.makedirs(paths.charts_dir, exist_ok=True)
    with open(paths.results_json, encoding="utf-8") as f:
        cw_all = json.load(f)
    with open(paths.summary_json, encoding="utf-8") as f:
        summary = json.load(f)
    cw_eval = [r for r in cw_all if r["evaluated"]]
    if not cw_eval:
        print(f"  [WARN] {library}: nessuna funzione con testo CodeWiki valutata, grafici non generati.")
        return []

    out = []
    def save(fn, *a):
        p = os.path.join(paths.charts_dir, a[-1])
        fn(*a[:-1], p)
        out.append(p)

    save(plot_cw_summary, cw_eval, library, "cw_metrics_summary.png")
    save(plot_cw_distributions, cw_eval, "cw_metrics_distributions.png")
    save(plot_cw_coverage, summary, cw_all, "cw_coverage_by_class.png")

    # ── Confronto con la pipeline ─────────────────────────────────────────────
    groups = group_db_functions(load_benchmark_functions(DB_PATH, library))
    pipeline = load_pipeline_records(library, pipeline_report, pipeline_mode)
    common_names = sorted({r["function_name"] for r in cw_eval} & set(pipeline))
    missing = sorted({r["function_name"] for r in cw_eval} - set(pipeline))

    with open(paths.mapped_json, encoding="utf-8") as f:
        mapped = json.load(f)
    cw_docs: Dict[str, List[str]] = {}
    for m in mapped:
        if m.get("matched") and m.get("doc_source") == "bullet":
            texts = cw_docs.setdefault(m["db_function_name"], [])
            if m["codewiki_doc"].strip() not in texts:
                texts.append(m["codewiki_doc"].strip())

    adv_cache: Dict[str, Dict] = {}
    if os.path.exists(paths.adv_results):
        with open(paths.adv_results, encoding="utf-8") as f:
            adv_cache = json.load(f)

    cw_common, pl_common = [], []
    for name in common_names:
        code = groups[name]["source_code"] if name in groups else ""
        cw_rec = next(r for r in cw_eval if r["function_name"] == name)
        cw_row = codewiki_metrics_on_canonical_code(cw_rec, code, " ".join(cw_docs.get(name, [])))
        cw_row.update(codewiki_advanced_metrics(adv_cache.get(name)))
        cw_common.append(cw_row)
        pl_common.append(pipeline_metrics(pipeline[name], code))

    save(plot_length_ratio, cw_eval, pl_common or None, "cw_length_ratio.png")

    print(f"  Pipeline: {len(pipeline)} funzioni {library} nei run ({pipeline_mode}), "
          f"{len(common_names)} in comune con le {len(cw_eval)} documentate da CodeWiki")

    if not common_names:
        print("  [WARN] Nessuna funzione in comune: grafici di confronto non generati.")
        return out

    stats = compare_stats(cw_common, pl_common)
    save(plot_cmp_bars, [s for s in stats if s["group"] == "nlp" and s["metric"] != "length_ratio"],
         len(common_names), library, "cmp_metrics_bars.png")
    save(plot_cmp_distributions, cw_common, pl_common, "cmp_distributions.png")
    save(plot_cmp_paired, cw_common, pl_common, "cmp_paired_functions.png")
    adv_path = os.path.join(paths.charts_dir, "cmp_advanced_metrics.png")
    if plot_cmp_advanced(cw_common, pl_common, adv_path):
        out.append(adv_path)
    else:
        print("  [INFO] Metriche avanzate CodeWiki non ancora calcolate: grafico avanzato non generato.")

    runs = sorted({p["run"] for p in pl_common})

    # Grafici e analisi aggiuntivi: round-trip per funzione, tassonomia errori, panoramica metriche
    from utils.plot_codewiki_extra import generate_extra
    extra_files, extra_lines, extra_summary = generate_extra(
        paths, library, cw_common, pl_common, common_names, pipeline, adv_cache)
    out += extra_files

    write_comparison_report(paths, stats, cw_common, pl_common, len(cw_eval), missing, runs, extra_lines)
    with open(paths.cmp_json, "w", encoding="utf-8") as f:
        json.dump({
            "library": library,
            "n_common": len(common_names),
            "n_codewiki_documented": len(cw_eval),
            "pipeline_runs": runs,
            "missing_in_pipeline": missing,
            "metrics": stats,
            "extra": extra_summary,
        }, f, ensure_ascii=False, indent=2, default=list)
    out += [paths.cmp_report, paths.cmp_json]
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Grafici CodeWiki e confronto con la pipeline della tesi")
    parser.add_argument("-l", "--library", default="TinyXML-2", help="Libreria da confrontare (default: TinyXML-2)")
    parser.add_argument("--pipeline-report", default=None,
                        help="eval_report_*.json specifico (default: tutti i run in results/, il piu' recente per funzione)")
    parser.add_argument("--pipeline-mode", default="multiagent", choices=["multiagent", "single", "any"],
                        help="Modalita' della pipeline da confrontare (default: multiagent)")
    args = parser.parse_args()
    for p in generate_all_charts(args.library, args.pipeline_report, args.pipeline_mode):
        print(f"  -> {os.path.relpath(p, ROOT_DIR)}")


if __name__ == "__main__":
    main()
