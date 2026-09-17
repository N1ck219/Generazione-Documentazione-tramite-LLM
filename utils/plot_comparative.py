"""
Script per la generazione di un grafico comparativo avanzato tra Modalità Ibrida Standard e Modalità Multi-Agente (Reader->Searcher->Writer->Verifier->Judge).
"""

import os
import json
import matplotlib.pyplot as plt
import numpy as np

ROOT_DIR = r"d:\python\TESI_Nicola_Flego"
SINGLE_EVAL_JSON = os.path.join(ROOT_DIR, "results", "benchmark_all", "eval_report_single.json")
MULTI_EVAL_JSON = os.path.join(ROOT_DIR, "results", "benchmark_all", "eval_report_multiagent.json")
SINGLE_RT_JSON = os.path.join(ROOT_DIR, "results", "benchmark_all", "roundtrip_results_single.json")
MULTI_RT_JSON = os.path.join(ROOT_DIR, "results", "benchmark_all", "roundtrip_results_multiagent.json")

OUTPUT_CHART_PATH = os.path.join(ROOT_DIR, "results", "benchmark_all", "comparative_hybrid_vs_multiagent.png")

def main():
    with open(SINGLE_EVAL_JSON, "r", encoding="utf-8") as f:
        single_eval = json.load(f)
    with open(MULTI_EVAL_JSON, "r", encoding="utf-8") as f:
        multi_eval = json.load(f)
    with open(SINGLE_RT_JSON, "r", encoding="utf-8") as f:
        single_rt = json.load(f)
    with open(MULTI_RT_JSON, "r", encoding="utf-8") as f:
        multi_rt = json.load(f)

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig = plt.figure(figsize=(20, 13))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1.0], hspace=0.3, wspace=0.25)

    # 1. Round-Trip Pass Rate per funzione (Confronto Single vs Multi-Agente)
    ax1 = fig.add_subplot(gs[0, :])
    funcs = [r["function_name"] for r in single_eval]
    n = len(funcs)
    x = np.arange(n)
    width = 0.38

    rt_single_map = {r["function_name"]: r["execution"]["pass_rate"] for r in single_rt["results"]}
    rt_multi_map = {r["function_name"]: r["execution"]["pass_rate"] for r in multi_rt["results"]}

    single_rates = [rt_single_map.get(fn, 0.0) for fn in funcs]
    multi_rates = [rt_multi_map.get(fn, 0.0) for fn in funcs]

    rects1 = ax1.bar(x - width/2, single_rates, width, label=f'Ibrido Standard (Media: {single_rt["avg_pass_rate"]}%)', color='#3b82f6', edgecolor='#1e40af', alpha=0.9)
    rects2 = ax1.bar(x + width/2, multi_rates, width, label=f'Multi-Agente + Judge (Media: {multi_rt["avg_pass_rate"]}%)', color='#10b981', edgecolor='#065f46', alpha=0.9)

    ax1.set_xticks(x)
    ax1.set_xticklabels(funcs, rotation=35, ha='right', fontsize=9, fontweight='bold')
    ax1.set_ylabel("Pass Rate % (Pytest Assertions)", fontsize=11, fontweight='bold')
    ax1.set_title("Round-Trip Differential Testing: Pass Rate Funzione per Funzione (Doc-to-Code Synthesis)", fontsize=13, fontweight='bold')
    ax1.set_ylim(0, 115)
    ax1.axhline(single_rt["avg_pass_rate"], color='#2563eb', linestyle='--', linewidth=1.2, alpha=0.7)
    ax1.axhline(multi_rt["avg_pass_rate"], color='#059669', linestyle='--', linewidth=1.2, alpha=0.7)
    ax1.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize=10)

    # 2. Macro-Metriche Globali (Bar chart affiancato)
    ax2 = fig.add_subplot(gs[1, 0])
    metrics_labels = [
        "Verifier Pass",
        "Param F1",
        "Return Match",
        "Actionability",
        "Edge Case Cov",
        "MRR Retrieval",
        "Hit@1 Retrieval",
        "Round-Trip Pass"
    ]

    # Valori normalizzati su 100%
    s_vals = [
        100.0,
        1.0 * 100,
        1.0 * 100,
        0.85 * 100,
        90.0,
        0.6232 * 100,
        45.0,
        single_rt["avg_pass_rate"]
    ]
    m_vals = [
        100.0,
        1.0 * 100,
        1.0 * 100,
        0.835 * 100,
        87.5,
        0.6449 * 100,
        50.0,
        multi_rt["avg_pass_rate"]
    ]

    y = np.arange(len(metrics_labels))
    height = 0.35

    ax2.barh(y - height/2, s_vals, height, label='Ibrido Standard', color='#60a5fa', edgecolor='#1d4ed8')
    ax2.barh(y + height/2, m_vals, height, label='Multi-Agente + Judge', color='#34d399', edgecolor='#047857')

    for i, (sv, mv) in enumerate(zip(s_vals, m_vals)):
        ax2.text(sv + 1, i - height/2, f"{sv:.1f}%", va='center', fontsize=8, fontweight='bold', color='#1e3a8a')
        ax2.text(mv + 1, i + height/2, f"{mv:.1f}%", va='center', fontsize=8, fontweight='bold', color='#064e3b')

    ax2.set_yticks(y)
    ax2.set_yticklabels(metrics_labels, fontsize=10, fontweight='bold')
    ax2.set_xlim(0, 120)
    ax2.invert_yaxis()
    ax2.set_xlabel("Punteggio / Percentuale (%)", fontsize=11, fontweight='bold')
    ax2.set_title("Confronto Macro-Metriche Chiave (AST, Retrieval & Esecuzione)", fontsize=12, fontweight='bold')
    ax2.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.9, fontsize=9)

    # 3. Radar / Polar Chart Semantico & Neurale
    ax3 = fig.add_subplot(gs[1, 1], polar=True)
    categories = [
        "SBERT Sim",
        "BERTScore F1",
        "CodeBERT F1",
        "METEOR",
        "BLEURT",
        "Checklist",
        "Judge Combined"
    ]
    # Punteggi scalati da 0 a 1
    s_radar = [
        0.6755,
        0.6433,
        0.6755,
        0.4723,
        0.6023,
        0.625,
        4.635 / 5.0
    ]
    m_radar = [
        0.6438,
        0.5958,
        0.6438,
        0.4248,
        0.5651,
        0.550,
        4.365 / 5.0
    ]

    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    s_radar_plot = s_radar + [s_radar[0]]
    m_radar_plot = m_radar + [m_radar[0]]
    angles_plot = angles + [angles[0]]

    ax3.plot(angles_plot, s_radar_plot, color='#2563eb', linewidth=2, label='Ibrido Standard')
    ax3.fill(angles_plot, s_radar_plot, color='#3b82f6', alpha=0.25)

    ax3.plot(angles_plot, m_radar_plot, color='#059669', linewidth=2, label='Multi-Agente + Judge')
    ax3.fill(angles_plot, m_radar_plot, color='#10b981', alpha=0.25)

    ax3.set_xticks(angles)
    ax3.set_xticklabels(categories, fontsize=9, fontweight='bold')
    ax3.set_ylim(0, 1.0)
    ax3.set_title("Profilo Neurale & LLM-Judge (Aderenza Lessicale/Semantica)", fontsize=12, fontweight='bold', pad=20)
    ax3.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), frameon=True, facecolor='white', fontsize=9)

    plt.suptitle("BENCHMARK COMPARATIVO: MODALITÀ IBRIDA STANDARD vs MODALITÀ MULTI-AGENTE\n(Campione di 20 funzioni casuali - All Libraries: C & C++)", fontsize=16, fontweight='bold', y=0.98)
    
    os.makedirs(os.path.dirname(OUTPUT_CHART_PATH), exist_ok=True)
    plt.savefig(OUTPUT_CHART_PATH, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Grafico comparativo salvato in: {OUTPUT_CHART_PATH}")

if __name__ == "__main__":
    main()
