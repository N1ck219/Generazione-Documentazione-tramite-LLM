"""
Studio Scientifico Sperimentale: Impatto della Lunghezza dei Token e Posizione della Modifica
sulle Metriche NLP (SBERT, BERTScore, CodeBERTScore, ROUGE-L, TF-IDF).

Casi di Studio Controllati:
1. Short (<128 token) - Modifica all'inizio (Head Diff)
2. Short (<128 token) - Modifica alla fine (Tail Diff)
3. Mid (~256-400 token) - Modifica all'inizio (Head Diff)
4. Mid (~256-400 token) - Modifica alla fine (Tail Diff)
5. Boundary (~500 token) - Modifica alla soglia critica (Critical Boundary Diff)
6. Truncated (>512 token) - Uguali nei primi 512 token, TOTALMENTE DIVERSI dopo (Equal Head / Different Tail)
7. Truncated (>512 token) - DIVERSI nei primi 512 token, UGUALI dopo (Different Head / Equal Tail)
8. Massive (~1024 token) - Due funzioni completamente diverse ma diluite con lo stesso boilerplate

Salva i risultati in: results/metrics_validation/img_finali/nlp_token_length_sensitivity_results.json
"""

import os
import sys
import json
from typing import Dict, List, Any
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.benchmark_metrics import (
    calculate_sbert_similarity,
    calculate_batch_bert_scores,
    calculate_rouge_l,
    calculate_tfidf_cosine,
    calculate_meteor_score,
)

# Generatore di blocchi di codice C realistici
def generate_c_block_common(n_lines: int) -> str:
    lines = []
    for i in range(n_lines):
        lines.append(f"    state_accum[{i % 8}] = (state_accum[{i % 8}] ^ 0x3F) + ((input_val * {i+1}) & 0xFF);")
        lines.append(f"    if (state_accum[{i % 8}] > 0x1000) {{ state_accum[{i % 8}] = 0; }}")
    return "\n".join(lines)

def generate_c_block_alt(n_lines: int) -> str:
    lines = []
    for i in range(n_lines):
        lines.append(f"    hash_digest[{i % 8}] = (hash_digest[{i % 8}] << 3) ^ ((entropy_seed ^ {i+7}) & 0xAA);")
        lines.append(f"    if (hash_digest[{i % 8}] & 0x01) {{ hash_digest[{i % 8}] >>= 1; }}")
    return "\n".join(lines)

TOKEN_BENCHMARK_SCENARIOS = [
    # -------------------------------------------------------------------------
    # 1. SHORT (<128 token) - Head Diff (Divergenza all'inizio, coda uguale)
    # -------------------------------------------------------------------------
    {
        "id": "short_head_diff",
        "category": "Short (<128 tok)",
        "name": "Short: Head Diff\n(Divergenza all'Inizio)",
        "tokens_est": 85,
        "ref": """int compute_transform(int input_val) {
    int state_accum[8] = {1, 2, 3, 4, 5, 6, 7, 8}; // INIT CONFIG A
    for (int i = 0; i < 4; i++) {
        state_accum[i] += input_val * 2;
    }
    return state_accum[0];
}""",
        "cand": """int compute_transform(int input_val) {
    int state_accum[8] = {99, 88, 77, 66, 55, 44, 33, 22}; // INIT CONFIG B (DIVERSO)
    for (int i = 0; i < 4; i++) {
        state_accum[i] += input_val * 2;
    }
    return state_accum[0];
}"""
    },

    # -------------------------------------------------------------------------
    # 2. SHORT (<128 token) - Tail Diff (Inizio uguale, divergenza alla fine)
    # -------------------------------------------------------------------------
    {
        "id": "short_tail_diff",
        "category": "Short (<128 tok)",
        "name": "Short: Tail Diff\n(Divergenza alla Fine)",
        "tokens_est": 85,
        "ref": """int compute_transform(int input_val) {
    int state_accum[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    for (int i = 0; i < 4; i++) {
        state_accum[i] += input_val * 2;
    }
    return state_accum[0]; // RITORNO A
}""",
        "cand": """int compute_transform(int input_val) {
    int state_accum[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    for (int i = 0; i < 4; i++) {
        state_accum[i] += input_val * 2;
    }
    return -state_accum[7]; // RITORNO B (OPPOSTO)
}"""
    },

    # -------------------------------------------------------------------------
    # 3. MID (~300 token) - Head Diff (Divergenza all'inizio, lungo corpo comune)
    # -------------------------------------------------------------------------
    {
        "id": "mid_head_diff",
        "category": "Mid (~300 tok)",
        "name": "Mid: Head Diff\n(Divergenza all'Inizio)",
        "tokens_est": 320,
        "ref": "int process_stream(int input_val) {\n    int state_accum[8] = {1, 2, 3, 4, 5, 6, 7, 8};\n"
               + generate_c_block_common(20)
               + "\n    return state_accum[0];\n}",
        "cand": "int process_stream(int input_val) {\n    int state_accum[8] = {99, 88, 77, 66, 55, 44, 33, 22};\n"
               + generate_c_block_common(20)
               + "\n    return state_accum[0];\n}"
    },

    # -------------------------------------------------------------------------
    # 4. MID (~300 token) - Tail Diff (Lungo corpo comune, divergenza alla fine)
    # -------------------------------------------------------------------------
    {
        "id": "mid_tail_diff",
        "category": "Mid (~300 tok)",
        "name": "Mid: Tail Diff\n(Divergenza alla Fine)",
        "tokens_est": 320,
        "ref": "int process_stream(int input_val) {\n    int state_accum[8] = {1, 2, 3, 4, 5, 6, 7, 8};\n"
               + generate_c_block_common(20)
               + "\n    return state_accum[0];\n}",
        "cand": "int process_stream(int input_val) {\n    int state_accum[8] = {1, 2, 3, 4, 5, 6, 7, 8};\n"
               + generate_c_block_common(20)
               + "\n    return -state_accum[7] * 99; // CRITICAL DIVERGENCE\n}"
    },

    # -------------------------------------------------------------------------
    # 5. TRUNCATED (>512 token) - UGUALI nei primi 512 token, TOTALMENTE DIVERSI DOPO
    # (The Truncation Blind Spot: La seconda metà viene tagliata!)
    # -------------------------------------------------------------------------
    {
        "id": "over_512_equal_head_diff_tail",
        "category": "Over 512 tok",
        "name": "Over 512: Head Uguale,\nTail Opposta (Cieca)",
        "tokens_est": 750,
        "ref": "int transform_pipeline(int input_val) {\n    int state_accum[8] = {0};\n"
               + generate_c_block_common(40) # ~520 token identici
               + "\n    // --- ZONA OLTRE 512 TOKEN ---\n"
               + "    int final_result = state_accum[0] + 100;\n"
               + generate_c_block_common(15)
               + "\n    return final_result;\n}",
        "cand": "int transform_pipeline(int input_val) {\n    int state_accum[8] = {0};\n"
               + generate_c_block_common(40) # ~520 token identici
               + "\n    // --- ZONA OLTRE 512 TOKEN: COMPLETAMENTE OPPOSTA ---\n"
               + "    int final_result = -99999;\n"
               + generate_c_block_alt(15)
               + "\n    return final_result;\n}"
    },

    # -------------------------------------------------------------------------
    # 6. TRUNCATED (>512 token) - DIVERSI nei primi 512 token, UGUALI DOPO
    # (The Truncation Inversion: L'inizio diverso viene catturato)
    # -------------------------------------------------------------------------
    {
        "id": "over_512_diff_head_equal_tail",
        "category": "Over 512 tok",
        "name": "Over 512: Head Diversa,\nTail Uguale (Catturata)",
        "tokens_est": 750,
        "ref": "int pipeline_alpha(int input_val) {\n    int state_accum[8] = {0};\n"
               + generate_c_block_common(20) # Head A
               + "\n    // --- ZONA CENTRO E CODA COMUNE ---\n"
               + generate_c_block_common(35)
               + "\n    return state_accum[0];\n}",
        "cand": "int pipeline_beta(int input_val) {\n    int hash_digest[8] = {0};\n"
               + generate_c_block_alt(20) # Head B completamente diversa
               + "\n    // --- ZONA CENTRO E CODA COMUNE ---\n"
               + generate_c_block_common(35)
               + "\n    return state_accum[0];\n}"
    },

    # -------------------------------------------------------------------------
    # 7. MASSIVE (~1000 token) - Enorme diluizione comune con logica breve e opposta
    # (Token Dilution / Needle in a Haystack)
    # -------------------------------------------------------------------------
    {
        "id": "massive_dilution_needle",
        "category": "Massive (~1000 tok)",
        "name": "Massive 1000t: Diluizione\n(Min vs Max in Boilerplate)",
        "tokens_est": 1050,
        "ref": "int extreme_finder(int a, int b) {\n"
               + generate_c_block_common(60) # Massive boilerplate
               + "\n    return (a < b) ? a : b; // CERCA MINIMO\n}",
        "cand": "int extreme_finder(int a, int b) {\n"
               + generate_c_block_common(60) # Stesso boilerplate
               + "\n    return (a > b) ? a : b; // BUG CRITICO: CERCA MASSIMO\n}"
    }
]


def run_token_sensitivity_benchmark():
    print("=" * 80)
    print("VALUTAZIONE SCIENTIFICA: IMPATTO DELLA LUNGHEZZA DEI TOKEN SULLE METRICHE NLP")
    print(f"Scenari controllati: {len(TOKEN_BENCHMARK_SCENARIOS)}")
    print("=" * 80)

    refs = [s["ref"] for s in TOKEN_BENCHMARK_SCENARIOS]
    cands = [s["cand"] for s in TOKEN_BENCHMARK_SCENARIOS]

    print("\n[1/5] Calcolo ROUGE-L (LCS su tutta la lunghezza)...")
    rouge_l_scores = [calculate_rouge_l(r, c) for r, c in zip(refs, cands)]

    print("\n[2/5] Calcolo TF-IDF Cosine (Bag-of-Words pesato)...")
    tfidf_scores = [calculate_tfidf_cosine(r, c) for r, c in zip(refs, cands)]

    print("\n[3/5] Calcolo SBERT Cosine (SentenceTransformer: all-MiniLM-L6-v2, limite 512)...")
    sbert_scores = [calculate_sbert_similarity(r, c) for r, c in zip(refs, cands)]

    print("\n[4/5] Calcolo BERTScore F1 (bert-base-uncased, limite 512)...")
    bert_res = calculate_batch_bert_scores(refs, cands, model_type="bert-base-uncased")
    bert_f1_scores = [b["f1"] for b in bert_res]

    print("\n[5/5] Calcolo CodeBERTScore F1 (microsoft/codebert-base, limite 512)...")
    codebert_res = calculate_batch_bert_scores(refs, cands, model_type="microsoft/codebert-base")
    codebert_f1_scores = [cb["f1"] for cb in codebert_res]

    full_results = []
    for i, s in enumerate(TOKEN_BENCHMARK_SCENARIOS):
        full_results.append({
            "id": s["id"],
            "category": s["category"],
            "name": s["name"],
            "tokens_est": s["tokens_est"],
            "scores": {
                "SBERT": sbert_scores[i],
                "BERTScore_F1": bert_f1_scores[i],
                "CodeBERT_F1": codebert_f1_scores[i],
                "ROUGE_L": rouge_l_scores[i],
                "TFIDF": tfidf_scores[i]
            }
        })

    out_file = os.path.join(ROOT_DIR, "results", "metrics_validation", "img_finali", "nlp_token_length_sensitivity_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)

    print(f"\n[OK] Risultati salvati in: {out_file}")
    return full_results


if __name__ == "__main__":
    run_token_sensitivity_benchmark()
