#!/usr/bin/env python3
"""
generate_thesis_unified_plots.py
--------------------------------
Genera tutti i grafici scientifici uniformati per la tesi magistrale:
- Capitolo 4: Analisi e validazione delle metriche di valutazione
- Capitolo 5: Validazione sperimentale su benchmark C/C++ reali

Stile grafico accademico unificato:
- Palette: mako-inspired / deep academic teal & indigo
- Typography: sans-serif pulita (DejaVu Sans / Arial), standard hierarchy
- DPI: 300 per stampa ad alta fedeltà
- Layout: compatto, bordi discreti, gridline soffuse (alpha=0.3)
"""

import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

# ---------------------------------------------------------
# Configurazione globale dello stile grafico accademico
# ---------------------------------------------------------
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

mpl.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica', 'Liberation Sans'],
    'font.size': 10,
    'axes.titlesize': 13,
    'axes.titleweight': 'bold',
    'axes.titlepad': 12,
    'axes.labelsize': 11,
    'axes.labelweight': 'bold',
    'axes.labelpad': 8,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 9.5,
    'legend.fontsize': 9.5,
    'legend.title_fontsize': 10,
    'figure.titlesize': 14,
    'figure.titleweight': 'bold',
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
    'axes.edgecolor': '#333333',
    'axes.linewidth': 0.9,
    'grid.color': '#B0BEC5',
    'grid.linestyle': '--',
    'grid.linewidth': 0.6,
    'grid.alpha': 0.4,
    'lines.linewidth': 1.8,
    'lines.markersize': 7,
})

# Palette cromatica accademica istituzionale (Teal / Deep Blue / Slate / Amber / Coral)
COLOR_PALETTE = {
    'primary': '#1A365D',     # Deep Navy
    'secondary': '#0D9488',   # Deep Teal
    'accent1': '#2563EB',     # Royal Blue
    'accent2': '#D97706',     # Warm Amber / Orange
    'accent3': '#DC2626',     # Crimson
    'slate': '#475569',       # Slate Gray
    'neutral_light': '#F8FAFC',
    'neutral_border': '#CBD5E1',
    'success': '#16A34A',
    'warning': '#EA580C',
    'danger': '#B91C1C'
}

# Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_DIR = PROJECT_ROOT / "thesis" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def plot_crossmodal_metrics():
    """
    (a) fig_metriche_nlp_crossmodal.png
    Confronto SBERT, BERTScore F1, CodeBERT F1, ROUGE-L sui 4 campi/rappresentazioni:
    - Raw C vs Python Code
    - Canonical Pseudocode
    - Mermaid Flowchart
    - Docstring (Benchmark generato vs Reference)
    """
    canon_file = RESULTS_DIR / "metrics_validation" / "canonical_representation_results.json"
    bench_file = RESULTS_DIR / "benchmark_all" / "latest" / "eval_report_multiagent.json"

    with open(canon_file, encoding='utf-8') as f:
        canon_data = json.load(f)
    with open(bench_file, encoding='utf-8') as f:
        bench_data = json.load(f)

    # Calcolo medie per ciascuna rappresentazione
    # 1. Raw Code, Pseudo, Flowchart da canonical_representation_results.json
    raw_sbert = np.mean([x['scores']['raw']['SBERT'] for x in canon_data])
    raw_bert = np.mean([x['scores']['raw']['BERTScore'] for x in canon_data])
    raw_codebert = np.mean([x['scores']['raw']['CodeBERT'] for x in canon_data])
    raw_rouge = np.mean([x['scores']['raw']['ROUGE'] for x in canon_data])

    pseudo_sbert = np.mean([x['scores']['pseudo']['SBERT'] for x in canon_data])
    pseudo_bert = np.mean([x['scores']['pseudo']['BERTScore'] for x in canon_data])
    pseudo_codebert = np.mean([x['scores']['pseudo']['CodeBERT'] for x in canon_data])
    pseudo_rouge = np.mean([x['scores']['pseudo']['ROUGE'] for x in canon_data])

    flow_sbert = np.mean([x['scores']['flowchart']['SBERT'] for x in canon_data])
    flow_bert = np.mean([x['scores']['flowchart']['BERTScore'] for x in canon_data])
    flow_codebert = np.mean([x['scores']['flowchart']['CodeBERT'] for x in canon_data])
    flow_rouge = np.mean([x['scores']['flowchart']['ROUGE'] for x in canon_data])

    # 2. Docstring dal benchmark reale
    doc_sbert = np.mean([x['metrics']['sbert_similarity'] for x in bench_data])
    doc_bert = np.mean([x['metrics']['bert_score_f1'] for x in bench_data])
    doc_codebert = np.mean([x['metrics']['codebert_score_f1'] for x in bench_data])
    doc_rouge = np.mean([x['metrics']['rouge_l'] for x in bench_data])

    modalities = ['Codice Grezzo\n(Raw Code)', 'Pseudocodice\nCanonico', 'Diagramma\nFlowchart', 'Documentazione\n(Docstring)']
    metrics = ['SBERT', 'BERTScore F1', 'CodeBERT F1', 'ROUGE-L']

    values = np.array([
        [raw_sbert, raw_bert, raw_codebert, raw_rouge],
        [pseudo_sbert, pseudo_bert, pseudo_codebert, pseudo_rouge],
        [flow_sbert, flow_bert, flow_codebert, flow_rouge],
        [doc_sbert, doc_bert, doc_codebert, doc_rouge]
    ])  # shape: (4 modalities, 4 metrics)

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    x = np.arange(len(modalities))
    bar_width = 0.18
    palette = ['#0D9488', '#2563EB', '#D97706', '#64748B']

    for i, m_name in enumerate(metrics):
        offset = (i - 1.5) * bar_width
        bars = ax.bar(x + offset, values[:, i], width=bar_width, label=m_name,
                      color=palette[i], edgecolor='#1E293B', linewidth=0.7, alpha=0.92)
        # Etichette sui bar
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=8, fontweight='bold', color='#1E293B')

    ax.set_ylabel('Punteggio Normalizzato [0.0 - 1.0]')
    ax.set_title('Confronto Prestazioni Metriche Cross-Modali e Rappresentazioni Canoniche')
    ax.set_xticks(x)
    ax.set_xticklabels(modalities, fontweight='semibold')
    ax.set_ylim(0, 1.15)
    ax.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.35)

    out_path = OUTPUT_DIR / "fig_metriche_nlp_crossmodal.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_adversarial_paradox():
    """
    (b) fig_nlp_adversarial_paradox.png
    Confronto del comportamento su casi critici (Parafrasi, Negazione critica, Scambio ruoli, Verbosità, Ortogonale)
    per dimostrare il paradosso delle metriche neurali sulle negazioni e l'effetto della verbosità.
    """
    doc_file = RESULTS_DIR / "metrics_validation" / "doc_metrics_results.json"
    with open(doc_file, encoding='utf-8') as f:
        data = json.load(f)

    # Raggruppiamo per categoria
    cats = ['PARAPHRASE', 'CRITICAL_NEGATION', 'ROLE_SWAP', 'VERBOSITY_FLUFF', 'ORTHOGONAL']
    cat_labels = [
        'Parafrasi\nEquivalente',
        'Negazione Critica\n(Inversione Vincoli)',
        'Scambio Ruoli\n(src vs dest)',
        'Verbosità & Fluff\n(Diluizione Testo)',
        'Contesto\nOrtogonale'
    ]

    means_sbert = []
    means_bert = []
    means_rouge = []

    for cat in cats:
        items = [x for x in data if x.get('category') == cat]
        means_sbert.append(np.mean([it['scores']['SBERT'] for it in items]))
        means_bert.append(np.mean([it['scores']['BERT_F1'] for it in items]))
        means_rouge.append(np.mean([it['scores']['ROUGE-L'] for it in items]))

    fig, ax = plt.subplots(figsize=(10, 5.8))
    x = np.arange(len(cats))
    bar_width = 0.25

    bars1 = ax.bar(x - bar_width, means_sbert, width=bar_width, label='Sentence-BERT Similarity',
                   color='#0D9488', edgecolor='#1E293B', linewidth=0.7, alpha=0.92)
    bars2 = ax.bar(x, means_bert, width=bar_width, label='BERTScore F1',
                   color='#2563EB', edgecolor='#1E293B', linewidth=0.7, alpha=0.92)
    bars3 = ax.bar(x + bar_width, means_rouge, width=bar_width, label='ROUGE-L F1 (Lessicale)',
                   color='#D97706', edgecolor='#1E293B', linewidth=0.7, alpha=0.92)

    # Evidenziazione area paradosso con annotate
    for i, bar in enumerate(bars1):
        ax.annotate(f"{bar.get_height():.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    for i, bar in enumerate(bars2):
        ax.annotate(f"{bar.get_height():.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    for i, bar in enumerate(bars3):
        ax.annotate(f"{bar.get_height():.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight='bold')

    # Box di warning per il paradosso
    ax.annotate("Paradosso Neurale:\nSBERT > 0.91 nonostante\ninversione semantica!",
                xy=(1.0, 0.92), xytext=(1.35, 1.05),
                arrowprops=dict(facecolor='#DC2626', edgecolor='#DC2626', width=1.5, headwidth=6, shrink=0.08),
                fontsize=8.5, fontweight='bold', color='#B91C1C',
                bbox=dict(boxstyle="round,pad=0.3", fc="#FEF2F2", ec="#DC2626", lw=1))

    ax.set_ylabel('Punteggio di Similarità Stimata')
    ax.set_title('Il Paradosso delle Metriche Neurali di Documentazione su Casi Avversari e Critici')
    ax.set_xticks(x)
    ax.set_xticklabels(cat_labels, fontweight='semibold')
    ax.set_ylim(0, 1.22)
    ax.axhline(0.8, color='#94A3B8', linestyle=':', linewidth=1.2, label='Soglia Similarità Elevata (0.80)')
    ax.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.35)

    out_path = OUTPUT_DIR / "fig_nlp_adversarial_paradox.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_radar_overview():
    """
    (c) fig_benchmark_overview_radar.png
    Profilo globale delle metriche dell'ultimo run:
    - Aderenza AST (param_f1)
    - Actionability (actionability_score)
    - Semantica Neurale (sbert_similarity)
    - Copertura Errori (error_documentation_score)
    - Round-Trip Pass Rate (pass_rate / 100)
    - Retrieval MRR (retrieval_rr)
    """
    bench_file = RESULTS_DIR / "benchmark_all" / "latest" / "eval_report_multiagent.json"
    with open(bench_file, encoding='utf-8') as f:
        data = json.load(f)

    categories = [
        'Aderenza AST\n(Param F1)',
        'Actionability\nDocstring',
        'Semantica Neurale\n(SBERT)',
        'Copertura Errori\n& Casi Limite',
        'Round-Trip\nPass Rate',
        'Retrieval MRR\n(Hit@1 / RR)'
    ]
    N = len(categories)

    # Medie
    ast_f1 = np.mean([x['metrics']['param_f1'] for x in data])
    actionability = np.mean([x['metrics']['actionability_score'] for x in data])
    sbert = np.mean([x['metrics']['sbert_similarity'] for x in data])
    error_cov = np.mean([x['metrics']['error_documentation_score'] for x in data])
    rt_pass = np.mean([x['metrics']['roundtrip_pass_rate'] / 100.0 for x in data])
    retrieval_rr = np.mean([x['metrics']['retrieval_rr'] for x in data])

    values = [ast_f1, actionability, sbert, error_cov, rt_pass, retrieval_rr]
    values += values[:1]  # chiusura poligono

    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7.5, 7.5), subplot_kw=dict(polar=True))

    # Impostazione offset e direzione
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Disegna assi e label
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=9.5, fontweight='bold', color='#1E293B')

    # Y ticks
    ax.set_rlabel_position(30)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], color="#64748B", size=8.5)
    plt.ylim(0, 1.1)

    # Plot dati
    ax.plot(angles, values, color='#0D9488', linewidth=2.4, linestyle='solid', label='Pipeline Multi-Agente (Latest Run)')
    ax.fill(angles, values, color='#0D9488', alpha=0.25)

    # Punti sui vertici
    ax.scatter(angles[:-1], values[:-1], color='#1A365D', s=55, zorder=5)

    for a, v in zip(angles[:-1], values[:-1]):
        ax.annotate(f"{v:.2f}",
                    xy=(a, v),
                    xytext=(0, 7), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1A365D')

    plt.title('Profilo Prestazionale Globale della Pipeline Multi-Agente\n(Benchmark Sintetico-Funzionale)',
              pad=25, fontsize=12.5, fontweight='bold')
    plt.legend(loc='lower right', bbox_to_anchor=(1.15, -0.05), frameon=True, facecolor='white', framealpha=0.9)

    out_path = OUTPUT_DIR / "fig_benchmark_overview_radar.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_roundtrip_taxonomic():
    """
    (d) fig_roundtrip_taxonomic_breakdown.png
    Prestazioni del Round-Trip Differential Testing (Self-Consistency Pass Rate vs Dual Agreement)
    disaggregate per le 3 categorie tassonomiche:
    - Stateless / Primitive
    - Pointer / Buffer-Driven
    - Stateful / Object-Graph
    """
    bench_file = RESULTS_DIR / "benchmark_all" / "latest" / "eval_report_multiagent.json"
    with open(bench_file, encoding='utf-8') as f:
        data = json.load(f)

    tax_groups = {
        'Stateless / Primitive': [],
        'Pointer / Buffer-Driven': [],
        'Stateful / Object-Graph': []
    }

    for item in data:
        ftype = item.get('roundtrip', {}).get('function_type', 'Altro')
        if ftype in tax_groups:
            tax_groups[ftype].append(item)

    categories = list(tax_groups.keys())
    sample_sizes = [len(tax_groups[c]) for c in categories]
    cat_labels = [f"{c}\n(N={n})" for c, n in zip(categories, sample_sizes)]

    pass_rates = [np.mean([x['metrics']['roundtrip_pass_rate'] for x in tax_groups[c]]) for c in categories]
    dual_agreements = [np.mean([x['roundtrip']['execution']['differential']['differential_agreement_rate']
                                for x in tax_groups[c]]) for c in categories]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    x = np.arange(len(categories))
    bar_width = 0.32

    b1 = ax.bar(x - bar_width/2, pass_rates, width=bar_width, label='Round-Trip Pass Rate (Self-Consistency)',
                color='#0D9488', edgecolor='#1E293B', linewidth=0.7, alpha=0.9)
    b2 = ax.bar(x + bar_width/2, dual_agreements, width=bar_width, label='Dual Differential Agreement (Synthesized vs Reference)',
                color='#2563EB', edgecolor='#1E293B', linewidth=0.7, alpha=0.9)

    for bar in b1:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                    fontsize=8.5, fontweight='bold', color='#1E293B')
    for bar in b2:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                    fontsize=8.5, fontweight='bold', color='#1E293B')

    ax.set_ylabel('Percentuale di Successo [%]')
    ax.set_title('Efficacia del Round-Trip Differential Testing per Categoria Tassonomica')
    ax.set_xticks(x)
    ax.set_xticklabels(cat_labels, fontweight='semibold')
    ax.set_ylim(0, 105)
    ax.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.35)

    out_path = OUTPUT_DIR / "fig_roundtrip_taxonomic_breakdown.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_roundtrip_error_causes():
    """
    (e) fig_roundtrip_error_causes.png
    Distribuzione causale degli errori nel Round-Trip:
    - Behavioral / Contract Failure
    - Interface / Signature Mismatch
    - Other Execution Error
    - Missing Symbol / Environment
    """
    rt_file = RESULTS_DIR / "benchmark_all" / "latest" / "roundtrip_results.json"
    with open(rt_file, encoding='utf-8') as f:
        data = json.load(f)

    err_categories = data['error_analysis']['categories']
    names = [c['category'] for c in err_categories]
    counts = [c['count'] for c in err_categories]
    percentages = [c['percentage'] for c in err_categories]

    # Mappatura etichette in italiano
    it_names = [
        'Fallimento Comportamentale / Contratto\n(AssertionError)',
        'Discrepanza Interfaccia / Firma\n(TypeError / Signature)',
        'Errori di Esecuzione Runtime\n(Attribute / ExceptionGroup)',
        'Simbolo / Ambiente Mancante\n(NameError / Import)'
    ]

    colors = ['#DC2626', '#D97706', '#2563EB', '#64748B']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.0), gridspec_kw={'width_ratios': [1.3, 1]})

    # Bar plot orizzontale
    y_pos = np.arange(len(it_names))
    bars = ax1.barh(y_pos, counts, color=colors, edgecolor='#1E293B', linewidth=0.7, alpha=0.9)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(it_names, fontsize=9.5, fontweight='semibold')
    ax1.invert_yaxis()
    ax1.set_xlabel('Numero di Eventi di Errore Rilevati')
    ax1.set_title('Tassonomia Causale dei Fallimenti Round-Trip')
    ax1.set_xlim(0, max(counts) + 3)

    for bar, pct in zip(bars, percentages):
        width = bar.get_width()
        ax1.annotate(f"{int(width)} ({pct:.1f}%)",
                     xy=(width, bar.get_y() + bar.get_height() / 2),
                     xytext=(5, 0), textcoords="offset points",
                     va='center', ha='left', fontsize=9, fontweight='bold', color='#1E293B')

    # Donut chart
    wedges, texts, autotexts = ax2.pie(
        counts,
        autopct='%1.1f%%',
        colors=colors,
        startangle=140,
        pctdistance=0.75,
        wedgeprops=dict(width=0.45, edgecolor='#FFFFFF', linewidth=1.5)
    )
    for at in autotexts:
        at.set_fontsize(8.5)
        at.set_weight('bold')
    ax2.set_title('Ripartizione Percentuale', fontsize=11, fontweight='bold')

    out_path = OUTPUT_DIR / "fig_roundtrip_error_causes.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_semantic_vs_roundtrip_scatter():
    """
    (f) fig_semantic_vs_roundtrip_scatter.png
    Scatter plot correlazione tra Sentence-BERT similarity e Round-Trip Pass Rate
    con retta di regressione e residui evidenziati.
    """
    bench_file = RESULTS_DIR / "benchmark_all" / "latest" / "eval_report_multiagent.json"
    with open(bench_file, encoding='utf-8') as f:
        data = json.load(f)

    sbert_scores = np.array([x['metrics']['sbert_similarity'] for x in data])
    rt_passes = np.array([x['metrics']['roundtrip_pass_rate'] for x in data])
    labels = [x['function_name'].split('::')[-1] for x in data]

    # Regressione lineare
    slope, intercept = np.polyfit(sbert_scores, rt_passes, 1)
    y_pred = slope * sbert_scores + intercept
    residuals = rt_passes - y_pred

    # Correlazione di Pearson
    r_corr = np.corrcoef(sbert_scores, rt_passes)[0, 1]

    fig, ax = plt.subplots(figsize=(8.5, 6.0))

    # Retta di regressione
    x_line = np.linspace(sbert_scores.min() - 0.05, sbert_scores.max() + 0.05, 100)
    ax.plot(x_line, slope * x_line + intercept, color='#2563EB', linestyle='--', linewidth=1.8,
            label=f'Retta di Regressione (Pearson r = {r_corr:.2f})')

    # Linee dei residui
    for i in range(len(sbert_scores)):
        ax.plot([sbert_scores[i], sbert_scores[i]], [rt_passes[i], y_pred[i]],
                color='#CBD5E1', linestyle=':', linewidth=1.0, zorder=2)

    # Scatter points con colormap basata sui residui
    scatter = ax.scatter(sbert_scores, rt_passes, c=np.abs(residuals), cmap='viridis',
                         s=80, edgecolors='#1E293B', linewidths=0.9, zorder=4, alpha=0.95)

    # Annotazioni per i casi più rilevanti
    for i, label in enumerate(labels):
        offset_y = 4 if rt_passes[i] < 90 else -8
        ax.annotate(label, xy=(sbert_scores[i], rt_passes[i]),
                    xytext=(0, offset_y), textcoords="offset points",
                    ha='center', fontsize=7.5, color='#334155')

    cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label('Entità Residuo |y - ŷ|', fontsize=9.5, fontweight='bold')
    cbar.ax.tick_params(labelsize=8.5)

    ax.set_xlabel('Sentence-BERT Similarity (Docstring vs Reference)')
    ax.set_ylabel('Round-Trip Pass Rate [%]')
    ax.set_title('Correlazione tra Similarità Semantica Neurale e Pass Rate Funzionale')
    ax.set_ylim(-5, 115)
    ax.set_xlim(0.38, 0.76)
    ax.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(True, linestyle='--', alpha=0.35)

    out_path = OUTPUT_DIR / "fig_semantic_vs_roundtrip_scatter.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_loc_complexity_pareto():
    """
    (g) fig_loc_complexity_pareto.png
    Scalabilità delle prestazioni al variare delle Linee di Codice (LOC) sorgente.
    Usa una scala logaritmica sull'asse X per accogliere funzioni da 1 riga a 1500 righe.
    """
    bench_file = RESULTS_DIR / "benchmark_all" / "latest" / "eval_report_multiagent.json"
    with open(bench_file, encoding='utf-8') as f:
        data = json.load(f)

    locs = [len(x.get('source_code', '').splitlines()) for x in data]
    rt_pass = [x['metrics']['roundtrip_pass_rate'] for x in data]
    actionability = [x['metrics']['actionability_score'] * 100 for x in data]
    names = [x['function_name'].split('::')[-1] for x in data]

    # Sort per LOC
    sorted_indices = np.argsort(locs)
    locs_sorted = np.array(locs)[sorted_indices]
    rt_sorted = np.array(rt_pass)[sorted_indices]
    act_sorted = np.array(actionability)[sorted_indices]
    names_sorted = np.array(names)[sorted_indices]

    fig, ax1 = plt.subplots(figsize=(9.5, 5.5))

    # Scatter & Linee di andamento
    ax1.set_xscale('log')
    ax1.plot(locs_sorted, rt_sorted, color='#0D9488', marker='o', markersize=7,
             linewidth=1.8, label='Round-Trip Pass Rate [%]', alpha=0.9)
    ax1.plot(locs_sorted, act_sorted, color='#D97706', marker='s', markersize=6,
             linewidth=1.8, linestyle='-.', label='Actionability Score [%]', alpha=0.9)

    # Evidenziazione del range di LOC
    ax1.axvspan(1, 15, color='#F1F5F9', alpha=0.6, label='Funzioni Modulari / Compatte (LOC ≤ 15)')
    ax1.axvspan(15, 2000, color='#FEF3C7', alpha=0.25, label='Monoliti Complessi (LOC > 15)')

    # Annotazioni per casi estremi
    ax1.annotate("http_parser_execute\n(1515 LOC)", xy=(1515, 20), xytext=(400, 40),
                 arrowprops=dict(facecolor='#DC2626', edgecolor='#DC2626', width=1.2, headwidth=5, shrink=0.1),
                 fontsize=8.5, fontweight='bold', color='#B91C1C',
                 bbox=dict(boxstyle="round,pad=0.25", fc="#FEF2F2", ec="#DC2626", lw=0.8))

    ax1.set_xlabel('Linee di Codice Sorgente (LOC C/C++) - Scala Logaritmica')
    ax1.set_ylabel('Efficacia Metriche [%]')
    ax1.set_title('Scalabilità della Pipeline Multi-Agente al Variare della Complessità del Codice (LOC)')
    ax1.set_ylim(-5, 115)
    ax1.grid(True, which='both', linestyle='--', alpha=0.35)
    ax1.legend(loc='lower left', frameon=True, facecolor='white', framealpha=0.9)

    out_path = OUTPUT_DIR / "fig_loc_complexity_pareto.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_metric_distribution_violin():
    """
    (h) fig_distribution_violin.png
    Distribuzione e varianza delle metriche principali:
    - Param F1 (AST)
    - Actionability
    - SBERT Sim
    - BERTScore F1
    - CodeBERT F1
    - LLM Judge (Normalizzato [0-1])
    - Round-Trip Pass Rate (Normalizzato [0-1])
    """
    bench_file = RESULTS_DIR / "benchmark_all" / "latest" / "eval_report_multiagent.json"
    with open(bench_file, encoding='utf-8') as f:
        data = json.load(f)

    metrics_dict = {
        'AST F1': [x['metrics']['param_f1'] for x in data],
        'Actionability': [x['metrics']['actionability_score'] for x in data],
        'SBERT': [x['metrics']['sbert_similarity'] for x in data],
        'BERTScore': [x['metrics']['bert_score_f1'] for x in data],
        'CodeBERT': [x['metrics']['codebert_score_f1'] for x in data],
        'LLM Judge': [x['metrics']['judge_combined'] / 5.0 for x in data],
        'Round-Trip': [x['metrics']['roundtrip_pass_rate'] / 100.0 for x in data]
    }

    df = pd.DataFrame(metrics_dict)

    fig, ax = plt.subplots(figsize=(10, 5.8))

    # Violinplot arricchito con boxplot interno
    palette = sns.color_palette(['#0D9488', '#2563EB', '#D97706', '#64748B', '#0284C7', '#7C3AED', '#16A34A'])
    sns.violinplot(data=df, palette=palette, inner='quartile', cut=0, linewidth=1.2, ax=ax)
    sns.stripplot(data=df, color='#1E293B', size=4.5, jitter=0.15, alpha=0.6, ax=ax)

    ax.set_ylabel('Punteggio Normalizzato [0.0 - 1.0]')
    ax.set_title('Distribuzione e Dispersione delle Metriche Principali di Benchmark (N=15)')
    ax.set_ylim(-0.05, 1.1)
    ax.grid(axis='y', linestyle='--', alpha=0.35)

    out_path = OUTPUT_DIR / "fig_distribution_violin.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def plot_cross_correlation_matrix():
    """
    (i) fig_cross_correlation_matrix.png
    Matrice di correlazione Pearson r tra tutte le metriche nell'ultimo run.
    """
    bench_file = RESULTS_DIR / "benchmark_all" / "latest" / "eval_report_multiagent.json"
    with open(bench_file, encoding='utf-8') as f:
        data = json.load(f)

    # Selezioniamo le metriche numeriche chiave
    selected_metrics = [
        'param_f1',
        'retrieval_rr',
        'sbert_similarity',
        'bert_score_f1',
        'codebert_score_f1',
        'rouge_l',
        'tfidf_similarity',
        'actionability_score',
        'judge_combined',
        'roundtrip_pass_rate'
    ]

    labels = [
        'AST Param F1',
        'Retrieval RR',
        'SBERT Sim',
        'BERTScore F1',
        'CodeBERT F1',
        'ROUGE-L',
        'TF-IDF Sim',
        'Actionability',
        'LLM Judge',
        'Round-Trip Pass'
    ]

    rows = []
    for x in data:
        row = [x['metrics'].get(m, 0.0) for m in selected_metrics]
        rows.append(row)

    df = pd.DataFrame(rows, columns=labels)
    # Rimuoviamo colonne a varianza 0 (se presenti) per evitare NaN in correlazione, ma conserviamo quelle costanti annotando 0
    corr = df.corr()

    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    mask = np.triu(np.ones_like(corr, dtype=bool))

    cmap = sns.diverging_palette(220, 20, as_cmap=True)

    sns.heatmap(corr, mask=mask, cmap=cmap, vmin=-1.0, vmax=1.0, center=0,
                square=True, linewidths=0.6, linecolor='#FFFFFF',
                cbar_kws={"shrink": 0.8, "label": "Coefficiente di Correlazione Pearson (r)"},
                annot=True, fmt='.2f', annot_kws={"size": 8.5, "weight": "bold"}, ax=ax)

    ax.set_title('Matrice di Correlazione Incrociata tra Metriche di Valutazione', pad=15)

    out_path = OUTPUT_DIR / "fig_cross_correlation_matrix.png"
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Salvato: {out_path.name}")


def main():
    print("=" * 65)
    print("Inizio generazione grafici uniformi per la tesi magistrale...")
    print(f"Destinazione: {OUTPUT_DIR}")
    print("=" * 65)

    plot_crossmodal_metrics()
    plot_adversarial_paradox()
    plot_radar_overview()
    plot_roundtrip_taxonomic()
    plot_roundtrip_error_causes()
    plot_semantic_vs_roundtrip_scatter()
    plot_loc_complexity_pareto()
    plot_metric_distribution_violin()
    plot_cross_correlation_matrix()

    print("=" * 65)
    print("Tutti i 9 grafici scientifici generati con successo a 300 DPI!")
    print("=" * 65)


if __name__ == '__main__':
    main()
