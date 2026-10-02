"""
Script per la generazione dei grafici scientifici (300 DPI) dedicati allo
stress test estremo sui limiti delle metriche (Troncamento, Distrazione Min/Max,
Negazione singolo carattere, Off-by-one, Offuscamento nomi, Fluff & Allucinazione).

Usa esattamente lo stesso template visivo accademico:
- Stile Seaborn Whitegrid personalizzato
- Colori armonizzati coerenti con la tesi
- Annotazioni numeriche puntuali su ogni barra
- Pannello analitico di confronto a coppie / famiglie
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
INPUT_JSON = ROOT_DIR / "results" / "metrics_validation" / "img_finali" / "stress_test_metrics_limits_results.json"
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


def generate_stress_test_main_plot(data: List[Dict[str, Any]]):
    """
    Grafico Principale di Stress Test:
    Confronta sui 6 scenari limite estremi le 4 famiglie:
    1. Metriche NLP Classiche (Media SBERT + CodeBERT + ROUGE-L)
    2. LLM-as-a-Judge Superficiale / Naive (senza Chain-of-Thought rigoroso)
    3. LLM-as-a-Judge Strict CoT (con tassonomia formale DEF-1..5)
    4. Round-Trip Dynamic Pytest (esecuzione funzionale reale)
    """
    labels = [
        "1. Troncamento >512t\n(Bug a riga 95)",
        "2. Min vs Max\n(Inversione speculare)",
        "3. Negazione Carattere\n(Contratto == vs !=)",
        "4. Off-by-One\n(Intervallo < vs <=)",
        "5. Renaming Nomi\n(Logica invariata)",
        "6. Camouflage Alluc.\n(Fluff forbito)"
    ]

    nlp_avg = [np.mean([d["scores"]["SBERT"], d["scores"]["CodeBERT"], d["scores"]["ROUGE_L"]]) for d in data]
    judge_naive = [d["scores"]["Judge_Naive"] for d in data]
    judge_strict = [d["scores"]["Judge_Strict_CoT"] for d in data]
    roundtrip = [d["scores"]["RoundTrip_PassRate"] for d in data]

    # Layout a due pannelli coerente con la tesi:
    # Subplot 1 (Sinistro): Le 4 famiglie a confronto sui 6 scenari
    # Subplot 2 (Destro): Vulnerabilità Empirica (Score Assegnato al Bug - 0.0) -> più alto = più vulnerabile!
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7.2), gridspec_kw={'width_ratios': [1.85, 1.0]})

    x = np.arange(len(labels))
    width = 0.20

    c_nlp = '#0284C7'       # Sky Blue
    c_naive = '#F59E0B'     # Amber
    c_strict = '#8B5CF6'    # Royal Purple
    c_rt = '#10B981'        # Emerald Green

    b1 = ax1.bar(x - 1.5 * width, nlp_avg, width, label='Metriche NLP (SBERT/CodeBERT/ROUGE)', color=c_nlp, edgecolor='#0F172A', linewidth=0.65, alpha=0.92)
    b2 = ax1.bar(x - 0.5 * width, judge_naive, width, label='LLM Judge Superficiale (No CoT)', color=c_naive, edgecolor='#0F172A', linewidth=0.65, alpha=0.92)
    b3 = ax1.bar(x + 0.5 * width, judge_strict, width, label='LLM Judge Strict (Audit CoT DEF-1..5)', color=c_strict, edgecolor='#0F172A', linewidth=0.65, alpha=0.92)
    b4 = ax1.bar(x + 1.5 * width, roundtrip, width, label='Round-Trip Pytest (Verità Funzionale)', color=c_rt, edgecolor='#0F172A', linewidth=0.65, alpha=0.92)

    # Annotazioni numeriche verticali
    for bars in [b1, b2, b3, b4]:
        for bar in bars:
            h = bar.get_height()
            if h >= 0.04:
                ax1.annotate(
                    f"{h:.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 2), textcoords="offset points",
                    ha='center', va='bottom', fontsize=7.2, fontweight='bold', color='#1E293B', rotation=90
                )

    ax1.set_title("Analisi Comparativa dei Limiti delle Metriche nei 6 Scenari di Stress Test", fontsize=12.5, pad=12)
    ax1.set_ylabel("Punteggio Assegnato [0.0 - 1.0]", fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.2, fontweight='semibold')
    ax1.set_ylim(0.0, 1.20)
    ax1.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', framealpha=0.95, edgecolor='#CBD5E1', ncol=2)
    ax1.grid(axis='y', linestyle='--', alpha=0.45)

    # -------------------------------------------------------------------------
    # SUBPLOT 2: The Deception Index / Vulnerabilità al Falso Positivo
    # Quanta illusione di correttezza genera la metrica su bug critici?
    # Differenza tra Metrica NLP e Verità Funzionale (RoundTrip):
    # Deception = Score_NLP - RoundTrip_PassRate
    # Se Deception > 0 (Rosso): La metrica promuove codice rotto o con bug!
    # Se Deception < 0 (Verde): La metrica penalizza ingiustamente codice corretto (es. renaming).
    # -------------------------------------------------------------------------
    deception_deltas = np.array(nlp_avg) - np.array(roundtrip)
    y_pos = np.arange(len(labels))

    short_scenario_labels = [
        "1. Troncamento >512 Tokens",
        "2. Distrazione Min vs Max",
        "3. Negazione Singolo Carattere",
        "4. Off-by-One Boundary",
        "5. Rinominazione Variabili",
        "6. Camouflage Allucinazione"
    ]

    bar_colors = ['#DC2626' if d > 0.05 else ('#D97706' if d < -0.05 else '#16A34A') for d in deception_deltas]

    h_bars = ax2.barh(y_pos, deception_deltas, color=bar_colors, edgecolor='#0F172A', linewidth=0.7, alpha=0.88, height=0.55)
    ax2.axvline(0, color='#0F172A', linewidth=1.1)

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(short_scenario_labels, fontsize=9.5, fontweight='semibold')
    ax2.set_xlabel("Deception Index: Delta = Score(NLP) - Verità Funzionale(Pytest)", fontsize=10.5)
    ax2.set_title("Deception Index:\nVulnerabilità ai Falsi Positivi delle Metriche NLP", fontsize=12.5, pad=12)

    ax2.set_xlim(-0.70, 1.15)
    ax2.grid(axis='x', linestyle='--', alpha=0.45)

    for bar, d in zip(h_bars, deception_deltas):
        w = bar.get_width()
        x_text = w + (0.02 if w >= 0 else -0.02)
        ha = 'left' if w >= 0 else 'right'
        ax2.annotate(
            f"{d:+.2f}",
            xy=(x_text, bar.get_y() + bar.get_height() / 2),
            va='center', ha=ha, fontsize=8.5, fontweight='bold',
            color='#B91C1C' if d > 0.05 else ('#B45309' if d < -0.05 else '#15803D')
        )

    ax2.annotate(
        "Rosso (Delta > 0): FALSO POSITIVO (promuove bug critici)\nArancione (Delta < 0): FALSO NEGATIVO (cieco al refactoring)\nVerde (Delta = 0): Perfetto allineamento",
        xy=(0.5, 0.02), xycoords='axes fraction',
        ha='center', va='bottom', fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", fc="#F8FAFC", ec="#CBD5E1", lw=0.8)
    )

    plt.suptitle("Stress Test Scientifico sui Limiti Architetturali delle Metriche di Valutazione", fontsize=14.5, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    out_file = OUTPUT_DIR / "stress_test_metrics_limits_comparison.png"
    plt.savefig(out_file)
    plt.close()
    print(f"[OK] Grafico principale di stress test salvato: {out_file.name}")


def generate_llm_judge_robustness_plot(data: List[Dict[str, Any]]):
    """
    Grafico 2: Studio di Robustezza dell'LLM-as-a-Judge.
    Confronto diretto:
    - LLM Judge Superficiale / Naive (vulnerabile al tono forbito, distrazione min/max, off-by-one)
    - LLM Judge con Audit Strict CoT (Chain-of-Thought e tassonomia formale DEF)
    """
    labels = [
        "1. Troncamento >512t\n(Bug riga 95)",
        "2. Min vs Max\n(Speculare)",
        "3. Negazione Carattere\n(== vs !=)",
        "4. Off-by-One\n(< vs <=)",
        "5. Nomi Variabili\n(Offuscamento)",
        "6. Camouflage Alluc.\n(Fluff Forbito)"
    ]

    judge_naive = [d["scores"]["Judge_Naive"] for d in data]
    judge_strict = [d["scores"]["Judge_Strict_CoT"] for d in data]
    deltas = np.array(judge_naive) - np.array(judge_strict)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6.8), gridspec_kw={'width_ratios': [1.85, 1.0]})

    x = np.arange(len(labels))
    width = 0.35

    b1 = ax1.bar(x - width/2, judge_naive, width, label='LLM-as-a-Judge Superficiale (Prompt Standard)', color='#F59E0B', edgecolor='#0F172A', linewidth=0.65, alpha=0.92)
    b2 = ax1.bar(x + width/2, judge_strict, width, label='LLM-as-a-Judge Rigoroso (Audit CoT + Rubrica DEF)', color='#6366F1', edgecolor='#0F172A', linewidth=0.65, alpha=0.92)

    for bars in [b1, b2]:
        for bar in bars:
            h = bar.get_height()
            if h >= 0.04:
                ax1.annotate(
                    f"{h:.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 2), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight='bold', color='#1E293B', rotation=90
                )

    ax1.set_title("Vulnerabilità di LLM-as-a-Judge alla Distrazione Superficiale e al Camouflage", fontsize=12.5, pad=12)
    ax1.set_ylabel("Punteggio Assegnato [0.0 - 1.0]", fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.5, fontweight='semibold')
    ax1.set_ylim(0.0, 1.18)
    ax1.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', framealpha=0.95, edgecolor='#CBD5E1')
    ax1.grid(axis='y', linestyle='--', alpha=0.45)

    # Subplot 2: Guadagno di Accuratezza con Strict CoT
    y_pos = np.arange(len(labels))
    h_bars = ax2.barh(y_pos, deltas, color='#10B981', edgecolor='#0F172A', linewidth=0.7, alpha=0.88, height=0.55)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels, fontsize=9.2, fontweight='semibold')
    ax2.set_xlabel("Riduzione dell'Allucinazione / Falso Positivo: Delta = Naive - Strict", fontsize=10.5)
    ax2.set_title("Efficacia del Chain-of-Thought:\nSmascheramento dei Difetti Nascosti", fontsize=12.5, pad=12)
    ax2.set_xlim(0.0, 1.05)
    ax2.grid(axis='x', linestyle='--', alpha=0.45)

    for bar, d in zip(h_bars, deltas):
        w = bar.get_width()
        ax2.annotate(
            f"+{d:.2f}",
            xy=(w + 0.02, bar.get_y() + bar.get_height() / 2),
            va='center', ha='left', fontsize=8.5, fontweight='bold', color='#047857'
        )

    plt.suptitle("Validazione di Robustezza: LLM-as-a-Judge Standard vs Strict CoT Audit", fontsize=14.5, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    out_file = OUTPUT_DIR / "llm_judge_distraction_and_camouflage_study.png"
    plt.savefig(out_file)
    plt.close()
    print(f"[OK] Grafico di robustezza LLM Judge salvato: {out_file.name}")


def main():
    print("=" * 80)
    print("GENERAZIONE GRAFICI SCIENTIFICI DEGLI STRESS TEST DEI LIMITI DELLE METRICHE")
    print(f"Destinazione: {OUTPUT_DIR}")
    print("=" * 80)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    generate_stress_test_main_plot(data)
    generate_llm_judge_robustness_plot(data)

    print("=" * 80)
    print("Grafici di stress test a 300 DPI generati con successo!")
    print("=" * 80)


if __name__ == "__main__":
    main()
