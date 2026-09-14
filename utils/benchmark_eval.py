"""
Script per il Benchmark e la Valutazione della Documentazione Generata vs Ground Truth.
Permette di:
1. Scegliere la libreria da valutare (cJSON o OpenCV).
2. Impostare un limite al numero di funzioni (per rapidita' e controllo quota).
3. Scegliere la modalita' di generazione (Ibrida Standard o Multi-Agente).
4. Generare la documentazione tramite la pipeline LLM e validarla con Verifier.
5. Calcolare metriche quantitative di aderenza alla documentazione originale (Ground Truth):
   - Token Overlap / Jaccard Similarity
   - Copertura e precisione dei parametri (@param vs doc originale)
   - Correttezza complessita' temporale e spaziale rispetto all'AST
6. Esportare un report comparativo dettagliato sia in Markdown che in JSON.
"""

import os
import sys
import json
import sqlite3
import argparse
import re
from typing import List, Dict, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.llm_provider import GeminiLLMProvider, MockLLMProvider
from src.agents.reader_agent import ReaderAgent
from src.agents.searcher_agent import SearcherAgent
from src.agents.writer_agent import WriterAgent
from src.verifier import DocumentationVerifier

DB_PATH = os.path.join(ROOT_DIR, "dataset", "benchmark.db")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")


class MockMemoryDB:
    """Mock DB per fornire contesti vuoti al SearcherAgent durante i test individuali."""
    def get_callees_summaries(self, callees: List[str]):
        return []


def tokenize(text: str) -> set:
    if not text:
        return set()
    words = re.findall(r"\b\w+\b", text.lower())
    stop_words = {"the", "a", "an", "and", "or", "to", "of", "in", "for", "is", "by", "with", "from",
                  "il", "la", "le", "lo", "un", "una", "di", "a", "da", "in", "con", "su", "per", "tra", "fra"}
    return {w for w in words if w not in stop_words and len(w) > 1}


def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    t1 = tokenize(text1)
    t2 = tokenize(text2)
    if not t1 or not t2:
        return 0.0
    intersection = t1.intersection(t2)
    union = t1.union(t2)
    return round(len(intersection) / len(union), 4)


def calculate_token_recall(reference: str, candidate: str) -> float:
    ref_tokens = tokenize(reference)
    cand_tokens = tokenize(candidate)
    if not ref_tokens:
        return 0.0
    common = ref_tokens.intersection(cand_tokens)
    return round(len(common) / len(ref_tokens), 4)


def get_benchmark_candidates(library: str, limit: int, require_ground_truth: bool = True) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = """
        SELECT id, library, language, filename, function_name, signature,
               return_type, parameters, source_code, raw_comment, cleaned_doc,
               time_complexity, space_complexity
        FROM benchmark_functions
        WHERE LOWER(library) = LOWER(?)
    """
    if require_ground_truth:
        query += " AND length(cleaned_doc) > 0"
    query += " ORDER BY id LIMIT ?"

    cur.execute(query, (library, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    for r in rows:
        try:
            r["parameters"] = json.loads(r["parameters"])
        except Exception:
            r["parameters"] = []

    return rows


def run_evaluation(library: str = "cJSON", limit: int = 5, mode: str = "single", use_mock: bool = False, language: str = "en", roundtrip: bool = False):
    print("=" * 65)
    print(f"  BENCHMARK EVALUATION: {library.upper()} (Language: {language.upper()})")
    print(f"  Modalita': {mode.upper()} | Limite: {limit} funzioni")
    if roundtrip:
        print("  Round-Trip Differential Testing (Pytest): ATTIVO")
    print("=" * 65)

    candidates = get_benchmark_candidates(library, limit)
    if not candidates:
        print(f"[ERRORE] Nessuna funzione trovata per {library} con documentazione originale.")
        return

    print(f"Caricate {len(candidates)} funzioni con Ground Truth dal dataset.\n")

    # Inizializzazione LLM Provider
    api_key = os.getenv("GEMINI_API_KEY")
    if not use_mock and api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
        print("[LLM] Uso di GeminiLLMProvider (gemini-3.5-flash-lite)...")
        llm = GeminiLLMProvider(model_name="gemini-3.5-flash-lite", api_key=api_key, rpm_limit=15)
    else:
        print("[LLM] Uso di MockLLMProvider...")
        llm = MockLLMProvider()

    # Inizializzazione Pipeline Agenti
    reader_agent = ReaderAgent(llm)
    searcher_agent = SearcherAgent(MockMemoryDB())
    writer_agent = WriterAgent(llm)

    # Inizializzazione Verifier e Corpus Retrieval: carica funzioni dal DB ed estrae enums/macros dagli header
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT function_name, signature FROM benchmark_functions WHERE LOWER(library) = LOWER(?)", (library,))
    all_db_rows = cur.fetchall()
    conn.close()

    library_known_functions = [{"name": r[0]} for r in all_db_rows]
    corpus_functions = [{"name": r[0], "signature": r[1] or ""} for r in all_db_rows]

    # Estrazione simboli reali (enum, macro, typedef, struct) dagli header sorgente della libreria
    library_enums = []
    library_structs = []
    library_macros = []
    library_typedefs = []

    lib_source_dir = os.path.join(ROOT_DIR, "dataset", "sources", library)
    if os.path.exists(lib_source_dir):
        from src.extract_metadata import CCodeExtractor
        extractor = CCodeExtractor()
        for header_file in os.listdir(lib_source_dir):
            if header_file.endswith((".h", ".hpp")):
                h_path = os.path.join(lib_source_dir, header_file)
                try:
                    extra_args = ['-x', 'c++'] if library != "cJSON" else None
                    meta_h = extractor.extract_metadata(h_path, include_dirs=[lib_source_dir], extra_args=extra_args)
                    library_enums.extend(meta_h.get("enums", []))
                    library_structs.extend(meta_h.get("structs", []))
                    library_macros.extend(meta_h.get("macros", []))
                    library_typedefs.extend(meta_h.get("typedefs", []))
                except Exception as e:
                    pass

    dummy_meta = {
        "benchmark": {
            "functions": library_known_functions,
            "enums": library_enums,
            "structs": library_structs,
            "macros": library_macros,
            "typedefs": library_typedefs
        }
    }
    verifier = DocumentationVerifier(dummy_meta)

    item_by_name = {c["function_name"]: c for c in candidates}
    eval_results = []
    
    for idx, item in enumerate(candidates, 1):
        fname = item["function_name"]
        sig = item["signature"]
        code = item["source_code"]
        gt_doc = item["cleaned_doc"]

        print(f"[{idx}/{len(candidates)}] Generazione doc per: {fname}...")

        # Generazione Documentazione
        if mode == "multiagent":
            reader_facts = reader_agent.analyze_function(
                func_name=fname,
                signature=sig,
                source_code=code,
                raw_comment=item.get("raw_comment")
            )
            enriched_ctx = searcher_agent.enrich_context(reader_facts, [])
            gen_doc = writer_agent.write_documentation(
                enriched_context=enriched_ctx,
                source_code=code
            )
        else:
            gen_doc = llm.generate_documentation(
                func_name=fname,
                signature=sig,
                source_code=code,
                callees_summaries=[],
                raw_comment=item.get("raw_comment"),
                language=language
            )

        # Validazione Verifier
        func_info_for_verifier = {
            "name": fname,
            "return_type": item["return_type"],
            "parameters": item["parameters"],
            "time_complexity": item["time_complexity"],
            "space_complexity": item["space_complexity"]
        }
        val_res = verifier.verify_function_doc(func_info_for_verifier, gen_doc)

        brief_summary = gen_doc.get("brief_summary", "")
        doxygen_block = gen_doc.get("full_doxygen_doc") or gen_doc.get("doxygen_block", "")
        
        # 1. Parsing strutturato Doxygen
        from utils.benchmark_metrics import (
            parse_doxygen_block,
            calculate_tfidf_cosine,
            calculate_rouge_l,
            calculate_parameter_slot_metrics,
            calculate_return_match,
            calculate_sbert_similarity,
            calculate_brevity_penalty,
            calculate_bleurt_score,
            calculate_code_retrieval_mrr,
            calculate_batch_bert_scores,
            generate_benchmark_charts
        )
        parsed_doc = parse_doxygen_block(doxygen_block)

        # 2. Ramo Semantico/Descrizione: confronta GT con @brief + @details (senza tag o boilerplate)
        generated_description = f"{brief_summary} {parsed_doc.get('brief', '')} {parsed_doc.get('details', '')}".strip()
        
        tfidf_sim = calculate_tfidf_cosine(gt_doc, generated_description)
        rouge_l_score = calculate_rouge_l(gt_doc, generated_description)
        jaccard = calculate_jaccard_similarity(gt_doc, generated_description)
        recall = calculate_token_recall(gt_doc, generated_description)
        sbert_sim = calculate_sbert_similarity(gt_doc, generated_description)
        brevity_info = calculate_brevity_penalty(gt_doc, generated_description)
        bleurt_val = calculate_bleurt_score(gt_doc, generated_description)

        # 3. Ramo Task a Valle: Code Retrieval (MRR / Hit@K)
        # Interroga l'intero corpus di funzioni della libreria usando la descrizione generata
        retrieval_res = calculate_code_retrieval_mrr(
            generated_query=generated_description,
            target_function_name=fname,
            corpus_functions=corpus_functions
        )

        # 4. Ramo Strutturato/Contratti: Slot-Filling parametri & return vs AST
        param_slot = calculate_parameter_slot_metrics(item["parameters"], parsed_doc.get("params", []))
        return_match_score = calculate_return_match(item["return_type"], parsed_doc.get("returns", []))

        eval_results.append({
            "id": item["id"],
            "function_name": fname,
            "signature": sig,
            "source_code": code,
            "ground_truth": gt_doc,
            "generated_summary": brief_summary,
            "generated_description": generated_description,
            "generated_doxygen": doxygen_block,
            "is_valid": val_res.get("is_valid", False),
            "verifier_errors": val_res.get("errors", []),
            "parsed_components": {
                "documented_params": [p["name"] for p in parsed_doc.get("params", [])],
                "ast_params": [p.get("name") for p in item["parameters"] if p.get("name")],
                "has_return_doc": len(parsed_doc.get("returns", [])) > 0
            },
            "retrieval": retrieval_res,
            "metrics": {
                "param_f1": param_slot["f1"],
                "param_precision": param_slot["precision"],
                "param_recall": param_slot["recall"],
                "return_match": return_match_score,
                "retrieval_rr": retrieval_res["reciprocal_rank"],
                "hit_at_1": retrieval_res["hit_at_1"],
                "hit_at_5": retrieval_res["hit_at_5"],
                "sbert_similarity": sbert_sim,
                "bert_score_f1": 0.0,      # popolato in batch sotto
                "bert_score_precision": 0.0,
                "bert_score_recall": 0.0,
                "codebert_score_f1": 0.0,  # popolato in batch sotto
                "codebert_score_precision": 0.0,
                "codebert_score_recall": 0.0,
                "bleurt_score": bleurt_val,
                "length_ratio": brevity_info["length_ratio"],
                "brevity_penalty": brevity_info["brevity_penalty"],
                "tfidf_similarity": tfidf_sim,
                "rouge_l": rouge_l_score,
                "jaccard_similarity": jaccard,
                "ground_truth_recall": recall
            }
        })

    # Calcolo Batch BERTScore e CodeBERTScore su CPU per efficienza
    print("\n[INFO METRICHE] Calcolo BERTScore e CodeBERTScore in corso...")
    all_refs = [r["ground_truth"] for r in eval_results]
    all_cands = [r["generated_description"] for r in eval_results]

    # Standard BERTScore
    try:
        bert_scores = calculate_batch_bert_scores(all_refs, all_cands, model_type="bert-base-uncased")
        for r, bs in zip(eval_results, bert_scores):
            r["metrics"]["bert_score_precision"] = bs["precision"]
            r["metrics"]["bert_score_recall"] = bs["recall"]
            r["metrics"]["bert_score_f1"] = bs["f1"]
    except Exception as e:
        print(f"[WARN] Salto BERTScore: {e}")

    # CodeBERTScore (specializzato su linguaggi di programmazione)
    try:
        codebert_scores = calculate_batch_bert_scores(all_refs, all_cands, model_type="microsoft/codebert-base")
        for r, cs in zip(eval_results, codebert_scores):
            r["metrics"]["codebert_score_precision"] = cs["precision"]
            r["metrics"]["codebert_score_recall"] = cs["recall"]
            r["metrics"]["codebert_score_f1"] = cs["f1"]
    except Exception as e:
        print(f"[WARN] Salto CodeBERTScore: {e}")

    # Calcolo LLM-as-a-Judge con Gemini (5 iterazioni Prospettiva A e 5 Prospettiva B)
    if not use_mock and api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
        print("\n[INFO METRICHE] Avvio LLM-as-a-Judge con Gemini (5 rounds per funzione, Temp=0.4)...")
        from utils.llm_judge import GeminiJudgeEvaluator
        judge = GeminiJudgeEvaluator(model_name="gemini-3.5-flash-lite", api_key=api_key, temperature=0.4)
        
        try:
            from tqdm import tqdm
            func_pbar = tqdm(eval_results, desc="[LLM-Judge Funzioni]", unit="func")
        except ImportError:
            func_pbar = eval_results

        for idx, r in enumerate(func_pbar, 1):
            fname = r["function_name"]
            if hasattr(func_pbar, "set_description"):
                func_pbar.set_description(f"[LLM-Judge] {fname[:25]}")
            else:
                print(f"  [{idx}/{len(eval_results)}] Giudizio per: {fname}...")

            judge_res = judge.run_multi_round_evaluation(
                func_name=fname,
                signature=r["signature"],
                source_code=item_by_name[fname]["source_code"],
                ground_truth=r["ground_truth"],
                generated_doc=f"{r['generated_summary']}\n{r['generated_doxygen']}",
                rounds=5
            )
            r["metrics"]["judge_score_a"] = judge_res["perspective_a"]["mean"]
            r["metrics"]["judge_std_a"] = judge_res["perspective_a"]["std"]
            r["metrics"]["judge_score_b"] = judge_res["perspective_b"]["mean"]
            r["metrics"]["judge_std_b"] = judge_res["perspective_b"]["std"]
            r["metrics"]["judge_combined"] = judge_res["combined_score"]
            r["judge_details"] = judge_res

    # Esecuzione opzionale Round-Trip Differential Testing (se specificato flag --roundtrip)
    if roundtrip and not use_mock and api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
        print("\n[INFO METRICHE] Avvio Round-Trip Differential Testing (Doc-to-Code & Pytest)...")
        from utils.roundtrip_eval import RoundTripEvaluator
        rt_evaluator = RoundTripEvaluator(llm_provider=llm)
        for r in eval_results:
            fname = r["function_name"]
            sig = r["signature"]
            doc = f"{r['generated_summary']}\n{r['generated_doxygen']}"
            print(f"  -> Dual Round-Trip test per: {fname}...")
            rt_res = rt_evaluator.evaluate_function_roundtrip(fname, sig, doc, source_code=r.get("source_code", ""))
            r["roundtrip"] = rt_res
            r["metrics"]["roundtrip_pass_rate"] = rt_res["execution"]["pass_rate"]

    # Output cartella
    benchmark_dir = os.path.join(RESULTS_DIR, f"benchmark_{library.lower()}")
    os.makedirs(benchmark_dir, exist_ok=True)
    json_path = os.path.join(benchmark_dir, f"eval_report_{mode}.json")
    md_path = os.path.join(benchmark_dir, f"eval_report_{mode}.md")
    chart_path = os.path.join(benchmark_dir, f"eval_charts_{mode}.png")

    # Generazione Grafico Visuale Matplotlib
    generate_benchmark_charts(eval_results, chart_path, library_name=library)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2, ensure_ascii=False)

    # Scrittura report Markdown
    write_markdown_report(md_path, library, mode, eval_results, chart_filename=os.path.basename(chart_path))

    print("\n" + "=" * 65)
    print("  VALUTAZIONE BENCHMARK COMPLETATA CON SUCCESSO!")
    print(f"  Report Markdown: {md_path}")
    print(f"  Grafici Visuali: {chart_path}")
    print(f"  Dati JSON:       {json_path}")
    print("=" * 65)


def write_markdown_report(md_path: str, library: str, mode: str, results: List[Dict[str, Any]], chart_filename: str = ""):
    n_res = len(results)
    avg_param_f1 = round(sum(r["metrics"]["param_f1"] for r in results) / n_res, 4) if n_res else 0
    avg_return_match = round(sum(r["metrics"]["return_match"] for r in results) / n_res, 4) if n_res else 0
    avg_sbert = round(sum(r["metrics"]["sbert_similarity"] for r in results) / n_res, 4) if n_res else 0
    avg_bert_f1 = round(sum(r["metrics"]["bert_score_f1"] for r in results) / n_res, 4) if n_res else 0
    avg_codebert_f1 = round(sum(r["metrics"]["codebert_score_f1"] for r in results) / n_res, 4) if n_res else 0
    
    has_judge = "judge_score_a" in results[0]["metrics"]
    if has_judge:
        avg_judge_a = round(sum(r["metrics"]["judge_score_a"] for r in results) / n_res, 3)
        avg_judge_b = round(sum(r["metrics"]["judge_score_b"] for r in results) / n_res, 3)
        avg_judge_comb = round(sum(r["metrics"]["judge_combined"] for r in results) / n_res, 3)
    else:
        avg_judge_a = avg_judge_b = avg_judge_comb = 0.0

    avg_bleurt = round(sum(r["metrics"]["bleurt_score"] for r in results) / n_res, 4) if n_res else 0
    avg_tfidf = round(sum(r["metrics"]["tfidf_similarity"] for r in results) / n_res, 4) if n_res else 0
    avg_rouge_l = round(sum(r["metrics"]["rouge_l"] for r in results) / n_res, 4) if n_res else 0
    avg_recall = round(sum(r["metrics"]["ground_truth_recall"] for r in results) / n_res, 4) if n_res else 0
    
    # Metriche Task a Valle: Code Retrieval
    avg_mrr = round(sum(r["metrics"].get("retrieval_rr", 0.0) for r in results) / n_res, 4) if n_res else 0
    avg_hit1 = round(sum(r["metrics"].get("hit_at_1", 0.0) for r in results) / n_res, 4) if n_res else 0
    avg_hit5 = round(sum(r["metrics"].get("hit_at_5", 0.0) for r in results) / n_res, 4) if n_res else 0

    valid_count = sum(1 for r in results if r["is_valid"])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Report Benchmark Documentazione: {library}\n\n")
        f.write(f"- **Libreria**: `{library}`\n")
        f.write(f"- **Modalita' Pipeline**: `{mode}`\n")
        f.write(f"- **Funzioni Valutate**: {n_res}\n")
        f.write(f"- **Funzioni Valide al Verifier**: {valid_count}/{n_res} ({round(valid_count/n_res*100, 1)}%)\n")
        f.write(f"- **Parameter F1-Score Medio (vs AST)**: `{avg_param_f1}`\n")
        f.write(f"- **Return Contract Match Medio**: `{avg_return_match}`\n")
        if has_judge:
            f.write(f"- **LLM-Judge Faithfulness (Code+GT vs Doc) [1-5]**: `{avg_judge_a}/5.0`\n")
            f.write(f"- **LLM-Judge Alignment (GT vs Doc) [1-5]**: `{avg_judge_b}/5.0`\n")
            f.write(f"- **LLM-Judge Punteggio Combinato [1-5]**: `{avg_judge_comb}/5.0`\n")
        f.write(f"- **Downstream Code Retrieval MRR**: `{avg_mrr}` (Hit@1: `{round(avg_hit1*100, 1)}%`, Hit@5: `{round(avg_hit5*100, 1)}%`)\n")
        f.write(f"- **Sentence-BERT Cosine Similarity Media**: `{avg_sbert}`\n")
        f.write(f"- **BERTScore F1-Score Medio**: `{avg_bert_f1}`\n")
        f.write(f"- **CodeBERTScore F1-Score Medio**: `{avg_codebert_f1}`\n")
        f.write(f"- **BLEURT Quality Score Medio**: `{avg_bleurt}`\n")
        f.write(f"- **TF-IDF Cosine Similarity Media**: `{avg_tfidf}`\n")
        f.write(f"- **ROUGE-L Score Medio**: `{avg_rouge_l}`\n")
        f.write(f"- **Recall Chiavi Ground Truth Media**: `{avg_recall}`\n\n")

        if chart_filename:
            f.write("## 📈 Dashboard Grafica di Benchmark (Neural, Judge & AST Metrics)\n\n")
            f.write(f"![Metriche Benchmark]({chart_filename})\n\n")

        f.write("## 📋 Tabella Comparativa Completa (SBERT, BERTScore, LLM-Judge & AST)\n\n")
        if has_judge:
            f.write("| Funzione | Verifier | Param F1 | SBERT Sim | BERTScore | Judge (Code+GT) | Judge (GT) | Code Retrieval (Rank) |\n")
            f.write("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
            for r in results:
                status = "Sì" if r["is_valid"] else "No"
                j_a = f"{r['metrics']['judge_score_a']} ± {r['metrics']['judge_std_a']}"
                j_b = f"{r['metrics']['judge_score_b']} ± {r['metrics']['judge_std_b']}"
                ret_info = f"Rank #{r['retrieval']['rank']} (RR: {r['retrieval']['reciprocal_rank']})" if 'retrieval' in r else "N/A"
                f.write(f"| `{r['function_name']}` | {status} | **{r['metrics']['param_f1']}** | {r['metrics']['sbert_similarity']} | {r['metrics']['bert_score_f1']} | **{j_a}** | {j_b} | {ret_info} |\n")
        else:
            f.write("| Funzione | Verifier | Param F1 | SBERT Sim | BERTScore | CodeBERT | BLEURT | Code Retrieval (Rank) |\n")
            f.write("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
            for r in results:
                status = "Sì" if r["is_valid"] else "No"
                ret_info = f"Rank #{r['retrieval']['rank']} (RR: {r['retrieval']['reciprocal_rank']})" if 'retrieval' in r else "N/A"
                f.write(f"| `{r['function_name']}` | {status} | **{r['metrics']['param_f1']}** | {r['metrics']['sbert_similarity']} | {r['metrics']['bert_score_f1']} | {r['metrics']['codebert_score_f1']} | {r['metrics']['bleurt_score']} | {ret_info} |\n")

        f.write("\n## 🔍 Dettagli Funzione per Funzione\n\n")
        for r in results:
            f.write(f"### `{r['function_name']}`\n")
            f.write(f"- **Firma**: `{r['signature']}`\n")
            f.write(f"- **Metriche Contratti AST**: Param F1: `{r['metrics']['param_f1']}` (Precision: `{r['metrics']['param_precision']}`, Recall: `{r['metrics']['param_recall']}`) | Return Match: `{r['metrics']['return_match']}`\n")
            if has_judge and "judge_details" in r:
                jd = r["judge_details"]
                f.write(f"- **LLM Judge Faithfulness (Code+GT)**: `{r['metrics']['judge_score_a']} ± {r['metrics']['judge_std_a']}` / 5.0\n")
                f.write(f"  > *Motivazione Giudice*: {jd['perspective_a']['sample_reasoning']}\n")
                f.write(f"- **LLM Judge Alignment (GT only)**: `{r['metrics']['judge_score_b']} ± {r['metrics']['judge_std_b']}` / 5.0\n")
                f.write(f"  > *Motivazione Giudice*: {jd['perspective_b']['sample_reasoning']}\n")
            if "retrieval" in r:
                f.write(f"- **Task a Valle (Code Retrieval)**: Rank Target: `#{r['retrieval']['rank']}` | Reciprocal Rank: `{r['retrieval']['reciprocal_rank']}` | Hit@1: `{r['retrieval']['hit_at_1']}` | Top Match: `{r['retrieval']['top_match']}`\n")
            f.write(f"- **Metriche Semantiche Dense**: SBERT Sim: `{r['metrics']['sbert_similarity']}` | BERTScore F1: `{r['metrics']['bert_score_f1']}` | CodeBERTScore F1: `{r['metrics']['codebert_score_f1']}` | BLEURT: `{r['metrics']['bleurt_score']}`\n")
            f.write(f"- **Metriche Lessicali**: TF-IDF Sim: `{r['metrics']['tfidf_similarity']}` | ROUGE-L: `{r['metrics']['rouge_l']}` | GT Key Recall: `{r['metrics']['ground_truth_recall']}` | Length Ratio: `{r['metrics']['length_ratio']}`\n\n")
            f.write(f"- **Documentazione Originale (Ground Truth)**:\n> {r['ground_truth'].replace(chr(10), chr(10) + '> ')}\n\n")
            f.write(f"- **Breve Spiegazione LLM**: {r['generated_summary']}\n\n")
            f.write(f"- **Blocco Doxygen Generato**:\n```c\n{r['generated_doxygen']}\n```\n\n")
            if r["verifier_errors"]:
                f.write(f"- **Segnalazioni Verifier**: {', '.join(r['verifier_errors'])}\n\n")
            f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser(description="Valutazione Benchmark Documentazione Generata vs Ground Truth")
    parser.add_argument("-l", "--library", default="cJSON", choices=["cJSON", "OpenCV", "TinyXML-2"], help="Libreria su cui eseguire il test (default: cJSON)")
    parser.add_argument("-n", "--limit", type=int, default=5, help="Numero massimo di funzioni da documentare e confrontare (default: 5)")
    parser.add_argument("-m", "--mode", default="single", choices=["single", "multiagent"], help="Modalita': 'single' (Ibrido Standard) o 'multiagent'")
    parser.add_argument("--lang", default="en", choices=["en", "it"], help="Lingua per la documentazione LLM: 'en' (default) o 'it'")
    parser.add_argument("--roundtrip", action="store_true", help="Esegue anche la validazione Round-Trip (Doc-to-Code Synthesis & Pytest execution)")
    parser.add_argument("--mock", action="store_true", help="Forza l'uso del MockLLM senza effettuare chiamate API reali")

    args = parser.parse_args()
    run_evaluation(library=args.library, limit=args.limit, mode=args.mode, use_mock=args.mock, language=args.lang, roundtrip=args.roundtrip)


if __name__ == "__main__":
    main()
