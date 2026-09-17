"""
Generatore della Dashboard Grafica per Round-Trip Differential Testing.
Produce un confronto dettagliato per funzione e grafici di sintesi globale per:
1. Self-Consistency Pass Rate % (Codice sintetizzato da Documentazione vs Test)
2. Dual Agreement Rate % (Codice Documentato vs Codice Reale C/C++)
3. Disaggregazione Tassonomica per Categoria Funzionale (Stateless, Pointer/Buffer, Stateful)
4. Media Combinata e Indicatori Globali
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_roundtrip_charts(results_list, output_image_path, avg_pass_rate=None, avg_differential_agreement=None, library_name=None):
    """
    Genera la dashboard grafica scientifica del Round-Trip Differential Testing:
    - ax1 (in alto): Bar chart delle funzioni raggruppate per Categoria Tassonomica
    - ax2 (in basso a sinistra): Distribuzione e Pass Rate / Dual Agreement disaggregati per Categoria
    - ax3 (in basso a destra): Sintesi Globale (Doc Pass Rate, Dual Agreement, Media Combinata)
    """
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    # Se non specificato, determina la categoria tassonomica per ciascuna funzione
    def _get_category(r):
        if "function_type" in r and r["function_type"]:
            return r["function_type"]
        fn = r.get("name") or r.get("function_name", "")
        sig = r.get("signature", "").lower()
        if "::" in fn or any(t in sig for t in ["cjson *", "xmlnode", "xmlattribute", "xmldocument", "xmlhandle"]):
            return "Stateful / Object-Graph"
        if any(p in sig for p in ["*", "buf", "char *", "void *", "size_t"]):
            return "Pointer / Buffer-Driven"
        return "Stateless / Primitive"

    # Estrazione e raggruppamento
    enriched_results = []
    for r in results_list:
        fn = r.get("name") or r.get("function_name", "func")
        pr = float(r.get("pass_rate", r.get("execution", {}).get("pass_rate", 0.0)))
        diff_val = 0.0
        if "diff_agreement" in r:
            diff_val = float(r["diff_agreement"])
        elif "differential" in r.get("execution", {}):
            diff_val = float(r["execution"]["differential"].get("differential_agreement_rate", 0.0))
        elif "differential_agreement_rate" in r:
            diff_val = float(r["differential_agreement_rate"])
        
        cat = _get_category(r)
        enriched_results.append({
            "name": fn,
            "pass_rate": pr,
            "diff_agreement": diff_val,
            "category": cat
        })

    # Ordiniamo per categoria e poi per pass_rate decrescente per una leggibilità scientifica chiara
    category_order = ["Stateless / Primitive", "Pointer / Buffer-Driven", "Stateful / Object-Graph"]
    enriched_results.sort(key=lambda x: (category_order.index(x["category"]) if x["category"] in category_order else 99, -x["pass_rate"]))

    funcs = [r["name"] for r in enriched_results]
    doc_rates = [r["pass_rate"] for r in enriched_results]
    diff_rates = [r["diff_agreement"] for r in enriched_results]
    categories = [r["category"] for r in enriched_results]

    has_diff_data = any(dr > 0 for dr in diff_rates) or (avg_differential_agreement is not None and avg_differential_agreement > 0)

    # Calcolo medie globali
    if avg_pass_rate is None:
        avg_pass_rate = round(float(np.mean(doc_rates)), 1) if doc_rates else 0.0
    else:
        avg_pass_rate = round(float(avg_pass_rate), 1)

    if avg_differential_agreement is None:
        avg_differential_agreement = round(float(np.mean(diff_rates)), 1) if diff_rates else 0.0
    else:
        avg_differential_agreement = round(float(avg_differential_agreement), 1)

    overall_mean = round((avg_pass_rate + avg_differential_agreement) / 2.0, 1)

    n = len(funcs)
    fig = plt.figure(figsize=(22, 13))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.7, 1.0], width_ratios=[1.25, 1.0])

    ax1 = fig.add_subplot(gs[0, :])  # In alto: Bar chart ordinato per categorie tassonomiche
    ax2 = fig.add_subplot(gs[1, 0])  # In basso a sinistra: Medie per Categoria Tassonomica
    ax3 = fig.add_subplot(gs[1, 1])  # In basso a destra: Sintesi Globale

    # Nome libreria
    if not library_name:
        path_lower = output_image_path.lower()
        if "cjson" in path_lower:
            library_name = "cJSON"
        elif "tinyxml2" in path_lower:
            library_name = "TinyXML-2"
        elif "httpparser" in path_lower or "http_parser" in path_lower:
            library_name = "http-parser"
        elif "opencv" in path_lower:
            library_name = "OpenCV"
        elif "miniz" in path_lower:
            library_name = "miniz"
        elif "sqlite" in path_lower:
            library_name = "SQLite"
        elif "all" in path_lower:
            library_name = "Multi-Library Benchmark"
        else:
            library_name = "Benchmark"

    # =========================================================================
    # 1. Bar Chart Comparativo con Separatori di Categoria
    # =========================================================================
    x = np.arange(n)
    width = 0.38 if has_diff_data else 0.65

    if has_diff_data:
        ax1.bar(x - width/2, doc_rates, width=width, color='#3b82f6', edgecolor='#1e293b', 
                linewidth=0.8, label=f'Self-Consistency Pass Rate (Doc) [Media: {avg_pass_rate}%]', zorder=3)
        ax1.bar(x + width/2, diff_rates, width=width, color='#10b981', edgecolor='#1e293b', 
                linewidth=0.8, label=f'Dual Agreement Rate (Doc vs Codice Reale) [Media: {avg_differential_agreement}%]', zorder=3)
        
        ax1.axhline(avg_pass_rate, color='#2563eb', linestyle='--', linewidth=1.4, alpha=0.85)
        ax1.axhline(avg_differential_agreement, color='#059669', linestyle='--', linewidth=1.4, alpha=0.85)
        ax1.axhline(overall_mean, color='#dc2626', linestyle=':', linewidth=1.8, label=f'Media Combinata: {overall_mean}%')
    else:
        colors = ['#10b981' if r >= 80 else ('#3b82f6' if r >= 50 else ('#f59e0b' if r > 0 else '#ef4444')) for r in doc_rates]
        ax1.bar(x, doc_rates, color=colors, edgecolor='#1f2937', linewidth=0.8, width=width, zorder=3)
        ax1.axhline(avg_pass_rate, color='#dc2626', linestyle='--', linewidth=1.5, label=f'Media Globale: {avg_pass_rate}%')

    # Tracciamento linee di separazione e banner di Categoria in alto
    last_cat = None
    cat_starts = {}
    for idx, c in enumerate(categories):
        if c != last_cat:
            cat_starts[c] = idx
            if last_cat is not None:
                ax1.axvline(idx - 0.5, color='#94a3b8', linestyle='-', linewidth=1.5, alpha=0.7)
            last_cat = c

    # Calcolo medie per categoria per arricchire i banner
    cat_means_map = {}
    for c in list(dict.fromkeys(categories)):
        c_items = [r for r in enriched_results if r["category"] == c]
        doc_m = round(float(np.mean([r["pass_rate"] for r in c_items])), 1) if c_items else 0.0
        diff_m = round(float(np.mean([r["diff_agreement"] for r in c_items])), 1) if c_items else 0.0
        cat_means_map[c] = (doc_m, diff_m, len(c_items))

    # Aggiunge etichette di categoria in cima al grafico con le relative medie
    cat_colors = {
        "Stateless / Primitive": "#dbeafe",
        "Pointer / Buffer-Driven": "#fef3c7",
        "Stateful / Object-Graph": "#fce7f3"
    }
    cat_text_colors = {
        "Stateless / Primitive": "#1e40af",
        "Pointer / Buffer-Driven": "#92400e",
        "Stateful / Object-Graph": "#9d174d"
    }
    sorted_cats = list(cat_starts.keys())
    for i, c in enumerate(sorted_cats):
        start_idx = cat_starts[c]
        end_idx = cat_starts[sorted_cats[i+1]] if i+1 < len(sorted_cats) else n
        mid_idx = (start_idx + end_idx - 1) / 2.0
        doc_m, diff_m, cnt = cat_means_map.get(c, (0.0, 0.0, 0))
        banner_text = f"[{c.upper()}] (n={cnt})\nMedie: Doc {doc_m}% | Dual {diff_m}%"
        ax1.text(mid_idx, 111, banner_text, ha='center', va='center', fontsize=8.8, fontweight='bold',
                 color=cat_text_colors.get(c, '#0f172a'),
                 bbox=dict(boxstyle="round,pad=0.4", facecolor=cat_colors.get(c, '#f1f5f9'), edgecolor="#cbd5e1", alpha=0.95))

    ax1.set_xticks(x)
    rotation_angle = 75 if n > 15 else 45
    ax1.set_xticklabels(funcs, rotation=rotation_angle, ha='right', fontsize=8.5, fontweight='bold')
    ax1.set_ylim(0, 126)
    ax1.set_ylabel("Percentuale di Successo %", fontsize=11, fontweight='bold')
    ax1.set_title(f"Valutazione Round-Trip Differential per Categorie Funzionali ({library_name})", fontsize=14, fontweight='bold', pad=14)
    ax1.grid(axis='y', linestyle=':', alpha=0.7)
    ax1.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.92, fontsize=9.5)

    # =========================================================================
    # 2. Performance Disaggregata per Categoria Tassonomica
    # =========================================================================
    unique_cats = [c for c in category_order if any(cat == c for cat in categories)]
    if not unique_cats:
        unique_cats = list(dict.fromkeys(categories))

    cat_doc_means = []
    cat_diff_means = []
    cat_counts = []
    for c in unique_cats:
        c_items = [r for r in enriched_results if r["category"] == c]
        cat_counts.append(len(c_items))
        cat_doc_means.append(round(float(np.mean([r["pass_rate"] for r in c_items])), 1) if c_items else 0.0)
        cat_diff_means.append(round(float(np.mean([r["diff_agreement"] for r in c_items])), 1) if c_items else 0.0)

    x_cat = np.arange(len(unique_cats))
    w_cat = 0.35
    labels_with_count = [f"{c}\n({cnt} funzioni)" for c, cnt in zip(unique_cats, cat_counts)]

    bars_cd = ax2.bar(x_cat - w_cat/2, cat_doc_means, width=w_cat, color='#3b82f6', edgecolor='#1e293b', label='Doc Self-Consistency', zorder=3)
    bars_cf = ax2.bar(x_cat + w_cat/2, cat_diff_means, width=w_cat, color='#10b981', edgecolor='#1e293b', label='Dual Agreement (vs Reale)', zorder=3)

    for bar, val in zip(bars_cd, cat_doc_means):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 1.8, f"{val}%", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#1e3a8a')

    for bar, val in zip(bars_cf, cat_diff_means):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 1.8, f"{val}%", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#065f46')

    ax2.set_xticks(x_cat)
    ax2.set_xticklabels(labels_with_count, fontsize=9.5, fontweight='bold')
    ax2.set_ylim(0, 115)
    ax2.set_ylabel("Percentuale Media %", fontsize=11, fontweight='bold')
    ax2.set_title("Performance Disaggregata per Categoria Funzionale", fontsize=12, fontweight='bold')
    ax2.grid(axis='y', linestyle=':', alpha=0.7)
    ax2.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize=9)

    # =========================================================================
    # 3. Metriche di Sintesi Globale: Percentuali & Media Finale
    # =========================================================================
    summary_labels = [
        '1. Pass Rate (Doc)\nSelf-Consistency',
        '2. Dual Agreement\nDoc vs Codice Reale',
        '3. Media Finale\nCombinata'
    ]
    summary_vals = [avg_pass_rate, avg_differential_agreement, overall_mean]
    summary_colors = ['#3b82f6', '#10b981', '#f59e0b']

    bars3 = ax3.bar(summary_labels, summary_vals, color=summary_colors, edgecolor='#1e293b', width=0.48, zorder=3)
    ax3.set_ylim(0, 115)
    ax3.set_ylabel("Percentuale %", fontsize=11, fontweight='bold')
    ax3.set_title("Sintesi Globale Round-Trip (Metriche Chiave & Media)", fontsize=12, fontweight='bold')
    ax3.grid(axis='y', linestyle=':', alpha=0.7)

    for bar, val in zip(bars3, summary_vals):
        ax3.text(bar.get_x() + bar.get_width()/2, val + 2.5, f"{val}%", ha='center', va='bottom', fontsize=12, fontweight='bold', color='#0f172a')

    ax3.axhline(overall_mean, color='#dc2626', linestyle='--', linewidth=1.5, alpha=0.75)

    plt.tight_layout()
    plt.savefig(output_image_path, dpi=200)
    plt.close()
    print(f"-> Grafico Round-Trip salvato con successo in: {output_image_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Genera la dashboard grafica del Round-Trip")
    parser.add_argument("-j", "--json", default="results/benchmark_all/run_20260916_173829_multiagent/roundtrip_results.json", help="File roundtrip_results.json")
    parser.add_argument("-o", "--output", default="results/benchmark_all/run_20260916_173829_multiagent/eval_chart_roundtrip.png", help="Percorso immagine di output")
    parser.add_argument("-l", "--lib", default=None, help="Nome della libreria (es. 'Multi-Library Benchmark' o 'cJSON')")
    args = parser.parse_args()

    json_path = os.path.join(ROOT_DIR, args.json) if not os.path.isabs(args.json) else args.json
    output_path = os.path.join(ROOT_DIR, args.output) if not os.path.isabs(args.output) else args.output

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        results = data.get("results", [])
        avg_pr = data.get("avg_pass_rate")
        avg_diff = data.get("avg_differential_agreement")
        generate_roundtrip_charts(results, output_path, avg_pass_rate=avg_pr, avg_differential_agreement=avg_diff, library_name=args.lib)
    else:
        print(f"[ERRORE] File JSON non trovato: {json_path}")
