"""
Generatore di grafici diagnostici per la tassonomia e distribuzione degli errori del Round-Trip.
Produce visualizzazioni scientifiche chiare ed eleganti per la tesi:
1. Grafico a barre orizzontali delle macro-categorie di errore con percentuali e conteggi.
2. Grafico a torta / donut delle macro-categorie di errore.
3. Classifica delle top funzioni con fallimenti e relativi tipi di errore.
"""

import os
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Any, Optional

# Palette professionale per le categorie di errore (color-coded per gravità/tipologia)
CATEGORY_COLORS = {
    "Missing Symbol / Environment": "#e74c3c",       # Rosso vivace (simboli/helper mancanti)
    "Interface / Signature Mismatch": "#e67e22",     # Arancione (mismatch di firma)
    "Behavioral / Contract Failure": "#9b59b6",      # Viola (calcolo o asserzione fallita)
    "Test Harness / Generator Bug": "#3498db",       # Blu (anomalie suite test)
    "Syntax / Compilation Error": "#c0392b",         # Rosso scuro (sintassi non valida)
    "Timeout / Hang": "#34495e",                     # Grigio scuro (timeout)
    "Other Execution Error": "#95a5a6"               # Grigio chiaro (altri errori)
}
DEFAULT_COLOR = "#7f8c8d"


def generate_roundtrip_error_charts(
    analysis_data: Dict[str, Any],
    output_image_path: str,
    library_name: Optional[str] = None
) -> str:
    """
    Genera un'immagine composita a 2 pannelli:
    - Sinistra: Bar chart orizzontale delle macro-categorie di errore con percentuali e conteggi
    - Destra: Top 8 funzioni con maggior numero di errori e stacked bar per categoria
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_image_path)), exist_ok=True)
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    categories = analysis_data.get("categories", [])
    function_breakdown = analysis_data.get("function_breakdown", [])
    summary = analysis_data.get("summary", {})

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), dpi=200)

    lib_str = f" - Libreria: {library_name}" if library_name else ""
    fig.suptitle(
        f"Analisi Diagnostica Errori Round-Trip (Doc-to-Code Synthesis){lib_str}\n"
        f"Totale Test Valutati: {summary.get('total_evaluated', 0)} funzioni | "
        f"Funzioni con Errori: {summary.get('failing_functions', 0)} | "
        f"Totale Fallimenti: {summary.get('total_error_events', 0)}",
        fontsize=13,
        fontweight='bold',
        y=1.02
    )

    # -------------------------------------------------------------
    # 1. PANNELLO SINISTRO: Distribuzione Macro-Categorie di Errore
    # -------------------------------------------------------------
    if categories:
        cats = [c["category"] for c in reversed(categories)]
        counts = [c["count"] for c in reversed(categories)]
        pcts = [c["percentage"] for c in reversed(categories)]
        colors = [CATEGORY_COLORS.get(c, DEFAULT_COLOR) for c in cats]

        y_pos = np.arange(len(cats))
        bars = ax1.barh(y_pos, counts, color=colors, height=0.55, edgecolor='black', alpha=0.88)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(cats, fontsize=10, fontweight='bold')
        ax1.set_xlabel("Numero di Fallimenti Test Registrati", fontsize=10, labelpad=8)
        ax1.set_title("Distribuzione delle Cause di Fallimento (Tassonomia)", fontsize=11, fontweight='bold', pad=10)

        max_c = max(counts) if counts else 10
        ax1.set_xlim(0, max_c * 1.25)

        for bar, count, pct in zip(bars, counts, pcts):
            w = bar.get_width()
            ax1.text(
                w + (max_c * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{count} ({pct}%)",
                ha='left',
                va='center',
                fontsize=9.5,
                fontweight='bold',
                color='#2c3e50'
            )
    else:
        ax1.text(0.5, 0.5, "Nessun errore riscontrato!\nTutti i test sono passati.", ha='center', va='center', fontsize=12)
        ax1.axis('off')

    # -------------------------------------------------------------
    # 2. PANNELLO DESTRO: Top Funzioni con Più Fallimenti
    # -------------------------------------------------------------
    top_funcs = [fb for fb in function_breakdown if fb.get("tests_failed", 0) > 0][:8]
    if top_funcs:
        top_funcs_rev = list(reversed(top_funcs))
        f_names = [f["function_name"] for f in top_funcs_rev]
        f_failed = [f["tests_failed"] for f in top_funcs_rev]
        f_totals = [f["total_tests"] for f in top_funcs_rev]

        y_pos2 = np.arange(len(f_names))

        # Colora ciascuna barra con la categoria prevalente per quella funzione
        func_colors = []
        for f in top_funcs_rev:
            fails = f.get("failures", [])
            primary_cat = fails[0]["category"] if fails else "Other Execution Error"
            func_colors.append(CATEGORY_COLORS.get(primary_cat, DEFAULT_COLOR))

        bars2 = ax2.barh(y_pos2, f_failed, color=func_colors, height=0.55, edgecolor='black', alpha=0.88)
        ax2.set_yticks(y_pos2)
        ax2.set_yticklabels([f"`{n}`" for n in f_names], fontsize=9.5, family='monospace')
        ax2.set_xlabel("Test Falliti", fontsize=10, labelpad=8)
        ax2.set_title("Top Funzioni con Maggior Numero di Errori", fontsize=11, fontweight='bold', pad=10)

        max_f = max(f_failed) if f_failed else 10
        ax2.set_xlim(0, max_f * 1.35)

        for bar, failed, total in zip(bars2, f_failed, f_totals):
            w = bar.get_width()
            ax2.text(
                w + (max_f * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{failed}/{total} falliti",
                ha='left',
                va='center',
                fontsize=9.5,
                fontweight='bold',
                color='#c0392b' if failed == total else '#d35400'
            )
    else:
        ax2.text(0.5, 0.5, "Tutte le funzioni hanno superato i test.", ha='center', va='center', fontsize=12)
        ax2.axis('off')

    plt.tight_layout()
    plt.savefig(output_image_path, bbox_inches='tight', dpi=200)
    plt.close(fig)

    return output_image_path
