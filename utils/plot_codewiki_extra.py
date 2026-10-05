"""
plot_codewiki_extra.py
----------------------
Analisi e grafici aggiuntivi del confronto CodeWiki vs pipeline della tesi, chiamati da
utils/plot_codewiki_comparison.py (generate_all_charts):

  Round-trip (Doc-to-Code + test differenziali)
    cmp_roundtrip_per_function.png   pass rate e dual agreement per funzione, con i casi anomali
                                     (timeout, sintesi vuota, test che falliscono anche sul reference)
    cmp_roundtrip_errors.png         tipologie di test falliti, pipeline vs CodeWiki
                                     (stessa tassonomia di utils/roundtrip_error_analysis.py)
  Panoramica di tutte le metriche
    cmp_delta_heatmap.png            funzione x metrica: chi vince e di quanto
    cmp_win_loss.png                 per metrica: funzioni vinte / pareggiate / perse
    cmp_advanced_per_function.png    judge, retrieval, CodeBERTScore e actionability per funzione

Tutte le funzioni di questo modulo lavorano solo su dati gia' calcolati: nessuna chiamata API.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

from utils.roundtrip_error_analysis import analyze_roundtrip_errors
from utils.plot_codewiki_comparison import (
    C_PIPELINE, C_CODEWIKI, C_NEUTRAL, INK, INK_2, GRID, SURFACE,
    _style_value_axis, paired_values, wilcoxon_p,
)

TIE_FRACTION = 0.01  # |delta| sotto l'1% del range della metrica = pareggio

# (chiave, etichetta, range) delle metriche mostrate nella heatmap / nel grafico vittorie-sconfitte
OVERVIEW_METRICS: List[Tuple[str, str, float]] = [
    ("sbert_similarity", "SBERT", 1.0),
    ("bertscore_f1", "BERTScore F1", 1.0),
    ("meteor_score", "METEOR", 1.0),
    ("tfidf_cosine", "TF-IDF cosine", 1.0),
    ("rouge_l", "ROUGE-L", 1.0),
    ("concept_checklist_score", "Concept checklist", 1.0),
    ("actionability_score", "Actionability", 1.0),
    ("error_doc_rate", "Error doc. rate", 1.0),
    ("edge_case_coverage", "Edge case coverage", 1.0),
    ("codebert_f1", "CodeBERTScore F1", 1.0),
    ("retrieval_rr", "Retrieval MRR", 1.0),
    ("judge_a", "Judge A - Faithfulness", 4.0),
    ("judge_b", "Judge B - Alignment", 4.0),
    ("roundtrip_pass_rate", "Round-trip pass rate", 100.0),
    ("roundtrip_dual_agreement", "Dual agreement", 100.0),
]


# ── Round-trip: estrazione e classificazione ──────────────────────────────────

def _rt_info(rt: Optional[Dict]) -> Optional[Dict[str, Any]]:
    """Riassunto di un risultato round-trip, con i flag dei casi anomali."""
    if not rt:
        return None
    ex = rt.get("execution", {}) or {}
    diff = ex.get("differential", {}) or {}
    output = (ex.get("test_output") or "")
    total = ex.get("total_tests", 0) or 0
    flags = []
    if not (rt.get("synthesized_code") or "").strip():
        flags.append("sintesi vuota")
    if "timed out" in output.lower() or "timeout" in output.lower():
        flags.append("timeout")
    if diff.get("reference_total", 0) and diff.get("reference_passed", 0) == 0:
        flags.append("test falliscono sul reference")
    return {
        "pass_rate": ex.get("pass_rate"),
        "total_tests": total,
        "passed": ex.get("passed", 0),
        "dual": diff.get("differential_agreement_rate"),
        "ref_pass": diff.get("reference_pass_rate"),
        "flags": flags,
        "no_tests": total == 0,
    }


def collect_roundtrip(names: List[str], pipeline_records: Dict[str, Dict],
                      adv_cache: Dict[str, Dict]) -> Dict[str, Dict[str, Optional[Dict]]]:
    """{funzione: {"pipeline": info, "codewiki": info, "_raw": (rt pipeline, rt codewiki)}}"""
    out = {}
    for n in names:
        rt_p = (pipeline_records.get(n) or {}).get("roundtrip")
        rt_c = (adv_cache.get(n) or {}).get("roundtrip")
        out[n] = {"pipeline": _rt_info(rt_p), "codewiki": _rt_info(rt_c), "_raw": (rt_p, rt_c)}
    return out


# ── Grafici round-trip ────────────────────────────────────────────────────────

def plot_roundtrip_per_function(rt: Dict[str, Dict], library: str, path: str) -> bool:
    names = [n for n, v in rt.items() if v["pipeline"] and v["codewiki"]]
    if not names:
        return False
    # ordine: differenza di pass rate (la pipeline avanti in basso, CodeWiki avanti in alto)
    names.sort(key=lambda n: (rt[n]["pipeline"]["pass_rate"] or 0) - (rt[n]["codewiki"]["pass_rate"] or 0))
    y = np.arange(len(names))

    fig, axes = plt.subplots(1, 2, figsize=(12, 0.34 * len(names) + 2.2), sharey=True)
    panels = [("pass_rate", "Round-trip pass rate (%)"), ("dual", "Dual agreement (%)")]
    for ax, (key, title) in zip(axes, panels):
        for yi, n in zip(y, names):
            p, c = rt[n]["pipeline"], rt[n]["codewiki"]
            a, b = p[key], c[key]
            if a is None or b is None:
                continue
            ax.plot([a, b], [yi, yi], color=GRID, linewidth=2, zorder=1)
            # a pari valore i due punti coinciderebbero: si spostano un po' in verticale
            dy = 0.14 if a == b else 0.0
            for val, info, color, off in [(a, p, C_PIPELINE, dy), (b, c, C_CODEWIKI, -dy)]:
                if info["no_tests"]:
                    # nessun test eseguito (timeout / sintesi vuota): cerchio vuoto, non e' uno zero "vero"
                    ax.scatter([val], [yi + off], s=52, facecolor=SURFACE, edgecolor=color, linewidth=1.8, zorder=3)
                else:
                    ax.scatter([val], [yi + off], s=40, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.set_title(title, fontsize=10)
        _style_value_axis(ax, "x", (-3, 103))
    axes[0].set_yticks(y, names, fontsize=8)
    axes[0].scatter([], [], s=40, color=C_PIPELINE, label="Pipeline tesi")
    axes[0].scatter([], [], s=40, color=C_CODEWIKI, label="CodeWiki")
    axes[0].scatter([], [], s=52, facecolor=SURFACE, edgecolor=INK_2, linewidth=1.8,
                    label="nessun test eseguito (timeout / sintesi vuota)")
    fig.legend(loc="upper left", bbox_to_anchor=(0.01, 0.945), ncol=3, fontsize=9)
    fig.suptitle(f"Round-trip per funzione - {library} (ordinate per vantaggio della pipeline)",
                 x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path)
    plt.close(fig)
    return True


def roundtrip_error_tables(rt: Dict[str, Dict]) -> Optional[Dict[str, Dict]]:
    """Tassonomia degli errori per entrambi i sistemi, sulle stesse funzioni."""
    names = [n for n, v in rt.items() if v["pipeline"] and v["codewiki"]]
    if not names:
        return None
    out = {}
    for label, idx in (("pipeline", 0), ("codewiki", 1)):
        results = [rt[n]["_raw"][idx] for n in names]
        out[label] = analyze_roundtrip_errors(results)
    return out


def plot_roundtrip_errors(analysis: Dict[str, Dict], library: str, path: str) -> bool:
    cats: Dict[str, Dict[str, int]] = {}
    for label, a in analysis.items():
        for c in a["categories"]:
            cats.setdefault(c["category"], {"pipeline": 0, "codewiki": 0})[label] = c["count"]
    if not cats:
        return False
    order = sorted(cats, key=lambda c: -(cats[c]["pipeline"] + cats[c]["codewiki"]))
    y = np.arange(len(order))[::-1]
    h = 0.36
    fig, ax = plt.subplots(figsize=(9, 0.62 * len(order) + 2.0))
    pl = [cats[c]["pipeline"] for c in order]
    cw = [cats[c]["codewiki"] for c in order]
    ax.barh(y + h / 2, pl, height=h, color=C_PIPELINE, edgecolor=SURFACE, linewidth=2, label="Pipeline tesi")
    ax.barh(y - h / 2, cw, height=h, color=C_CODEWIKI, edgecolor=SURFACE, linewidth=2, label="CodeWiki")
    top = max(pl + cw + [1])
    for yi, a, b in zip(y, pl, cw):
        ax.text(a + top * 0.01, yi + h / 2, str(a), va="center", fontsize=9, color=INK)
        ax.text(b + top * 0.01, yi - h / 2, str(b), va="center", fontsize=9, color=INK)
    ax.set_yticks(y, order)
    _style_value_axis(ax, "x", (0, top * 1.12))
    ax.set_xlabel("Test falliti per tipologia di errore (sulle stesse funzioni)")
    ax.set_title(f"Round-trip: perche' i test falliscono - {library}", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9, borderaxespad=0.2)
    fig.savefig(path)
    plt.close(fig)
    return True


# ── Panoramica di tutte le metriche ───────────────────────────────────────────

def _delta_matrix(cw: List[Dict], pl: List[Dict]):
    """(nomi, metriche valide, matrice delta normalizzata, matrice delta grezza) con NaN dove manca un valore."""
    metrics = [m for m in OVERVIEW_METRICS if any(r.get(m[0]) is not None for r in cw)
               and any(r.get(m[0]) is not None for r in pl)]
    names = [c["function_name"] for c in cw]
    pl_by = {r["function_name"]: r for r in pl}
    raw = np.full((len(names), len(metrics)), np.nan)
    for i, c in enumerate(cw):
        p = pl_by[c["function_name"]]
        for j, (key, _, _) in enumerate(metrics):
            a, b = p.get(key), c.get(key)
            if a is not None and b is not None:
                raw[i, j] = a - b
    ranges = np.array([m[2] for m in metrics])
    return names, metrics, raw / ranges, raw


def plot_delta_heatmap(cw: List[Dict], pl: List[Dict], library: str, path: str) -> bool:
    names, metrics, norm, raw = _delta_matrix(cw, pl)
    if not names or not metrics:
        return False
    # righe ordinate per vantaggio medio della pipeline
    order = np.argsort(np.nanmean(np.where(np.isnan(norm), 0, norm), axis=1))
    norm, raw = norm[order], raw[order]
    names = [names[i] for i in order]

    cmap = LinearSegmentedColormap.from_list("cw_vs_pl", [C_CODEWIKI, "#f2f1ed", C_PIPELINE])
    cmap.set_bad("#ffffff")
    lim = 0.6
    fig, ax = plt.subplots(figsize=(0.62 * len(metrics) + 4.5, 0.32 * len(names) + 2.6))
    im = ax.imshow(np.ma.masked_invalid(norm), cmap=cmap, norm=Normalize(-lim, lim), aspect="auto")
    ax.set_xticks(range(len(metrics)), [m[1] for m in metrics], rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(names)), names, fontsize=8)
    ax.xaxis.tick_top()
    plt.setp(ax.get_xticklabels(), rotation=40, ha="left", rotation_mode="anchor")
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks(np.arange(-.5, len(metrics), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(names), 1), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    for i in range(norm.shape[0]):
        for j in range(norm.shape[1]):
            if np.isnan(norm[i, j]):
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=6, color=INK_2)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Differenza (Pipeline - CodeWiki), in frazione del range della metrica", fontsize=8)
    cbar.ax.tick_params(labelsize=8, length=0)
    fig.suptitle(f"Chi vince, funzione per funzione - {library}   (blu = meglio la pipeline, arancio = meglio CodeWiki)",
                 x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK, y=1.0)
    fig.savefig(path)
    plt.close(fig)
    return True


def win_loss_counts(cw: List[Dict], pl: List[Dict]) -> List[Dict[str, Any]]:
    rows = []
    for key, label, rng in OVERVIEW_METRICS:
        a, b = paired_values(cw, pl, key)  # a = CodeWiki, b = pipeline
        if not a:
            continue
        d = np.array(b) - np.array(a)
        eps = TIE_FRACTION * rng
        rows.append({
            "metric": key, "label": label, "n": len(a),
            "pipeline_wins": int((d > eps).sum()),
            "ties": int((np.abs(d) <= eps).sum()),
            "codewiki_wins": int((d < -eps).sum()),
        })
    return rows


def plot_win_loss(rows: List[Dict[str, Any]], library: str, path: str) -> bool:
    if not rows:
        return False
    rows = sorted(rows, key=lambda r: (r["pipeline_wins"] - r["codewiki_wins"]) / max(r["n"], 1))
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(9.5, 0.42 * len(rows) + 2.2))
    kw = dict(height=0.62, edgecolor=SURFACE, linewidth=2)
    cw_w = np.array([r["codewiki_wins"] / r["n"] * 100 for r in rows])
    ties = np.array([r["ties"] / r["n"] * 100 for r in rows])
    pl_w = np.array([r["pipeline_wins"] / r["n"] * 100 for r in rows])
    ax.barh(y, cw_w, color=C_CODEWIKI, label="CodeWiki meglio", **kw)
    ax.barh(y, ties, left=cw_w, color=C_NEUTRAL, label="pareggio", **kw)
    ax.barh(y, pl_w, left=cw_w + ties, color=C_PIPELINE, label="Pipeline meglio", **kw)
    for yi, r, a, t, p in zip(y, rows, cw_w, ties, pl_w):
        if a >= 8:
            ax.text(a / 2, yi, str(r["codewiki_wins"]), ha="center", va="center", fontsize=8, color=SURFACE, fontweight="bold")
        if p >= 8:
            ax.text(a + t + p / 2, yi, str(r["pipeline_wins"]), ha="center", va="center", fontsize=8, color=SURFACE, fontweight="bold")
    ax.set_yticks(y, [f"{r['label']}  (n={r['n']})" for r in rows])
    _style_value_axis(ax, "x", (0, 100))
    ax.set_xlabel("% delle funzioni (pareggio = differenza sotto l'1% del range della metrica)")
    ax.set_title(f"Vittorie, pareggi e sconfitte per metrica - {library}", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9, borderaxespad=0.2)
    fig.savefig(path)
    plt.close(fig)
    return True


def plot_advanced_per_function(cw: List[Dict], pl: List[Dict], library: str, path: str) -> bool:
    """Dumbbell per funzione di judge, retrieval, CodeBERTScore e actionability."""
    pl_by = {r["function_name"]: r for r in pl}
    panels = [
        ("judge_combined", "Judge combinato (1-5)", (1, 5)),
        ("retrieval_rr", "Retrieval - reciprocal rank", (0, 1)),
        ("codebert_f1", "CodeBERTScore F1", (0, 1)),
        ("actionability_score", "Actionability", (0, 1)),
    ]
    panels = [p for p in panels if any(c.get(p[0]) is not None for c in cw)]
    common = [c for c in cw if c["function_name"] in pl_by]
    if not panels or not common:
        return False
    key0 = panels[0][0]
    common.sort(key=lambda c: (pl_by[c["function_name"]].get(key0) or 0) - (c.get(key0) or 0))
    y = np.arange(len(common))
    fig, axes = plt.subplots(1, len(panels), figsize=(3.4 * len(panels) + 2.5, 0.32 * len(common) + 2.0), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (key, title, lim) in zip(axes, panels):
        for yi, c in zip(y, common):
            a, b = c.get(key), pl_by[c["function_name"]].get(key)
            if a is None or b is None:
                continue
            ax.plot([a, b], [yi, yi], color=GRID, linewidth=2, zorder=1)
            dy = 0.14 if a == b else 0.0
            ax.scatter([b], [yi + dy], s=36, color=C_PIPELINE, edgecolor=SURFACE, linewidth=1.5, zorder=3)
            ax.scatter([a], [yi - dy], s=36, color=C_CODEWIKI, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.set_title(title, fontsize=10)
        pad = (lim[1] - lim[0]) * 0.03
        _style_value_axis(ax, "x", (lim[0] - pad, lim[1] + pad))
    axes[0].set_yticks(y, [c["function_name"] for c in common], fontsize=8)
    axes[0].scatter([], [], s=36, color=C_PIPELINE, label="Pipeline tesi")
    axes[0].scatter([], [], s=36, color=C_CODEWIKI, label="CodeWiki")
    fig.legend(loc="upper left", bbox_to_anchor=(0.01, 0.945), ncol=2, fontsize=9)
    fig.suptitle(f"Judge, retrieval, CodeBERTScore e actionability per funzione - {library}",
                 x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path)
    plt.close(fig)
    return True


# ── Testo per il report ───────────────────────────────────────────────────────

def _f(v, nd=1):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "N/A"


def roundtrip_report(rt: Dict[str, Dict], analysis: Optional[Dict[str, Dict]]) -> Tuple[List[str], Dict[str, Any]]:
    """Sezioni Markdown sul round-trip e un dizionario riassuntivo per il JSON."""
    names = sorted(n for n, v in rt.items() if v["pipeline"] and v["codewiki"])
    if not names:
        return [], {}

    def row(n):
        return rt[n]["pipeline"], rt[n]["codewiki"]

    lines = [
        "",
        "## Round-trip: dettaglio per funzione",
        "",
        "| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |",
        "|----------|-----------------------|------------------------|---------------|---------------|----------|",
    ]
    for n in names:
        p, c = row(n)
        notes = []
        if p["flags"]:
            notes.append("pipeline: " + ", ".join(p["flags"]))
        if c["flags"]:
            notes.append("CodeWiki: " + ", ".join(c["flags"]))
        lines.append(
            f"| `{n}` | {_f(p['pass_rate'])} ({p['total_tests']}) | {_f(c['pass_rate'])} ({c['total_tests']}) | "
            f"{_f(p['dual'])} | {_f(c['dual'])} | {'; '.join(notes) or '-'} |")

    # ── casi senza test eseguiti
    anomalous = [(n, s, rt[n][s]) for n in names for s in ("pipeline", "codewiki") if rt[n][s]["no_tests"]]
    lines += [
        "",
        "### Funzioni senza test eseguiti",
        "",
    ]
    if anomalous:
        lines += [
            "Un pass rate 0% con **0 test eseguiti** non misura la qualita' della documentazione: "
            "i test non sono nemmeno partiti.",
            "",
            "| Funzione | Sistema | Causa | Test generati passano sul reference |",
            "|----------|---------|-------|-------------------------------------|",
        ]
        for n, s, info in anomalous:
            lines.append(f"| `{n}` | {'Pipeline' if s == 'pipeline' else 'CodeWiki'} | "
                         f"{', '.join(info['flags']) or 'non determinata'} | {_f(info['ref_pass'])}% |")
    else:
        lines.append("Nessuna: tutte le funzioni hanno eseguito almeno un test in entrambi i sistemi.")

    n_ref_fail = {s: sum(1 for n in names if "test falliscono sul reference" in rt[n][s]["flags"])
                  for s in ("pipeline", "codewiki")}
    lines += [
        "",
        f"Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference "
        f"(suite probabilmente inaffidabile): pipeline {n_ref_fail['pipeline']}, CodeWiki {n_ref_fail['codewiki']}.",
    ]

    # ── medie sul sottoinsieme valido
    valid = [n for n in names if not rt[n]["pipeline"]["no_tests"] and not rt[n]["codewiki"]["no_tests"]]
    summary: Dict[str, Any] = {
        "n_functions": len(names),
        "n_valid_both": len(valid),
        "no_tests": {s: sum(1 for n in names if rt[n][s]["no_tests"]) for s in ("pipeline", "codewiki")},
        "reference_suite_fails": n_ref_fail,
    }
    lines += ["", "### Medie escludendo le funzioni senza test eseguiti", ""]
    if valid:
        lines += [
            f"Sulle {len(valid)} funzioni con test eseguiti in entrambi i sistemi:",
            "",
            "| Metrica | Pipeline | CodeWiki | Wilcoxon p |",
            "|---------|----------|----------|------------|",
        ]
        for key, label in (("pass_rate", "Round-trip pass rate (%)"), ("dual", "Dual agreement (%)")):
            a = [rt[n]["pipeline"][key] for n in valid if rt[n]["pipeline"][key] is not None and rt[n]["codewiki"][key] is not None]
            b = [rt[n]["codewiki"][key] for n in valid if rt[n]["pipeline"][key] is not None and rt[n]["codewiki"][key] is not None]
            p = wilcoxon_p(b, a)
            lines.append(f"| {label} | {_f(float(np.mean(a)) if a else None)} | {_f(float(np.mean(b)) if b else None)} | "
                         f"{'n<6' if p is None and 0 < len(a) < 6 else _f(p, 4)} |")
            summary[key] = {"pipeline": float(np.mean(a)) if a else None, "codewiki": float(np.mean(b)) if b else None,
                            "p_value": p, "n": len(a)}
    else:
        lines.append("Nessuna funzione con test eseguiti in entrambi i sistemi.")

    # ── tassonomia errori
    if analysis:
        cats = {}
        for label, a in analysis.items():
            for c in a["categories"]:
                cats.setdefault(c["category"], {"pipeline": 0, "codewiki": 0})[label] = c["count"]
        tot = {s: sum(v[s] for v in cats.values()) for s in ("pipeline", "codewiki")}
        lines += [
            "",
            "### Tipologie di errore (test falliti)",
            "",
            "Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi "
            "sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` "
            "(CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).",
            "",
            "| Tipologia | Pipeline | % | CodeWiki | % |",
            "|-----------|----------|---|----------|---|",
        ]
        for cat in sorted(cats, key=lambda c: -(cats[c]["pipeline"] + cats[c]["codewiki"])):
            v = cats[cat]
            lines.append(f"| {cat} | {v['pipeline']} | {_f(v['pipeline'] / tot['pipeline'] * 100 if tot['pipeline'] else None)} | "
                         f"{v['codewiki']} | {_f(v['codewiki'] / tot['codewiki'] * 100 if tot['codewiki'] else None)} |")
        lines.append(f"| **Totale** | **{tot['pipeline']}** | | **{tot['codewiki']}** | |")
        summary["error_categories"] = cats

    summary["per_function"] = {
        n: {s: {k: v for k, v in rt[n][s].items()} for s in ("pipeline", "codewiki")} for n in names}
    return lines, summary


def generate_extra(paths, library: str, cw_common: List[Dict], pl_common: List[Dict],
                   common_names: List[str], pipeline_records: Dict[str, Dict],
                   adv_cache: Dict[str, Dict]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    Genera i grafici aggiuntivi e le sezioni di report.
    Restituisce (file_creati, righe_markdown, riassunto_json).
    """
    charts = paths.charts_dir
    created: List[str] = []
    lines: List[str] = []
    summary: Dict[str, Any] = {}

    def save(fn, *args, name: str):
        p = os.path.join(charts, name)
        if fn(*args, p):
            created.append(p)

    rt = collect_roundtrip(common_names, pipeline_records, adv_cache)
    has_rt = any(v["pipeline"] and v["codewiki"] for v in rt.values())
    if has_rt:
        analysis = roundtrip_error_tables(rt)
        save(plot_roundtrip_per_function, rt, library, name="cmp_roundtrip_per_function.png")
        if analysis:
            save(plot_roundtrip_errors, analysis, library, name="cmp_roundtrip_errors.png")
        lines, summary = roundtrip_report(rt, analysis)

    save(plot_delta_heatmap, cw_common, pl_common, library, name="cmp_delta_heatmap.png")
    wl = win_loss_counts(cw_common, pl_common)
    save(plot_win_loss, wl, library, name="cmp_win_loss.png")
    save(plot_advanced_per_function, cw_common, pl_common, library, name="cmp_advanced_per_function.png")
    summary["win_loss"] = wl
    return created, lines, summary
