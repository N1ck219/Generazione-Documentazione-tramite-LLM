"""
Script per la generazione dei grafici accademici uniformati (300 DPI)
per le metriche avanzate (LLM-as-a-Judge, Round-Trip Testing, Code Retrieval MRR, Concept Checklist).

Usa esattamente lo stesso template visivo accademico approvato:
- Subplot 1 (Sinistro): Bar chart raggruppato a 6 barre per le 5 classi concettuali (Equivalenti, Adversarial, Simili, Ortogonali, Fluff).
- Subplot 2 (Destro): Bar chart orizzontale dell'Adversarial Paradox Delta (Delta = Score(Bug) - Score(Equiv)).
  - Verde (Delta < 0): Risoluzione del paradosso (il bug logico viene severamente penalizzato).
  - Rosso (Delta > 0): Presenza del paradosso (la metrica premia codice invertito/errato).

Grafici prodotti in results/metrics_validation/img_finali/:
1. judge_metric_faithfulness.png (Perspective A: Technical Faithfulness & Contract)
2. judge_metric_alignment.png (Perspective B: Semantic Alignment & Completeness)
3. judge_metric_combined.png (Combined Judge Score)
4. roundtrip_metric_pass_rate.png (Pytest Execution Pass Rate %)
5. roundtrip_metric_dual_agreement.png (Dual Differential Execution Agreement %)
6. retrieval_metric_mrr.png (Code Retrieval MRR)
7. concept_checklist_score.png (Concept & Contract Checklist Score)
8. advanced_metric_overview_all_classes.png (Quadro sinottico comparativo)
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT_DIR / "results" / "metrics_validation" / "img_finali" / "judge_roundtrip_5classes_results.json"
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
        'key': 'Judge_Faithfulness',
        'title': 'LLM-as-a-Judge: Fedeltà Tecnica e Contratto (Perspective A)',
        'filename': 'judge_metric_faithfulness.png',
        'ylabel': 'Judge Faithfulness Score [0.0 - 1.0]',
        'description': 'Audit semantico della correttezza contrattuale, assenza di allucinazioni e conformità dei vincoli'
    },
    {
        'key': 'Judge_Alignment',
        'title': 'LLM-as-a-Judge: Allineamento Semantico e Completezza (Perspective B)',
        'filename': 'judge_metric_alignment.png',
        'ylabel': 'Judge Alignment Score [0.0 - 1.0]',
        'description': 'Aderenza all\'intento funzionale dell\'autore originale e cattura delle sfumature e dei warning'
    },
    {
        'key': 'Judge_Combined',
        'title': 'LLM-as-a-Judge: Punteggio Combinato Unificato (Perspective A + B)',
        'filename': 'judge_metric_combined.png',
        'ylabel': 'Judge Combined Score [0.0 - 1.0]',
        'description': 'Media armonizzata tra fedeltà tecnica del codice e allineamento semantico della specifica'
    },
    {
        'key': 'RoundTrip_PassRate',
        'title': 'Round-Trip Testing: Pytest Pass Rate % (Esecuzione Dinamica)',
        'filename': 'roundtrip_metric_pass_rate.png',
        'ylabel': 'Pytest Pass Rate [0.0 - 1.0]',
        'description': 'Tasso di superamento della suite di test unitari sintetizzati a partire dalla documentazione'
    },
    {
        'key': 'RoundTrip_DualAgreement',
        'title': 'Round-Trip Testing: Dual Differential Execution Agreement',
        'filename': 'roundtrip_metric_dual_agreement.png',
        'ylabel': 'Differential Agreement [0.0 - 1.0]',
        'description': 'Accordo comportamentale deterministico tra l\'implementazione di riferimento e il candidato'
    },
    {
        'key': 'Code_Retrieval_MRR',
        'title': 'Task a Valle: Code Retrieval MRR (Mean Reciprocal Rank)',
        'filename': 'retrieval_metric_mrr.png',
        'ylabel': 'Reciprocal Rank (MRR) [0.0 - 1.0]',
        'description': 'Capacità di identificare la funzione target nel corpus denso di 30 funzioni'
    },
    {
        'key': 'Concept_Checklist',
        'title': 'Concept Checklist & Contract Guard Coverage',
        'filename': 'concept_checklist_score.png',
        'ylabel': 'Checklist Score [0.0 - 1.0]',
        'description': 'Verifica deterministica della presenza di guardie di errore, vincoli di tipo ed edge-cases'
    }
]


def load_data():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def generate_single_metric_plot(metric_cfg: Dict[str, str], data: List[Dict[str, Any]]):
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

    # Creazione figura a 2 pannelli con proporzioni identiche ai grafici NLP
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
    # Se Delta < 0 (Verde) -> Comportamento corretto: la metrica penalizza il bug logico.
    # Se Delta > 0 (Rosso) -> Paradosso: la metrica premia paradossalmente il bug!
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

    min_x = min(-1.05, min(deltas) - 0.12)
    max_x = max(0.25, max(deltas) + 0.15)
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

    # Nota interpretativa in basso a sinistra o a destra in base a disponibilità
    ax2.annotate(
        "Verde (Delta < 0): RISOLUZIONE PARADOSSO (Penalizzazione del bug)\nRosso (Delta > 0): PARADOSSO (Premiazione del codice rotto)",
        xy=(0.5, 0.02), xycoords='axes fraction',
        ha='center', va='bottom', fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", fc="#F8FAFC", ec="#CBD5E1", lw=0.8)
    )

    plt.suptitle(f"Valutazione Metrica: {metric_title}", fontsize=14.5, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    out_file = OUTPUT_DIR / filename
    plt.savefig(out_file)
    plt.close()
    print(f"[OK] Grafico generato con successo: {out_file.name}")


def generate_overview_advanced_metrics(data: List[Dict[str, Any]]):
    """
    Quadro sinottico riassuntivo che compara le metriche avanzate (Judge, RoundTrip, Retrieval, Checklist)
    rispetto alle metriche lessicali/neurali di riferimento.
    """
    categories = CATEGORIES
    metrics = [m['key'] for m in METRICS_CONFIG]
    metric_labels = [
        'Judge Faithfulness',
        'Judge Alignment',
        'Judge Combined',
        'Round-Trip Pass Rate',
        'Dual Agreement',
        'Code Retrieval MRR',
        'Checklist Coverage'
    ]

    cat_means = {cat: [] for cat in categories}
    for cat in categories:
        cat_items = [it for it in data if it['category'] == cat]
        for m in metrics:
            avg_val = np.mean([it['scores'][m] for it in cat_items])
            cat_means[cat].append(avg_val)

    fig, ax = plt.subplots(figsize=(14, 7))
    y = np.arange(len(categories))
    bar_h = 0.11
    colors = ['#4F46E5', '#7C3AED', '#2563EB', '#059669', '#10B981', '#0284C7', '#D97706']

    for i, m_name in enumerate(metric_labels):
        offset = (i - 3) * bar_h
        vals = [cat_means[cat][i] for cat in categories]
        bars = ax.barh(y + offset, vals, height=bar_h, label=m_name, color=colors[i], edgecolor='#0F172A', linewidth=0.6)

    ax.set_yticks(y)
    ax.set_yticklabels(CAT_LABELS, fontsize=10, fontweight='semibold')
    ax.set_xlabel("Punteggio Medio Aggregato [0.0 - 1.0]", fontsize=11)
    ax.set_title("Quadro Sinottico: Confronto Metriche Avanzate (Judge, Round-Trip, Retrieval, Checklist)", fontsize=13, pad=12)
    ax.set_xlim(0.0, 1.15)
    ax.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', framealpha=0.95, edgecolor='#CBD5E1', ncol=2)
    ax.grid(axis='x', linestyle='--', alpha=0.5)

    out_file = OUTPUT_DIR / "advanced_metric_overview_all_classes.png"
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close()
    print(f"[OK] Grafico sinottico avanzato generato: {out_file.name}")


def main():
    print("=" * 80)
    print("GENERAZIONE GRAFICI SCIENTIFICI DELLE METRICHE NON-NLP PER LA TESI")
    print(f"Destinazione: {OUTPUT_DIR}")
    print("=" * 80)

    data = load_data()

    # 1. Genera un grafico individuale per ciascuna delle 7 metriche non-NLP
    for m_cfg in METRICS_CONFIG:
        generate_single_metric_plot(m_cfg, data)

    # 2. Genera il grafico sinottico d'insieme
    generate_overview_advanced_metrics(data)

    print("=" * 80)
    print("Tutti gli 8 grafici unificati a 300 DPI sono pronti in img_finali!")
    print("=" * 80)


if __name__ == "__main__":
    main()
