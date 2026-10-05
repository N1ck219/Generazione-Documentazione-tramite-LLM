"""
Script per la generazione dei grafici scientifici uniformati per la tesi magistrale.
Produce un grafico ad alta risoluzione (300 DPI) per ciascuna metrica NLP:
1. SBERT Cosine Similarity
2. BERTScore F1
3. CodeBERTScore F1
4. ROUGE-L
5. TF-IDF Cosine Similarity
6. METEOR Score

I grafici confrontano le 5 classi concettuali:
- Equivalenti
- Adversarial (Bug Critico)
- Simili (Dominio Affine)
- Ortogonali (Zero Baseline)
- Fluff / Verbosita'

Su tutti i 6 campi / rappresentazioni disponibili:
- C vs C
- Python vs Python
- C vs Python (Cross-Language)
- Doc vs Doc (Doxygen / Docstring)
- Mermaid vs Mermaid (Diagrammi AST / Control Flow)
- Pseudocodice vs Pseudocodice (Canonical IR)

Salvati nella cartella results/metrics_validation/img_finali/
con stile unico, elegante e accademico.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

# Percorsi
ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT_DIR / "results" / "metrics_validation" / "img_finali" / "nlp_benchmark_5classes_results.json"
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
    'xtick.labelsize': 10,
    'ytick.labelsize': 9.5,
    'legend.fontsize': 9.5,
    'legend.title_fontsize': 10,
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

# Palette cromatica coerente per i 6 domini / rappresentazioni
DOMAIN_COLORS = {
    'C vs C': '#1E3A8A',                 # Deep Navy Blue
    'Python vs Python': '#0284C7',       # Sky Blue
    'C vs Python': '#0D9488',            # Deep Teal
    'Doc vs Doc': '#8B5CF6',             # Royal Purple / Violet
    'Mermaid vs Mermaid': '#F59E0B',     # Warm Amber / Orange
    'Pseudocodice vs Pseudocodice': '#10B981' # Emerald Green
}

CATEGORIES = [
    'EQUIVALENT',
    'ADVERSARIAL',
    'DOMAIN_SIMILAR',
    'ORTHOGONAL',
    'FLUFF_VERBOSITY'
]

CAT_LABELS = [
    'Equivalenti\n(Stessa Logica)',
    'Adversarial\n(Bug Critico / Negaz.)',
    'Simili\n(Dominio Affine)',
    'Ortogonali\n(Zero Baseline)',
    'Fluff / Verbosità\n(Diluizione Testuale)'
]

DOMAINS = [
    'C vs C',
    'Python vs Python',
    'C vs Python',
    'Doc vs Doc',
    'Mermaid vs Mermaid',
    'Pseudocodice vs Pseudocodice'
]

DOMAIN_SHORT_LABELS = [
    'C vs C',
    'Python vs Python',
    'C vs Python (Cross)',
    'Doc vs Doc',
    'Mermaid Flowchart',
    'Pseudocodice Canonico'
]

METRICS_CONFIG = [
    {
        'key': 'SBERT',
        'title': 'Sentence-BERT Cosine Similarity (all-MiniLM-L6-v2)',
        'filename': 'nlp_metric_sbert.png',
        'ylabel': 'SBERT Cosine Similarity [0.0 - 1.0]',
        'description': 'Similarità semantica densa a livello di intero enunciato (pooling 384-d)'
    },
    {
        'key': 'BERTScore_F1',
        'title': 'BERTScore F1 (bert-base-uncased)',
        'filename': 'nlp_metric_bertscore_f1.png',
        'ylabel': 'BERTScore F1-Score [0.0 - 1.0]',
        'description': 'Allineamento greedy token-to-token contestualizzato generale'
    },
    {
        'key': 'CodeBERT_F1',
        'title': 'CodeBERTScore F1 (microsoft/codebert-base)',
        'filename': 'nlp_metric_codebert_f1.png',
        'ylabel': 'CodeBERT F1-Score [0.0 - 1.0]',
        'description': 'Allineamento contestuale specializzato su codice sorgente e commenti bilingui'
    },
    {
        'key': 'ROUGE_L',
        'title': 'ROUGE-L F1 (Longest Common Subsequence)',
        'filename': 'nlp_metric_rouge_l.png',
        'ylabel': 'ROUGE-L F1-Score [0.0 - 1.0]',
        'description': 'Sovrapposizione lessicale esatta basata sulla più lunga sottosequenza comune'
    },
    {
        'key': 'TFIDF_Cosine',
        'title': 'TF-IDF Cosine Similarity',
        'filename': 'nlp_metric_tfidf_cosine.png',
        'ylabel': 'TF-IDF Cosine Similarity [0.0 - 1.0]',
        'description': 'Somiglianza angolare pesata sulla frequenza dei termini (Bag-of-Words pesato)'
    },
    {
        'key': 'METEOR',
        'title': 'METEOR Score (Synonyms, Stemming & WordNet)',
        'filename': 'nlp_metric_meteor.png',
        'ylabel': 'METEOR Score [0.0 - 1.0]',
        'description': 'Allineamento lessicale avanzato con stemming, sinonimia e penalità di frammentazione'
    }
]


def load_data():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def generate_single_metric_plot(metric_cfg: Dict[str, str], data: List[Dict[str, Any]]):
    """
    Genera un grafico unificato a 2 pannelli (layout scientifico per tesi):
    - Subplot 1 (Sinistro): Bar chart raggruppato a 6 barre per ognuna delle 5 classi concettuali.
    - Subplot 2 (Destro): Bar chart del Delta 'Adversarial Paradox' (Adversarial - Equivalente)
      per ciascuno dei 6 domini, evidenziando se la metrica premia paradossalmente il bug!
    """
    metric_key = metric_cfg['key']
    metric_title = metric_cfg['title']
    filename = metric_cfg['filename']
    ylabel = metric_cfg['ylabel']

    # Estrazione matrice (5 categorie x 6 domini)
    matrix = np.zeros((len(CATEGORIES), len(DOMAINS)))
    for c_idx, cat in enumerate(CATEGORIES):
        for d_idx, dom in enumerate(DOMAINS):
            match = [item for item in data if item['category'] == cat and item['domain'] == dom]
            if match:
                matrix[c_idx, d_idx] = match[0]['scores'][metric_key]
            else:
                matrix[c_idx, d_idx] = 0.0

    # Creazione figura a 2 pannelli con proporzioni 1.8 : 1
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6.8), gridspec_kw={'width_ratios': [1.85, 1.0]})

    # -------------------------------------------------------------------------
    # SUBPLOT 1: Confronto delle 5 Classi attraverso i 6 Campi
    # -------------------------------------------------------------------------
    x = np.arange(len(CATEGORIES))
    n_bars = len(DOMAINS)
    total_width = 0.82
    bar_width = total_width / n_bars

    for d_idx, dom in enumerate(DOMAINS):
        offset = (d_idx - (n_bars - 1) / 2) * bar_width
        vals = matrix[:, d_idx]
        color = DOMAIN_COLORS[dom]
        label = DOMAIN_SHORT_LABELS[d_idx]
        bars = ax1.bar(
            x + offset, vals, width=bar_width, label=label,
            color=color, edgecolor='#0F172A', linewidth=0.65, alpha=0.92
        )
        # Annotazione valori sopra ogni barra
        for bar in bars:
            h = bar.get_height()
            if h >= 0.04:
                ax1.annotate(
                    f"{h:.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 2), textcoords="offset points",
                    ha='center', va='bottom', fontsize=7.2, fontweight='bold', color='#1E293B', rotation=90
                )

    ax1.set_title(f"Distribuzione del Punteggio nelle 5 Classi Concettuali", fontsize=12.5, pad=12)
    ax1.set_ylabel(ylabel, fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(CAT_LABELS, fontsize=9.5, fontweight='semibold')
    ax1.set_ylim(0.0, 1.18)
    ax1.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', framealpha=0.92, edgecolor='#CBD5E1', ncol=2)
    ax1.grid(axis='y', linestyle='--', alpha=0.45)

    # -------------------------------------------------------------------------
    # SUBPLOT 2: The Adversarial Paradox Delta (Bug Critico - Equivalente)
    # Delta = Score(ADVERSARIAL) - Score(EQUIVALENT)
    # Se Delta > 0 (Rosso) -> Paradosso: la metrica assegna score piu' alto al codice rotto!
    # Se Delta < 0 (Verde) -> Comportamento corretto: la metrica penalizza il bug logico.
    # -------------------------------------------------------------------------
    equiv_vals = matrix[0, :]  # EQUIVALENT
    advers_vals = matrix[1, :] # ADVERSARIAL
    deltas = advers_vals - equiv_vals

    y_pos = np.arange(len(DOMAINS))
    bar_colors = ['#DC2626' if d > 0 else '#16A34A' for d in deltas]

    h_bars = ax2.barh(y_pos, deltas, color=bar_colors, edgecolor='#0F172A', linewidth=0.7, alpha=0.88, height=0.55)
    ax2.axvline(0, color='#0F172A', linewidth=1.1)

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(DOMAIN_SHORT_LABELS, fontsize=9.5, fontweight='semibold')
    ax2.set_xlabel("Differenza di Score: Delta = Score(Bug) - Score(Equiv)", fontsize=10.5)
    ax2.set_title("The Adversarial Paradox:\nSensibilità ai Bug Logici per Campo", fontsize=12.5, pad=12)

    min_x = min(-0.45, min(deltas) - 0.12)
    max_x = max(0.45, max(deltas) + 0.15)
    ax2.set_xlim(min_x, max_x)
    ax2.grid(axis='x', linestyle='--', alpha=0.45)

    for bar, d in zip(h_bars, deltas):
        w = bar.get_width()
        x_text = w + (0.02 if w >= 0 else -0.02)
        ha = 'left' if w >= 0 else 'right'
        ax2.annotate(
            f"{d:+.3f}",
            xy=(x_text, bar.get_y() + bar.get_height() / 2),
            va='center', ha=ha, fontsize=8.5, fontweight='bold',
            color='#B91C1C' if d > 0 else '#15803D'
        )

    # Nota interpretativa in basso a destra
    ax2.annotate(
        "Rosso (Delta > 0): PARADOSSO (premia codice rotto!)\nVerde (Delta < 0): Penalizzazione corretta del bug",
        xy=(0.5, 0.02), xycoords='axes fraction',
        ha='center', va='bottom', fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", fc="#F8FAFC", ec="#CBD5E1", lw=0.8)
    )

    plt.suptitle(f"Valutazione Metrica NLP: {metric_title}", fontsize=14.5, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    out_file = OUTPUT_DIR / filename
    plt.savefig(out_file)
    plt.close()
    print(f"[OK] Grafico generato con successo: {out_file.name}")


def generate_overview_radar_all_metrics(data: List[Dict[str, Any]]):
    """
    Grafico sinottico opzionale: Radar/Spider chart riassuntivo che compara
    le 6 metriche medie nelle 5 classi concettuali.
    """
    categories = CATEGORIES
    metrics = [m['key'] for m in METRICS_CONFIG]
    metric_labels = ['SBERT', 'BERT F1', 'CodeBERT F1', 'ROUGE-L', 'TF-IDF', 'METEOR']

    # Medie per classe su tutti i domini
    cat_means = {cat: [] for cat in categories}
    for cat in categories:
        cat_items = [it for it in data if it['category'] == cat]
        for m in metrics:
            avg_val = np.mean([it['scores'][m] for it in cat_items])
            cat_means[cat].append(avg_val)

    # Grafico a barre orizzontali aggregate
    fig, ax = plt.subplots(figsize=(13, 6.5))
    y = np.arange(len(categories))
    bar_h = 0.11
    colors = ['#0D9488', '#2563EB', '#10B981', '#64748B', '#0284C7', '#F59E0B', '#8B5CF6']

    for i, m_name in enumerate(metric_labels):
        offset = (i - 3) * bar_h
        vals = [cat_means[cat][i] for cat in categories]
        bars = ax.barh(y + offset, vals, height=bar_h, label=m_name, color=colors[i], edgecolor='#0F172A', linewidth=0.6)

    ax.set_yticks(y)
    ax.set_yticklabels(CAT_LABELS, fontsize=10, fontweight='semibold')
    ax.set_xlabel("Punteggio Medio Aggregato [0.0 - 1.0]", fontsize=11)
    ax.set_title("Quadro Sinottico: Confronto delle 6 Metriche NLP sulle 5 Classi Concettuali", fontsize=13, pad=12)
    ax.set_xlim(0.0, 1.15)
    ax.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', framealpha=0.95, edgecolor='#CBD5E1', ncol=2)
    ax.grid(axis='x', linestyle='--', alpha=0.5)

    out_file = OUTPUT_DIR / "nlp_metric_overview_all_classes.png"
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close()
    print(f"[OK] Grafico sinottico generato: {out_file.name}")


def main():
    print("=" * 80)
    print("GENERAZIONE GRAFICI SCIENTIFICI DELLE METRICHE NLP PER LA TESI")
    print(f"Destinazione: {OUTPUT_DIR}")
    print("=" * 80)

    data = load_data()

    # 1. Genera un grafico individuale per ciascuna delle 6 metriche
    for m_cfg in METRICS_CONFIG:
        generate_single_metric_plot(m_cfg, data)

    # 2. Genera il grafico sinottico d'insieme
    generate_overview_radar_all_metrics(data)

    print("=" * 80)
    print("Tutti i 7 grafici unificati a 300 DPI sono pronti in img_finali!")
    print("=" * 80)


if __name__ == "__main__":
    main()
