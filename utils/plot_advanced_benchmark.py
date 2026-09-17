"""
Suite Completa di Grafici Avanzati per il Benchmark di Documentazione LLM.
Genera artefatti visivi scientifici per ogni esecuzione:
1. Radar / Spider Chart delle 6 Dimensioni di Qualita'.
2. Scatter Plot di Correlazione Semantica vs Round-Trip Pass Rate (con regressione lineare).
3. Box & Violin Plot della Distribuzione delle Metriche Chiave.
4. Heatmap Funzione x Metriche (Matrice di Confidenza).
5. Breakdown Verifier & Error Categorization.
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')


def generate_radar_chart(eval_results: List[Dict[str, Any]], output_path: str, mode_name: str = "Pipeline", library_name: str = "Benchmark"):
    """
    1. RADAR / SPIDER CHART MULTI-DIMENSIONALE
    Raggruppa le metriche nei 6 pilastri fondamentali:
    - Aderenza AST (Param F1, Return Match)
    - Semantica Neurale (SBERT, BERTScore, CodeBERT)
    - Qualita' Software (Actionability Score)
    - Copertura Errori & Edge Case (EDR, ECC)
    - Affidabilita' Formale (1.0 - Hallucination Rate)
    - Downstream Utility (Code Retrieval MRR e/o Round-Trip Pass Rate)
    """
    if not eval_results:
        return

    # Calcolo valori medi normalizzati [0.0 - 1.0]
    param_f1 = np.mean([r["metrics"]["param_f1"] for r in eval_results])
    ret_match = np.mean([r["metrics"]["return_match"] for r in eval_results])
    ast_adherence = (param_f1 + ret_match) / 2.0

    sbert = np.mean([r["metrics"]["sbert_similarity"] for r in eval_results])
    bert_f1 = np.mean([r["metrics"]["bert_score_f1"] for r in eval_results])
    codebert_f1 = np.mean([r["metrics"]["codebert_score_f1"] for r in eval_results])
    neural_semantics = (sbert + bert_f1 + (codebert_f1 if codebert_f1 > 0 else sbert)) / 3.0

    actionability = np.mean([r["metrics"].get("actionability_score", 0.0) for r in eval_results])

    edr = np.mean([r["metrics"].get("error_documentation_score", 0.0) for r in eval_results])
    ecc = np.mean([r["metrics"].get("edge_case_coverage", 0.0) for r in eval_results])
    edge_cases = (edr + ecc) / 2.0

    hallucination_rate = np.mean([r["metrics"].get("hallucination_rate", 0.0) for r in eval_results]) / 100.0
    formal_reliability = max(0.0, 1.0 - hallucination_rate)

    retrieval_rr = np.mean([r["metrics"].get("retrieval_rr", 1.0) for r in eval_results])
    has_rt = any("roundtrip" in r for r in eval_results)
    if has_rt:
        rt_pass = np.mean([r["roundtrip"]["execution"]["pass_rate"] for r in eval_results if "roundtrip" in r]) / 100.0
        downstream_utility = (retrieval_rr + rt_pass) / 2.0
    else:
        downstream_utility = retrieval_rr

    categories = [
        'Aderenza Contratti AST\n(Param F1 + Return)',
        'Semantica Neurale\n(SBERT + BERT + CodeBERT)',
        'Actionability\n(Comandi, Enum & Tipi)',
        'Copertura Eccezioni\n(EDR + Edge Cases)',
        'Affidabilita\' Formale\n(Anti-Allucinazione)',
        'Downstream Utility\n(Retrieval + RoundTrip)'
    ]
    values = [ast_adherence, neural_semantics, actionability, edge_cases, formal_reliability, downstream_utility]

    # Chiusura del poligono
    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Allontana le etichette per evitare qualsiasi sovrapposizione con i vertici del radar
    ax.tick_params(pad=35)
    plt.xticks(angles[:-1], categories, size=10, fontweight='bold', color='#0f172a')
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=8.5)
    plt.ylim(0, 1.18)

    color = '#4f46e5' if mode_name.lower() == 'multiagent' else '#0284c7'
    ax.plot(angles, values, color=color, linewidth=2.8, linestyle='solid', label=f"{mode_name} ({library_name})")
    ax.fill(angles, values, color=color, alpha=0.25)

    # Disegna i punti sui vertici con etichetta posizionata con cura
    for angle, val in zip(angles[:-1], values[:-1]):
        ax.plot(angle, val, 'o', color=color, markersize=8, markeredgecolor='white', markeredgewidth=1.5)
        # Posiziona il testo del valore leggermente offset
        offset_r = val + 0.07 if val < 1.0 else val + 0.05
        ax.text(angle, offset_r, f"{val:.2f}", horizontalalignment='center', size=9, fontweight='bold', color='#1e293b')

    plt.title(f"Profilo di Qualita' Multi-Dimensionale ({mode_name.upper()} - {library_name})\n", size=14, fontweight='bold', y=1.12)
    plt.legend(loc='upper right', bbox_to_anchor=(1.22, 1.15), frameon=True, facecolor='white', framealpha=0.95)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"-> Radar Chart salvato in: {output_path}")


def generate_semantic_vs_roundtrip_scatter(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    2. SCATTER PLOT DI CORRELAZIONE: SEMANTICA vs COMPORTAMENTO REALE (ROUND-TRIP)
    Mette in relazione la similarità semantica (SBERT) con il reale Pass Rate Pytest.
    Risolve le sovrapposizioni delle etichette con posizionamento dinamico ad offset alternati.
    """
    valid_points = [r for r in eval_results if "roundtrip" in r]
    if not valid_points:
        return

    x_sbert = [r["metrics"]["sbert_similarity"] for r in valid_points]
    y_rt = [r["roundtrip"]["execution"]["pass_rate"] for r in valid_points]
    names = [r["function_name"] for r in valid_points]

    has_judge = "judge_score_a" in valid_points[0]["metrics"]
    if has_judge:
        judge_scores = [r["metrics"]["judge_score_a"] for r in valid_points]
        c_vals = judge_scores
        c_label = "LLM-Judge Faithfulness [1-5]"
    else:
        c_vals = [r["metrics"]["param_f1"] for r in valid_points]
        c_label = "Param F1 (AST)"

    fig, ax = plt.subplots(figsize=(11, 7.5))

    scatter = ax.scatter(x_sbert, y_rt, c=c_vals, cmap='cividis', s=180, alpha=0.9, edgecolors='#0f172a', linewidth=1.5, zorder=4)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label(c_label, fontsize=10.5, fontweight='bold')

    # Linea di regressione lineare (trend)
    if len(x_sbert) >= 2:
        z = np.polyfit(x_sbert, y_rt, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(x_sbert), max(x_sbert), 50)
        ax.plot(x_line, p(x_line), "r--", alpha=0.85, linewidth=2.2, label=f"Trend Line (Slope: {z[0]:.1f})", zorder=3)
        corr = np.corrcoef(x_sbert, y_rt)[0, 1] if np.std(x_sbert) > 0 and np.std(y_rt) > 0 else 0.0
        ax.text(0.04, 0.92, f"Correlazione Pearson r = {corr:.2f}", transform=ax.transAxes,
                fontsize=11, fontweight='bold', bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.92, edgecolor='#cbd5e1'))

    # Ordinamento e posizionamento intelligente delle etichette per evitare sovrapposizioni
    # Definiamo una serie di offset geometrici sfalsati (sopra, sotto, destra, sinistra)
    label_offsets = [
        (0, 12, 'center', 'bottom'),
        (0, -16, 'center', 'top'),
        (14, 8, 'left', 'bottom'),
        (-14, 8, 'right', 'bottom'),
        (14, -12, 'left', 'top'),
        (-14, -12, 'right', 'top'),
    ]

    # Raggruppa i punti che hanno coordinate molto vicine per sfalsarli
    point_indices = sorted(range(len(valid_points)), key=lambda i: (y_rt[i], x_sbert[i]))
    occupied_positions = []
    for rank, idx in enumerate(point_indices):
        x = x_sbert[idx]
        y = y_rt[idx]
        name = names[idx]

        # Scegli l'offset migliore
        offset_idx = rank % len(label_offsets)
        ox, oy, ha, va = label_offsets[offset_idx]

        # Se il punto è vicino a 100%, forza l'offset verso il basso
        if y >= 95:
            oy = -15 - (10 * (rank % 3))
            va = 'top'
            ha = 'center'
        # Se il punto è vicino a 0%, forza l'offset verso l'alto
        elif y <= 5:
            oy = 15 + (10 * (rank % 3))
            va = 'bottom'
            ha = 'center'

        ax.annotate(
            name,
            (x, y),
            textcoords="offset points",
            xytext=(ox, oy),
            ha=ha,
            va=va,
            fontsize=8.5,
            fontweight='bold',
            color='#1e293b',
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.75, edgecolor="none"),
            arrowprops=dict(arrowstyle="-", color="#94a3b8", lw=0.8, alpha=0.7)
        )

    ax.set_xlabel("Sentence-BERT Cosine Similarity (Aderenza Semantica a Ground Truth)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Round-Trip Pytest Pass Rate % (Auto-Consistenza Comportamentale)", fontsize=11, fontweight='bold')
    ax.set_title(f"Correlazione: Plausibilita' Semantica vs Correttezza Funzionale Reale ({library_name})", fontsize=13, fontweight='bold')
    ax.set_ylim(-10, 115)
    ax.set_xlim(min(0.0, min(x_sbert) - 0.08), max(1.0, max(x_sbert) + 0.08))
    ax.grid(True, linestyle=':', alpha=0.6)
    if len(x_sbert) >= 2:
        ax.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.9)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"-> Scatter Plot Semantica vs Round-Trip salvato in: {output_path}")


def generate_metrics_distribution_plot(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    3. BOX & VIOLIN PLOT DELLE DISTRIBUZIONI
    Mostra la dispersione statistica con legenda esplicita:
    - Linea rossa orizzontale = Mediana del campione
    - Pallini scuri = Singoli punti/funzioni (con jitter per mostrare densita')
    - Corpo violino viola/blu = Distribuzione di probabilita' (KDE)
    """
    if not eval_results:
        return

    data = []
    labels = []

    labels.append("Param F1")
    data.append([r["metrics"]["param_f1"] for r in eval_results])

    labels.append("Return Match")
    data.append([r["metrics"]["return_match"] for r in eval_results])

    labels.append("SBERT Sim")
    data.append([r["metrics"]["sbert_similarity"] for r in eval_results])

    labels.append("BERTScore")
    data.append([r["metrics"]["bert_score_f1"] for r in eval_results])

    labels.append("METEOR")
    data.append([r["metrics"].get("meteor_score", 0.0) for r in eval_results])

    labels.append("Actionability")
    data.append([r["metrics"].get("actionability_score", 0.0) for r in eval_results])

    if "judge_score_a" in eval_results[0]["metrics"]:
        labels.append("Judge (Norm)")
        data.append([r["metrics"]["judge_score_a"] / 5.0 for r in eval_results])

    if any("roundtrip" in r for r in eval_results):
        labels.append("RoundTrip (Norm)")
        data.append([r["roundtrip"]["execution"]["pass_rate"] / 100.0 for r in eval_results if "roundtrip" in r])

    fig, ax = plt.subplots(figsize=(12, 7))

    parts = ax.violinplot(data, showmeans=False, showmedians=True, showextrema=True)
    for pc in parts['bodies']:
        pc.set_facecolor('#6366f1')
        pc.set_edgecolor('#3730a3')
        pc.set_alpha(0.55)
    parts['cmedians'].set_color('#dc2626')
    parts['cmedians'].set_linewidth(2.8)

    # Sovrapponi i punti individuali con jitter casuale
    scatter_handle = None
    for i, col_data in enumerate(data, start=1):
        jitter = np.random.normal(0, 0.04, size=len(col_data))
        scatter_handle = ax.scatter(i + jitter, col_data, alpha=0.75, s=36, color='#1e293b', edgecolors='#f8fafc', linewidth=0.8, zorder=5)

    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, fontsize=10, fontweight='bold', rotation=20, ha='right')
    ax.set_ylabel("Punteggio Normalizzato [0.0 - 1.0]", fontsize=10.5, fontweight='bold')
    ax.set_title(f"Distribuzione Statistica e Varianza delle Metriche ({library_name})", fontsize=13, fontweight='bold')
    ax.set_ylim(-0.05, 1.15)
    ax.grid(axis='y', linestyle=':', alpha=0.7)

    # Legenda esplicita che spiega cosa sono la linea rossa, i pallini e l'area violino
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend_elements = [
        Line2D([0], [0], color='#dc2626', lw=2.8, label='Linea Rossa: Mediana della metrica'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#1e293b', markeredgecolor='#f8fafc', markersize=8, label='Pallini Scuri: Singole funzioni valutate (con jitter)'),
        Patch(facecolor='#6366f1', edgecolor='#3730a3', alpha=0.55, label='Area Violino: Densità di probabilità (KDE)')
    ]
    ax.legend(handles=legend_elements, loc='lower left', frameon=True, facecolor='white', framealpha=0.95, fontsize=9.5)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"-> Violin/Distribution Plot salvato in: {output_path}")


def generate_function_confidence_heatmap(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    4. HEATMAP: MATRICE DI CONFIDENZA FUNZIONE x METRICHE
    Aggiornato con:
    - Nuova palette moderna ad alto contrasto (YlGnBu / viridis per chiarezza e accessibilità).
    - Valori perfettamente centrati dentro ogni cella.
    - Griglia bianca marcata per separare i riquadri senza toccare i numeri.
    """
    if not eval_results:
        return

    funcs = [r["function_name"] for r in eval_results]
    col_names = ["Verifier", "Param F1", "Return Match", "SBERT", "METEOR", "Actionability"]
    has_judge = "judge_score_a" in eval_results[0]["metrics"]
    if has_judge:
        col_names.append("Judge")
    has_rt = any("roundtrip" in r for r in eval_results)
    if has_rt:
        col_names.append("RoundTrip")

    matrix = []
    for r in eval_results:
        row = [
            1.0 if r["is_valid"] else 0.0,
            r["metrics"]["param_f1"],
            r["metrics"]["return_match"],
            r["metrics"]["sbert_similarity"],
            r["metrics"].get("meteor_score", 0.0),
            r["metrics"].get("actionability_score", 0.0)
        ]
        if has_judge:
            row.append(r["metrics"].get("judge_score_a", 0.0) / 5.0)
        if has_rt:
            rt_val = r["roundtrip"]["execution"]["pass_rate"] / 100.0 if "roundtrip" in r else 0.0
            row.append(rt_val)
        matrix.append(row)

    matrix = np.array(matrix)

    n_rows = len(funcs)
    n_cols = len(col_names)
    fig_height = max(6.0, n_rows * 0.75)
    fig, ax = plt.subplots(figsize=(11, fig_height))

    # Usiamo la palette moderna ad alto contrasto 'YlGnBu'
    im = ax.imshow(matrix, cmap='YlGnBu', vmin=0.0, vmax=1.0, aspect='auto')

    # Configurazione precisa dei tick e dei confini di cella
    ax.set_xticks(np.arange(n_cols))
    ax.set_yticks(np.arange(n_rows))
    ax.set_xticklabels(col_names, fontsize=10, fontweight='bold')
    ax.set_yticklabels(funcs, fontsize=9.5, fontweight='bold')

    # Sposta i label delle colonne in alto per consultazione standard
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="left", rotation_mode="anchor")

    # Griglia marcata: disattiviamo la griglia classica e disegniamo linee bianche tra i riquadri
    ax.grid(False)
    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="white", linestyle='-', linewidth=2.5)
    ax.tick_params(which="minor", bottom=False, left=False, top=False)

    # Scrittura dei valori perfettamente al centro di ciascun riquadro
    for i in range(n_rows):
        for j in range(n_cols):
            val = matrix[i, j]
            # Contrasto dinamico del testo: scuro su sfondo chiaro, bianco su sfondo scuro
            text_color = "white" if val >= 0.65 else "#0f172a"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=text_color, fontsize=10, fontweight='bold')

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Indice di Qualità Normalizzato [0.0 - 1.0]", rotation=-90, va="bottom", fontsize=10, fontweight='bold')

    ax.set_title(f"Matrice di Confidenza Funzione x Metriche ({library_name})\n", fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"-> Heatmap di Confidenza salvata in: {output_path}")


def generate_verifier_errors_breakdown(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    5. BREAKDOWN ERRORI E CAUSE DI SCARTO VERIFIER & JUDGE
    Analizza i motivi per cui una funzione e' stata segnalata dal Verifier o dal Giudice.
    """
    if not eval_results:
        return

    categories = {
        "Parametri Mancanti/Discrepanti": 0,
        "Tipo di Ritorno Errato/Mancante": 0,
        "Simboli Non Validi o Allucinati": 0,
        "Rigetto Giudice (Score < 4)": 0,
        "Superato al 1° Tentativo": 0
    }

    for r in eval_results:
        errors = r.get("verifier_errors", [])
        if not errors:
            categories["Superato al 1° Tentativo"] += 1
            continue

        err_str = " ".join(errors).lower()
        if "param" in err_str or "mancante" in err_str or "parametro" in err_str:
            categories["Parametri Mancanti/Discrepanti"] += 1
        if "return" in err_str or "ritorno" in err_str or "void" in err_str:
            categories["Tipo di Ritorno Errato/Mancante"] += 1
        if "judge" in err_str or "critic" in err_str:
            categories["Rigetto Giudice (Score < 4)"] += 1
        if "simbolo" in err_str or "allucin" in err_str or "symbol" in err_str:
            categories["Simboli Non Validi o Allucinati"] += 1

    labels = [k for k, v in categories.items() if v > 0 or k == "Superato al 1° Tentativo"]
    counts = [categories[k] for k in labels]
    colors = ['#ef4444', '#f97316', '#eab308', '#8b5cf6', '#10b981']

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.barh(labels, counts, color=colors[:len(labels)], edgecolor='#1e293b', height=0.55)

    for bar, val in zip(bars, counts):
        pct = round(val / len(eval_results) * 100, 1)
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height()/2, f"{val} ({pct}%)", va='center', fontsize=9, fontweight='bold')

    ax.set_xlabel("Numero di Funzioni Coinvolte", fontsize=10, fontweight='bold')
    ax.set_title(f"Breakdown Esiti del Verifier & Rigetti del Giudice ({library_name})", fontsize=12, fontweight='bold')
    ax.set_xlim(0, max(counts) + max(2, int(max(counts)*0.25)))
    ax.grid(axis='x', linestyle=':', alpha=0.7)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"-> Verifier Breakdown salvato in: {output_path}")


def generate_correlation_matrix_heatmap(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    6. CROSS-CORRELATION MATRIX HEATMAP (N x N)
    Matrice di correlazione lineare di Pearson tra le metriche del benchmark
    per identificare collinearità, ortogonalità o divergenze scientifiche.
    """
    if not eval_results or len(eval_results) < 2:
        return

    # Estrazione vettori metriche
    metric_defs = [
        ("Param F1", lambda r: r["metrics"]["param_f1"]),
        ("SBERT Sim", lambda r: r["metrics"]["sbert_similarity"]),
        ("BERTScore F1", lambda r: r["metrics"]["bert_score_f1"]),
        ("CodeBERT F1", lambda r: r["metrics"].get("codebert_score_f1", 0.0)),
        ("METEOR", lambda r: r["metrics"].get("meteor_score", 0.0)),
        ("Actionability", lambda r: r["metrics"].get("actionability_score", 0.0)),
        ("Checklist", lambda r: r["metrics"].get("concept_checklist_score", 0.0)),
    ]

    # Includi Round-Trip se presente
    has_rt = any("roundtrip" in r for r in eval_results)
    if has_rt:
        metric_defs.append(("Round-Trip %", lambda r: r.get("roundtrip", {}).get("execution", {}).get("pass_rate", 0.0) / 100.0))

    # Includi Giudice se presente
    has_judge = any("judge_score_a" in r["metrics"] for r in eval_results)
    if has_judge:
        metric_defs.append(("Judge Faith", lambda r: r["metrics"].get("judge_score_a", 0.0) / 5.0))

    labels = [m[0] for m in metric_defs]
    data_matrix = []
    for _, extractor in metric_defs:
        vals = [extractor(r) for r in eval_results]
        data_matrix.append(vals)

    data_matrix = np.array(data_matrix, dtype=float)  # shape: (n_metrics, n_samples)
    n_vars = len(labels)

    # Calcolo correlazione con gestione di colonne a varianza zero (evita warning/NaN)
    corr_matrix = np.zeros((n_vars, n_vars))
    for i in range(n_vars):
        for j in range(n_vars):
            if i == j:
                corr_matrix[i, j] = 1.0
            else:
                std_i = np.std(data_matrix[i])
                std_j = np.std(data_matrix[j])
                if std_i > 1e-9 and std_j > 1e-9:
                    c = np.corrcoef(data_matrix[i], data_matrix[j])[0, 1]
                    corr_matrix[i, j] = 0.0 if np.isnan(c) else float(c)
                else:
                    corr_matrix[i, j] = 0.0

    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr_matrix, cmap='coolwarm', vmin=-1.0, vmax=1.0, aspect='auto')

    ax.set_xticks(np.arange(n_vars))
    ax.set_yticks(np.arange(n_vars))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=10, fontweight='bold', color='#1e293b')
    ax.set_yticklabels(labels, fontsize=10, fontweight='bold', color='#1e293b')

    # Griglia marcata: disattiviamo la griglia classica e disegniamo linee bianche tra i riquadri
    ax.grid(False)
    ax.set_xticks(np.arange(-0.5, n_vars, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_vars, 1), minor=True)
    ax.grid(which="minor", color="white", linestyle='-', linewidth=2.0)
    ax.tick_params(which="minor", bottom=False, left=False, top=False)

    for i in range(n_vars):
        for j in range(n_vars):
            val = corr_matrix[i, j]
            text_color = "white" if abs(val) > 0.45 else "#0f172a"
            ax.text(j, i, f"{val:+.2f}", ha="center", va="center", color=text_color, fontsize=9, fontweight='bold')

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Coefficiente di Correlazione di Pearson ($r$)", rotation=-90, va="bottom", fontsize=10, fontweight='bold')

    ax.set_title(f"Matrice di Cross-Correlazione tra Metriche ({library_name})\n", fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"-> Cross-Correlation Matrix salvata in: {output_path}")


def generate_semantic_vs_roundtrip_residuals(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    7. DISCREPANCY / RESIDUALS PLOT: SEMANTICA vs ROUND-TRIP
    Grafico a barre divergenti del residuo Delta = SBERT - (Round-Trip / 100).
    - Delta > 0: Allucinazione Plausibile / Sovrastima Semantica (sembra ottima ma fallisce i test a valle).
    - Delta < 0: Parafrasi Robusta / Sottostima Semantica (termini diversi ma logica perfetta).
    """
    rt_results = [r for r in eval_results if "roundtrip" in r]
    if not rt_results:
        return

    funcs = []
    deltas = []
    colors = []
    annotations = []

    for r in rt_results:
        name = r.get("function_name", r.get("name", "func"))
        sbert = float(r["metrics"]["sbert_similarity"])
        rt_pass = float(r["roundtrip"]["execution"]["pass_rate"]) / 100.0
        diff = sbert - rt_pass  # Delta residuo [-1.0, +1.0]

        funcs.append(name)
        deltas.append(diff)
        if diff > 0.05:
            colors.append('#ef4444')  # Rosso: Sovrastima semantica
            annotations.append("Allucinazione Plausibile")
        elif diff < -0.05:
            colors.append('#3b82f6')  # Blu: Parafrasi robusta
            annotations.append("Parafrasi Robusta")
        else:
            colors.append('#10b981')  # Verde: Perfetta coerenza
            annotations.append("Coerente")

    fig_height = max(7.0, len(funcs) * 0.45)
    fig, ax = plt.subplots(figsize=(11.5, fig_height))
    y_pos = np.arange(len(funcs))

    bars = ax.barh(y_pos, deltas, color=colors, edgecolor='#1e293b', height=0.55)
    ax.axvline(0, color='#0f172a', linewidth=1.5, linestyle='--')

    for bar, diff in zip(bars, deltas):
        offset = 0.025 if diff >= 0 else -0.025
        ha = 'left' if diff >= 0 else 'right'
        ax.text(diff + offset, bar.get_y() + bar.get_height()/2, f"{diff:+.2f}",
                va='center', ha=ha, fontsize=8.5, fontweight='bold', color='#0f172a')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(funcs, fontsize=8.5, fontweight='bold')
    ax.set_xlabel(r"Residuo Discrepanza $\Delta = \mathrm{SBERT} - (\mathrm{RoundTrip} / 100)$", fontsize=10, fontweight='bold')
    ax.set_title(f"Analisi dei Residui: Sovrastima vs Sottostima Semantica ({library_name})", fontsize=12, fontweight='bold')

    min_d = min(deltas, default=0.0)
    max_d = max(deltas, default=0.0)
    left_limit = min(-1.05, min_d - 0.25)
    right_limit = max(1.05, max_d + 0.25)
    ax.set_xlim(left_limit, right_limit)
    ax.grid(axis='x', linestyle=':', alpha=0.7)

    # Legenda personalizzata chiara ed esplicativa
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#ef4444', edgecolor='#1e293b', label=r'Allucinazione Plausibile ($\Delta > +0.05$): Semantica Alta ma Test Falliti'),
        Patch(facecolor='#10b981', edgecolor='#1e293b', label=r'Allineato / Coerente ($|\Delta| \leq 0.05$): Semantica e Test Coerenti'),
        Patch(facecolor='#3b82f6', edgecolor='#1e293b', label=r'Parafrasi Robusta ($\Delta < -0.05$): Sintassi Diversa ma Test Superati')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0.0, -0.05), frameon=True, facecolor='white', framealpha=0.95, fontsize=9.0)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"-> Residuals Discrepancy Plot salvato in: {output_path}")


def generate_complexity_vs_performance_plot(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    8. PARETO COMPLEXITY vs PERFORMANCE PLOT (SCALA LOGARITMICA SU LOC)
    Mette in relazione la complessità strutturale del codice C/C++ (LOC in scala logaritmica)
    con la performance finale (Round-Trip Pass Rate o Giudice/SBERT).
    L'uso della scala logaritmica consente di visualizzare in modo armonico e senza schiacciamenti
    l'intero spettro di complessità, dalle funzioni di 1 LOC fino ai parser di oltre 1500 LOC.
    """
    if not eval_results:
        return

    locs = []
    scores = []
    names = []
    is_rt = any("roundtrip" in r for r in eval_results)

    for r in eval_results:
        # Calcolo LOC del codice sorgente (minimo 1)
        code = r.get("source_code", "")
        loc = max(1, len(code.splitlines()) if code else 1)
        locs.append(loc)
        names.append(r.get("function_name", r.get("name", "func")))

        if is_rt and "roundtrip" in r:
            score = float(r["roundtrip"]["execution"]["pass_rate"])
        else:
            score = float(r["metrics"]["sbert_similarity"]) * 100.0
        scores.append(score)

    y_label = "Round-Trip Pass Rate %" if is_rt else "SBERT Similarity Score (%)"

    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    scatter = ax.scatter(locs, scores, c=scores, cmap='viridis', s=130, edgecolors='#1e293b', linewidths=1.5, zorder=3)

    # Impostazione scala logaritmica sull'asse delle ascisse (LOC)
    ax.set_xscale('log')

    # Linea di tendenza logaritmica (scores vs log(locs))
    if len(locs) >= 3 and np.std(locs) > 1e-4:
        log_x = np.log10(locs)
        z = np.polyfit(log_x, scores, 1)
        p = np.poly1d(z)
        x_trend = np.logspace(np.log10(min(locs)), np.log10(max(locs)), 100)
        y_trend = p(np.log10(x_trend))
        ax.plot(x_trend, y_trend, color='#ef4444', linestyle='--', linewidth=2.0,
                label=f'Trend Line Log-OLS: {z[0]:+.2f} per decade di LOC', zorder=2)
        ax.legend(loc='upper left', bbox_to_anchor=(0.0, -0.15), frameon=True, facecolor='white', framealpha=0.95, fontsize=9.5)

    # Annotazione selettiva mirata: annotiamo solo i casi più rilevanti (estremi, outlier intermedi e funzioni chiave)
    # per preservare la massima leggibilità grafica
    annotated_pts = []
    sorted_pts = sorted(zip(locs, scores, names), key=lambda t: t[0])
    key_candidates = []
    for x, y, name in sorted_pts:
        # Punti intermedi (degradazione o casi interessanti)
        if 0 < y < 95:
            key_candidates.append((x, y, name, 'intermediate'))
        # Estremi assoluti di complessità
        elif x == min(locs) or x == max(locs):
            key_candidates.append((x, y, name, 'extreme_loc'))
        # Casi di fallimento critico (y=0)
        elif y == 0:
            key_candidates.append((x, y, name, 'failure'))
        # Campioni a punteggio pieno (y=100) ben distribuiti
        else:
            key_candidates.append((x, y, name, 'top'))

    # Filtraggio per evitare sovrapposizioni
    for x, y, name, cat in key_candidates:
        too_close = False
        for (ax_val, ay_val) in annotated_pts:
            log_dist = abs(np.log10(x) - np.log10(ax_val))
            y_dist = abs(y - ay_val)
            if log_dist < 0.35 and y_dist < 25:
                too_close = True
                break
        
        # Includi se non troppo vicino o se è un caso intermedio critico
        if (not too_close or cat == 'intermediate') and len(annotated_pts) < 10:
            annotated_pts.append((x, y))
            short_name = name if len(name) <= 20 else name[:17] + "..."
            
            if y >= 90:
                y_text = y - 9
                va_align = 'top'
            elif y <= 10:
                y_text = y + 9
                va_align = 'bottom'
            else:
                y_text = y + 8 if len(annotated_pts) % 2 == 0 else y - 8
                va_align = 'bottom' if len(annotated_pts) % 2 == 0 else 'top'

            ax.annotate(short_name, (x, y), xytext=(x, y_text),
                        fontsize=8.0, fontweight='bold', color='#0f172a',
                        ha='center', va=va_align,
                        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.92, edgecolor='#94a3b8'),
                        arrowprops=dict(arrowstyle='->', color='#475569', lw=0.8))

    ax.set_xlabel("Linee di Codice Sorgente C/C++ (LOC) [Scala Logaritmica]", fontsize=10.5, fontweight='bold')
    ax.set_ylabel(y_label, fontsize=10.5, fontweight='bold')
    ax.set_title(f"Analisi di Scalabilità: Complessità Codice vs Performance ({library_name})\n", fontsize=12.5, fontweight='bold')
    ax.set_ylim(-8, 118)
    
    # Range logaritmico confortevole
    min_x = max(0.8, min(locs) * 0.7)
    max_x = max(locs) * 1.5
    ax.set_xlim(min_x, max_x)
    ax.grid(True, which="both", linestyle=':', alpha=0.6)

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label(y_label, rotation=-90, va="bottom", fontsize=9.5, fontweight='bold')

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"-> Complexity vs Performance Plot salvato in: {output_path}")


def generate_pipeline_stage_flow(eval_results: List[Dict[str, Any]], output_path: str, library_name: str = "Benchmark"):
    """
    9. PIPELINE STAGE-TRANSITION FLOW BREAKDOWN
    Diagramma dell'imbuto di validazione (Funzioni Generate -> Verifier Pass -> Judge Pass -> RoundTrip Pass).
    Mostra come la pipeline multilivello filtra progressivamente le imperfezioni fino alla certificazione formale.
    """
    if not eval_results:
        return

    total = len(eval_results)
    verifier_pass = sum(1 for r in eval_results if r.get("is_valid", True))
    
    # Judge pass: score combined >= 3.5 o score A >= 3.5
    has_judge = any("judge_score_a" in r.get("metrics", {}) for r in eval_results)
    if has_judge:
        judge_pass = sum(1 for r in eval_results if r.get("metrics", {}).get("judge_score_a", 5.0) >= 3.5)
    else:
        judge_pass = verifier_pass

    has_rt = any("roundtrip" in r for r in eval_results)
    if has_rt:
        rt_pass = sum(1 for r in eval_results if r.get("roundtrip", {}).get("execution", {}).get("pass_rate", 0.0) >= 80.0)
    else:
        rt_pass = None

    stages = ["1. Draft LLM Generato", "2. Verifier Formale AST"]
    counts = [total, verifier_pass]
    colors = ['#3b82f6', '#10b981']

    if has_judge:
        stages.append("3. LLM-as-a-Judge (≥3.5)")
        counts.append(judge_pass)
        colors.append('#8b5cf6')

    if rt_pass is not None:
        stages.append("4. Round-Trip Pass (≥80%)")
        counts.append(rt_pass)
        colors.append('#f59e0b')

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(stages, counts, color=colors, edgecolor='#1e293b', width=0.55, zorder=3)

    for bar, val in zip(bars, counts):
        pct = round(val / total * 100, 1)
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.12, f"{val}/{total}\n({pct}%)",
                ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#0f172a')

    ax.set_ylabel("Numero Funzioni Certificate", fontsize=10, fontweight='bold')
    ax.set_title(f"Flusso di Validazione e Filtraggio Pipeline ({library_name})\n", fontsize=12, fontweight='bold')
    ax.set_ylim(0, total + max(1.5, total * 0.25))
    ax.grid(axis='y', linestyle=':', alpha=0.7)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"-> Pipeline Stage Flow salvato in: {output_path}")


def generate_all_advanced_charts(eval_results: List[Dict[str, Any]], run_dir: str, mode_name: str, library_name: str) -> List[str]:
    """
    Coordina la generazione di tutti i 9 grafici avanzati salvandoli all'interno della cartella run_dir.
    Restituisce la lista dei percorsi dei file generati.
    """
    created_charts = []

    # 1. Radar Chart
    radar_path = os.path.join(run_dir, "eval_chart_radar.png")
    try:
        generate_radar_chart(eval_results, radar_path, mode_name=mode_name, library_name=library_name)
        if os.path.exists(radar_path):
            created_charts.append(radar_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Radar Chart: {e}")

    # 2. Scatter Plot Semantica vs Round-Trip
    scatter_path = os.path.join(run_dir, "eval_chart_semantic_vs_roundtrip.png")
    try:
        generate_semantic_vs_roundtrip_scatter(eval_results, scatter_path, library_name=library_name)
        if os.path.exists(scatter_path):
            created_charts.append(scatter_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Scatter Plot: {e}")

    # 3. Distribution & Violin Plot
    violin_path = os.path.join(run_dir, "eval_chart_distributions.png")
    try:
        generate_metrics_distribution_plot(eval_results, violin_path, library_name=library_name)
        if os.path.exists(violin_path):
            created_charts.append(violin_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Distribution Plot: {e}")

    # 4. Heatmap di Confidenza Funzione x Metriche
    heatmap_path = os.path.join(run_dir, "eval_chart_heatmap.png")
    try:
        generate_function_confidence_heatmap(eval_results, heatmap_path, library_name=library_name)
        if os.path.exists(heatmap_path):
            created_charts.append(heatmap_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Heatmap: {e}")

    # 5. Breakdown Errori Verifier
    breakdown_path = os.path.join(run_dir, "eval_chart_verifier_breakdown.png")
    try:
        generate_verifier_errors_breakdown(eval_results, breakdown_path, library_name=library_name)
        if os.path.exists(breakdown_path):
            created_charts.append(breakdown_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Breakdown Verifier: {e}")

    # 6. Matrice di Cross-Correlazione tra Tutte le Metriche
    corr_path = os.path.join(run_dir, "eval_chart_cross_correlation.png")
    try:
        generate_correlation_matrix_heatmap(eval_results, corr_path, library_name=library_name)
        if os.path.exists(corr_path):
            created_charts.append(corr_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Cross-Correlation Heatmap: {e}")

    # 7. Grafico dei Residui (Allucinazione Plausibile vs Parafrasi Robusta)
    residuals_path = os.path.join(run_dir, "eval_chart_discrepancy_residuals.png")
    try:
        generate_semantic_vs_roundtrip_residuals(eval_results, residuals_path, library_name=library_name)
        if os.path.exists(residuals_path):
            created_charts.append(residuals_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Residuals Plot: {e}")

    # 8. Pareto Complessità vs Performance
    pareto_path = os.path.join(run_dir, "eval_chart_complexity_pareto.png")
    try:
        generate_complexity_vs_performance_plot(eval_results, pareto_path, library_name=library_name)
        if os.path.exists(pareto_path):
            created_charts.append(pareto_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Complexity Pareto Plot: {e}")

    # 9. Flusso di Filtraggio e Transizioni di Stadio Pipeline
    flow_path = os.path.join(run_dir, "eval_chart_pipeline_flow.png")
    try:
        generate_pipeline_stage_flow(eval_results, flow_path, library_name=library_name)
        if os.path.exists(flow_path):
            created_charts.append(flow_path)
    except Exception as e:
        print(f"[WARN] Impossibile generare Pipeline Flow Plot: {e}")

    return created_charts

