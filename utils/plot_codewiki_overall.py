"""
plot_codewiki_overall.py
------------------------
Risultati complessivi del confronto CodeWiki vs pipeline su tutte le librerie.

Legge, per ogni libreria con un confronto gia' calcolato:
  compare_CodeWiki/<Libreria>/codewiki_vs_pipeline_summary.json
  compare_CodeWiki/<Libreria>/codewiki_metrics_summary.json
e produce in compare_CodeWiki/overall/:
  overall_coverage.png          copertura: funzioni descritte da CodeWiki vs documentate dalla pipeline
  overall_judge.png             judge combinato per libreria
  overall_delta_heatmap.png     libreria x metrica: chi vince (con asterisco se Wilcoxon p < 0.05)
  overall_win_loss_pooled.png   vittorie/pareggi/sconfitte per metrica sommando tutte le librerie
  overall_pooled_means.png      medie ponderate sul numero di funzioni, tutte le librerie insieme
e compare_CodeWiki/OVERALL_REPORT.md con tabelle e note metodologiche.

Nessuna chiamata API: lavora solo su file gia' prodotti.

Utilizzo:
  .venv/Scripts/python utils/plot_codewiki_overall.py
"""

import os
import sys
import json
from typing import Any, Dict, List, Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.codewiki_config import COMPARE_ROOT, discover_libraries, lib_paths
from utils.plot_codewiki_comparison import (
    C_PIPELINE, C_CODEWIKI, C_MERMAID, C_NEUTRAL, INK, INK_2, GRID, SURFACE, _style_value_axis,
)

OUT_DIR = os.path.join(COMPARE_ROOT, "overall")
REPORT = os.path.join(COMPARE_ROOT, "OVERALL_REPORT.md")

# (chiave, etichetta, range per normalizzare la differenza)
HEATMAP_METRICS = [
    ("sbert_similarity", "SBERT", 1.0), ("bertscore_f1", "BERTScore F1", 1.0),
    ("bleurt_estimate", "BLEURT (stima)", 1.0), ("meteor_score", "METEOR", 1.0),
    ("tfidf_cosine", "TF-IDF cosine", 1.0), ("rouge_l", "ROUGE-L", 1.0),
    ("concept_checklist_score", "Concept checklist", 1.0), ("actionability_score", "Actionability", 1.0),
    ("error_doc_rate", "Error doc. rate", 1.0), ("edge_case_coverage", "Edge case coverage", 1.0),
    ("codebert_f1", "CodeBERTScore F1", 1.0), ("retrieval_rr", "Retrieval MRR", 1.0),
    ("judge_a", "Judge A - Faithfulness", 4.0), ("judge_b", "Judge B - Alignment", 4.0),
    ("roundtrip_pass_rate", "Round-trip pass rate", 100.0), ("roundtrip_dual_agreement", "Dual agreement", 100.0),
]
# metriche per le medie ponderate, raggruppate per scala
POOLED_PANELS = [
    ("Metriche in [0, 1]", (0, 1), [
        ("sbert_similarity", "SBERT"), ("bertscore_f1", "BERTScore F1"), ("meteor_score", "METEOR"),
        ("rouge_l", "ROUGE-L"), ("tfidf_cosine", "TF-IDF"), ("actionability_score", "Actionability"),
        ("concept_checklist_score", "Concept checklist"), ("codebert_f1", "CodeBERTScore"),
        ("retrieval_rr", "Retrieval MRR")]),
    ("Judge LLM (1-5)", (1, 5), [("judge_a", "Faithfulness"), ("judge_b", "Alignment"), ("judge_combined", "Combinato")]),
    ("Round-trip (%)", (0, 100), [("roundtrip_pass_rate", "Pass rate"), ("roundtrip_dual_agreement", "Dual agreement")]),
]


def _load(path: str) -> Optional[Dict]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all() -> List[Dict[str, Any]]:
    out = []
    for lib in discover_libraries()["ready"]:
        p = lib_paths(lib)
        cmp_ = _load(p.cmp_json)
        cw = _load(p.summary_json)
        if not cmp_ or not cw or not cmp_.get("n_common"):
            continue
        out.append({"library": lib, "cmp": cmp_, "cw": cw,
                    "metrics": {m["metric"]: m for m in cmp_["metrics"]}})
    # ordine: piu' funzioni confrontate per prime
    out.sort(key=lambda r: -r["cmp"]["n_common"])
    return out


def _pipeline_documented(lib: str) -> int:
    from utils.plot_codewiki_comparison import load_pipeline_records
    return len(load_pipeline_records(lib, None, "multiagent"))


def _save(fig, name: str) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path)
    plt.close(fig)
    return path


# ── Grafici ───────────────────────────────────────────────────────────────────

def plot_coverage(data: List[Dict]) -> str:
    libs = [d["library"] for d in data][::-1]
    fig, ax = plt.subplots(figsize=(9.5, 0.9 * len(libs) + 2.2))
    y = np.arange(len(libs))
    h = 0.36
    kw = dict(edgecolor=SURFACE, linewidth=2)
    for yi, d in zip(y, data[::-1]):
        tot = d["cw"]["total_db_functions"]
        doc, ment = d["cw"]["total_db_documented"], d["cw"]["total_db_mentioned"]
        pl = _pipeline_documented(d["library"])
        ax.barh(yi + h / 2, doc / tot * 100, height=h, color=C_CODEWIKI, label="CodeWiki: con testo descrittivo", **kw)
        ax.barh(yi + h / 2, (ment - doc) / tot * 100, left=doc / tot * 100, height=h, color=C_MERMAID,
                label="CodeWiki: solo nominate", **kw)
        ax.barh(yi - h / 2, min(pl, tot) / tot * 100, height=h, color=C_PIPELINE, label="Pipeline: documentate", **kw)
        ax.text(ment / tot * 100 + 1, yi + h / 2, f"{doc}/{tot} descritte", va="center", fontsize=8, color=INK_2)
        ax.text(min(pl, tot) / tot * 100 + 1, yi - h / 2, f"{min(pl, tot)}/{tot}", va="center", fontsize=8, color=INK_2)
    ax.set_yticks(y, libs)
    _style_value_axis(ax, "x", (0, 118))
    ax.set_xlabel("% delle funzioni con Ground Truth nel DB")
    ax.set_title("Copertura: quante funzioni documenta ciascun sistema", pad=30)
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=8, borderaxespad=0.2)
    return _save(fig, "overall_coverage.png")


def plot_judge(data: List[Dict]) -> Optional[str]:
    rows = [(d["library"], d["metrics"].get("judge_combined")) for d in data]
    rows = [(l, m) for l, m in rows if m and m["n"]]
    if not rows:
        return None
    rows = rows[::-1]
    y = np.arange(len(rows))
    h = 0.36
    fig, ax = plt.subplots(figsize=(9, 0.8 * len(rows) + 2.0))
    ax.barh(y + h / 2, [m["pipeline_mean"] for _, m in rows], height=h, color=C_PIPELINE, edgecolor=SURFACE, linewidth=2, label="Pipeline tesi")
    ax.barh(y - h / 2, [m["codewiki_mean"] for _, m in rows], height=h, color=C_CODEWIKI, edgecolor=SURFACE, linewidth=2, label="CodeWiki")
    for yi, (_, m) in zip(y, rows):
        star = " *" if m["p_value"] is not None and m["p_value"] < 0.05 else ""
        ax.text(m["pipeline_mean"] + 0.05, yi + h / 2, f"{m['pipeline_mean']:.2f}", va="center", fontsize=9, color=INK)
        ax.text(m["codewiki_mean"] + 0.05, yi - h / 2, f"{m['codewiki_mean']:.2f}{star}", va="center", fontsize=9, color=INK)
    ax.set_yticks(y, [f"{l}  (n={m['n']})" for l, m in rows])
    _style_value_axis(ax, "x", (0, 5.6))
    ax.set_xlabel("Judge LLM combinato, 1-5   (* = Wilcoxon p < 0.05)")
    ax.set_title("Giudizio dell'LLM-judge per libreria", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9, borderaxespad=0.2)
    return _save(fig, "overall_judge.png")


def plot_delta_heatmap(data: List[Dict]) -> str:
    metrics = [m for m in HEATMAP_METRICS if any(d["metrics"].get(m[0], {}).get("n") for d in data)]
    norm = np.full((len(data), len(metrics)), np.nan)
    sig = np.zeros_like(norm, dtype=bool)
    for i, d in enumerate(data):
        for j, (key, _, rng) in enumerate(metrics):
            m = d["metrics"].get(key)
            if m and m["n"] and m["delta"] is not None:
                norm[i, j] = m["delta"] / rng
                sig[i, j] = m["p_value"] is not None and m["p_value"] < 0.05
    cmap = LinearSegmentedColormap.from_list("cw_vs_pl", [C_CODEWIKI, "#f2f1ed", C_PIPELINE])
    cmap.set_bad("#ffffff")
    fig, ax = plt.subplots(figsize=(0.7 * len(metrics) + 3.5, 0.6 * len(data) + 3.0))
    im = ax.imshow(np.ma.masked_invalid(norm), cmap=cmap, norm=Normalize(-0.5, 0.5), aspect="auto")
    ax.set_xticks(range(len(metrics)), [m[1] for m in metrics], fontsize=8)
    ax.set_yticks(range(len(data)), [f"{d['library']}  (n={d['cmp']['n_common']})" for d in data], fontsize=9)
    ax.xaxis.tick_top()
    plt.setp(ax.get_xticklabels(), rotation=40, ha="left", rotation_mode="anchor")
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks(np.arange(-.5, len(metrics), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(data), 1), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    for i in range(norm.shape[0]):
        for j in range(norm.shape[1]):
            if np.isnan(norm[i, j]):
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=7, color=INK_2)
            elif sig[i, j]:
                ax.text(j, i, "*", ha="center", va="center", fontsize=14, fontweight="bold", color=INK)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Differenza media (Pipeline - CodeWiki), frazione del range", fontsize=8)
    cbar.ax.tick_params(labelsize=8, length=0)
    fig.suptitle("Pipeline vs CodeWiki per libreria   (blu = meglio la pipeline, arancio = meglio CodeWiki, * = Wilcoxon p < 0.05)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=1.02)
    return _save(fig, "overall_delta_heatmap.png")


def pooled_win_loss(data: List[Dict]) -> List[Dict]:
    agg: Dict[str, Dict] = {}
    for d in data:
        for r in d["cmp"].get("extra", {}).get("win_loss", []):
            a = agg.setdefault(r["metric"], {"metric": r["metric"], "label": r["label"], "n": 0,
                                             "pipeline_wins": 0, "ties": 0, "codewiki_wins": 0})
            for k in ("n", "pipeline_wins", "ties", "codewiki_wins"):
                a[k] += r[k]
    return list(agg.values())


def plot_win_loss(rows: List[Dict]) -> Optional[str]:
    if not rows:
        return None
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
    ax.set_xlabel("% delle funzioni, tutte le librerie insieme (pareggio = differenza sotto l'1% del range)")
    ax.set_title("Vittorie, pareggi e sconfitte per metrica - tutte le librerie", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9, borderaxespad=0.2)
    return _save(fig, "overall_win_loss_pooled.png")


def pooled_means(data: List[Dict]) -> Dict[str, Dict]:
    out = {}
    for _, _, items in POOLED_PANELS:
        for key, label in items:
            num_p = num_c = den = 0.0
            for d in data:
                m = d["metrics"].get(key)
                if m and m["n"] and m["pipeline_mean"] is not None and m["codewiki_mean"] is not None:
                    num_p += m["pipeline_mean"] * m["n"]
                    num_c += m["codewiki_mean"] * m["n"]
                    den += m["n"]
            if den:
                out[key] = {"label": label, "n": int(den), "pipeline": num_p / den, "codewiki": num_c / den}
    return out


def plot_pooled_means(pm: Dict[str, Dict]) -> str:
    panels = [(t, lim, [(k, l) for k, l in items if k in pm]) for t, lim, items in POOLED_PANELS]
    panels = [p for p in panels if p[2]]
    widths = [max(len(p[2]), 2) for p in panels]
    fig, axes = plt.subplots(1, len(panels), figsize=(3.0 + 1.0 * sum(widths), 4.6),
                             gridspec_kw={"width_ratios": widths})
    axes = np.atleast_1d(axes)
    for ax, (title, lim, items) in zip(axes, panels):
        x = np.arange(len(items))
        w = 0.38
        a = [pm[k]["pipeline"] for k, _ in items]
        b = [pm[k]["codewiki"] for k, _ in items]
        ax.bar(x - w / 2, np.array(a) - lim[0], bottom=lim[0], width=w, color=C_PIPELINE, edgecolor=SURFACE, linewidth=2,
               label="Pipeline tesi")
        ax.bar(x + w / 2, np.array(b) - lim[0], bottom=lim[0], width=w, color=C_CODEWIKI, edgecolor=SURFACE, linewidth=2,
               label="CodeWiki")
        fmt_ = "{:.0f}" if lim[1] == 100 else "{:.2f}"
        for xi, va, vb in zip(x, a, b):
            ax.text(xi - w / 2, va + (lim[1] - lim[0]) * 0.015, fmt_.format(va), ha="center", fontsize=7.5, color=INK)
            ax.text(xi + w / 2, vb + (lim[1] - lim[0]) * 0.015, fmt_.format(vb), ha="center", fontsize=7.5, color=INK)
        ax.set_xticks(x, [l for _, l in items], rotation=35, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10)
        _style_value_axis(ax, "y", (lim[0], lim[1] * 1.0 + (lim[1] - lim[0]) * 0.08))
    axes[0].legend(loc="upper left", fontsize=8)
    n_all = max(v["n"] for v in pm.values())
    fig.suptitle(f"Medie ponderate sul numero di funzioni - tutte le librerie (fino a {n_all} funzioni per metrica)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return _save(fig, "overall_pooled_means.png")


# ── Report ────────────────────────────────────────────────────────────────────

def _f(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "N/A"


def write_report(data: List[Dict], pm: Dict[str, Dict], charts: List[str], skipped: List[str]) -> str:
    L = [
        "# Confronto CodeWiki vs pipeline della tesi - risultati complessivi",
        "",
        f"> {len(data)} librerie, {sum(d['cmp']['n_common'] for d in data)} funzioni confrontate in totale. "
        "Generato da `utils/plot_codewiki_overall.py` a partire dai riepiloghi di ogni libreria "
        "(`compare_CodeWiki/<Libreria>/`). Nessuna chiamata API.",
        "",
        "## Copertura",
        "",
        "| Libreria | Funzioni nel DB | CodeWiki: nominate | CodeWiki: con testo | Pipeline: documentate | In comune (confronto) |",
        "|----------|-----------------|--------------------|---------------------|-----------------------|-----------------------|",
    ]
    for d in data:
        cw = d["cw"]
        L.append(f"| {d['library']} | {cw['total_db_functions']} | {cw['total_db_mentioned']} | "
                 f"{cw['total_db_documented']} | {min(_pipeline_documented(d['library']), cw['total_db_functions'])} | "
                 f"{d['cmp']['n_common']} |")
    L += [
        "",
        "Il confronto qualitativo si fa solo sulle funzioni che CodeWiki descrive con un testo e che hanno un "
        "Ground Truth. Le funzioni solo *nominate* (elenchi di nomi, diagrammi) contano nella copertura ma non hanno "
        "testo da valutare.",
        "",
        "## Metriche chiave per libreria (Pipeline / CodeWiki)",
        "",
        "Un asterisco indica una differenza significativa (Wilcoxon appaiato, p < 0.05; calcolato solo per n >= 6).",
        "",
    ]
    keys = [("judge_combined", "Judge (1-5)"), ("sbert_similarity", "SBERT"), ("bertscore_f1", "BERTScore"),
            ("meteor_score", "METEOR"), ("actionability_score", "Actionability"), ("retrieval_rr", "Retrieval MRR"),
            ("codebert_f1", "CodeBERT"), ("roundtrip_pass_rate", "Round-trip %")]
    L.append("| Libreria | n | " + " | ".join(k[1] for k in keys) + " |")
    L.append("|----------|---|" + "|".join("---" for _ in keys) + "|")
    for d in data:
        cells = []
        for key, _ in keys:
            m = d["metrics"].get(key)
            if not m or not m["n"]:
                cells.append("N/A")
                continue
            star = "*" if m["p_value"] is not None and m["p_value"] < 0.05 else ""
            nd = 1 if key == "roundtrip_pass_rate" else 2
            cells.append(f"{_f(m['pipeline_mean'], nd)} / {_f(m['codewiki_mean'], nd)}{star}")
        L.append(f"| {d['library']} | {d['cmp']['n_common']} | " + " | ".join(cells) + " |")

    L += ["", "## Medie ponderate su tutte le librerie", "",
          "Media di ogni metrica pesata sul numero di funzioni di ciascuna libreria. "
          "E' una sintesi descrittiva: le librerie hanno dimensioni molto diverse (TinyXML-2 e sds pesano di piu').",
          "", "| Metrica | n | Pipeline | CodeWiki |", "|---------|---|----------|----------|"]
    for _, _, items in POOLED_PANELS:
        for key, label in items:
            if key in pm:
                v = pm[key]
                nd = 1 if key.startswith("roundtrip") else 3
                L.append(f"| {label} | {v['n']} | {_f(v['pipeline'], nd)} | {_f(v['codewiki'], nd)} |")

    wl = pooled_win_loss(data)
    if wl:
        L += ["", "## Vittorie per metrica (tutte le funzioni di tutte le librerie)", "",
              "| Metrica | n | Pipeline meglio | Pareggio | CodeWiki meglio |",
              "|---------|---|-----------------|----------|-----------------|"]
        for r in sorted(wl, key=lambda r: -(r["pipeline_wins"] - r["codewiki_wins"]) / max(r["n"], 1)):
            L.append(f"| {r['label']} | {r['n']} | {r['pipeline_wins']} | {r['ties']} | {r['codewiki_wins']} |")

    L += ["", "## Grafici", ""]
    for c in charts:
        rel = os.path.relpath(c, COMPARE_ROOT).replace("\\", "/")
        L.append(f"![{os.path.basename(c)}]({rel})")
        L.append("")
    L += [
        "I grafici di dettaglio di ogni libreria (distribuzioni, confronto per funzione, round-trip, heatmap funzione x metrica) "
        "sono in `compare_CodeWiki/<Libreria>/charts/`.",
        "",
        "## Note e limiti",
        "",
        "- **Round-trip**: le suite di test sono generate dall'LLM a partire dalla documentazione e spesso falliscono anche "
        "sul codice reference; molti errori sono di ambiente (simboli mancanti nello scaffold). Va letto come indicatore "
        "debole, non come misura diretta della qualita' della documentazione.",
        "- **Judge**: per alcune funzioni una o piu' chiamate del judge sono fallite (quota API) e i loro punteggi sono stati "
        "esclusi: `n` del judge puo' essere inferiore a quello delle altre metriche.",
        "- **Campioni piccoli**: fmt ha una sola funzione in comune, OpenCV 8, http-parser 9; i test statistici su campioni "
        "cosi' piccoli hanno poca potenza.",
        "- **Ground Truth ereditato da gruppo**: una parte delle funzioni di cJSON e TinyXML-2 ha come riferimento il commento "
        "condiviso da un gruppo di dichiarazioni piu' la nota `Variant:` (colonna `doc_origin = group` nel DB).",
    ]
    if skipped:
        L += ["", f"- Librerie senza confronto disponibile: {', '.join(skipped)}."]
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return REPORT


def generate_overall() -> List[str]:
    data = load_all()
    if not data:
        print("  [WARN] Nessuna libreria con confronto disponibile: risultati complessivi non generati.")
        return []
    found = discover_libraries()
    skipped = found["no_db"] + [l for l in found["ready"] if l not in {d["library"] for d in data}]
    charts = [plot_coverage(data)]
    for fn in (plot_judge, plot_delta_heatmap):
        p = fn(data)
        if p:
            charts.append(p)
    p = plot_win_loss(pooled_win_loss(data))
    if p:
        charts.append(p)
    pm = pooled_means(data)
    if pm:
        charts.append(plot_pooled_means(pm))
    report = write_report(data, pm, charts, skipped)
    return charts + [report]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in generate_overall():
        print(f"  -> {os.path.relpath(p, ROOT_DIR)}")


if __name__ == "__main__":
    main()
