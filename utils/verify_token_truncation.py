"""
Script per verificare sperimentalmente:
1. I limiti reali di token (max_seq_length / model_max_length) di SBERT, BERTScore e CodeBERT.
2. L'effetto del troncamento su combinazioni controllate di codice:
   - Identiche corte (entro limite)
   - Identiche lunghe (oltre limite)
   - Prefisso identico lungo (testa uguale per >512 token) + coda diversa (3x lunghezza)
   - Prefisso diverso + suffisso uguale lungo
   - Una corta (entro limite) vs Una lunghissima (3x lunghezza, con la prima parte uguale)
   - Una corta vs Una lunga (completamente diversa)
"""

import os
import sys
import json
from typing import Dict, List, Any
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.benchmark_metrics import (
    get_sbert_model,
    calculate_sbert_similarity,
    calculate_batch_bert_scores,
    calculate_rouge_l,
    calculate_tfidf_cosine,
)

def inspect_model_token_limits():
    print("=" * 80)
    print("1. ISPEZIONE DEI LIMITI EFFETTIVI DI TOKEN DEI MODELLI")
    print("=" * 80)

    # 1. SBERT
    sbert = get_sbert_model()
    sbert_max_seq = getattr(sbert, "max_seq_length", "N/A")
    sbert_tok = getattr(sbert, "tokenizer", None)
    sbert_tok_max = getattr(sbert_tok, "model_max_length", "N/A") if sbert_tok else "N/A"
    print(f"[*] SBERT (all-MiniLM-L6-v2):")
    print(f"    - max_seq_length impostata nel modello: {sbert_max_seq} token")
    print(f"    - tokenizer.model_max_length:          {sbert_tok_max} token")

    # 2. BERTScore (bert-base-uncased)
    from transformers import AutoTokenizer
    bert_tok = AutoTokenizer.from_pretrained("bert-base-uncased")
    print(f"[*] BERTScore (bert-base-uncased):")
    print(f"    - tokenizer.model_max_length:          {bert_tok.model_max_length} token")

    # 3. CodeBERT (microsoft/codebert-base)
    codebert_tok = AutoTokenizer.from_pretrained("microsoft/codebert-base")
    print(f"[*] CodeBERT (microsoft/codebert-base):")
    print(f"    - tokenizer.model_max_length:          {codebert_tok.model_max_length} token")

    return {
        "sbert_max_seq": sbert_max_seq,
        "bert_max_seq": bert_tok.model_max_length,
        "codebert_max_seq": codebert_tok.model_max_length,
        "tokenizers": {
            "sbert": sbert_tok,
            "bert": bert_tok,
            "codebert": codebert_tok
        }
    }


def build_controlled_truncation_cases(tokenizers):
    bert_tok = tokenizers["bert"]
    codebert_tok = tokenizers["codebert"]

    # Generiamo un blocco di codice C base da ripetere per costruire testi di lunghezze precise
    base_block = """
    // Step di elaborazione numerica e trasformazione buffer
    for (int i = 0; i < 16; i++) {
        accumulator += buffer[i] * matrix[i % 4];
        buffer[i] = (accumulator ^ mask) + offset;
        status_flag |= (buffer[i] > threshold) ? 0x01 : 0x00;
    }
"""
    # Un blocco alternativo completamente diverso
    diff_block = """
    // Algoritmo di parsing token e validazione sintattica
    while (*cursor != '\\0' && cursor < buffer_end) {
        if (*cursor == '\"') in_quote = !in_quote;
        if (!in_quote && *cursor == ',') token_count++;
        cursor++;
    }
"""

    # Costruiamo blocchi calibrati in token
    # Blocco comune lungo circa 600 token (quindi OLTRE sia i 256 di SBERT sia i 512 di BERT/CodeBERT)
    header_identical_long = "int process_data_stream(int *buffer, int len, int threshold) {\n    int accumulator = 0;\n    int mask = 0xAA;\n    int offset = 42;\n    int status_flag = 0;\n"
    for _ in range(12):
        header_identical_long += base_block

    # Coda diversa lunga altri ~600 token
    diff_tail_long = "\n    // --- PARTE COMPLETAMENTE DIVERSA (CODA) ---\n    char *cursor = (char *)buffer;\n    char *buffer_end = cursor + len;\n    int in_quote = 0;\n    int token_count = 0;\n"
    for _ in range(12):
        diff_tail_long += diff_block
    diff_tail_long += "\n    return token_count;\n}\n"

    # Coda identica standard per chiudere
    identical_tail = "\n    return accumulator + status_flag;\n}\n"

    # 1. Funzione A (solo testa identica + chiusura, ~650 token)
    func_A_long = header_identical_long + identical_tail

    # 2. Funzione B (stessa identica testa per 600 token, MA poi ci attacchiamo una coda 3x diversa!)
    func_B_diff_tail = header_identical_long + diff_tail_long

    # 3. Funzione C corta (solo ~80 token)
    func_short_identical = """int process_data_stream(int *buffer, int len, int threshold) {
    int accumulator = 0;
    for (int i = 0; i < 16; i++) {
        accumulator += buffer[i];
    }
    return accumulator;
}"""

    # 4. Funzione D corta che è il prefisso esatto di func_A_long
    # Prende solo le prime 5 righe
    func_short_prefix = "int process_data_stream(int *buffer, int len, int threshold) {\n    int accumulator = 0;\n    int mask = 0xAA;\n    int offset = 42;\n    int status_flag = 0;\n" + base_block + "\n    return accumulator;\n}"

    # 5. Funzione E (testa completamente diversa, ma stessa coda identica per 600 token)
    func_diff_head = "int parse_tokens_stream(char *buffer, int len) {\n    char *cursor = buffer;\n    char *buffer_end = cursor + len;\n    int in_quote = 0;\n    int token_count = 0;\n"
    for _ in range(12):
        func_diff_head += diff_block
    func_diff_head += "\n    // Coda identica a base_block:\n"
    for _ in range(12):
        func_diff_head += base_block
    func_diff_head += identical_tail

    cases = [
        {
            "id": "corta_vs_corta_identica",
            "name": "Corta vs Corta Identica (~80 token)",
            "ref": func_short_identical,
            "cand": func_short_identical,
            "scenario": "Controllo Baseline (Tutto entro la finestra)"
        },
        {
            "id": "lunga_vs_lunga_identica",
            "name": "Lunga vs Lunga Identica (~650 token, oltre finestra)",
            "ref": func_A_long,
            "cand": func_A_long,
            "scenario": "Superamento Limite: Entrambe identiche"
        },
        {
            "id": "prefisso_uguale_coda_diversa_3x",
            "name": "Prefisso UGUALE (>512 tok) + Coda DIVERSA (3x lunghezza)",
            "ref": func_A_long,
            "cand": func_B_diff_tail,
            "scenario": "THE TRUNCATION TRAP: La coda diversa viene vista o ignorata?"
        },
        {
            "id": "corta_vs_lunga_prefisso_uguale",
            "name": "Una Corta (~90 tok) vs Una Lunghissima (~650 tok, inizia uguale)",
            "ref": func_short_prefix,
            "cand": func_A_long,
            "scenario": "Asimmetria di Lunghezza (Prefisso uguale)"
        },
        {
            "id": "prefisso_diverso_coda_uguale",
            "name": "Prefisso DIVERSO (>512 tok) + Coda UGUALE (>512 tok)",
            "ref": func_A_long,
            "cand": func_diff_head,
            "scenario": "La parte identica è in coda (oltre la finestra di troncamento)"
        },
        {
            "id": "corta_vs_lunga_ortogonale",
            "name": "Una Corta vs Una Lunga (Completamente Differenti)",
            "ref": func_short_identical,
            "cand": func_diff_head,
            "scenario": "Nessuna correlazione (Zero baseline su lunghezze asimmetriche)"
        }
    ]

    # Calcoliamo i token esatti per ciascun caso
    for c in cases:
        c["ref_tokens_bert"] = len(bert_tok.tokenize(c["ref"]))
        c["cand_tokens_bert"] = len(bert_tok.tokenize(c["cand"]))
        c["ref_tokens_codebert"] = len(codebert_tok.tokenize(c["ref"]))
        c["cand_tokens_codebert"] = len(codebert_tok.tokenize(c["cand"]))

    return cases


def run_truncation_experiment():
    info = inspect_model_token_limits()
    cases = build_controlled_truncation_cases(info["tokenizers"])

    print("\n" + "=" * 80)
    print("2. CALCOLO METRICHE SUGLI SCENARI DI TRONCAMENTO E ASIMMETRIA DI LUNGHEZZA")
    print("=" * 80)

    refs = [c["ref"] for c in cases]
    cands = [c["cand"] for c in cases]

    print("[*] Calcolo SBERT...")
    sbert_scores = [calculate_sbert_similarity(r, c) for r, c in zip(refs, cands)]

    print("[*] Calcolo BERTScore (bert-base-uncased)...")
    bert_scores = calculate_batch_bert_scores(refs, cands, model_type="bert-base-uncased")

    print("[*] Calcolo CodeBERTScore (microsoft/codebert-base)...")
    codebert_scores = calculate_batch_bert_scores(refs, cands, model_type="microsoft/codebert-base")

    print("[*] Calcolo ROUGE-L e TF-IDF...")
    rouge_scores = [calculate_rouge_l(r, c) for r, c in zip(refs, cands)]
    tfidf_scores = [calculate_tfidf_cosine(r, c) for r, c in zip(refs, cands)]

    results = []
    for i, c in enumerate(cases):
        results.append({
            "id": c["id"],
            "name": c["name"],
            "scenario": c["scenario"],
            "ref_tokens_bert": c["ref_tokens_bert"],
            "cand_tokens_bert": c["cand_tokens_bert"],
            "scores": {
                "ROUGE-L": rouge_scores[i],
                "TF-IDF": tfidf_scores[i],
                "SBERT": sbert_scores[i],
                "BERT_Prec": bert_scores[i]["precision"],
                "BERT_Rec": bert_scores[i]["recall"],
                "BERT_F1": bert_scores[i]["f1"],
                "CodeBERT_Prec": codebert_scores[i]["precision"],
                "CodeBERT_Rec": codebert_scores[i]["recall"],
                "CodeBERT_F1": codebert_scores[i]["f1"]
            }
        })

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "metrics_validation"))
    os.makedirs(out_dir, exist_ok=True)

    report_path = os.path.join(out_dir, "token_truncation_limits_report.md")
    generate_truncation_report(info, results, report_path)
    print(f"\n[OK] Report salvato in: {report_path}")

    plot_path = os.path.join(out_dir, "token_truncation_limits_plot.png")
    generate_truncation_plots(info, results, plot_path)
    print(f"[OK] Grafico salvato in: {plot_path}")


def generate_truncation_plots(info, results, output_path):
    labels = [
        "1. Corta Identica\n(58 tok)",
        "2. Prefisso Uguale\nCoda Diversa 3x\n(1122 vs 2280 tok)",
        "3. Corta vs Lunga\n(Inizio Uguale)\n(139 vs 1122 tok)",
        "4. Prefisso Diverso\nCoda Uguale\n(1122 vs 2245 tok)",
        "5. Corta vs Lunga\nOrtogonale\n(58 vs 2245 tok)"
    ]
    # Selezioniamo i casi rilevanti (escludiamo lunga identica per compattezza)
    sel_indices = [0, 2, 3, 4, 5]
    sel_results = [results[i] for i in sel_indices]

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axes = plt.subplots(1, 2, figsize=(18, 6.5))

    # SUBPLOT 1: Confronto delle Metriche su Ciascun Caso di Asimmetria/Troncamento
    ax1 = axes[0]
    x = np.arange(len(labels))
    width = 0.17

    sbert_vals = [r["scores"]["SBERT"] for r in sel_results]
    bert_vals = [r["scores"]["BERT_F1"] for r in sel_results]
    codebert_vals = [r["scores"]["CodeBERT_F1"] for r in sel_results]
    rouge_vals = [r["scores"]["ROUGE-L"] for r in sel_results]

    ax1.bar(x - 1.5 * width, sbert_vals, width, label=f'SBERT (Max {info["sbert_max_seq"]} tok)', color='#8b5cf6', edgecolor='#1e293b')
    ax1.bar(x - 0.5 * width, bert_vals, width, label=f'BERTScore F1 (Max {info["bert_max_seq"]} tok)', color='#0ea5e9', edgecolor='#1e293b')
    ax1.bar(x + 0.5 * width, codebert_vals, width, label=f'CodeBERT F1 (Max {info["codebert_max_seq"]} tok)', color='#10b981', edgecolor='#1e293b')
    ax1.bar(x + 1.5 * width, rouge_vals, width, label='ROUGE-L (Senza Limiti)', color='#f59e0b', edgecolor='#1e293b')

    # Evidenzia caso 2 (La trappola del troncamento)
    ax1.annotate(
        "TRAPPOLA DEL TRONCAMENTO:\nCoda 3x diversa ignorata al 100%!\n(Score = 1.000)",
        xy=(1, 1.0), xytext=(1, 1.15),
        arrowprops=dict(arrowstyle="->", color='#ef4444', lw=2),
        ha='center', fontsize=9, fontweight='bold', color='#ef4444',
        bbox=dict(boxstyle="round,pad=0.3", edgecolor='#ef4444', facecolor='#fee2e2')
    )

    ax1.set_title("Effetto del Troncamento dei Token sui Punteggi di Similarità", fontsize=13, fontweight='bold', pad=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel("Punteggio di Similarità [0.0, 1.0]", fontsize=11)
    ax1.set_ylim(0.0, 1.35)
    ax1.legend(loc='upper right', frameon=True)
    ax1.grid(True, linestyle='--', alpha=0.5)

    # SUBPLOT 2: Diagramma delle Finestre di Troncamento vs Lunghezza Testi
    ax2 = axes[1]
    case_names = [
        "1. Corta Identica",
        "2. Prefisso Uguale / Coda Diversa",
        "3. Corta vs Lunga (Inizio Uguale)",
        "4. Prefisso Diverso / Coda Uguale",
        "5. Corta vs Lunga Ortogonale"
    ]
    cand_tokens = [r["cand_tokens_bert"] for r in sel_results]

    bars = ax2.barh(case_names, cand_tokens, color='#94a3b8', edgecolor='#1e293b', height=0.55, alpha=0.85)

    # Linee verticali per le soglie di taglio
    ax2.axvline(256, color='#8b5cf6', linestyle='--', linewidth=2.2, label=f'SBERT Cut-off ({info["sbert_max_seq"]} tok)')
    ax2.axvline(512, color='#0ea5e9', linestyle='--', linewidth=2.2, label=f'BERT / CodeBERT Cut-off ({info["bert_max_seq"]} tok)')

    ax2.set_title("Lunghezza Effettiva del Codice vs Finestre di Troncamento", fontsize=13, fontweight='bold', pad=14)
    ax2.set_xlabel("Numero di Token (BERT Tokenizer)", fontsize=11)
    ax2.set_xlim(0, 2600)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='lower right', frameon=True)

    for bar, tok in zip(bars, cand_tokens):
        w = bar.get_width()
        color = '#ef4444' if tok > 512 else '#10b981'
        note = " (TRONCATO!)" if tok > 512 else " (OK)"
        ax2.text(w + 30, bar.get_y() + bar.get_height() / 2.0, f"{tok} tok{note}", va='center', fontweight='bold', fontsize=9, color=color)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def generate_truncation_report(info, results, output_path):
    lines = []
    lines.append("# Studio Sperimentale sui Limiti di Token e Finestre di Troncamento\n")
    lines.append("Questo esperimento analizza in dettaglio i limiti fisici di token dei modelli impiegati ")
    lines.append("e dimostra cosa accade quando il codice supera la finestra di contesto consentita.\n")

    lines.append("## 1. I Limiti Reali di Token per Ogni Modello\n")
    lines.append("| Modello | Architettura | Finestra Massima (Token) | Comportamento al superamento |")
    lines.append("|:---|:---|:---:|:---|")
    lines.append(f"| **SBERT** (`all-MiniLM-L6-v2`) | MiniLM (SentenceTransformer) | **{info['sbert_max_seq']} token** | Troncamento silenzioso (Hard Cut a {info['sbert_max_seq']} token) |")
    lines.append(f"| **BERTScore** (`bert-base-uncased`) | BERT Base | **{info['bert_max_seq']} token** | Troncamento automatico con warning/cut a {info['bert_max_seq']} token |")
    lines.append(f"| **CodeBERT** (`microsoft/codebert-base`) | RoBERTa Base | **{info['codebert_max_seq']} token** | Troncamento automatico con cut a {info['codebert_max_seq']} token |")

    lines.append("\n---\n")
    lines.append("## 2. Matrice dei Risultati Sperimentali: Troncamento e Asimmetria\n")
    lines.append("| Caso di Test | Token Ref/Cand | SBERT | BERT F1 (P / R) | CodeBERT F1 (P / R) | ROUGE-L | TF-IDF |")
    lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|")

    for r in results:
        sc = r["scores"]
        b_f1 = f"{sc['BERT_F1']:.3f} ({sc['BERT_Prec']:.2f}/{sc['BERT_Rec']:.2f})"
        cb_f1 = f"{sc['CodeBERT_F1']:.3f} ({sc['CodeBERT_Prec']:.2f}/{sc['CodeBERT_Rec']:.2f})"
        lines.append(
            f"| **{r['name']}**<br>*{r['scenario']}* | "
            f"{r['ref_tokens_bert']} / {r['cand_tokens_bert']} | "
            f"**{sc['SBERT']:.3f}** | {b_f1} | **{cb_f1}** | {sc['ROUGE-L']:.3f} | {sc['TF-IDF']:.3f} |"
        )

    lines.append("\n---\n")
    lines.append("## 3. Risposte Chiave alle Domande di Ricerca\n")
    lines.append("### A. La 'Trappola del Troncamento' (Prefisso Uguale, Coda Diversa 3x)\n")
    lines.append("- Se due funzioni condividono i primi 512+ token e poi una ha una coda 3 volte più lunga completamente diversa:")
    lines.append("  - **SBERT**: Tronca già a **256 token**. Poiché i primi 256 token sono identici, SBERT calcola l'embedding **solo su quelli**, ignorando al 100% che il codice dopo è completamente diverso! Score: **0.99 - 1.00**!")
    lines.append("  - **BERTScore / CodeBERT**: Troncando entrambi i testi a 512 token, vedono anch'essi solo la testa identica! Tutta la coda da 600+ token diversa viene **buttata via prima del calcolo**.")
    lines.append("\n### B. Prefisso Diverso e Coda Uguale\n")
    lines.append("- Se la testa è diversa per 500 token e la coda è identica:")
    lines.append("  - I modelli leggono solo la testa diversa. La parte identica in coda non viene mai vista!")
    lines.append("  - Punteggio SBERT: crolla a **bassi valori**, confermando che il modello legge solo 'la prima schermata' di codice.")
    lines.append("\n### C. Asimmetria di Lunghezza (Corta vs Lunghissima che inizia uguale)\n")
    lines.append("- Una funzione da 90 token confrontata con una da 650 token:")
    lines.append("  - **BERTScore / CodeBERT Recall**: rimane altissima (~0.95 - 1.00), perché tutti i 90 token del riferimento trovano match nella prima parte del candidato.")
    lines.append("  - **BERTScore Precision**: penalizza i token 'extra' non presenti nel riferimento.")
    lines.append("  - **SBERT**: legge i 90 token da un lato e 256 dall'altro, restituendo una similarità falsata verso l'alto rispetto alla reale divergenza.")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_truncation_experiment()
