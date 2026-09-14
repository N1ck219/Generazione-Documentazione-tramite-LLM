import os
import json
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any

def generate_code_size_distribution_charts(stats_data: List[Dict[str, Any]], output_dir: str):
    """
    Genera grafici e istogrammi analitici per mostrare la distribuzione della dimensione
    del codice e dei prompt inoltrati all'LLM (in Righe di Codice, Caratteri e Token Stimati).
    """
    if not stats_data:
        return

    os.makedirs(output_dir, exist_ok=True)

    # Estrazione metriche
    lines_of_code = [d["loc"] for d in stats_data]
    prompt_tokens = [d["prompt_tokens_est"] for d in stats_data]

    # Stile moderno e pulito
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    # -------------------------------------------------------------
    # 1. Istogramma Distribuzione Righe di Codice (LOC)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    min_loc = min(lines_of_code)
    max_loc = max(lines_of_code)
    avg_loc = sum(lines_of_code) / len(lines_of_code)

    # Calcolo bin dinamico e leggibile
    if max_loc - min_loc <= 20:
        bins = np.arange(min_loc, max_loc + 2) - 0.5
        ticks = np.arange(min_loc, max_loc + 1)
    else:
        num_bins = min(15, max(5, int(np.sqrt(len(lines_of_code)))))
        bins = np.linspace(min_loc, max_loc, num_bins + 1)
        ticks = np.round(bins).astype(int)

    n, bins_edges, patches = ax.hist(
        lines_of_code,
        bins=bins,
        color='#0284c7',
        edgecolor='#082f49',
        linewidth=1.2,
        rwidth=0.85
    )

    # Linea della media
    ax.axvline(avg_loc, color='#ef4444', linestyle='--', linewidth=2, label=f'Media: {avg_loc:.1f} LOC')

    ax.set_title('Distribuzione della Dimensione delle Funzioni (Righe di Codice)', fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel('Righe di Codice Sorgente (LOC)', fontsize=11, labelpad=8)
    ax.set_ylabel('Numero di Funzioni', fontsize=11, labelpad=8)
    ax.set_xticks(ticks)
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)

    # Valori sopra le barre
    for patch in patches:
        height = patch.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}',
                        xy=(patch.get_x() + patch.get_width() / 2, height),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontweight='bold', fontsize=9, color='#0f172a')

    plt.tight_layout()
    loc_hist_path = os.path.join(output_dir, "loc_distribution.png")
    plt.savefig(loc_hist_path, dpi=200)
    plt.close()

    # -------------------------------------------------------------
    # 2. Distribuzione Aggregata dei Token del Prompt LLM
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    min_tok = min(prompt_tokens)
    max_tok = max(prompt_tokens)
    avg_tok = sum(prompt_tokens) / len(prompt_tokens)

    num_bins_tok = min(12, max(6, int(np.sqrt(len(prompt_tokens)))))
    tok_bins = np.linspace(min_tok, max_tok, num_bins_tok + 1)

    n_tok, bins_tok_edges, tok_patches = ax.hist(
        prompt_tokens,
        bins=tok_bins,
        color='#38bdf8',
        edgecolor='#0369a1',
        linewidth=1.2,
        rwidth=0.85
    )

    # Linea della media
    ax.axvline(avg_tok, color='#dc2626', linestyle='--', linewidth=2, label=f'Media: {avg_tok:.0f} Token')

    ax.set_title('Distribuzione Generale dei Token per Prompt LLM (Footprint Stimato)', fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel('Fascia di Token Stimati nel Prompt', fontsize=11, labelpad=8)
    ax.set_ylabel('Numero di Funzioni nella Fascia', fontsize=11, labelpad=8)
    ax.set_xticks(np.round(tok_bins).astype(int))
    ax.tick_params(axis='x', rotation=30)
    ax.grid(axis='y', linestyle=':', alpha=0.7)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)

    for patch in tok_patches:
        height = patch.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}',
                        xy=(patch.get_x() + patch.get_width() / 2, height),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontweight='bold', fontsize=9, color='#0f172a')

    plt.tight_layout()
    tokens_chart_path = os.path.join(output_dir, "prompt_tokens_per_function.png")
    plt.savefig(tokens_chart_path, dpi=200)
    plt.close()

    # Salva anche il file JSON statistico riassuntivo
    summary_json_path = os.path.join(output_dir, "code_size_metrics.json")
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_functions": len(stats_data),
            "loc_metrics": {
                "min": min(lines_of_code),
                "max": max(lines_of_code),
                "avg": round(sum(lines_of_code) / len(lines_of_code), 2) if lines_of_code else 0
            },
            "token_metrics": {
                "min": min(prompt_tokens),
                "max": max(prompt_tokens),
                "avg": round(sum(prompt_tokens) / len(prompt_tokens), 2) if prompt_tokens else 0
            },
            "detailed_functions": stats_data
        }, f, indent=2)

    print(f"-> Grafici di distribuzione della dimensione del codice generati in: {output_dir}")
