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
from typing import List, Dict, Any, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.llm_provider import GeminiLLMProvider, MockLLMProvider
from src.agents.reader_agent import ReaderAgent
from src.agents.searcher_agent import SearcherAgent
from src.agents.writer_agent import WriterAgent
from src.verifier import DocumentationVerifier
from utils.roundtrip_error_analysis import (
    analyze_roundtrip_errors,
    save_roundtrip_error_report,
)

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


def get_benchmark_candidates(
    library: str,
    limit: int,
    require_ground_truth: bool = True,
    sampling: str = "sequential",
    seed: Optional[int] = None,
    min_loc: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Estrae le funzioni candidate per il benchmark dal database SQLite secondo 3 strategie:
    1. 'sequential' / 'first': prime N funzioni ordinate per ID (deterministico standard).
    2. 'random': campionamento casuale uniforme tra tutte le funzioni (con seed opzionale).
    3. 'stratified' / 'constrained': campionamento stratificato per quantili di lunghezza (LOC).
       Divide l'intero pool ordinato per LOC in N partizioni esponenziali/logaritmiche ed estrae
       una funzione per ciascun scaglione, garantendo una copertura perfetta da 1 a 100+ LOC.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    params = []
    if library.lower() in ("all", "*"):
        query = """
            SELECT id, library, language, filename, function_name, signature,
                   return_type, parameters, source_code, raw_comment, cleaned_doc,
                   time_complexity, space_complexity
            FROM benchmark_functions
            WHERE 1=1
        """
    else:
        query = """
            SELECT id, library, language, filename, function_name, signature,
                   return_type, parameters, source_code, raw_comment, cleaned_doc,
                   time_complexity, space_complexity
            FROM benchmark_functions
            WHERE LOWER(library) = LOWER(?)
        """
        params.append(library)

    if require_ground_truth:
        query += " AND length(cleaned_doc) > 0"

    cur.execute(query, tuple(params))
    all_rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    for r in all_rows:
        try:
            r["parameters"] = json.loads(r["parameters"])
        except Exception:
            r["parameters"] = []
        code = r.get("source_code", "")
        r["loc"] = len(code.splitlines()) if code else 1

    # Filtro opzionale su min_loc
    if min_loc is not None and min_loc > 1:
        filtered = [r for r in all_rows if r["loc"] >= min_loc]
        if filtered:
            all_rows = filtered
        else:
            print(f"[WARN] Nessuna funzione con LOC >= {min_loc}, mantengo il set completo.")

    if not all_rows:
        return []

    # 1. STRATIFIED QUANTILE SAMPLING (Casuale con Vincoli di Lunghezza)
    if sampling in ("stratified", "constrained", "loc", "quantiles"):
        import random
        import numpy as np

        # Ordina deterministicamente per LOC crescenti e ID come tie-break
        all_rows.sort(key=lambda x: (x["loc"], x["id"]))

        actual_limit = min(limit, len(all_rows))
        unique_locs = sorted(list(set(r["loc"] for r in all_rows)))
        
        # Generiamo N bin logaritmici per coprire armoniosamente da funzioni brevi a complesse
        min_v = max(1.0, float(min(unique_locs)))
        max_v = max(float(max(unique_locs)), min_v + 1.0)
        bins = np.logspace(np.log10(min_v), np.log10(max_v), actual_limit + 1)

        rng = random.Random(seed)
        selected = []
        for i in range(actual_limit):
            low = bins[i]
            high = bins[i + 1]
            # Candidati nel range attuale non ancora selezionati
            cands = [r for r in all_rows if (low <= r["loc"] <= high if i == actual_limit - 1 else low <= r["loc"] < high) and r not in selected]
            if not cands:
                # Se il bin è vuoto, prendi i candidati con LOC più vicina al punto mediano
                mid = (low + high) / 2.0
                remaining = [r for r in all_rows if r not in selected]
                remaining.sort(key=lambda r: abs(r["loc"] - mid))
                cands = remaining[:max(1, len(remaining) // actual_limit + 1)]
            
            chosen = rng.choice(cands)
            selected.append(chosen)

        return selected

    # 2. RANDOM SAMPLING (Casuale Puro)
    elif sampling in ("random", "uniform"):
        import random
        rng = random.Random(seed)
        return rng.sample(all_rows, min(limit, len(all_rows)))

    # 3. SEQUENTIAL / DETERMINISTIC (Prime N)
    else:
        all_rows.sort(key=lambda x: x["id"])
        return all_rows[:limit]


def run_evaluation(
    library: str = "cJSON",
    limit: int = 5,
    mode: str = "single",
    use_mock: bool = False,
    language: str = "en",
    roundtrip: bool = False,
    sampling: str = "sequential",
    seed: Optional[int] = None,
    min_loc: Optional[int] = None
):
    print("=" * 65)
    print(f"  BENCHMARK EVALUATION: {library.upper()} (Language: {language.upper()})")
    strat_desc = f"STRATIFICATA PER LOC (Vincoli di complessita', seed={seed})" if sampling == "stratified" else (f"CASUALE (seed={seed})" if sampling == "random" else "SEQUENZIALE (Prime N)")
    print(f"  Modalita': {mode.upper()} | Limite: {limit} funzioni | Campionamento: {strat_desc}")
    if min_loc:
        print(f"  Filtro Complessita': LOC minime >= {min_loc}")
    if roundtrip:
        print("  Round-Trip Differential Testing (Pytest): ATTIVO")
    print("=" * 65)

    candidates = get_benchmark_candidates(library, limit, sampling=sampling, seed=seed, min_loc=min_loc)
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
    from src.agents.judge_agent import JudgeAgent
    judge_agent = JudgeAgent(llm)

    # Inizializzazione Verifier e Corpus Retrieval: carica funzioni dal DB ed estrae enums/macros dagli header
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if library.lower() in ("all", "*"):
        cur.execute("SELECT DISTINCT function_name, signature FROM benchmark_functions")
    else:
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

    libs_to_scan = [d for d in os.listdir(os.path.join(ROOT_DIR, "dataset", "sources"))] if library.lower() in ("all", "*") else [library]
    from src.extract_metadata import CCodeExtractor
    extractor = CCodeExtractor()
    for lib_item in libs_to_scan:
        lib_source_dir = os.path.join(ROOT_DIR, "dataset", "sources", lib_item)
        if os.path.exists(lib_source_dir):
            for header_file in os.listdir(lib_source_dir):
                if header_file.endswith((".h", ".hpp")):
                    h_path = os.path.join(lib_source_dir, header_file)
                    try:
                        extra_args = ['-x', 'c++'] if lib_item.lower() not in ("cjson", "sds") else None
                        meta_h = extractor.extract_metadata(h_path, include_dirs=[lib_source_dir], extra_args=extra_args)
                        library_enums.extend(meta_h.get("enums", []))
                        library_structs.extend(meta_h.get("structs", []))
                        library_macros.extend(meta_h.get("macros", []))
                        library_typedefs.extend(meta_h.get("typedefs", []))
                    except Exception:
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

        # Generazione Documentazione con ciclo di validazione e Judge
        max_attempts = 3
        validation_feedback = None
        critic_feedback = None
        gen_doc = None
        val_res = None
        judge_res = None

        for attempt in range(max_attempts):
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
                    source_code=code,
                    validation_feedback=validation_feedback,
                    critic_feedback=critic_feedback
                )
            else:
                gen_doc = llm.generate_documentation(
                    func_name=fname,
                    signature=sig,
                    source_code=code,
                    callees_summaries=[],
                    raw_comment=item.get("raw_comment"),
                    validation_feedback=validation_feedback,
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

            # Judge Agent (solo in modalità multiagent e se Verifier ha passato)
            if mode == "multiagent" and val_res.get("is_valid", False):
                judge_res = judge_agent.evaluate_documentation(
                    func_name=fname,
                    signature=sig,
                    source_code=code,
                    doxygen_doc=gen_doc.get("full_doxygen_doc", ""),
                    brief_summary=gen_doc.get("brief_summary", ""),
                    language=language
                )
                score = judge_res.get("score", 5)
                critique = judge_res.get("critique", "")

                if score < 4 and attempt < max_attempts - 1:
                    critic_feedback = f"Punteggio: {score}/5. Critica: {critique}"
                    val_res["is_valid"] = False
                    val_res["errors"].append(f"[JUDGE CRITIC REJECT - Score {score}/5]: {critique}")
                    print(f"  -> [JUDGE REJECT] Tentativo {attempt+1}, Voto: {score}/5. Rigenerazione...")
                else:
                    print(f"  -> [JUDGE APPROVED] Tentativo {attempt+1}, Voto: {score}/5")
                    critic_feedback = None

            if val_res["is_valid"]:
                break
            else:
                validation_feedback = " ".join(val_res["errors"])

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
            calculate_meteor_score,
            evaluate_semantic_checklist,
            calculate_error_documentation_rate,
            calculate_edge_case_coverage,
            calculate_actionability_score,
            calculate_hallucination_rate,
            calculate_frechet_embedding_distance,
            generate_benchmark_charts
        )
        parsed_doc = parse_doxygen_block(doxygen_block)

        # 2. Ramo Semantico/Descrizione: confronta GT con @brief + @details (senza tag o boilerplate)
        generated_description = f"{brief_summary} {parsed_doc.get('brief', '')} {parsed_doc.get('details', '')}".strip()
        
        tfidf_sim = calculate_tfidf_cosine(gt_doc, generated_description)
        rouge_l_score = calculate_rouge_l(gt_doc, generated_description)
        meteor_val = calculate_meteor_score(gt_doc, generated_description)
        jaccard = calculate_jaccard_similarity(gt_doc, generated_description)
        recall = calculate_token_recall(gt_doc, generated_description)
        sbert_sim = calculate_sbert_similarity(gt_doc, generated_description)
        brevity_info = calculate_brevity_penalty(gt_doc, generated_description)
        bleurt_val = calculate_bleurt_score(gt_doc, generated_description)
        checklist_info = evaluate_semantic_checklist(gt_doc, generated_description)

        # 3. Ramo Qualità Intrinseca del Software (EDR, ECC, Actionability, Hallucination)
        edr_info = calculate_error_documentation_rate(code, parsed_doc.get("returns", []), parsed_doc.get("details", ""))
        ecc_info = calculate_edge_case_coverage(code, doxygen_block)
        actionability_val = calculate_actionability_score(parsed_doc, item.get("parameters", []))
        hallucination_val = calculate_hallucination_rate(val_res.get("errors", []), len(parsed_doc.get("params", [])) + max(1, len(parsed_doc.get("returns", []))))

        # 4. Ramo Task a Valle: Code Retrieval (MRR / Hit@K)
        retrieval_res = calculate_code_retrieval_mrr(
            generated_query=generated_description,
            target_function_name=fname,
            corpus_functions=corpus_functions
        )

        # 5. Ramo Strutturato/Contratti: Slot-Filling parametri & return vs AST
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
                "meteor_score": meteor_val,
                "concept_checklist_score": checklist_info["checklist_score"],
                "error_documentation_score": edr_info["score"],
                "edge_case_coverage": ecc_info["coverage"],
                "actionability_score": actionability_val,
                "hallucination_rate": hallucination_val,
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
    roundtrip_summary = None
    if roundtrip and not use_mock and api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
        print("\n" + "=" * 65)
        print("  AVVIO ROUND-TRIP DIFFERENTIAL TESTING INTEGRATO (Doc-to-Code & Dual Pytest)")
        print("=" * 65)
        from utils.roundtrip_eval import RoundTripEvaluator
        rt_evaluator = RoundTripEvaluator(llm_provider=llm)
        rt_results_list = []
        for idx_rt, r in enumerate(eval_results, 1):
            fname = r["function_name"]
            sig = r["signature"]
            doc = f"{r['generated_summary']}\n{r['generated_doxygen']}"
            print(f"\n[{idx_rt}/{len(eval_results)}] Dual Round-Trip test per: {fname}...")
            lib_val = r.get("library") or library
            rt_res = rt_evaluator.evaluate_function_roundtrip(fname, sig, doc, source_code=r.get("source_code", ""), library=lib_val)
            r["roundtrip"] = rt_res
            r["metrics"]["roundtrip_pass_rate"] = rt_res["execution"]["pass_rate"]
            diff = rt_res["execution"].get("differential", {})
            sem = rt_res["execution"].get("semantic_tests", {})
            auto = rt_res["execution"].get("auto_property_tests", {})
            diff_str = f" | Dual Agreement: {diff.get('differential_agreement_rate', 'N/A')}%" if diff else ""
            print(f"  -> Pass Rate Doc: {rt_res['execution']['pass_rate']}% ({rt_res['execution']['passed']}/{rt_res['execution']['total_tests']} passati) [Sem: {sem.get('passed', 0)}/{sem.get('total', 0)} | Auto: {auto.get('passed', 0)}/{auto.get('total', 0)}]{diff_str}")
            rt_results_list.append(rt_res)

        avg_rt_pass = round(sum(r["execution"]["pass_rate"] for r in rt_results_list) / len(rt_results_list), 1) if rt_results_list else 0.0
        diff_rates = [r["execution"]["differential"]["differential_agreement_rate"] for r in rt_results_list if "differential" in r["execution"]]
        avg_diff_agreement = round(sum(diff_rates) / len(diff_rates), 1) if diff_rates else 0.0
        roundtrip_summary = {
            "avg_pass_rate": avg_rt_pass,
            "avg_differential_agreement": avg_diff_agreement,
            "results": rt_results_list
        }
        print("\n" + "=" * 65)
        print("  ROUND-TRIP DIFFERENTIAL TESTING COMPLETATO:")
        print(f"  Pass Rate Medio Sintesi da Doc: {avg_rt_pass}%")
        if diff_rates:
            print(f"  Dual Agreement Medio (Doc vs Reference C/C++): {avg_diff_agreement}%")
        print("=" * 65)

    # Output cartella storicizzata con timestamp
    import shutil
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_bench_dir = os.path.join(RESULTS_DIR, f"benchmark_{library.lower()}")
    benchmark_dir = os.path.join(base_bench_dir, f"run_{timestamp}_{mode}")
    latest_bench_dir = os.path.join(base_bench_dir, "latest")
    os.makedirs(benchmark_dir, exist_ok=True)
    os.makedirs(latest_bench_dir, exist_ok=True)

    json_path = os.path.join(benchmark_dir, f"eval_report_{mode}.json")
    md_path = os.path.join(benchmark_dir, f"eval_report_{mode}.md")
    chart_path = os.path.join(benchmark_dir, f"eval_charts_{mode}.png")
    config_path = os.path.join(benchmark_dir, "execution_config.json")
    rt_json_path = os.path.join(benchmark_dir, "roundtrip_results.json")
    rt_chart_path = os.path.join(benchmark_dir, "eval_chart_roundtrip.png")

    # Costruzione del comando esatto da riga di comando per riprodurre fedelmente l'esperimento
    cmd_parts = [
        "python utils/benchmark_eval.py",
        f"-l {library}",
        f"-n {limit}",
        f"-m {mode}"
    ]
    if language != "en":
        cmd_parts.append(f"--lang {language}")
    if sampling != "sequential":
        cmd_parts.append(f"--sampling {sampling}")
        if seed is not None:
            cmd_parts.append(f"--seed {seed}")
    if min_loc:
        cmd_parts.append(f"--min-loc {min_loc}")
    if roundtrip:
        cmd_parts.append("--roundtrip")
    else:
        cmd_parts.append("--no-roundtrip")
    if use_mock:
        cmd_parts.append("--mock")
    reproduction_command = " ".join(cmd_parts)

    # Salva le impostazioni/configurazioni date da terminale
    bench_config = {
        "timestamp": timestamp,
        "reproduction_command": reproduction_command,
        "library": library,
        "mode": mode,
        "limit": limit,
        "language": language,
        "roundtrip": roundtrip,
        "sampling": sampling,
        "seed": seed,
        "min_loc": min_loc,
        "use_mock": use_mock
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(bench_config, f, indent=2, ensure_ascii=False)

    # Generazione Grafico Visuale Matplotlib del Benchmark
    generate_benchmark_charts(eval_results, chart_path, library_name=library)

    # Generazione Suite di Grafici Avanzati (Radar, Scatter Semantica-vs-RoundTrip, Distribuzioni, Heatmap, Breakdown)
    from utils.plot_advanced_benchmark import generate_all_advanced_charts
    advanced_chart_paths = generate_all_advanced_charts(
        eval_results=eval_results,
        run_dir=benchmark_dir,
        mode_name=mode,
        library_name=library
    )

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2, ensure_ascii=False)

    rt_error_analysis = None
    rt_error_report_path = os.path.join(benchmark_dir, "roundtrip_error_report.md")
    rt_err_chart_path = os.path.join(benchmark_dir, "eval_chart_roundtrip_errors.png")

    # Salvataggio e grafici del Round-Trip se eseguito
    if roundtrip_summary:
        # Analisi diagnostica delle cause di errore
        rt_error_analysis = analyze_roundtrip_errors(roundtrip_summary.get("results", []))
        roundtrip_summary["error_analysis"] = {
            "summary": rt_error_analysis["summary"],
            "categories": rt_error_analysis["categories"],
            "subtypes": rt_error_analysis["subtypes"]
        }

        # Salva roundtrip_results.json arricchito
        with open(rt_json_path, "w", encoding="utf-8") as f:
            json.dump(roundtrip_summary, f, indent=2, ensure_ascii=False)

        # Genera il grafico visivo dedicato agli errori se ci sono errori
        try:
            from utils.plot_roundtrip_errors import generate_roundtrip_error_charts
            generate_roundtrip_error_charts(
                rt_error_analysis,
                rt_err_chart_path,
                library_name=library
            )
            print(f"[OK] Grafico Diagnostico Errori Round-Trip generato in: {rt_err_chart_path}")
        except Exception as e:
            print(f"[WARN] Impossibile generare il grafico errori Round-Trip: {e}")

        # Salva report diagnostico dedicato in Markdown (includendo il riferimento al grafico)
        save_roundtrip_error_report(
            rt_error_analysis,
            output_md_path=rt_error_report_path,
            title=f"Round-Trip Error Diagnostic Report - {library} ({mode})",
            chart_filename=os.path.basename(rt_err_chart_path) if os.path.exists(rt_err_chart_path) else ""
        )
        print(f"[OK] Report diagnostico errori Round-Trip salvato in: {rt_error_report_path}")

        try:
            from utils.plot_roundtrip import generate_roundtrip_charts
            formatted_for_plot = [
                {
                    "name": r["function_name"],
                    "signature": r.get("signature", ""),
                    "function_type": r.get("function_type"),
                    "pass_rate": r["execution"]["pass_rate"],
                    "diff_agreement": r["execution"].get("differential", {}).get("differential_agreement_rate", 0.0),
                    "passed": r["execution"]["passed"],
                    "total": r["execution"]["total_tests"]
                }
                for r in roundtrip_summary["results"]
            ]
            generate_roundtrip_charts(
                formatted_for_plot,
                rt_chart_path,
                avg_pass_rate=roundtrip_summary.get("avg_pass_rate"),
                avg_differential_agreement=roundtrip_summary.get("avg_differential_agreement"),
                library_name=library
            )
        except Exception as e:
            print(f"[WARN] Impossibile generare il grafico Round-Trip: {e}")

    # Scrittura report Markdown (incluso il resoconto Round-Trip se presente e il comando per la riproducibilità)
    advanced_chart_filenames = [os.path.basename(p) for p in advanced_chart_paths if os.path.exists(p)]
    write_markdown_report(
        md_path,
        library,
        mode,
        eval_results,
        chart_filename=os.path.basename(chart_path),
        roundtrip_summary=roundtrip_summary,
        rt_chart_filename=os.path.basename(rt_chart_path) if roundtrip_summary and os.path.exists(rt_chart_path) else "",
        reproduction_command=reproduction_command,
        advanced_chart_filenames=advanced_chart_filenames,
        rt_error_analysis=rt_error_analysis
    )

    # Sincronizza una copia nella cartella 'latest' per consultazione rapida
    artifacts_to_mirror = [
        (f"eval_report_{mode}.json", json_path),
        (f"eval_report_{mode}.md", md_path),
        (f"eval_charts_{mode}.png", chart_path),
        ("execution_config.json", config_path)
    ]
    if roundtrip_summary:
        artifacts_to_mirror.append(("roundtrip_results.json", rt_json_path))
        if os.path.exists(rt_chart_path):
            artifacts_to_mirror.append(("eval_chart_roundtrip.png", rt_chart_path))
        if os.path.exists(rt_error_report_path):
            artifacts_to_mirror.append(("roundtrip_error_report.md", rt_error_report_path))
        if os.path.exists(rt_err_chart_path):
            artifacts_to_mirror.append(("eval_chart_roundtrip_errors.png", rt_err_chart_path))

    for p in advanced_chart_paths:
        if os.path.exists(p):
            artifacts_to_mirror.append((os.path.basename(p), p))

    for fname, target_p in artifacts_to_mirror:
        if os.path.exists(target_p):
            shutil.copy2(target_p, os.path.join(latest_bench_dir, fname))

    print("\n" + "=" * 65)
    print("  VALUTAZIONE BENCHMARK E ROUND-TRIP COMPLETATI CON SUCCESSO!")
    print(f"  Report Markdown: {md_path}")
    print(f"  Grafici Visuali: {chart_path}")
    if roundtrip_summary and os.path.exists(rt_chart_path):
        print(f"  Grafico Round-Trip: {rt_chart_path}")
    print(f"  Dati JSON:       {json_path}")
    print(f"  Impostazioni:    {config_path}")
    print(f"  Cartella Run:    {benchmark_dir}")
    print(f"  Mirror Latest:   {latest_bench_dir}")
    print(f"\n  [RIPRODUCIBILITA'] Comando CLI esatto:")
    print(f"  {reproduction_command}")
    print("=" * 65)


def write_markdown_report(md_path: str, library: str, mode: str, results: List[Dict[str, Any]], chart_filename: str = "", roundtrip_summary: Dict[str, Any] = None, rt_chart_filename: str = "", reproduction_command: str = "", advanced_chart_filenames: List[str] = None, rt_error_analysis: Dict[str, Any] = None):
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
    avg_meteor = round(sum(r["metrics"].get("meteor_score", 0.0) for r in results) / n_res, 4) if n_res else 0
    avg_checklist = round(sum(r["metrics"].get("concept_checklist_score", 0.0) for r in results) / n_res, 4) if n_res else 0
    avg_edr = round(sum(r["metrics"].get("error_documentation_score", 0.0) for r in results) / n_res * 100, 1) if n_res else 0.0
    avg_ecc = round(sum(r["metrics"].get("edge_case_coverage", 0.0) for r in results) / n_res * 100, 1) if n_res else 0.0
    avg_actionability = round(sum(r["metrics"].get("actionability_score", 0.0) for r in results) / n_res, 4) if n_res else 0.0
    avg_hallucination = round(sum(r["metrics"].get("hallucination_rate", 0.0) for r in results) / n_res, 2) if n_res else 0.0
    avg_tfidf = round(sum(r["metrics"]["tfidf_similarity"] for r in results) / n_res, 4) if n_res else 0
    avg_rouge_l = round(sum(r["metrics"]["rouge_l"] for r in results) / n_res, 4) if n_res else 0
    avg_recall = round(sum(r["metrics"]["ground_truth_recall"] for r in results) / n_res, 4) if n_res else 0
    
    # Calcolo Fréchet Embedding Distance globale
    from utils.benchmark_metrics import get_sbert_model, calculate_frechet_embedding_distance
    sbert_model = get_sbert_model()
    fid_distance = 0.0
    if sbert_model and n_res >= 2:
        try:
            ref_embs = sbert_model.encode([r["ground_truth"] for r in results], convert_to_numpy=True)
            cand_embs = sbert_model.encode([r["generated_description"] for r in results], convert_to_numpy=True)
            fid_distance = calculate_frechet_embedding_distance(ref_embs, cand_embs)
        except Exception:
            pass

    # Metriche Task a Valle: Code Retrieval
    avg_mrr = round(sum(r["metrics"].get("retrieval_rr", 0.0) for r in results) / n_res, 4) if n_res else 0
    avg_hit1 = round(sum(r["metrics"].get("hit_at_1", 0.0) for r in results) / n_res, 4) if n_res else 0
    avg_hit5 = round(sum(r["metrics"].get("hit_at_5", 0.0) for r in results) / n_res, 4) if n_res else 0

    valid_count = sum(1 for r in results if r["is_valid"])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Report Benchmark Documentazione: {library}\n\n")
        if reproduction_command:
            f.write(f"> **Comando CLI per la riproduzione esatta dell'esperimento:**\n```bash\n{reproduction_command}\n```\n\n")
        f.write(f"- **Libreria**: `{library}`\n")
        f.write(f"- **Modalita' Pipeline**: `{mode}`\n")
        f.write(f"- **Funzioni Valutate**: {n_res}\n")
        f.write(f"- **Funzioni Valide al Verifier**: {valid_count}/{n_res} ({round(valid_count/n_res*100, 1)}%)\n")
        f.write(f"- **Hallucination Rate Globale**: `{avg_hallucination}%`\n")
        f.write(f"- **Parameter F1-Score Medio (vs AST)**: `{avg_param_f1}`\n")
        f.write(f"- **Return Contract Match Medio**: `{avg_return_match}`\n")
        f.write(f"- **Actionability Score (AS)**: `{avg_actionability}` / 1.0\n")
        f.write(f"- **Error Documentation Rate (EDR)**: `{avg_edr}%`\n")
        f.write(f"- **Edge Case Coverage (ECC)**: `{avg_ecc}%`\n")
        if has_judge:
            f.write(f"- **LLM-Judge Faithfulness (Code+GT vs Doc) [1-5]**: `{avg_judge_a}/5.0`\n")
            f.write(f"- **LLM-Judge Alignment (GT vs Doc) [1-5]**: `{avg_judge_b}/5.0`\n")
            f.write(f"- **LLM-Judge Punteggio Combinato [1-5]**: `{avg_judge_comb}/5.0`\n")
        f.write(f"- **Downstream Code Retrieval MRR**: `{avg_mrr}` (Hit@1: `{round(avg_hit1*100, 1)}%`, Hit@5: `{round(avg_hit5*100, 1)}%`)\n")
        if roundtrip_summary:
            f.write(f"- **Round-Trip Pass Rate Medio (Doc Synthesis)**: `{roundtrip_summary['avg_pass_rate']}%`\n")
            if roundtrip_summary.get('avg_differential_agreement'):
                f.write(f"- **Round-Trip Dual Agreement (Doc vs Code Reale)**: `{roundtrip_summary['avg_differential_agreement']}%`\n")
        f.write(f"- **Sentence-BERT Cosine Similarity Media**: `{avg_sbert}`\n")
        f.write(f"- **BERTScore F1-Score Medio**: `{avg_bert_f1}`\n")
        f.write(f"- **CodeBERTScore F1-Score Medio**: `{avg_codebert_f1}`\n")
        f.write(f"- **METEOR Score Medio (Synonyms & Stems)**: `{avg_meteor}`\n")
        f.write(f"- **BLEURT Quality Score Medio**: `{avg_bleurt}`\n")
        f.write(f"- **Concept Checklist Score (Semantic Facts)**: `{avg_checklist}`\n")
        f.write(f"- **Fréchet Embedding Distance (FID / W2)**: `{fid_distance}`\n")
        f.write(f"- **TF-IDF Cosine Similarity Media**: `{avg_tfidf}`\n")
        f.write(f"- **ROUGE-L Score Medio**: `{avg_rouge_l}`\n")
        f.write(f"- **Recall Chiavi Ground Truth Media**: `{avg_recall}`\n\n")

        if chart_filename:
            f.write("## 📈 Dashboard Grafica di Benchmark (Neural, Judge & AST Metrics)\n\n")
            f.write(f"![Metriche Benchmark]({chart_filename})\n\n")

        if advanced_chart_filenames:
            f.write("## 🔬 Analisi Diagnostica & Statistica Avanzata\n\n")
            for achart in advanced_chart_filenames:
                if "radar" in achart:
                    f.write(f"### 🕸️ Profilo di Qualità a 6 Dimensioni (Radar Chart)\n![Radar Chart]({achart})\n\n")
                elif "semantic_vs_roundtrip" in achart:
                    f.write(f"### 🔀 Correlazione Semantica Neurale vs Round-Trip Pass Rate Reale\n![Scatter Correlation]({achart})\n\n")
                elif "distributions" in achart:
                    f.write(f"### 🎻 Distribuzione Statistica & Varianza delle Metriche (Violin Plot)\n![Violin Plot]({achart})\n\n")
                elif "heatmap" in achart:
                    f.write(f"### 🎯 Matrice di Confidenza Funzione × Metriche (Heatmap)\n![Confidence Heatmap]({achart})\n\n")
                elif "verifier_breakdown" in achart:
                    f.write(f"### 🛡️ Breakdown Cause di Scarto Verifier & Rigetti del Giudice\n![Verifier Breakdown]({achart})\n\n")
                elif "cross_correlation" in achart:
                    f.write(f"### 🔗 Matrice di Cross-Correlazione delle Metriche (Pearson $r$ Heatmap)\n![Cross-Correlation Heatmap]({achart})\n\n")
                elif "discrepancy_residuals" in achart:
                    f.write(f"### ⚖️ Analisi dei Residui: Allucinazione Plausibile vs Parafrasi Robusta\n![Residuals Discrepancy]({achart})\n\n")
                elif "complexity_pareto" in achart:
                    f.write(f"### 📈 Scalabilità e Complessità del Codice (LOC vs Performance)\n![Complexity Pareto]({achart})\n\n")
                elif "pipeline_flow" in achart:
                    f.write(f"### ⏳ Imbuto di Validazione e Transizioni della Pipeline\n![Pipeline Flow]({achart})\n\n")

        if rt_chart_filename:
            f.write("## 🧪 Dashboard Round-Trip Differential Testing (Pytest Assertions)\n\n")
            f.write(f"![Metriche Round-Trip]({rt_chart_filename})\n\n")

        if rt_error_analysis and rt_error_analysis.get("categories"):
            f.write("## 🩺 Diagnostica Tipologie di Errore Round-Trip\n\n")
            f.write("> Sintesi delle cause di fallimento dei test di validazione Doc-to-Code. Il report completo è disponibile in `roundtrip_error_report.md`.\n\n")
            f.write("| Tipologia Errore | Occorrenze | Percentuale (%) | Descrizione Operativa |\n")
            f.write("|---|:---:|:---:|---|\n")
            for c in rt_error_analysis.get("categories", []):
                cat_name = c["category"]
                desc = ""
                if "Missing Symbol" in cat_name:
                    desc = "Dipendenze, costanti o helper mancanti nello scaffold."
                elif "Interface" in cat_name:
                    desc = "Mismatch di firma, parametri mancanti o incompatibilità di tipi."
                elif "Behavioral" in cat_name:
                    desc = "La logica non produce il valore atteso dal test (discrepanza contrattuale)."
                elif "Test Harness" in cat_name:
                    desc = "Mancata eccezione attesa o anomalia harness."
                elif "Syntax" in cat_name:
                    desc = "Errore di sintassi nel codice generato dall'LLM."
                else:
                    desc = "Altro errore di runtime o timeout."
                f.write(f"| **{cat_name}** | `{c['count']}` | **{c['percentage']}%** | {desc} |\n")
            f.write("\n")

        f.write("## 📋 Tabella Comparativa Completa (SBERT, BERTScore, METEOR, LLM-Judge & AST)\n\n")
        rt_col_header = " | Round-Trip (Doc/Dual)" if roundtrip_summary else ""
        rt_col_sep = "|:---:" if roundtrip_summary else ""
        if has_judge:
            f.write(f"| Funzione | Verifier | Param F1 | SBERT | METEOR | Actionability | Judge (Code+GT) | Code Retrieval (Rank){rt_col_header} |\n")
            f.write(f"|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:{rt_col_sep}|\n")
            for r in results:
                status = "Sì" if r["is_valid"] else "No"
                j_a = f"{r['metrics']['judge_score_a']} ± {r['metrics']['judge_std_a']}"
                ret_info = f"Rank #{r['retrieval']['rank']} (RR: {r['retrieval']['reciprocal_rank']})" if 'retrieval' in r else "N/A"
                rt_str = ""
                if roundtrip_summary and "roundtrip" in r:
                    rt_info = r["roundtrip"]["execution"]
                    diff_val = rt_info.get("differential", {}).get("differential_agreement_rate", "N/A")
                    rt_str = f" | {rt_info['pass_rate']}% ({diff_val}%)"
                elif roundtrip_summary:
                    rt_str = " | N/A"
                f.write(f"| `{r['function_name']}` | {status} | **{r['metrics']['param_f1']}** | {r['metrics']['sbert_similarity']} | {r['metrics'].get('meteor_score', 'N/A')} | {r['metrics'].get('actionability_score', 'N/A')} | **{j_a}** | {ret_info}{rt_str} |\n")
        else:
            f.write(f"| Funzione | Verifier | Param F1 | SBERT Sim | METEOR | CodeBERT | Actionability | Code Retrieval (Rank){rt_col_header} |\n")
            f.write(f"|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:{rt_col_sep}|\n")
            for r in results:
                status = "Sì" if r["is_valid"] else "No"
                ret_info = f"Rank #{r['retrieval']['rank']} (RR: {r['retrieval']['reciprocal_rank']})" if 'retrieval' in r else "N/A"
                rt_str = ""
                if roundtrip_summary and "roundtrip" in r:
                    rt_info = r["roundtrip"]["execution"]
                    diff_val = rt_info.get("differential", {}).get("differential_agreement_rate", "N/A")
                    rt_str = f" | {rt_info['pass_rate']}% ({diff_val}%)"
                elif roundtrip_summary:
                    rt_str = " | N/A"
                f.write(f"| `{r['function_name']}` | {status} | **{r['metrics']['param_f1']}** | {r['metrics']['sbert_similarity']} | {r['metrics'].get('meteor_score', 'N/A')} | {r['metrics']['codebert_score_f1']} | {r['metrics'].get('actionability_score', 'N/A')} | {ret_info}{rt_str} |\n")

        f.write("\n## 🔍 Dettagli Funzione per Funzione\n\n")
        for r in results:
            f.write(f"### `{r['function_name']}`\n")
            f.write(f"- **Firma**: `{r['signature']}`\n")
            f.write(f"- **Metriche Contratti AST**: Param F1: `{r['metrics']['param_f1']}` (Precision: `{r['metrics']['param_precision']}`, Recall: `{r['metrics']['param_recall']}`) | Return Match: `{r['metrics']['return_match']}`\n")
            f.write(f"- **Qualità Software & Actionability**: Actionability Score: `{r['metrics'].get('actionability_score', 'N/A')}` | Error Doc Rate: `{r['metrics'].get('error_documentation_score', 'N/A')}` | Edge Case Cov: `{r['metrics'].get('edge_case_coverage', 'N/A')}` | Hallucination Rate: `{r['metrics'].get('hallucination_rate', 0.0)}%`\n")
            if has_judge and "judge_details" in r:
                jd = r["judge_details"]
                f.write(f"- **LLM Judge Faithfulness (Code+GT)**: `{r['metrics']['judge_score_a']} ± {r['metrics']['judge_std_a']}` / 5.0\n")
                f.write(f"  > *Motivazione Giudice*: {jd['perspective_a']['sample_reasoning']}\n")
                f.write(f"- **LLM Judge Alignment (GT only)**: `{r['metrics']['judge_score_b']} ± {r['metrics']['judge_std_b']}` / 5.0\n")
                f.write(f"  > *Motivazione Giudice*: {jd['perspective_b']['sample_reasoning']}\n")
            if "retrieval" in r:
                f.write(f"- **Task a Valle (Code Retrieval)**: Rank Target: `#{r['retrieval']['rank']}` | Reciprocal Rank: `{r['retrieval']['reciprocal_rank']}` | Hit@1: `{r['retrieval']['hit_at_1']}` | Top Match: `{r['retrieval']['top_match']}`\n")
            if "roundtrip" in r:
                rt_exec = r["roundtrip"]["execution"]
                rt_diff = rt_exec.get("differential", {})
                diff_text = f" | Dual Agreement: {rt_diff.get('differential_agreement_rate', 'N/A')}% (Ref Pass: {rt_diff.get('reference_pass_rate', 'N/A')}%)" if rt_diff else ""
                f.write(f"- **Round-Trip Test**: Pass Rate Doc: `{rt_exec['pass_rate']}%` ({rt_exec['passed']}/{rt_exec['total_tests']} passati){diff_text}\n")
            f.write(f"- **Metriche Semantiche & Lessicali**: SBERT Sim: `{r['metrics']['sbert_similarity']}` | METEOR: `{r['metrics'].get('meteor_score', 'N/A')}` | Concept Checklist: `{r['metrics'].get('concept_checklist_score', 'N/A')}` | BERTScore F1: `{r['metrics']['bert_score_f1']}` | BLEURT: `{r['metrics']['bleurt_score']}` | ROUGE-L: `{r['metrics']['rouge_l']}`\n\n")
            f.write(f"- **Documentazione Originale (Ground Truth)**:\n> {r['ground_truth'].replace(chr(10), chr(10) + '> ')}\n\n")
            f.write(f"- **Breve Spiegazione LLM**: {r['generated_summary']}\n\n")
            f.write(f"- **Blocco Doxygen Generato**:\n```c\n{r['generated_doxygen']}\n```\n\n")
            if r["verifier_errors"]:
                f.write(f"- **Segnalazioni Verifier**: {', '.join(r['verifier_errors'])}\n\n")
            f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Valutazione Benchmark Documentazione Generata vs Ground Truth con Round-Trip Integrato",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Esempi di utilizzo:
  python utils/benchmark_eval.py                                   # Menu interattivo con selezione guidata e scelta Round-Trip
  python utils/benchmark_eval.py -l cJSON -n 10 --roundtrip       # Benchmark 10 funzioni con Round-Trip automatico
  python utils/benchmark_eval.py -l cJSON -n 10 --no-roundtrip    # Solo benchmark senza Round-Trip
  python utils/benchmark_eval.py -l all -n 20 -r --seed 42 -m multiagent --roundtrip
"""
    )
    parser.add_argument("-l", "--library", default=None, choices=["cJSON", "OpenCV", "TinyXML-2", "sds", "fmt", "miniz", "http-parser", "all"], help="Libreria su cui eseguire il test: 'cJSON', 'OpenCV', 'TinyXML-2', 'sds', 'fmt', 'miniz', 'http-parser' o 'all' per l'intero pool (default: cJSON)")
    parser.add_argument("-n", "--limit", type=int, default=None, help="Numero massimo di funzioni da documentare e confrontare (default: 5)")
    parser.add_argument("-s", "--sampling", default="sequential", choices=["sequential", "random", "stratified"], help="Strategia di campionamento: 'sequential' (prime N per ID), 'random' (casuale puro), 'stratified' (casuale con vincoli di complessita'/quantili LOC)")
    parser.add_argument("-r", "--random", action="store_true", help="Scorciatoia per --sampling random")
    parser.add_argument("--stratified", action="store_true", help="Scorciatoia per --sampling stratified")
    parser.add_argument("--seed", type=int, default=None, help="Seed numerico per riproducibilità esatta del campionamento random o stratificato")
    parser.add_argument("--min-loc", type=int, default=None, help="Filtro opzionale: considera solo funzioni con almeno N linee di codice sorgente C/C++")
    parser.add_argument("-m", "--mode", default="single", choices=["single", "multiagent"], help="Modalita': 'single' (Ibrido Standard) o 'multiagent'")
    parser.add_argument("--lang", default="en", choices=["en", "it"], help="Lingua per la documentazione LLM: 'en' (default) o 'it'")
    parser.add_argument("--roundtrip", dest="roundtrip", action="store_true", default=None, help="Esegue anche la validazione Round-Trip (Doc-to-Code Synthesis & Dual Pytest)")
    parser.add_argument("--no-roundtrip", dest="roundtrip", action="store_false", help="Disabilita la validazione Round-Trip a fine benchmark")
    parser.add_argument("--mock", action="store_true", help="Forza l'uso del MockLLM senza effettuare chiamate API reali")

    args = parser.parse_args()

    # Risoluzione flag di campionamento se passati via CLI
    sampling_strategy = args.sampling
    if args.stratified:
        sampling_strategy = "stratified"
    elif args.random:
        sampling_strategy = "random"

    # Se non sono stati passati argomenti espliciti da riga di comando (es. solo `python utils/benchmark_eval.py`), avviamo il menu interattivo
    if args.library is None and args.limit is None:
        print("==================================================")
        print("  BENCHMARK & VALUTAZIONE GROUND TRUTH (C/C++)    ")
        print("==================================================")
        libraries = ["cJSON", "OpenCV", "TinyXML-2", "sds", "fmt", "miniz", "http-parser", "all"]
        print("\nLibrerie disponibili:")
        for idx, lib in enumerate(libraries, 1):
            print(f"  [{idx}] {lib}")
        
        lib_choice = input(f"\nSeleziona libreria [1-{len(libraries)}] (default: 1 [cJSON]): ").strip()
        chosen_lib = "cJSON"
        if lib_choice.isdigit():
            idx = int(lib_choice) - 1
            if 0 <= idx < len(libraries):
                chosen_lib = libraries[idx]
        elif lib_choice in libraries:
            chosen_lib = lib_choice

        limit_choice = input("Numero di funzioni da valutare (default: 5): ").strip()
        chosen_limit = int(limit_choice) if limit_choice.isdigit() and int(limit_choice) > 0 else 5

        mode_choice = input("Modalita' pipeline [1: single, 2: multiagent] (default: 1): ").strip()
        chosen_mode = "multiagent" if mode_choice in ("2", "multiagent", "m") else "single"

        # Selezione strategia di campionamento
        print("\nStrategia di selezione delle funzioni:")
        print("  [1] Sequenziale (Non casuale, prime N funzioni per ID)")
        print("  [2] Casuale puro (Campionamento uniforme sull'intero pool)")
        print("  [3] Casuale con vincoli (Stratificato per quantili di lunghezza LOC: da funzioni brevi a 100+ LOC)")
        samp_choice = input("Seleziona modalita' [1-3] (default: 1): ").strip()
        
        chosen_seed = args.seed
        chosen_min_loc = args.min_loc

        if samp_choice == "3" or samp_choice.lower().startswith("strat"):
            sampling_strategy = "stratified"
            seed_input = input("  -> Inserisci Seed per riproducibilita' esatta (es: 42, oppure Invio per seed casuale): ").strip()
            if seed_input.isdigit() or (seed_input.startswith("-") and seed_input[1:].isdigit()):
                chosen_seed = int(seed_input)
            loc_input = input("  -> Filtro opzionale LOC minime (es: 10 per escludere one-liner, oppure Invio per nessuna restrizione): ").strip()
            if loc_input.isdigit() and int(loc_input) > 0:
                chosen_min_loc = int(loc_input)
        elif samp_choice == "2" or samp_choice.lower().startswith("rand"):
            sampling_strategy = "random"
            seed_input = input("  -> Inserisci Seed per riproducibilita' esatta (es: 42, oppure Invio per seed casuale): ").strip()
            if seed_input.isdigit() or (seed_input.startswith("-") and seed_input[1:].isdigit()):
                chosen_seed = int(seed_input)
        else:
            sampling_strategy = "sequential"

        # Richiesta esplicita per il Round-Trip
        rt_choice = input("\nEseguire automaticamente anche il Round-Trip Differential Testing al termine? [S/n] (default: S): ").strip().lower()
        chosen_roundtrip = rt_choice not in ("n", "no")

        run_evaluation(
            library=chosen_lib,
            limit=chosen_limit,
            mode=chosen_mode,
            use_mock=args.mock,
            language=args.lang,
            roundtrip=chosen_roundtrip,
            sampling=sampling_strategy,
            seed=chosen_seed,
            min_loc=chosen_min_loc
        )
        return

    # Esecuzione diretta da riga di comando con flag passati
    chosen_lib = args.library if args.library is not None else "cJSON"
    chosen_limit = args.limit if args.limit is not None else 5
    chosen_roundtrip = True if args.roundtrip is None else args.roundtrip

    run_evaluation(
        library=chosen_lib,
        limit=chosen_limit,
        mode=args.mode,
        use_mock=args.mock,
        language=args.lang,
        roundtrip=chosen_roundtrip,
        sampling=sampling_strategy,
        seed=args.seed,
        min_loc=args.min_loc
    )


if __name__ == "__main__":
    main()

