"""
Generatore di Grafici Accademici per la Tesi:
Sensibilita' e Limiti Strutturali delle Metriche NLP rispetto a:
- Lunghezza dei Token (Short <128, Mid ~300, Over 512, Massive ~1000)
- Posizione della Divergenza (Head vs Tail)
- Hard Truncation Boundary (Cecita' Oltre i 512 token)
- Diluizione del Segnale (Needle-in-a-Haystack)

Stile coordinato con la suite scientifica della tesi:
- 2 Subplot coordinati
- Figure size (18, 7.2), 300 DPI
- Palette e annotazioni coerenti
- Salvataggio in results/metrics_validation/img_finali/
"""

import os
import sys
import json
from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT_DIR / "results" / "metrics_validation" / "img_finali" / "nlp_token_length_sensitivity_results.json"
OUTPUT_DIR = ROOT_DIR / "results" / "metrics_validation" / "img_finali"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Stile Globale Matplotlib
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

mpl.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
    'font.size': 10,
    'axes.titlesize': 13,
    'axes.titleweight': 'bold',
    'axes.titlepad': 14,
    'axes.labelsize': 11,
    'axes.labelweight': 'bold',
    'axes.labelpad': 8,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 9.5,
    'figure.titlesize': 15,
    'figure.titleweight': 'bold',
    'legend.fontsize': 9.5,
    'legend.frameon': True,
    'legend.framealpha': 0.95,
    'figure.autolayout': False
})

METRIC_PALETTE = {
    'SBERT': '#1f77b4',         # Steel Blue
    'BERTScore_F1': '#ff7f0e',  # Warm Amber
    'CodeBERT_F1': '#2ca02c',   # Forest Green
    'ROUGE_L': '#9467bd',       # Deep Purple
    'TFIDF': '#8c564b'          # Muted Rust
}

METRIC_LABELS = {
    'SBERT': 'SBERT (all-MiniLM-L6)',
    'BERTScore_F1': 'BERTScore F1 (bert-base)',
    'CodeBERT_F1': 'CodeBERTScore F1 (codebert)',
    'ROUGE_L': 'ROUGE-L (LCS ratio)',
    'TFIDF': 'TF-IDF Cosine (n-grams)'
}

def generate_token_length_plots():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    fig = plt.figure(figsize=(20, 8.2), dpi=300)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.75, 1.0], wspace=0.26)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    # -------------------------------------------------------------------------
    # SUBPLOT 1: Grouped Bar Chart su tutti i 7 Scenari
    # -------------------------------------------------------------------------
    scenario_names = [d["name"] for d in data]
    scenario_ids = [d["id"] for d in data]
    tokens = [d["tokens_est"] for d in data]
    metrics = ['SBERT', 'BERTScore_F1', 'CodeBERT_F1', 'ROUGE_L', 'TFIDF']
    
    n_scenarios = len(data)
    n_metrics = len(metrics)
    bar_width = 0.15
    index = np.arange(n_scenarios)

    for i, m in enumerate(metrics):
        scores = [d["scores"][m] for d in data]
        offsets = index + (i - (n_metrics - 1) / 2) * bar_width
        rects = ax1.bar(
            offsets, scores, bar_width,
            label=METRIC_LABELS[m],
            color=METRIC_PALETTE[m],
            alpha=0.90,
            edgecolor='black',
            linewidth=0.6,
            zorder=3
        )
        
        # Etichette sui valori più significativi
        for r, score in zip(rects, scores):
            if score < 0.82:
                ax1.text(
                    r.get_x() + r.get_width()/2., r.get_height() + 0.02,
                    f"{score:.2f}",
                    ha='center', va='bottom', fontsize=7.5, rotation=90,
                    weight='bold', color='#333333'
                )

    ax1.set_title("Sensibilità delle Metriche NLP a Lunghezza dei Token e Posizione della Modifica", pad=12)
    ax1.set_ylabel("Punteggio di Similarità Stimato [0.0 - 1.0]")
    ax1.set_xticks(index)
    ax1.set_xticklabels(scenario_names, fontsize=8.2)
    ax1.set_ylim(0.0, 1.18)
    ax1.axhline(1.0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    
    # Evidenziazione area oltre 512 token
    ax1.axvspan(3.5, 6.5, color='#ffcccc', alpha=0.20, zorder=1)
    ax1.text(5.0, 1.10, "⚠️ Zona Troncamento Rigido (>512 tok) & Diluizione", 
             ha='center', va='center', fontsize=9.2, fontweight='bold', color='#a83232',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffe6e6', edgecolor='#ff9999', alpha=0.9))

    ax1.grid(True, linestyle=':', alpha=0.6, zorder=0)
    ax1.legend(loc='lower left', ncol=3, framealpha=0.95, edgecolor='#cccccc', fontsize=8.8)

    # -------------------------------------------------------------------------
    # SUBPLOT 2: Studio della Cecità da Troncamento (Equal Head vs Equal Tail a >512 tok)
    # & Asimmetria Head vs Tail
    # -------------------------------------------------------------------------
    idx_blind = scenario_ids.index("over_512_equal_head_diff_tail")
    idx_caught = scenario_ids.index("over_512_diff_head_equal_tail")
    
    scores_blind = [data[idx_blind]["scores"][m] for m in metrics]
    scores_caught = [data[idx_caught]["scores"][m] for m in metrics]
    
    y_idx = np.arange(len(metrics))
    h_bar = 0.35

    b1 = ax2.barh(y_idx + h_bar/2, scores_blind, h_bar, 
                 label='Head Uguale, Tail Opposta\n(Modifica oltre token 512)', 
                 color='#d9534f', edgecolor='black', linewidth=0.7, alpha=0.85, zorder=3)
    b2 = ax2.barh(y_idx - h_bar/2, scores_caught, h_bar, 
                 label='Head Diversa, Tail Uguale\n(Modifica nei primi 512 tok)', 
                 color='#5cb85c', edgecolor='black', linewidth=0.7, alpha=0.85, zorder=3)

    for r in b1:
        w = r.get_width()
        label_text = f"{w:.3f}" if w < 1.0 else "1.000 (CIECA)"
        ax2.text(w - 0.04 if w >= 0.9 else w + 0.02, r.get_y() + r.get_height()/2,
                 label_text, ha='right' if w >= 0.9 else 'left', va='center',
                 fontsize=8.5, fontweight='bold', color='white' if w >= 0.9 else '#a83232')

    for r in b2:
        w = r.get_width()
        ax2.text(w + 0.02, r.get_y() + r.get_height()/2,
                 f"{w:.3f}", ha='left', va='center', fontsize=8.5, fontweight='bold', color='#2b662b')

    ax2.set_title("Focus Boundary 512: Cecità di Troncamento Asimmetrica", pad=12)
    ax2.set_xlabel("Punteggio di Similarità")
    ax2.set_yticks(y_idx)
    ax2.set_yticklabels([METRIC_LABELS[m].split(" (")[0] for m in metrics], fontweight='bold')
    ax2.set_xlim(0.0, 1.25)
    ax2.grid(True, linestyle=':', alpha=0.6, zorder=0)
    ax2.legend(loc='lower right', framealpha=0.95, edgecolor='#cccccc', fontsize=8.5)

    # Didascalia interpretativa in calce al subplot 2
    ax2.text(0.5, -0.12, 
             "• Se divergenza >512 tok: SBERT, BERTScore e CodeBERT sono ciechi (1.000).\n"
             "• Se divergenza nei primi 512 tok: la diversità viene catturata (0.65 - 0.79).\n"
             "• ROUGE-L non ha limite rigido di token ma soffre l'appiattimento da diluizione.",
             transform=ax2.transAxes, fontsize=8.5, verticalalignment='top', horizontalalignment='center',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#fffbe6', edgecolor='#ffe58f', alpha=0.95))

    fig.suptitle("Analisi Sperimentale dei Limiti delle Metriche NLP: Lunghezza dei Token, Posizione e Troncamento",
                 fontsize=14.5, weight='bold', y=0.98)

    output_path = OUTPUT_DIR / "nlp_metric_token_length_position_sensitivity.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Grafico generato con successo: {output_path}")

if __name__ == "__main__":
    generate_token_length_plots()
