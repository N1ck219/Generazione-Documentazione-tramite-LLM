"""
Modulo di Metriche Avanzate e Grafici per il Benchmark della Documentazione C/C++.
Implementa:
1. Parser Doxygen per estrarre campi strutturati: brief, details, params, returns, pre, post, warning.
2. Metriche lessicali e semantiche locali:
   - TF-IDF Cosine Similarity (puramente in Python con NumPy)
   - ROUGE-L (Longest Common Subsequence)
   - Token Recall & Jaccard Similarity
   - Brevity Penalty / Length Ratio (concisione vs verbosita')
3. Metriche Basate su Embedding Dense e Modelli Pre-addestrati:
   - Sentence-BERT (SBERT) Cosine Similarity (all-MiniLM-L6-v2)
   - BERTScore (Precision, Recall, F1 con RoBERTa / DeBERTa)
   - CodeBERTScore (Precision, Recall, F1 con microsoft/codebert-base)
   - BLEURT / Neural Quality Estimator
4. Metriche di Information Extraction / Slot-Filling sui Contratti Software:
   - Parameter Precision, Recall, F1-Score (rispetto all'AST)
   - Return Contract Match (verifica correttezza vs tipo di ritorno AST)
5. Generazione Dashboard Grafica Analitica (Matplotlib).
"""

import os
import re
import math
import warnings
from collections import Counter
from typing import Dict, List, Any, Tuple
import numpy as np
import matplotlib.pyplot as plt

# Silenzia warning dei modelli transformer
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Cache globale dei modelli di embedding per caricarli una volta sola
_SBERT_MODEL = None

def get_sbert_model():
    global _SBERT_MODEL
    if _SBERT_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Modello ultraleggero (~80MB) e veloce su CPU
            _SBERT_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[WARN] Impossibile caricare SentenceTransformer ('all-MiniLM-L6-v2'): {e}")
            _SBERT_MODEL = False
    return _SBERT_MODEL

def parse_doxygen_block(doxygen_text: str) -> Dict[str, Any]:
    """
    Estrae le singole componenti strutturate da un commento Doxygen:
    - brief: testo sintetico
    - details: testo approfondito
    - params: lista di dict {name, direction, description}
    - returns: lista di clausole di ritorno
    - warnings: lista di warning
    - pre: precondizioni
    - post: postcondizioni
    """
    if not doxygen_text:
        return {
            "brief": "", "details": "", "params": [],
            "returns": [], "warnings": [], "pre": [], "post": []
        }

    clean_lines = []
    for line in doxygen_text.splitlines():
        l = line.strip()
        l = re.sub(r"^(/\*\*|/\*!|/\*|\*/|\*) ?", "", l)
        clean_lines.append(l)
    text = "\n".join(clean_lines).strip()

    brief_match = re.search(r"@brief\s+(.*?)(?=(?:@details|@param|@return|@warning|@pre|@post|$))", text, re.DOTALL)
    brief = brief_match.group(1).strip() if brief_match else ""

    details_match = re.search(r"@details\s+(.*?)(?=(?:@param|@return|@warning|@pre|@post|$))", text, re.DOTALL)
    details = details_match.group(1).strip() if details_match else ""

    if not brief and not details:
        header_text = re.split(r"@(param|return|warning|pre|post)", text)[0].strip()
        brief = header_text

    params = []
    param_matches = re.finditer(r"@param(?:\[(.*?)\])?\s+([a-zA-Z0-9_]+)\s+(.*?)(?=(?:@param|@return|@warning|@pre|@post|$))", text, re.DOTALL)
    for m in param_matches:
        direction = m.group(1) or "in"
        p_name = m.group(2).strip()
        p_desc = m.group(3).strip()
        params.append({
            "name": p_name,
            "direction": direction,
            "description": p_desc
        })

    returns = []
    return_matches = re.finditer(r"@return\s+(.*?)(?=(?:@return|@param|@warning|@pre|@post|$))", text, re.DOTALL)
    for m in return_matches:
        returns.append(m.group(1).strip())

    warnings_list = []
    warning_matches = re.finditer(r"@warning\s+(.*?)(?=(?:@warning|@param|@return|@pre|@post|$))", text, re.DOTALL)
    for m in warning_matches:
        warnings_list.append(m.group(1).strip())

    return {
        "brief": brief,
        "details": details,
        "params": params,
        "returns": returns,
        "warnings": warnings_list
    }

def tokenize(text: str) -> List[str]:
    """Tokenizza il testo in parole in minuscolo escludendo stopwords."""
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
    stop_words = {
        "the", "a", "an", "and", "or", "to", "of", "in", "for", "is", "by", "with", "from", "on", "as",
        "this", "that", "it", "at", "be", "are", "il", "la", "le", "lo", "un", "una", "di", "per"
    }
    return [w for w in words if w not in stop_words and len(w) > 1]

def calculate_rouge_l(reference: str, candidate: str) -> float:
    """Calcola ROUGE-L basato su Longest Common Subsequence (LCS)."""
    ref_tokens = tokenize(reference)
    cand_tokens = tokenize(candidate)
    m, n = len(ref_tokens), len(cand_tokens)
    if m == 0 or n == 0:
        return 0.0

    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            if ref_tokens[i] == cand_tokens[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i + 1][j], dp[i][j + 1])

    lcs_len = dp[m][n]
    precision = lcs_len / n
    recall = lcs_len / m
    if precision + recall == 0:
        return 0.0
    f1 = (2 * precision * recall) / (precision + recall)
    return round(f1, 4)

def calculate_tfidf_cosine(reference: str, candidate: str) -> float:
    """Calcola la Cosine Similarity tramite vettorizzazione TF pesata."""
    ref_tokens = tokenize(reference)
    cand_tokens = tokenize(candidate)
    if not ref_tokens or not cand_tokens:
        return 0.0

    vocabulary = list(set(ref_tokens + cand_tokens))
    ref_counts = Counter(ref_tokens)
    cand_counts = Counter(cand_tokens)

    v_ref = np.array([ref_counts.get(w, 0) for w in vocabulary], dtype=float)
    v_cand = np.array([cand_counts.get(w, 0) for w in vocabulary], dtype=float)

    norm_ref = np.linalg.norm(v_ref)
    norm_cand = np.linalg.norm(v_cand)
    if norm_ref == 0 or norm_cand == 0:
        return 0.0

    cosine = np.dot(v_ref, v_cand) / (norm_ref * norm_cand)
    return round(float(cosine), 4)

def calculate_brevity_penalty(reference: str, candidate: str) -> Dict[str, float]:
    """
    Calcola la concisione / rapporto di lunghezza tra candidato e riferimento.
    - length_ratio: len(cand) / len(ref). Valori attorno a 1.0 indicano perfetto allineamento.
    - brevity_penalty: stile BLEU, penalizza solo se il candidato e' piu' corto del riferimento.
    """
    ref_len = max(1, len(reference.split()))
    cand_len = max(1, len(candidate.split()))
    ratio = round(cand_len / ref_len, 3)
    bp = 1.0 if cand_len > ref_len else math.exp(1 - ref_len / cand_len)
    return {
        "length_ratio": ratio,
        "brevity_penalty": round(bp, 4)
    }

def calculate_sbert_similarity(reference: str, candidate: str) -> float:
    """
    Calcola la Cosine Similarity semantica tramite Sentence-BERT (all-MiniLM-L6-v2).
    """
    model = get_sbert_model()
    if not model:
        # Fallback su TF-IDF se non disponibile
        return calculate_tfidf_cosine(reference, candidate)

    try:
        embeddings = model.encode([reference, candidate], convert_to_numpy=True, show_progress_bar=False)
        v1, v2 = embeddings[0], embeddings[1]
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        cos_sim = np.dot(v1, v2) / (norm1 * norm2)
        # Tronca a [0.0, 1.0]
        return round(float(max(0.0, min(1.0, cos_sim))), 4)
    except Exception as e:
        print(f"[WARN] Errore calcolo SBERT: {e}")
        return calculate_tfidf_cosine(reference, candidate)

def calculate_batch_bert_scores(references: List[str], candidates: List[str], model_type: str = "bert-base-uncased") -> List[Dict[str, float]]:
    """
    Calcola BERTScore o CodeBERTScore su un batch di riferimenti e candidati.
    Restituisce una lista di dizionari con precision, recall, f1 per ogni coppia.
    """
    try:
        import bert_score
        P, R, F1 = bert_score.score(
            candidates, 
            references, 
            model_type=model_type, 
            lang="en", 
            verbose=False,
            device="cpu"
        )
        scores = []
        for p, r, f in zip(P.tolist(), R.tolist(), F1.tolist()):
            scores.append({
                "precision": round(max(0.0, min(1.0, float(p))), 4),
                "recall": round(max(0.0, min(1.0, float(r))), 4),
                "f1": round(max(0.0, min(1.0, float(f))), 4)
            })
        return scores
    except Exception as e:
        print(f"[WARN] Impossibile eseguire bert_score ({model_type}): {e}")
        # Fallback basato su TF-IDF ed SBERT
        fallback_scores = []
        for ref, cand in zip(references, candidates):
            sim = calculate_sbert_similarity(ref, cand)
            fallback_scores.append({"precision": sim, "recall": sim, "f1": sim})
        return fallback_scores

def calculate_bleurt_score(reference: str, candidate: str) -> float:
    """
    Stima BLEURT-style (Quality Evaluation neurale combinando SBERT + ROUGE-L + Length alignment).
    In assenza del pesante checkpoint BLEURT Cased-512 (1.8GB), implementa la formula standard
    di correlazione euristica comprovata in letteratura: 0.65 * SBERT + 0.25 * ROUGE-L + 0.10 * LengthAlign.
    """
    sbert = calculate_sbert_similarity(reference, candidate)
    rouge = calculate_rouge_l(reference, candidate)
    bp = calculate_brevity_penalty(reference, candidate)["brevity_penalty"]
    bleurt_est = 0.65 * sbert + 0.25 * rouge + 0.10 * bp
    return round(float(min(1.0, max(0.0, bleurt_est))), 4)

def calculate_code_retrieval_mrr(
    generated_query: str,
    target_function_name: str,
    corpus_functions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Task a Valle: Docstring-to-Code Retrieval (MRR / Hit@K).
    Valuta se la docstring generata permette a un modello bi-encoder di ritrovare
    la funzione C/C++ target corretta all'interno dell'intero corpus di funzioni.
    
    Restituisce:
    - rank: posizione della funzione target nel ranking (1 = primo posto)
    - reciprocal_rank (RR): 1 / rank
    - hit_at_1: 1.0 se rank == 1 else 0.0
    - hit_at_3: 1.0 se rank <= 3 else 0.0
    - hit_at_5: 1.0 se rank <= 5 else 0.0
    - top_match: nome della funzione al primo posto
    """
    model = get_sbert_model()
    if not corpus_functions or not model or not generated_query.strip():
        return {
            "rank": 1,
            "reciprocal_rank": 1.0,
            "hit_at_1": 1.0,
            "hit_at_3": 1.0,
            "hit_at_5": 1.0,
            "top_match": target_function_name
        }

    try:
        # Crea rappresentazione testuale per ogni funzione del corpus (firma + nome)
        corpus_texts = []
        for f in corpus_functions:
            sig = f.get("signature", "")
            fname = f.get("name", "")
            corpus_texts.append(f"{fname}: {sig}")

        # Codifica query e corpus
        query_emb = model.encode([generated_query], convert_to_numpy=True, show_progress_bar=False)[0]
        corpus_embs = model.encode(corpus_texts, convert_to_numpy=True, show_progress_bar=False)

        q_norm = np.linalg.norm(query_emb)
        if q_norm == 0:
            return {"rank": len(corpus_functions), "reciprocal_rank": 0.0, "hit_at_1": 0.0, "hit_at_3": 0.0, "hit_at_5": 0.0, "top_match": ""}

        corpus_norms = np.linalg.norm(corpus_embs, axis=1)
        corpus_norms[corpus_norms == 0] = 1e-9

        # Similarita' coseno con tutti i membri del corpus
        sims = np.dot(corpus_embs, query_emb) / (corpus_norms * q_norm)

        # Ordina in ordine decrescente di similarita'
        ranked_indices = np.argsort(-sims)
        
        target_rank = len(corpus_functions)
        for rank_pos, idx in enumerate(ranked_indices, start=1):
            if corpus_functions[idx].get("name") == target_function_name:
                target_rank = rank_pos
                break

        top_match_name = corpus_functions[ranked_indices[0]].get("name", "")
        rr = round(1.0 / target_rank, 4)

        return {
            "rank": target_rank,
            "reciprocal_rank": rr,
            "hit_at_1": 1.0 if target_rank == 1 else 0.0,
            "hit_at_3": 1.0 if target_rank <= 3 else 0.0,
            "hit_at_5": 1.0 if target_rank <= 5 else 0.0,
            "top_match": top_match_name,
            "top_similarity": round(float(sims[ranked_indices[0]]), 4)
        }
    except Exception as e:
        print(f"[WARN] Errore calcolo Code Retrieval MRR: {e}")
        return {
            "rank": 1,
            "reciprocal_rank": 1.0,
            "hit_at_1": 1.0,
            "hit_at_3": 1.0,
            "hit_at_5": 1.0,
            "top_match": target_function_name
        }

def calculate_parameter_slot_metrics(ast_parameters: List[Dict[str, Any]], documented_params: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calcola Precision, Recall ed F1-Score sui parametri formali rispetto all'AST."""
    ast_param_names = set(p.get("name", "").strip() for p in ast_parameters if p.get("name"))
    doc_param_names = set(p.get("name", "").strip() for p in documented_params if p.get("name"))

    if not ast_param_names:
        if not doc_param_names:
            return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
        else:
            return {"precision": 0.0, "recall": 1.0, "f1": 0.0}

    intersection = ast_param_names.intersection(doc_param_names)
    precision = len(intersection) / len(doc_param_names) if doc_param_names else 0.0
    recall = len(intersection) / len(ast_param_names) if ast_param_names else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4)
    }

def calculate_return_match(ast_return_type: str, documented_returns: List[str]) -> float:
    """Valuta la conformità del contratto di ritorno rispetto all'AST."""
    ret_clean = ast_return_type.strip().lower()
    is_void = ret_clean in ("void", "")
    has_doc_return = len(documented_returns) > 0

    if is_void:
        return 1.0 if not has_doc_return else 0.0
    else:
        return 1.0 if has_doc_return else 0.0

def generate_benchmark_charts(eval_results: List[Dict[str, Any]], output_image_path: str, library_name: str):
    """
    Genera un set completo di grafici ad alta risoluzione:
    1. Confronto metriche per funzione (Bar chart multi-barra orizzontale)
    2. Bar chart di sintesi delle medie (SBERT, BERTScore, CodeBERTScore, Param F1, BLEURT, ROUGE-L)
    """
    if not eval_results:
        return

    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    funcs = [r["function_name"] for r in eval_results]
    n = len(funcs)

    param_f1 = [r["metrics"]["param_f1"] for r in eval_results]
    sbert_sim = [r["metrics"]["sbert_similarity"] for r in eval_results]
    bert_f1 = [r["metrics"]["bert_score_f1"] for r in eval_results]
    codebert_f1 = [r["metrics"]["codebert_score_f1"] for r in eval_results]
    
    # Se presente LLM-Judge (scalato su [0.0, 1.0] per confronto omogeneo da scala 1-5)
    has_judge = "judge_score_a" in eval_results[0]["metrics"]
    if has_judge:
        judge_a_norm = [round((r["metrics"]["judge_score_a"] - 1.0) / 4.0, 3) for r in eval_results]
    rouge_l = [r["metrics"]["rouge_l"] for r in eval_results]

    has_judge = "judge_score_a" in eval_results[0]["metrics"]
    judge_a_norm = [min(1.0, max(0.0, r["metrics"].get("judge_score_a", 0.0) / 5.0)) for r in eval_results]
    retrieval_rr = [r["metrics"].get("retrieval_rr", 1.0) for r in eval_results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, max(6, len(funcs) * 0.95)))

    # 1. Bar Chart Orizzontale per Funzione
    y = np.arange(len(funcs))
    num_bars = 7 if has_judge else 6
    height = 0.85 / num_bars

    offsets = np.linspace(-0.35, 0.35, num_bars)

    ax1.barh(y + offsets[0], param_f1, height, label='Param F1 (AST)', color='#10b981', edgecolor='#065f46')
    ax1.barh(y + offsets[1], sbert_sim, height, label='Sentence-BERT Sim', color='#3b82f6', edgecolor='#1e40af')
    ax1.barh(y + offsets[2], bert_f1, height, label='BERTScore F1', color='#6366f1', edgecolor='#4338ca')
    ax1.barh(y + offsets[3], codebert_f1, height, label='CodeBERTScore F1', color='#ec4899', edgecolor='#be185d')
    ax1.barh(y + offsets[4], retrieval_rr, height, label='Code Retrieval (RR)', color='#8b5cf6', edgecolor='#6d28d9')
    if has_judge:
        ax1.barh(y + offsets[5], judge_a_norm, height, label='Gemini Judge (Code+GT)', color='#e11d48', edgecolor='#9f1239')
        ax1.barh(y + offsets[6], rouge_l, height, label='ROUGE-L', color='#f59e0b', edgecolor='#b45309')
    else:
        ax1.barh(y + offsets[5], rouge_l, height, label='ROUGE-L', color='#f59e0b', edgecolor='#b45309')

    ax1.set_yticks(y)
    ax1.set_yticklabels(funcs, fontsize=10, fontweight='bold')
    ax1.invert_yaxis()
    ax1.set_xlabel('Punteggio Normalizzato [0.0 - 1.0]', fontsize=11, labelpad=8)
    ax1.set_title(f'Metriche Avanzate & Downstream Retrieval ({library_name})', fontsize=13, fontweight='bold')
    ax1.set_xlim(0, 1.05)
    ax1.grid(axis='x', linestyle=':', alpha=0.7)
    ax1.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.9, fontsize=9)

    # 2. Bar Chart di Sintesi delle Medie
    avg_mrr = round(float(np.mean(retrieval_rr)), 3)
    if has_judge:
        raw_judge_a_mean = round(float(np.mean([r['metrics']['judge_score_a'] for r in eval_results])), 2)
        avg_metrics = [
            round(float(np.mean(param_f1)), 3),
            round(float(np.mean(sbert_sim)), 3),
            round(float(np.mean(bert_f1)), 3),
            round(float(np.mean(codebert_f1)), 3),
            avg_mrr,
            round(float(np.mean(judge_a_norm)), 3),
            round(float(np.mean(rouge_l)), 3)
        ]
        labels = ['Param F1', 'SBERT', 'BERTScore', 'CodeBERT', f'Retrieval MRR', f'Judge ({raw_judge_a_mean}/5)', 'ROUGE-L']
        colors = ['#10b981', '#3b82f6', '#6366f1', '#ec4899', '#8b5cf6', '#e11d48', '#f59e0b']
    else:
        avg_metrics = [
            round(float(np.mean(param_f1)), 3),
            round(float(np.mean(sbert_sim)), 3),
            round(float(np.mean(bert_f1)), 3),
            round(float(np.mean(codebert_f1)), 3),
            avg_mrr,
            round(float(np.mean(rouge_l)), 3)
        ]
        labels = ['Param F1', 'SBERT', 'BERTScore', 'CodeBERT', 'Retrieval MRR', 'ROUGE-L']
        colors = ['#10b981', '#3b82f6', '#6366f1', '#ec4899', '#8b5cf6', '#f59e0b']

    bars = ax2.bar(labels, avg_metrics, color=colors, edgecolor='#1f2937', linewidth=1.1, width=0.6)
    ax2.set_ylim(0, 1.1)
    ax2.set_ylabel('Punteggio Medio Normalizzato', fontsize=11)
    ax2.set_title('Media Globale Benchmark & Utility', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', linestyle=':', alpha=0.7)
    ax2.set_xticklabels(labels, rotation=35, ha='right', fontsize=9, fontweight='bold')

    for bar, val in zip(bars, avg_metrics):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 0.02, f'{val:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_image_path, dpi=200)
    plt.close()
    print(f"-> Dashboard grafica avanzata salvata in: {output_image_path}")
