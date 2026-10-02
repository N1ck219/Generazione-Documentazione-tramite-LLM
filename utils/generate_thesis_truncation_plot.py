"""
Script di Generazione del Grafico Scientifico:
"Effetto del Troncamento dei Token sui Punteggi di Similarità NLP"
Adattato con lo stile grafico uniforme e accademico a 300 DPI per la Tesi.

Confronta in due subplot coordinati:
- Subplot 1 (Sinistra): Punteggi di similarità delle metriche NLP su 5 scenari calibrati:
    1. Corta Identica (58 tok)
    2. Prefisso Uguale / Coda Diversa 3x (1122 vs 2280 tok) -> "Trappola del Troncamento"
    3. Corta vs Lunga (Inizio Uguale) (139 vs 1122 tok)
    4. Prefisso Diverso / Coda Uguale (1122 vs 2245 tok)
    5. Corta vs Lunga Ortogonale (58 vs 2245 tok)
- Subplot 2 (Destra): Lunghezza effettiva del codice vs finestre di troncamento hardware/modello
    (SBERT a 256 token, BERT / CodeBERT a 512 token) con etichette chiare.

Salvataggio in:
- results/metrics_validation/img_finali/nlp_metric_token_truncation_limits.png
- results/metrics_validation/token_truncation_limits_plot.png (aggiornato)
"""

import os
import sys
from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR_FINALI = ROOT_DIR / "results" / "metrics_validation" / "img_finali"
OUTPUT_DIR_OLD = ROOT_DIR / "results" / "metrics_validation"
OUTPUT_DIR_FINALI.mkdir(parents=True, exist_ok=True)

# Stile Globale Matplotlib uniformato con la suite della tesi
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
    'legend.fontsize': 9.5,
    'figure.titlesize': 15,
    'figure.titleweight': 'bold',
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.12,
    'axes.edgecolor': '#334155',
    'axes.linewidth': 0.9,
    'grid.color': '#CBD5E1',
    'grid.linestyle': '--',
    'grid.linewidth': 0.6,
    'grid.alpha': 0.5,
})

def generate_thesis_truncation_plot():
    # Dati sperimentali verificati
    labels = [
        "1. Corta Identica\n(58 tok)",
        "2. Prefisso Uguale\nCoda Diversa 3x\n(1122 vs 2280 tok)",
        "3. Corta vs Lunga\n(Inizio Uguale)\n(139 vs 1122 tok)",
        "4. Prefisso Diverso\nCoda Uguale\n(1122 vs 2245 tok)",
        "5. Corta vs Lunga\nOrtogonale\n(58 vs 2245 tok)"
    ]

    sbert_scores = [1.000, 1.000, 0.934, 0.412, 0.430]
    bert_scores  = [1.000, 1.000, 0.868, 0.645, 0.593]
    codebert_scores = [1.000, 1.000, 0.935, 0.827, 0.764]
    rouge_scores = [1.000, 0.678, 0.272, 0.663, 0.059]

    cand_tokens = [58, 2280, 1122, 2245, 2245]
    case_names = [
        "1. Corta Identica",
        "2. Prefisso Uguale / Coda Diversa 3x",
        "3. Corta vs Lunga (Inizio Uguale)",
        "4. Prefisso Diverso / Coda Uguale",
        "5. Corta vs Lunga Ortogonale"
    ]

    fig, axes = plt.subplots(1, 2, figsize=(20, 6.8), gridspec_kw={'width_ratios': [1.25, 1.0]})
    fig.subplots_adjust(wspace=0.38)

    # -------------------------------------------------------------------------
    # SUBPLOT 1: Confronto Metriche NLP sui 5 Scenari di Troncamento
    # -------------------------------------------------------------------------
    ax1 = axes[0]
    x = np.arange(len(labels))
    width = 0.18

    # Colori eleganti e coerenti con la suite della tesi
    c_sbert = '#8B5CF6'    # Royal Violet (SBERT)
    c_bert = '#0284C7'     # Sky Blue (BERTScore)
    c_codebert = '#10B981' # Emerald Green (CodeBERTScore)
    c_rouge = '#F59E0B'    # Amber/Orange (ROUGE-L)

    rects1 = ax1.bar(x - 1.5 * width, sbert_scores, width, label='SBERT (Max 256 tok)', color=c_sbert, edgecolor='#1E293B', linewidth=0.7)
    rects2 = ax1.bar(x - 0.5 * width, bert_scores, width, label='BERTScore F1 (Max 512 tok)', color=c_bert, edgecolor='#1E293B', linewidth=0.7)
    rects3 = ax1.bar(x + 0.5 * width, codebert_scores, width, label='CodeBERTScore F1 (Max 512 tok)', color=c_codebert, edgecolor='#1E293B', linewidth=0.7)
    rects4 = ax1.bar(x + 1.5 * width, rouge_scores, width, label='ROUGE-L (Senza Limite Fisico)', color=c_rouge, edgecolor='#1E293B', linewidth=0.7)

    ax1.set_title("Effetto del Troncamento dei Token sui Punteggi di Similarità NLP", pad=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.0)
    ax1.set_ylabel("Punteggio di Similarità [0.0 - 1.0]")
    ax1.set_ylim(0.0, 1.15)
    ax1.axhline(1.0, color='#94A3B8', linestyle=':', linewidth=0.8)
    ax1.legend(loc='upper right', frameon=True, framealpha=0.95, edgecolor='#CBD5E1')
    ax1.grid(True, linestyle='--', alpha=0.5)

    # -------------------------------------------------------------------------
    # SUBPLOT 2: Diagramma Finestre di Troncamento vs Lunghezza Effettiva
    # -------------------------------------------------------------------------
    ax2 = axes[1]
    y_pos = np.arange(len(case_names))
    bar_height = 0.55

    # Barre orizzontali dei token con stile pulito
    bars = ax2.barh(y_pos, cand_tokens, height=bar_height, color='#94A3B8', edgecolor='#334155', linewidth=0.8, alpha=0.85)

    # Linee verticali con soglie di taglio hardware/modello
    ax2.axvline(256, color='#8B5CF6', linestyle='--', linewidth=2.0, label='SBERT Cut-off (256 tok)')
    ax2.axvline(512, color='#0284C7', linestyle='--', linewidth=2.0, label='BERT / CodeBERT Cut-off (512 tok)')

    ax2.set_title("Lunghezza Effettiva del Codice vs Finestre di Troncamento", pad=12)
    ax2.set_xlabel("Numero di Token (BERT Tokenizer)")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(case_names, fontsize=9.0)
    ax2.set_xlim(0, 2750)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='lower right', frameon=True, framealpha=0.95, edgecolor='#CBD5E1')

    # Etichette su ciascuna barra con evidenziazione TRONCATO vs OK
    for bar, tok in zip(bars, cand_tokens):
        w = bar.get_width()
        is_trunc = tok > 512
        color = '#DC2626' if is_trunc else '#059669'
        note = " (TRONCATO!)" if is_trunc else " (OK)"
        ax2.text(w + 35, bar.get_y() + bar.get_height() / 2.0,
                 f"{tok} tok{note}",
                 va='center', fontweight='bold', fontsize=8.8, color=color)

    fig.suptitle("Analisi Sperimentale dei Limiti delle Metriche NLP: Lunghezza dei Token e Troncamento",
                 fontsize=14.5, weight='bold', y=0.99)

    # Salvataggio nelle cartelle target
    out_file1 = OUTPUT_DIR_FINALI / "nlp_metric_token_truncation_limits.png"
    out_file2 = OUTPUT_DIR_OLD / "token_truncation_limits_plot.png"
    
    plt.savefig(out_file1, dpi=300, bbox_inches='tight')
    plt.savefig(out_file2, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"[OK] Grafico tesi salvato in: {out_file1}")
    print(f"[OK] Grafico aggiornato in: {out_file2}")

if __name__ == "__main__":
    generate_thesis_truncation_plot()
