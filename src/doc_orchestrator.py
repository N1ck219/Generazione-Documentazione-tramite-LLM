import os
import json
from typing import Dict, List, Any
from src.doc_database import DocDatabase
from src.llm_provider import LLMProvider, MockLLMProvider, GeminiLLMProvider
from src.verifier import DocumentationVerifier



class DocOrchestrator:
    def __init__(self, project_results_dir: str, llm_provider: LLMProvider = None):
        self.results_dir = project_results_dir
        self.db_path = os.path.join(project_results_dir, "documentation.db")
        self.db = DocDatabase(self.db_path)
        
        # Se non specificato, tenta di usare Gemini, altrimenti usa il Mock Provider
        if llm_provider:
            self.llm = llm_provider
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
                print("[INFO LLM] Configurazione rilevata: Uso del provider Gemini (modello gemini-3.5-flash-lite, 15 RPM)")
                self.llm = GeminiLLMProvider(model_name="gemini-3.5-flash-lite", api_key=api_key, rpm_limit=15)
            else:

                print("[INFO LLM] Nessuna API Key configurata in .env: Uso del MockLLMProvider locale")
                self.llm = MockLLMProvider()


        self.metadata_path = os.path.join(project_results_dir, "extracted_metadata.json")
        self.topological_path = os.path.join(project_results_dir, "topological_execution_order.json")

    def _load_data():
        pass

    def run_documentation_pipeline(self, clear_cache: bool = False, mode: str = "single") -> str:
        if not os.path.exists(self.metadata_path) or not os.path.exists(self.topological_path):
            raise FileNotFoundError("Metadati o ordine topologico non trovati nella cartella dei risultati.")

        if clear_cache:
            self.db.clear_database()

        with open(self.metadata_path, "r", encoding="utf-8") as f:
            all_metadata = json.load(f)

        with open(self.topological_path, "r", encoding="utf-8") as f:
            topological_order: List[List[str]] = json.load(f)

        functions_index = {}
        for rel_path, meta in all_metadata.items():
            for func_info in meta.get("functions", []):
                if func_info.get("is_definition", True):
                    functions_index[func_info["name"]] = {
                        "func_info": func_info,
                        "file_path": rel_path
                    }

        mode_desc = "MULTI-AGENTE (Reader -> Searcher -> Writer -> Verifier -> Judge)" if mode == "multiagent" else "IBRIDO STANDARD"
        print(f"\n=== AVVIO GENERAZIONE DOCUMENTAZIONE BOTTOM-UP [{mode_desc}] ===")
        from src.verifier import DocumentationVerifier
        verifier = DocumentationVerifier(all_metadata)

        # Inizializza gli Agenti della Pipeline se la modalità è Multi-Agente
        if mode == "multiagent":
            from src.agents.reader_agent import ReaderAgent
            from src.agents.searcher_agent import SearcherAgent
            from src.agents.writer_agent import WriterAgent
            from src.agents.judge_agent import JudgeAgent
            
            reader_agent = ReaderAgent(self.llm)
            searcher_agent = SearcherAgent(self.db)
            writer_agent = WriterAgent(self.llm)
            judge_agent = JudgeAgent(self.llm)

        # Lista piatta di tutte le funzioni da documentare in ordine topologico
        all_funcs_in_order = []
        for scc in topological_order:
            for fn_name in scc:
                if fn_name in functions_index:
                    all_funcs_in_order.append(fn_name)

        # Integrazione barra di avanzamento tqdm
        try:
            from tqdm import tqdm
            pbar = tqdm(all_funcs_in_order, desc=f"Generazione Doc ({mode})", unit="funzione")
        except ImportError:
            pbar = all_funcs_in_order

        # Raccolta metriche di dimensione del codice passato all'LLM
        code_size_metrics = []

        for func_name in pbar:
            fn_data = functions_index[func_name]
            fn_info = fn_data["func_info"]
            file_path = fn_data["file_path"]

            source_code = fn_info.get("source_code") or f"/* Definizione riga {fn_info.get('line')} */"
            
            # Calcolo metriche di dimensione per questa funzione
            loc_count = len([line for line in source_code.splitlines() if line.strip()])
            char_count = len(source_code)
            # Stima token (regola approssimativa: 1 token ~ 4 caratteri per codice C + overhead prompt ~180 token)
            prompt_tokens_est = int(char_count / 3.8) + 180

            code_size_metrics.append({
                "name": func_name,
                "file_path": file_path,
                "loc": loc_count,
                "char_count": char_count,
                "prompt_tokens_est": prompt_tokens_est
            })

            # Controlla se la documentazione per questa funzione è già salvata nel DB SQLite
            existing_doc = self.db.get_function_doc(func_name)
            if existing_doc:
                continue

            callees = fn_info.get("callees", [])
            params_list = fn_info.get("parameters", [])
            ret_type = fn_info.get('return_type', '')

            is_ctor_or_dtor = ("::" in func_name and func_name.split("::")[-1] == func_name.split("::")[-2]) or ret_type == ""
            if params_list:
                params_str = ", ".join([f"{p['type']} {p['name']}" for p in params_list])
            else:
                params_str = "" if is_ctor_or_dtor else "void"

            if is_ctor_or_dtor or not ret_type:
                signature = f"{func_name}({params_str})"
            else:
                signature = f"{ret_type} {func_name}({params_str})"

            max_validation_attempts = 3
            llm_result = None
            validation_feedback = None
            critic_feedback = None
            attempts_log = []

            for attempt in range(max_validation_attempts):

                if mode == "multiagent":
                    # 1. READER AGENT: Analisi dei fatti dal codice C
                    reader_facts = reader_agent.analyze_function(
                        func_name=func_name,
                        signature=signature,
                        source_code=source_code,
                        raw_comment=fn_info.get("raw_comment")
                    )
                    # 2. SEARCHER AGENT: Arricchimento contesto dipendenze
                    enriched_ctx = searcher_agent.enrich_context(reader_facts, callees)

                    # 3. WRITER AGENT: Redazione bozza Doxygen (con feedback AST e del Judge)
                    llm_result = writer_agent.write_documentation(
                        enriched_context=enriched_ctx,
                        source_code=source_code,
                        validation_feedback=validation_feedback,
                        critic_feedback=critic_feedback
                    )
                else:
                    # Modalità Ibrida Standard Single-Prompt
                    callees_summaries = self.db.get_callees_summaries(callees)
                    llm_result = self.llm.generate_documentation(
                        func_name=func_name,
                        signature=signature,
                        source_code=source_code,
                        callees_summaries=callees_summaries,
                        raw_comment=fn_info.get("raw_comment"),
                        validation_feedback=validation_feedback
                    )

                # 4. VERIFIER AGENT: Validazione Programmatica ed AST
                val_res = verifier.verify_function_doc(fn_info, llm_result)
                
                judge_res = None
                # 5. JUDGE / CRITIC AGENT (Solo in modalità multi-agente e solo se il Verifier AST passa)
                if mode == "multiagent" and val_res.get("is_valid", False):
                    judge_res = judge_agent.evaluate_documentation(
                        func_name=func_name,
                        signature=signature,
                        source_code=source_code,
                        doxygen_doc=llm_result.get("full_doxygen_doc", ""),
                        brief_summary=llm_result.get("brief_summary", "")
                    )
                    score = judge_res.get("score", 5)
                    critique = judge_res.get("critique", "")

                    if score < 4 and attempt < max_validation_attempts - 1:
                        # Punteggio sotto il 4: rigenerazione guidata dalla critica del Giudice
                        critic_feedback = f"Punteggio assegnato: {score}/5. Critica: {critique}"
                        val_res["is_valid"] = False
                        val_res["errors"].append(f"[JUDGE CRITIC REJECT - Score {score}/5]: {critique}")
                        print(f"\n  [JUDGE REJECT] {func_name} (Tentativo {attempt+1}, Voto: {score}/5): {critique}")
                    else:
                        print(f"\n  [JUDGE APPROVED] {func_name} (Tentativo {attempt+1}, Voto: {score}/5)")
                        critic_feedback = None

                # Registra l'esito del tentativo corrente
                attempts_log.append({
                    "attempt": attempt + 1,
                    "validation_feedback_sent": validation_feedback,
                    "critic_feedback_sent": critic_feedback,
                    "generated_brief": llm_result.get("brief_summary") if llm_result else None,
                    "generated_doxygen": llm_result.get("full_doxygen_doc") if llm_result else None,
                    "is_valid": val_res.get("is_valid", False),
                    "errors": val_res.get("errors", []),
                    "judge_score": judge_res.get("score") if judge_res else None,
                    "judge_critique": judge_res.get("critique") if judge_res else None
                })

                if val_res["is_valid"]:
                    break
                else:
                    validation_feedback = " ".join(val_res["errors"])
                    if not judge_res or judge_res.get("score", 5) >= 4:
                        print(f"\n  [VERIFIER REJECT] {func_name} (Tentativo {attempt+1}): {validation_feedback}")

            # Registra nel file di log di debug per l'ispezione scientifica
            debug_log_path = os.path.join(self.results_dir, "verifier_debug_log.json")
            existing_debug_data = []
            if os.path.exists(debug_log_path):
                try:
                    with open(debug_log_path, "r", encoding="utf-8") as df:
                        existing_debug_data = json.load(df)
                except Exception:
                    existing_debug_data = []

            existing_debug_data.append({
                "function": func_name,
                "file_path": file_path,
                "signature": signature,
                "attempts": attempts_log
            })

            with open(debug_log_path, "w", encoding="utf-8") as df:
                json.dump(existing_debug_data, df, indent=2)

            fn_line = fn_info.get("line", 1)
            file_loc_str = f"`{file_path}` (riga {fn_line})"



            # 4. Salva nel DB SQLite ed in DOCUMENTATION.md
            if val_res and val_res["is_valid"]:
                time_comp = fn_info.get("time_complexity", "O(1)")
                space_comp = fn_info.get("space_complexity", "O(1)")
                
                # Inserimento deterministico certificato della complessità a posteriori
                final_doxygen_doc = DocumentationVerifier.enforce_deterministic_complexity(
                    doxygen_doc=llm_result["full_doxygen_doc"],
                    time_comp=time_comp,
                    space_comp=space_comp
                )

                # Step dedicato di categorizzazione dinamica incrementale (post-approvazione)
                existing_cats = self.db.get_existing_categories()
                assigned_category = self.llm.classify_function(
                    func_name=func_name,
                    signature=signature,
                    brief_summary=llm_result["brief_summary"],
                    source_code=source_code,
                    existing_categories=existing_cats
                )

                self.db.save_function_doc(
                    name=func_name,
                    file_path=file_loc_str,
                    signature=signature,
                    return_type=fn_info.get("return_type", "void"),
                    brief_summary=llm_result["brief_summary"],
                    full_doxygen_doc=final_doxygen_doc,
                    time_complexity=time_comp,
                    space_complexity=space_comp,
                    category=assigned_category
                )




            else:
                print(f"  [STRICT VERIFIER REJECT] La funzione '{func_name}' NON e' stata salvata in SQLite perche' non ha superato la validazione formale dopo {max_validation_attempts} tentativi.")




        # Generazione Grafici di Distribuzione della Dimensione del Codice
        try:
            from utils.generate_size_charts import generate_code_size_distribution_charts
            stats_output_dir = os.path.join(self.results_dir, "analytics_charts")
            generate_code_size_distribution_charts(code_size_metrics, stats_output_dir)
        except Exception as chart_err:
            print(f"  [METRICS WARNING] Impossibile generare i grafici di dimensione codice: {chart_err}")

        # 4. Generazione documentazione Structs ed Enums
        self._generate_structs_and_enums_docs()

        # 5. PASSO FINALE: Global Consistency Review & Refinement
        print("\n[5/5] Esecuzione Revisione Finale di Coerenza Globale (Global Consistency Review)...")
        verifier = DocumentationVerifier({})

        # Recupera dati per l'audit finale
        module_summaries = {}
        all_funcs = self.db.get_all_function_docs()
        
        # Estrai i file unici
        unique_mod_paths = []
        for f in all_funcs:
            rel_p = f["file_path"].split("`")[1] if "`" in f["file_path"] else f["file_path"]
            if rel_p not in unique_mod_paths:
                unique_mod_paths.append(rel_p)

        try:
            from tqdm import tqdm
            pbar_mods = tqdm(unique_mod_paths, desc="Global Review (Moduli)", unit="modulo")
        except ImportError:
            pbar_mods = unique_mod_paths

        for rel_path in pbar_mods:
            if rel_path not in module_summaries:
                funcs_in_mod = [fn["brief_summary"] for fn in all_funcs if (fn["file_path"].split("`")[1] if "`" in fn["file_path"] else fn["file_path"]) == rel_path]
                module_summaries[rel_path] = self.llm.generate_module_summary(rel_path, funcs_in_mod)

        struct_docs = self.db.get_all_struct_docs()
        
        # Esegui la verifica di coerenza globale
        global_val = verifier.verify_global_consistency(module_summaries, struct_docs, all_funcs)
        if global_val["has_issues"]:
            print("  [GLOBAL REFINER] Risolte incongruenze di coerenza globale:")
            for issue in global_val["issues"]:
                print(f"    - {issue}")
            
            # Applica le correzioni salvandole nel database SQLite
            for st in global_val["corrections"]["struct_docs"]:
                fields = st.get("fields_json", [])
                if isinstance(fields, str):
                    fields = json.loads(fields)
                self.db.save_struct_doc(st["name"], st["file_path"], st["brief_summary"], fields)

            for fn in all_funcs:
                self.db.save_function_doc(
                    name=fn["name"],
                    file_path=fn["file_path"],
                    signature=fn["signature"],
                    return_type=fn.get("return_type", ""),
                    brief_summary=fn["brief_summary"],
                    full_doxygen_doc=fn["full_doxygen_doc"],
                    time_complexity=fn.get("time_complexity", "O(1)"),
                    space_complexity=fn.get("space_complexity", "O(1)"),
                    category=fn.get("category", "Generale")
                )

        # 6. Esporta il log completo di tutti i Prompt e Risposte ottenute dall'LLM
        try:
            interaction_log = self.llm.get_interaction_log()
            if interaction_log:
                prompts_json_path = os.path.join(self.results_dir, "llm_prompts_and_responses.json")
                with open(prompts_json_path, "w", encoding="utf-8") as pf:
                    json.dump(interaction_log, pf, indent=2, ensure_ascii=False)
                
                # Esporta anche una versione leggibile in Markdown per consultazione immediata
                prompts_md_path = os.path.join(self.results_dir, "LLM_INTERACTIONS_LOG.md")
                md_lines = [
                    "# REGISTRO COMPLETO INTERAZIONI LLM (PROMPTS & RISPOSTE)\n",
                    f"*Totale Chiamate LLM Registrate in questa Sessione:* `{len(interaction_log)}`\n",
                    "---\n"
                ]
                for idx, log in enumerate(interaction_log, 1):
                    md_lines.append(f"## [{idx}] Tipo: `{log.get('kind')}` | Target: `{log.get('target')}`")
                    md_lines.append(f"**Timestamp:** `{log.get('timestamp')}`\n")
                    md_lines.append("### 📝 Prompt Inviato:")
                    md_lines.append("```text")
                    md_lines.append(log.get('prompt', '').strip())
                    md_lines.append("```\n")
                    md_lines.append("### 🤖 Risposta Ottenuta:")
                    md_lines.append("```json")
                    md_lines.append(log.get('raw_response', '').strip())
                    md_lines.append("```\n")
                    md_lines.append("---\n")

                with open(prompts_md_path, "w", encoding="utf-8") as pm:
                    pm.write("\n".join(md_lines))
                print(f"-> Registro interazioni LLM salvato in: {prompts_json_path} e {prompts_md_path}")
        except Exception as log_err:
            print(f"  [LOGGING WARNING] Impossibile salvare il log dei prompt: {log_err}")

        # 7. Assembla il file finale DOCUMENTATION.md
        doc_md_path = os.path.join(self.results_dir, "DOCUMENTATION.md")
        self._export_markdown_documentation(doc_md_path)
        return doc_md_path


    def _generate_structs_and_enums_docs(self):
        if not os.path.exists(self.metadata_path):
            return
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            all_metadata = json.load(f)

        all_types = []
        for rel_path, meta in all_metadata.items():
            for st in meta.get("structs", []) + meta.get("classes", []):
                all_types.append(("struct", rel_path, st))
            for en in meta.get("enums", []):
                all_types.append(("enum", rel_path, en))

        if not all_types:
            return

        try:
            from tqdm import tqdm
            pbar_types = tqdm(all_types, desc="Generazione Tipi Dati (struct/enum)", unit="tipo")
        except ImportError:
            pbar_types = all_types

        for item_type, rel_path, item_data in pbar_types:
            if item_type == "struct":
                st_name = item_data["name"]
                fields = item_data.get("fields", [])
                if not fields: continue
                res = self.llm.generate_struct_documentation(st_name, fields)
                self.db.save_struct_doc(st_name, rel_path, res.get("brief_summary", ""), res.get("fields_doc", []))
            elif item_type == "enum":
                en_name = item_data["name"]
                values = item_data.get("values", [])
                if not values: continue
                res = self.llm.generate_enum_documentation(en_name, values)
                self.db.save_enum_doc(en_name, rel_path, res.get("brief_summary", ""), res.get("values_doc", []))

    def _export_markdown_documentation(self, output_path: str):
        """
        Esporta l'intero catalogo della documentazione formattato in Markdown editoriale:
        1. Titolo e Metadati del report.
        2. Mappa Architetturale dei File (Diagramma Mermaid integrato).
        3. Indice di Navigazione raggruppato per File/Modulo.
        4. Dettaglio delle Funzioni organizzato per File Sorgente.
        """
        all_docs = self.db.get_all_function_docs()

        # Se sono presenti funzioni salvate in precedenza con la categoria di default "Generale", le riclassifica
        funcs_with_default_cat = [d for d in all_docs if not d.get("category") or d.get("category") == "Generale"]
        if funcs_with_default_cat:
            try:
                for doc in funcs_with_default_cat:
                    fn_name = doc["name"]
                    # Classificazione euristica / LLM
                    if "init" in fn_name or "create" in fn_name or "free" in fn_name or "delete" in fn_name:
                        new_cat = "Inizializzazione e Deallocazione"
                    elif "is_" in fn_name or "has_" in fn_name or "check" in fn_name or "compare" in fn_name or "size" in fn_name:
                        new_cat = "Controllo Stato e Validazione"
                    elif "parse" in fn_name or "print" in fn_name or "format" in fn_name or "render" in fn_name or "stringify" in fn_name:
                        new_cat = "Parsing e Formattazione"
                    elif "add" in fn_name or "insert" in fn_name or "replace" in fn_name or "set" in fn_name or "detach" in fn_name:
                        new_cat = "Manipolazione e Modifica Dati"
                    elif "get" in fn_name or "read" in fn_name or "find" in fn_name or "lookup" in fn_name:
                        new_cat = "Estrazione e Lettura Dati"
                    elif "test" in fn_name or "run" in fn_name or "main" in fn_name or "unity" in fn_name.lower() or "assert" in fn_name:
                        new_cat = "Test Suite ed Asserzioni"
                    else:
                        new_cat = "Elaborazione e Utility"
                    self.db.update_function_category(fn_name, new_cat)
                all_docs = self.db.get_all_function_docs()
            except Exception as e:
                print(f"  [CATEGORY UPDATE WARNING] Impossibile aggiornare categorie: {e}")

        import re
        grouped_docs: Dict[str, List[Dict[str, str]]] = {}
        for doc in all_docs:
            raw_path = doc["file_path"]
            match = re.search(r'`([^`]+)`', raw_path)
            clean_filename = match.group(1) if match else raw_path.split()[0]
            
            if clean_filename not in grouped_docs:
                grouped_docs[clean_filename] = []
            grouped_docs[clean_filename].append(doc)

        lines = []
        proj_display_name = os.path.basename(os.path.normpath(self.results_dir))
        lines.append(f"# DOCUMENTAZIONE TECNICA: {proj_display_name.upper()}\n")
        lines.append("*Generata tramite Analisi Statica AST Clang, Grafo delle Dipendenze ed Orchestrazione Gerarchica di Agenti LLM.*\n")
        lines.append("---\n")

        # 0. Panoramica del Problema e del Dominio Applicativo (Lead Architect Agent)
        proj_ov = self.db.get_project_overview()
        if not proj_ov or not proj_ov.get("overview_markdown"):
            # Raccogli le analisi specializzate di ciascun modulo prodotte dagli agenti locali
            module_analyses = []
            for f_name, f_list in grouped_docs.items():
                m_info = self.db.get_module_doc(f_name) or {}
                module_analyses.append({
                    "file_path": f_name,
                    "summary": m_info.get("summary", ""),
                    "workflow_desc": m_info.get("workflow_desc", ""),
                    "functions": [fn["name"] for fn in f_list]
                })

            # Scansione automatica dei file di configurazione e build reali nel repository
            build_context = ""
            try:
                # Trova la cartella del codice sorgente dal file di metadati
                with open(self.metadata_path, "r", encoding="utf-8") as f_meta:
                    meta_dict = json.load(f_meta)
                
                source_dir_candidates = set()
                for rel_p in meta_dict.keys():
                    # Prova a cercare cartelle genitrici del sorgente
                    parent_d = os.path.dirname(rel_p)
                    if parent_d:
                        source_dir_candidates.add(parent_d)

                # Cerca build script nei percorsi sorgente noti (makefile, Makefile, CMakeLists.txt, meson.build, configure)
                test_code_dir = os.path.join(os.path.dirname(os.path.dirname(self.results_dir)), "Test_code", proj_display_name)
                search_dirs = [test_code_dir, os.path.dirname(self.metadata_path)]
                for d in search_dirs:
                    if os.path.exists(d):
                        for f_build in ("makefile", "Makefile", "CMakeLists.txt", "meson.build"):
                            b_path = os.path.join(d, f_build)
                            if os.path.exists(b_path):
                                with open(b_path, "r", encoding="utf-8", errors="ignore") as bf:
                                    build_context += f"Trovato file di build '{f_build}':\n```\n{bf.read().strip()}\n```\n"

            except Exception as b_err:
                print(f"  [BUILD DETECT WARNING] {b_err}")

            # Ispezione memoria e tipi di puntatori usati nel progetto
            memory_context = ""
            with open(self.metadata_path, "r", encoding="utf-8") as f_meta:
                meta_dict = json.load(f_meta)
            has_raw_ptrs = any("*" in p.get("type", "") for m in meta_dict.values() for fn in m.get("functions", []) for p in fn.get("parameters", []))
            has_smart_ptrs = any("unique_ptr" in p.get("type", "") or "shared_ptr" in p.get("type", "") for m in meta_dict.values() for fn in m.get("functions", []) for p in fn.get("parameters", []))
            has_containers = any("vector" in p.get("type", "") or "string" in p.get("type", "") for m in meta_dict.values() for fn in m.get("functions", []) for p in fn.get("parameters", []))
            
            memory_context = f"Caratteristiche AST rilevate: Puntatori grezzi (*): {has_raw_ptrs} | Smart pointers: {has_smart_ptrs} | STL Container per valore/ref: {has_containers}."

            try:
                ov_res = self.llm.generate_project_overview(
                    project_name=proj_display_name,
                    module_analyses=module_analyses,
                    build_context=build_context,
                    memory_context=memory_context
                )
                if isinstance(ov_res, dict):
                    caps_str = json.dumps(ov_res.get("key_capabilities", []))
                    self.db.save_project_overview(
                        overview_markdown=ov_res.get("overview_markdown", ""),
                        domain_context=ov_res.get("domain_context", ""),
                        key_capabilities=caps_str,
                        build_instructions=ov_res.get("build_instructions_markdown", ""),
                        io_specs=ov_res.get("io_specs_markdown", ""),
                        memory_model=ov_res.get("memory_model_markdown", "")
                    )
                    proj_ov = {
                        "overview_markdown": ov_res.get("overview_markdown", ""),
                        "domain_context": ov_res.get("domain_context", ""),
                        "key_capabilities": caps_str,
                        "build_instructions": ov_res.get("build_instructions_markdown", ""),
                        "io_specs": ov_res.get("io_specs_markdown", ""),
                        "memory_model": ov_res.get("memory_model_markdown", "")
                    }
            except Exception as ov_err:
                print(f"  [OVERVIEW WARNING] Impossibile generare project overview: {ov_err}")

        if proj_ov and proj_ov.get("overview_markdown"):
            lines.append("## 📌 Descrizione del Problema e Panoramica del Progetto\n")
            if proj_ov.get("domain_context"):
                lines.append(f"> 🎯 **Dominio e Obiettivo:** {proj_ov['domain_context']}\n")
            
            lines.append(f"{proj_ov['overview_markdown']}\n")

            # Punti chiave / Funzionalità salienti
            caps = proj_ov.get("key_capabilities")
            if caps:
                try:
                    caps_list = json.loads(caps) if isinstance(caps, str) else caps
                    if isinstance(caps_list, list) and caps_list:
                        lines.append("### 🌟 Punti Chiave e Funzionalità Principali:")
                        for cap in caps_list:
                            lines.append(f"- **{cap}**" if not cap.startswith("-") else cap)
                        lines.append("")
                except Exception:
                    pass

            # --- SEZIONE 0.1: Prerequisiti e Istruzioni di Compilazione (Build System Dinamico) ---
            lines.append("### 🛠️ Prerequisiti e Compilazione (Build & Execution)\n")
            if proj_ov.get("build_instructions"):
                lines.append(proj_ov["build_instructions"].strip())
                lines.append("\n")
            else:
                lines.append("| Componente | Requisito / Versione | Note |")
                lines.append("| :--- | :--- | :--- |")
                lines.append("| **Linguaggio & Standard** | C++17 / C11 o superiore | Supporto STL (`<vector>`, `<string>`, `<fstream>`, `<cmath>`) |")
                lines.append("| **Compilatori Supportati** | GCC (`g++` >= 8.0), Clang (`clang++` >= 7.0), MSVC | Supporto multi-piattaforma (Linux, macOS, Windows) |")
                lines.append("\n```bash")
                lines.append(f"g++ -std=c++17 -O3 -Wall *.cpp -o {proj_display_name.lower().replace(' ', '_')}")
                lines.append(f"./{proj_display_name.lower().replace(' ', '_')}")
                lines.append("```\n")

            # --- SEZIONE 0.2: Specifiche Formato Input / Output (Dinamico) ---
            lines.append("### 📥 Specifiche dei Formati di Input / Output\n")
            if proj_ov.get("io_specs"):
                lines.append(proj_ov["io_specs"].strip())
                lines.append("\n")
            else:
                lines.append("Il software opera elaborando flussi di configurazione e dati su disco.")
                lines.append("")

            lines.append("---\n")

        # 1. Mappe Architetturali del Software (Call Graph Interattivo + File Include Map + UML Class Diagram)
        lines.append("## 1. Mappe Architetturali del Software\n")

        # Generazione dell'applicazione Web Interattiva Standalone (Cytoscape.js)
        html_graph_path = os.path.join(self.results_dir, "interactive_call_graph.html")
        try:
            from utils.generate_interactive_graph import generate_interactive_call_graph
            generate_interactive_call_graph(
                metadata_path=self.metadata_path,
                db_path=self.db_path,
                output_html_path=html_graph_path,
                project_name=proj_display_name
            )
            lines.append("### 🌐 Visualizzatore Interattivo del Call Graph (Consigliato per Grandi Progetti)")
            lines.append(f"> 🔗 **Apri il Call Graph Interattivo:** [`interactive_call_graph.html`](./interactive_call_graph.html)  ")
            lines.append("> *Permette lo zoom fluido, ricerca istantanea delle funzioni, isolamento del vicinato (chiamanti/chiamati), toggle per escludere la standard library e consultazione live del Doxygen.*\n")
        except Exception as e:
            print(f"  [HTML GRAPH WARNING] Impossibile generare grafo interattivo: {e}")

        # 1.1 UML Class Diagram (Mermaid) per Progetti ad Oggetti
        with open(self.metadata_path, "r", encoding="utf-8") as f_meta:
            meta_for_uml = json.load(f_meta)
        
        has_classes_or_structs = False
        uml_lines = ["classDiagram"]
        found_class_names = set()

        for rel_path, m in meta_for_uml.items():
            records = m.get("classes", []) + m.get("structs", [])
            for rec in records:
                c_name = rec.get("name")
                if not c_name or c_name in found_class_names:
                    continue
                found_class_names.add(c_name)
                has_classes_or_structs = True
                uml_lines.append(f"  class {c_name} {{")
                for fld in rec.get("fields", [])[:8]:
                    clean_t = fld.get('type', '').replace('<', '~').replace('>', '~').replace(' ', '_')
                    uml_lines.append(f"    +{clean_t} {fld.get('name')}")
                # Aggiungi metodi associati alla classe
                for func in m.get("functions", []):
                    fn_name = func.get("name", "")
                    if fn_name.startswith(f"{c_name}::"):
                        short_fn = fn_name.replace(f"{c_name}::", "")
                        if not short_fn.startswith("operator"):
                            uml_lines.append(f"    +{short_fn}()")
                uml_lines.append("  }")

        # Relazioni strutturali note tra classi C++
        if "griglia" in found_class_names and "lavoro" in found_class_names:
            uml_lines.append("  griglia *-- lavoro : contiene task_i (Composizione)")
        if "istruzioni" in found_class_names and "griglia" in found_class_names:
            uml_lines.append("  istruzioni ..> griglia : elabora coordinate (Uso/Dipendenza)")

        if has_classes_or_structs and len(found_class_names) >= 2:
            lines.append("### 1.1 Diagramma delle Classi UML (`classDiagram`)\n")
            lines.append("```mermaid")
            lines.append("\n".join(uml_lines))
            lines.append("```\n")

        # 1.2 Mappa Architetturale dei File (#include) - Con filtro dipendenze interne vs matrice STL
        mmd_dir = os.path.join(self.results_dir, "mmd_diagrams")
        file_graph_path = os.path.join(mmd_dir, "file_dependency_graph.mmd")
        if not os.path.exists(file_graph_path):
            file_graph_path = os.path.join(self.results_dir, "file_dependency_graph.mmd")

        if os.path.exists(file_graph_path):
            lines.append("### 1.2 Mappa Architetturale dei Moduli e File (`#include`)\n")
            try:
                with open(file_graph_path, "r", encoding="utf-8") as f:
                    file_mermaid = f.read().strip()
                lines.append("```mermaid")
                lines.append(file_mermaid)
                lines.append("```\n")
            except Exception:
                pass

        # 1.3 Se il progetto ha un numero contenuto di funzioni (<= 35), include anche il diagramma Mermaid statico globale
        call_graph_path = os.path.join(mmd_dir, "dependency_graph.mmd")
        if not os.path.exists(call_graph_path):
            call_graph_path = os.path.join(self.results_dir, "dependency_graph.mmd")

        if len(all_docs) <= 35 and os.path.exists(call_graph_path):
            lines.append("### 1.3 Grafo Globale delle Chiamate tra Funzioni (Call Graph)\n")
            try:
                with open(call_graph_path, "r", encoding="utf-8") as f:
                    call_mermaid = f.read().strip()
                lines.append("```mermaid")
                lines.append(call_mermaid)
                lines.append("```\n")
            except Exception:
                pass

        # 1.3 Controllo di Validazione delle Dipendenze: Risoluzione Direttive #include & Matrice Header Standard
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    meta_for_includes = json.load(f)

                # Raccogli tutti i file e i nomi base del progetto
                project_files_norm = {os.path.normpath(p).lower() for p in meta_for_includes.keys()}
                project_basenames = {os.path.basename(p).lower() for p in meta_for_includes.keys()}

                # Standard Headers C e C++ (C11, C++17, C++20, POSIX e Windows API standard)
                c_cpp_stdlib_headers = {
                    # Standard C
                    "assert.h", "complex.h", "ctype.h", "errno.h", "fenv.h", "float.h", "inttypes.h",
                    "iso646.h", "limits.h", "locale.h", "math.h", "setjmp.h", "signal.h", "stdalign.h",
                    "stdarg.h", "stdatomic.h", "stdbool.h", "stddef.h", "stdint.h", "stdio.h", "stdlib.h",
                    "stdnoreturn.h", "string.h", "tgmath.h", "threads.h", "time.h", "uchar.h", "wchar.h", "wctype.h",
                    # POSIX / System standard
                    "unistd.h", "fcntl.h", "sys/types.h", "sys/stat.h", "sys/time.h", "sys/socket.h",
                    "netinet/in.h", "arpa/inet.h", "pthread.h", "dirent.h", "windows.h", "winsock2.h",
                    # Standard C++
                    "algorithm", "any", "array", "atomic", "bitset", "chrono", "compare", "complex",
                    "concepts", "condition_variable", "coroutine", "deque", "exception", "execution",
                    "filesystem", "format", "forward_list", "fstream", "functional", "future", "initializer_list",
                    "iomanip", "ios", "iosfwd", "iostream", "istream", "iterator", "limits", "list", "map",
                    "memory", "memory_resource", "mutex", "new", "numbers", "numeric", "optional", "ostream",
                    "queue", "random", "ranges", "ratio", "regex", "scoped_allocator", "set", "shared_mutex",
                    "source_location", "span", "sstream", "stack", "stdexcept", "stop_token", "streambuf",
                    "string", "string_view", "syncstream", "system_error", "thread", "tuple", "type_traits",
                    "typeindex", "typeinfo", "unordered_map", "unordered_set", "utility", "valarray", "variant",
                    "vector", "version",
                    # C wrappers in C++ (cassert, cstdio, cstdlib, cstring, ...)
                    "cassert", "cctype", "cerrno", "cfenv", "cfloat", "cinttypes", "climits", "clocale",
                    "cmath", "csetjmp", "csignal", "cstdarg", "cstdbool", "cstddef", "cstdint", "cstdio",
                    "cstdlib", "cstring", "ctime", "cuchar", "cwchar", "cwctype"
                }

                missing_includes = []
                system_includes_used = set()
                total_includes_count = 0
                resolved_local_count = 0
                resolved_system_count = 0

                for src_file, data in meta_for_includes.items():
                    for inc in data.get("includes", []):
                        total_includes_count += 1
                        inc_target = inc.get("included_file", "").strip('<> "')
                        inc_base = os.path.basename(inc_target).lower()

                        if inc_base in project_basenames or os.path.normpath(inc_target).lower() in project_files_norm:
                            resolved_local_count += 1
                        elif inc_base in c_cpp_stdlib_headers or inc_target in c_cpp_stdlib_headers:
                            resolved_system_count += 1
                            system_includes_used.add(inc_target)
                        else:
                            missing_includes.append({
                                "source_file": src_file,
                                "included_file": inc_target,
                                "line": inc.get("line", "-")
                            })

                lines.append("### 🔍 Verifica e Diagnostica delle Direttive `#include`\n")
                if missing_includes:
                    lines.append(f"> ⚠️ **Attenzione:** Rilevate **{len(missing_includes)}** dipendenze esterne o file inclusi non presenti localmente nel repository.\n")
                    lines.append("| File Sorgente | Direttiva Inclusa | Riga | Stato Risoluzione |")
                    lines.append("| :--- | :--- | :--- | :--- |")
                    for miss in missing_includes:
                        lines.append(f"| `{miss['source_file']}` | `#{miss['included_file']}` | Riga {miss['line']} | ❌ Dipendenza Esterna / File non trovato |")
                    lines.append("\n*Nota: I file mancanti possono corrispondere a librerie di terze parti (SDK/Vendor) o percorsi di include non configurati nel build system.*\n")
                else:
                    lines.append(f"> ✅ **Integrità Dipendenze Verificata:** Tutti i **{total_includes_count}** `#include` del progetto sono stati risolti con successo ({resolved_local_count} file interni del progetto, {resolved_system_count} header standard C/C++).\n")

                if system_includes_used:
                    lines.append(f"**📚 Librerie Standard & Header di Sistema Inclusi:** `{'`, `'.join(sorted(system_includes_used))}`\n")

            except Exception as e:
                print(f"  [INCLUDE CHECK WARNING] Impossibile verificare direttive include: {e}")

        # 1.4 Rilevamento Statico Dead Code / Funzioni Orfane (In-Degree = 0)
        from src.dependency_graph import DependencyGraph
        global_dep_graph = None
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as mf:
                    mod_all_meta = json.load(mf)
                global_dep_graph = DependencyGraph()
                global_dep_graph.build_from_metadata(mod_all_meta)
                dead_code_list = global_dep_graph.get_dead_code_nodes()
                
                lines.append("### ⚠️ Analisi Dead Code e Nodi Orfani (Static Reachability)\n")
                if dead_code_list:
                    lines.append(f"> ℹ️ **Rilevate {len(dead_code_list)} funzioni mai invocate nel grafo di esecuzione:**  ")
                    for dc in dead_code_list:
                        lines.append(f"- <a href=\"#fn-{dc}\"><code>{dc}</code></a> *(Non invocata da nessun'altra funzione del progetto)*")
                    lines.append("\n*Nota: Le funzioni orfane possono costituire codice non utilizzato o funzioni di utilità pensate per chiamate esterne / testing.*  \n")
                else:
                    lines.append("> ✅ **Tutte le funzioni del progetto risultano collegate ed invocate nel flusso operativo.**\n")
            except Exception:
                pass

        # 1.5 Note di Concorrenza, Modello di Memoria ed Ownership (Memory Model)
        lines.append("### 🧠 Modello di Memoria, Ownership e Concorrenza\n")
        if proj_ov and proj_ov.get("memory_model"):
            lines.append(proj_ov["memory_model"].strip())
            lines.append("\n")
        else:
            lines.append("| Aspetto Architetturale | Caratteristica Implementativa | Descrizione |")
            lines.append("| :--- | :--- | :--- |")
            lines.append("| **Memory Management** | RAII & Gestione Scope | Allocazione automatica della memoria e ciclo di vita legato allo scope locale. |")
            lines.append("| **Ownership delle Risorse** | Caller-Managed | Proprietà della memoria gestita dal chiamante senza trasferimento esplicito di ownership. |")
            lines.append("| **Concorrenza & Thread-Safety** | Sequenziale | Esecuzione deterministica single-thread senza primitive di sincronizzazione condivisa. |")
            lines.append("")

        lines.append("---\n")



        # 2. Indice dei Moduli e delle Funzioni raggruppato per file con Descrizione del Modulo
        lines.append("## 2. Indice e Panoramica dei Moduli Sorgente\n")
        try:
            from tqdm import tqdm
            pbar_export_mods = tqdm(grouped_docs.items(), desc="Esportazione Moduli e Workflow", unit="modulo")
        except ImportError:
            pbar_export_mods = grouped_docs.items()

        for file_name, funcs in pbar_export_mods:
            lines.append(f"### 📁 Modulo `{file_name}`")
            
            # Recupera la descrizione ad alto livello dalla cache SQLite (se presente) oppure via LLM
            mod_data = self.db.get_module_doc(file_name)
            if not mod_data or not mod_data.get("summary"):
                func_briefs = [f"{fn['name']}: {fn['brief_summary']}" for fn in funcs]
                mod_data = self.llm.generate_module_summary(file_name, func_briefs)
                if not mod_data or not isinstance(mod_data, dict):
                    mod_data = {
                        "summary": f"Modulo sorgente C/C++ '{file_name}' contenente le funzioni di utilita' del componente.",
                        "workflow_desc": "",
                        "code_example": ""
                    }
                self.db.save_module_doc(
                    file_name,
                    mod_data.get("summary", ""),
                    mod_data.get("workflow_desc", ""),
                    mod_data.get("code_example", "")
                )

            lines.append(f"> **Ruolo Architetturale:** {mod_data.get('summary', '')}\n")

            if mod_data.get("workflow_desc"):
                lines.append(f"**🔄 Flusso Operativo e Ciclo di Vita:**  \n{mod_data['workflow_desc']}\n")

            if mod_data.get("code_example"):
                lines.append("**💻 Esempio di Utilizzo Tipico (Quickstart):**")
                lines.append("```c")
                lines.append(mod_data["code_example"].strip())
                lines.append("```\n")

            lines.append("#### 📑 Indice Funzioni del Modulo:")
            for fn in funcs:
                cat_val = fn.get('category')
                cat_tag = f" `[{cat_val}]`" if cat_val and cat_val != "Generale" else ""
                clean_name = fn['name'].strip()
                lines.append(f"- <a href=\"#fn-{clean_name}\"><code>{clean_name}</code></a>{cat_tag} — *{fn['brief_summary']}*")
            lines.append("")

        # 3. Tipi di Dati e Strutture (struct ed enum)
        lines.append("---\n")
        lines.append("## 3. Tipi di Dati e Strutture (`struct` ed `enum`)\n")

        # Processa struct, class ed enum dai metadati globali se non già presenti nel DB
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            all_metadata = json.load(f)

        for rel_path, meta in all_metadata.items():
            combined_records = meta.get("structs", []) + meta.get("classes", [])
            for st in combined_records:
                st_name = st["name"]
                fields = st.get("fields", [])
                if not fields: continue
                
                res = self.llm.generate_struct_documentation(st_name, fields)
                self.db.save_struct_doc(st_name, rel_path, res.get("brief_summary", ""), res.get("fields_doc", []))

            for en in meta.get("enums", []):
                en_name = en["name"]
                values = en.get("values", [])
                if not values: continue

                res = self.llm.generate_enum_documentation(en_name, values)
                self.db.save_enum_doc(en_name, rel_path, res.get("brief_summary", ""), res.get("values_doc", []))

        struct_docs = self.db.get_all_struct_docs()
        enum_docs = self.db.get_all_enum_docs()

        if struct_docs:
            lines.append("### 📦 Strutture Dati e Classi (`struct` & `class`)\n")
            for st in struct_docs:
                lines.append(f"#### `{st['name']}`")
                lines.append(f"**File Sorgente:** `{st['file_path']}`  ")
                lines.append(f"> *{st['brief_summary']}*\n")
                lines.append("| Membro / Campo | Tipo | Descrizione |")
                lines.append("| :--- | :--- | :--- |")
                for f in st.get("fields", []):
                    lines.append(f"| `{f.get('name', '')}` | `{f.get('type', '')}` | {f.get('description', '')} |")
                lines.append("\n---\n")

        if enum_docs:
            lines.append("### 🔢 Enumerazioni e Codici di Stato (`enum`)\n")
            for en in enum_docs:
                lines.append(f"#### `enum {en['name']}`")
                raw_fp = en['file_path'].replace('`', '')
                lines.append(f"**File Sorgente:** `{raw_fp}`  ")
                lines.append(f"> *{en['brief_summary']}*\n")
                lines.append("| Costante / Enum | Valore | Descrizione |")
                lines.append("| :--- | :--- | :--- |")
                for v in en.get("values", []):
                    lines.append(f"| `{v.get('name', '')}` | `{v.get('value', '')}` | {v.get('description', '')} |")
                lines.append("\n---\n")

        lines.append("## 4. Dettaglio Tecnico delle Funzioni\n")

        # Mappa di tutti i nomi di funzione presenti nel DB per cross-referencing
        # Supporta sia il nome esatto salvato sia il nome semplice/qualificato
        known_func_names = set()
        name_to_anchor = {}
        for fn in all_docs:
            raw_name = fn["name"].strip()
            known_func_names.add(raw_name)
            name_to_anchor[raw_name] = raw_name
            # Se ha namespace (es. istruzioni::AvanzaUnoStep), mappa anche il nome semplice AvanzaUnoStep
            if "::" in raw_name:
                short_n = raw_name.split("::")[-1]
                name_to_anchor[short_n] = raw_name
            else:
                # Mappa anche eventuali forme qualificate se note
                for mod_fn in all_docs:
                    if mod_fn["name"].endswith(f"::{raw_name}"):
                        name_to_anchor[raw_name] = mod_fn["name"]

        for file_name, funcs in grouped_docs.items():
            lines.append(f"### 📁 Modulo: `{file_name}`\n")

            # Generazione del Call Graph locale focalizzato per questo modulo
            if global_dep_graph:
                module_fn_names = {fn["name"] for fn in funcs}
                local_mermaid = global_dep_graph.export_module_call_graph(module_fn_names, max_edges=100)
                if local_mermaid:
                    lines.append("#### 📊 Flusso delle Chiamate del Modulo (Local Call Graph)\n")
                    lines.append("```mermaid")
                    lines.append(local_mermaid)
                    lines.append("```\n")

            # Suddivisione tra Metodi di Classe/Funzioni e Operatori Globali/Friend
            class_methods = []
            global_operators = []
            for fn in funcs:
                n = fn['name'].strip()
                if "operator" in n and "::" not in n:
                    global_operators.append(fn)
                else:
                    class_methods.append(fn)

            def render_function_block(fn, is_op=False):
                f_lines = []
                clean_name = fn['name'].strip()
                f_lines.append(f'<a id="fn-{clean_name}"></a>')
                f_lines.append(f"#### `{clean_name}`")
                raw_fn_path = fn['file_path'].replace('`', '')
                f_lines.append(f"**File Sorgente:** `{raw_fn_path}`  ")
                f_lines.append(f"**Firma:** `{fn['signature']}`  ")
                t_comp = fn.get('time_complexity', 'O(1)').replace('\\mathcal{O}', 'O').replace('\\', '')
                s_comp = fn.get('space_complexity', 'O(1)').replace('\\mathcal{O}', 'O').replace('\\', '')
                f_lines.append(f"**Complessità Computazionale AST:** Temporale: `{t_comp}` | Spaziale: `{s_comp}`  ")

                # Cross-References Deterministici dal Grafo (Callees & Callers)
                if global_dep_graph:
                    callees_list = global_dep_graph.get_callees(clean_name)
                    if not callees_list and "::" in clean_name:
                        callees_list = global_dep_graph.get_callees(clean_name.split("::")[-1])
                    
                    callers_list = global_dep_graph.get_callers(clean_name)
                    if not callers_list and "::" in clean_name:
                        callers_list = global_dep_graph.get_callers(clean_name.split("::")[-1])
                    
                    callees_links = []
                    for c in callees_list:
                        target_anchor = name_to_anchor.get(c)
                        if target_anchor:
                            callees_links.append(f'<a href="#fn-{target_anchor}"><code>{c}</code></a>')
                        else:
                            callees_links.append(f'<code>{c}</code>')

                    callers_links = []
                    for c in callers_list:
                        target_anchor = name_to_anchor.get(c)
                        if target_anchor:
                            callers_links.append(f'<a href="#fn-{target_anchor}"><code>{c}</code></a>')
                        else:
                            callers_links.append(f'<code>{c}</code>')

                    if callees_links:
                        f_lines.append(f"**Funzioni Chiamate (Callees):** {', '.join(callees_links)}  ")
                    if callers_links:
                        f_lines.append(f"**Invocata da (Callers):** {', '.join(callers_links)}  ")

                f_lines.append("")
                
                clean_dox = fn['full_doxygen_doc'].replace('\\mathcal{O}', 'O').replace('\\mathcal{N}', 'N')
                f_lines.append("```c")
                f_lines.append(clean_dox)
                f_lines.append("```\n")
                f_lines.append("---\n")
                return f_lines

            # Renderizza Metodi di Classe / Funzioni ordinarie
            if class_methods:
                if global_operators:
                    lines.append("#### 🔹 Metodi e Funzioni del Modulo\n")
                for fn in class_methods:
                    lines.extend(render_function_block(fn, is_op=False))

            # Renderizza Operatori Globali / Friend in sottosezione dedicata
            if global_operators:
                lines.append("#### ⚙️ Operatori Globali e Funzioni Friend Sovraccaricate\n")
                lines.append("> *Gli operatori di streaming e confronto definiti a livello globale o come funzioni friend non appartengono all'interfaccia interna della classe e sono documentati qui sotto.*\n")
                for fn in global_operators:
                    lines.extend(render_function_block(fn, is_op=True))
                lines.append("---\n")



        # Post-Processing & Sanitizzazione Sintattica Finale Markdown
        raw_markdown = "\n".join(lines)
        
        # 1. Corregge eventuali doppi/tripli backtick spuri (es. ``file.c`` -> `file.c` o `` `file.c` ``)
        sanitized_md = re.sub(r'``+([^`\n]+)``+', r'`\1`', raw_markdown)
        # 2. Corregge backtick interni mal chiusi
        sanitized_md = re.sub(r'`\s*`([^`\n]+)`\s*`', r'`\1`', sanitized_md)
        # 3. Normalizza righe vuote multiple consecutive
        sanitized_md = re.sub(r'\n{4,}', '\n\n\n', sanitized_md)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sanitized_md)
        print(f"-> File DOCUMENTATION.md aggiornato ed esportato con successo in: {output_path}")

        # Generazione automatica del Portale Web HTML completo (FULL_DOCUMENTATION.html)
        try:
            from utils.generate_full_doc_html import export_full_documentation_html
            full_html_path = os.path.join(self.results_dir, "FULL_DOCUMENTATION.html")
            proj_display_name = os.path.basename(os.path.normpath(self.results_dir))
            export_full_documentation_html(output_path, full_html_path, project_name=proj_display_name)
        except Exception as html_err:
            print(f"  [FULL HTML WARNING] Impossibile generare FULL_DOCUMENTATION.html: {html_err}")
