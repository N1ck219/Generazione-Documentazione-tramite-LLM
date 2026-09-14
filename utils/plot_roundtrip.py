"""
Generatore della Dashboard Grafica per Round-Trip Differential Testing.
Produce un grafico a barre dettagliato per funzione e un istogramma riassuntivo.
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_roundtrip_charts(results_list, output_image_path, avg_pass_rate):
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    # Prepariamo i dati
    funcs = [r["name"] for r in results_list]
    rates = [r["pass_rate"] for r in results_list]
    passed_tests = [r["passed"] for r in results_list]
    total_tests = [r["total"] for r in results_list]

    n = len(funcs)
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.8, 1.0], width_ratios=[1.3, 1.0])

    ax1 = fig.add_subplot(gs[0, :]) # In alto: Bar chart per tutte le 57 funzioni
    ax2 = fig.add_subplot(gs[1, 0]) # In basso a sinistra: Distribuzione classi di successo
    ax3 = fig.add_subplot(gs[1, 1]) # In basso a destra: Sintesi Globale

    # 1. Bar Chart delle 57 Funzioni
    x = np.arange(n)
    colors = ['#10b981' if r >= 80 else ('#3b82f6' if r >= 50 else ('#f59e0b' if r > 0 else '#ef4444')) for r in rates]
    bars1 = ax1.bar(x, rates, color=colors, edgecolor='#1f2937', linewidth=0.8, width=0.7)
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(funcs, rotation=80, ha='right', fontsize=8, fontweight='bold')
    ax1.set_ylim(0, 115)
    ax1.set_ylabel("Pass Rate % (Pytest Assertions)", fontsize=11, fontweight='bold')
    lib_name = "OpenCV" if "opencv" in output_image_path.lower() else "cJSON"
    ax1.set_title(f"Round-Trip Behavioral Differential Testing: Pass Rate per Funzione ({lib_name})", fontsize=14, fontweight='bold')
    ax1.axhline(avg_pass_rate, color='#dc2626', linestyle='--', linewidth=1.5, label=f'Media Globale: {avg_pass_rate}%')
    ax1.grid(axis='y', linestyle=':', alpha=0.7)
    ax1.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize=10)

    # 2. Distribuzione delle Fasce di Successo
    high = sum(1 for r in rates if r >= 80)
    medium = sum(1 for r in rates if 40 <= r < 80)
    low = sum(1 for r in rates if 0 < r < 40)
    zero = sum(1 for r in rates if r == 0)

    tier_labels = [
        'Piena Equivalenza\n[80% - 100%]',
        'Buona Equivalenza\n[40% - 79%]',
        'Sintassi/Edge-case Parziale\n[1% - 39%]',
        'Discrepanza Contrattuale\n[0%]'
    ]
    tier_counts = [high, medium, low, zero]
    tier_colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']

    bars2 = ax2.bar(tier_labels, tier_counts, color=tier_colors, edgecolor='#1f2937', width=0.55)
    ax2.set_ylabel("Numero di Funzioni", fontsize=11, fontweight='bold')
    ax2.set_title("Distribuzione Funzionale per Fasce di Pass Rate", fontsize=12, fontweight='bold')
    ax2.grid(axis='y', linestyle=':', alpha=0.7)
    ax2.set_ylim(0, max(tier_counts) + 5)

    for bar, val in zip(bars2, tier_counts):
        pct = round((val / n) * 100, 1)
        ax2.text(bar.get_x() + bar.get_width()/2, val + 0.8, f"{val} ({pct}%)", ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 3. Metriche di Sintesi
    tot_passed = sum(passed_tests)
    tot_all = sum(total_tests)
    global_test_pct = round((tot_passed / tot_all) * 100, 1) if tot_all > 0 else 0.0

    summary_labels = ['Pass Rate Medio\n(per Funzione)', 'Test Unitari Totali\nSuperati (Global %)', 'Funzioni Eseguite\ncon Successo (>0%)']
    summary_vals = [avg_pass_rate, global_test_pct, round(((n - zero) / n) * 100, 1)]
    summary_colors = ['#8b5cf6', '#06b6d4', '#10b981']

    bars3 = ax3.bar(summary_labels, summary_vals, color=summary_colors, edgecolor='#1f2937', width=0.45)
    ax3.set_ylim(0, 110)
    ax3.set_ylabel("Percentuale %", fontsize=11, fontweight='bold')
    ax3.set_title("Metriche di Sintesi Round-Trip", fontsize=12, fontweight='bold')
    ax3.grid(axis='y', linestyle=':', alpha=0.7)

    for bar, val in zip(bars3, summary_vals):
        ax3.text(bar.get_x() + bar.get_width()/2, val + 2.0, f"{val}%", ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_image_path, dpi=200)
    plt.close()
    print(f"-> Grafico salvato con successo in: {output_image_path}")

if __name__ == "__main__":
    # Dati esatti estratti dall'esecuzione del benchmark su 57 funzioni di cJSON
    results_raw = [
        {"name": "cJSON_AddItemReferenceToArray", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_AddItemToArray", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_AddItemToObjectCS", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_AddNullToObject", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Compare", "pass_rate": 80.0, "passed": 4, "total": 5},
        {"name": "cJSON_CreateIntArray", "pass_rate": 80.0, "passed": 4, "total": 5},
        {"name": "cJSON_CreateNull", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_CreateObjectReference", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_CreateRaw", "pass_rate": 100.0, "passed": 5, "total": 5},
        {"name": "cJSON_CreateStringReference", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Delete", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_DetachItemViaPointer", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_Duplicate", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetArrayItem", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetArraySize", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetErrorPtr", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_GetObjectItem", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetStringValue", "pass_rate": 11.1, "passed": 1, "total": 9},
        {"name": "cJSON_InitHooks", "pass_rate": 0.0, "passed": 0, "total": 1},
        {"name": "cJSON_InsertItemInArray", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_IsInvalid", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Minify", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Parse", "pass_rate": 60.0, "passed": 3, "total": 5},
        {"name": "cJSON_ParseWithOpts", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Print", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_PrintBuffered", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_PrintPreallocated", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_PrintUnformatted", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_SetNumberHelper", "pass_rate": 100.0, "passed": 5, "total": 5},
        {"name": "cJSON_SetValuestring", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Version", "pass_rate": 100.0, "passed": 5, "total": 5},
        {"name": "cJSON_malloc", "pass_rate": 80.0, "passed": 4, "total": 5},
        {"name": "cJSON_AddItemReferenceToArray_2", "pass_rate": 0.0, "passed": 0, "total": 1},
        {"name": "cJSON_AddItemToArray_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_AddItemToObjectCS_2", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_AddNullToObject_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Compare_2", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_CreateIntArray_2", "pass_rate": 100.0, "passed": 5, "total": 5},
        {"name": "cJSON_CreateNull_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_CreateObjectReference_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_CreateRaw_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_CreateStringReference_2", "pass_rate": 0.0, "passed": 0, "total": 0},
        {"name": "cJSON_Delete_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_DetachItemViaPointer_2", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_Duplicate_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetArrayItem_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetArraySize_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetErrorPtr_2", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_GetObjectItem_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_GetStringValue_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_InitHooks_2", "pass_rate": 0.0, "passed": 0, "total": 0},
        {"name": "cJSON_InsertItemInArray_2", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_IsInvalid_2", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_Minify_2", "pass_rate": 20.0, "passed": 1, "total": 5},
        {"name": "cJSON_Parse_2", "pass_rate": 60.0, "passed": 3, "total": 5},
        {"name": "cJSON_ParseWithOpts_2", "pass_rate": 0.0, "passed": 0, "total": 5},
        {"name": "cJSON_Print_2", "pass_rate": 20.0, "passed": 1, "total": 5}
    ]

    out_png = os.path.join(ROOT_DIR, "results", "benchmark_cjson", "roundtrip_charts.png")
    generate_roundtrip_charts(results_raw, out_png, avg_pass_rate=24.1)
