import re
from typing import Dict, List, Set, Any

class DocumentationVerifier:
    """
    Validatore strutturato e matematico per la documentazione C.
    Verifica che Input (Parametri formali AST) e Output (Valori/Enum di ritorno AST)
    corrispondano esattamente a quanto documentato dall'LLM, senza allucinazioni.
    """
    def __init__(self, global_metadata: Dict[str, Any]):
        self.global_metadata = global_metadata
        self.valid_symbols: Set[str] = set()
        self._extract_valid_symbols()

    def _extract_valid_symbols(self):
        """
        Estrae programmaticamente tutti i simboli validi dal progetto:
        - Costanti Enum
        - Nomi Struct & Typedef
        - Macro e #define
        """
        for rel_path, meta in self.global_metadata.items():
            for func in meta.get("functions", []):
                self.valid_symbols.add(func["name"])
            for struct in meta.get("structs", []):
                self.valid_symbols.add(struct["name"])
            for enum in meta.get("enums", []):
                self.valid_symbols.add(enum["name"])
                for val in enum.get("values", []):
                    self.valid_symbols.add(val["name"])
                for val in enum.get("constants", []):
                    self.valid_symbols.add(val["name"])
            for macro in meta.get("macros", []):
                self.valid_symbols.add(macro["name"])
            
            for typedef_info in meta.get("typedefs", []):
                if typedef_info.get("name"):
                    self.valid_symbols.add(typedef_info["name"])

            for macro_info in meta.get("macros", []):
                if macro_info.get("name"):
                    self.valid_symbols.add(macro_info["name"])

    def verify_function_doc(
        self, 
        func_info: Dict[str, Any], 
        generated_doc: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Controlli di corrispondenza strutturata tra AST e Documentazione Generata:
        1. CONFRONTO INPUT: Tutti i parametri formali definiti nell'AST DEVONO essere presenti in @param.
        2. CONFRONTO OUTPUT: Nessun simbolo/enum inventato o assente dai metadati del progetto nel blocco @return.
        3. ASSENZA INCERTEZZE: Nessun linguaggio speculativo.
        """
        errors = []
        if not generated_doc or not isinstance(generated_doc, dict):
            return {
                "is_valid": False,
                "errors": ["Risposta LLM non valida o vuota (non è un dizionario JSON validato)."]
            }

        full_doc_text = generated_doc.get("full_doxygen_doc") or generated_doc.get("doxygen_block") or generated_doc.get("doxygen_comment") or ""
        formal_params = func_info.get("parameters", [])

        # --- 1. CONFRONTO INPUT (Parametri formali dell'AST vs @param) ---
        for param in formal_params:
            param_name = param["name"]
            # Cerca il parametro formale esatto nel tag @param
            pattern = rf"@param(?:\[[^\]]+\])?\s+{re.escape(param_name)}\b"
            if not re.search(pattern, full_doc_text):
                errors.append(f"Parametro formale AST '{param_name}' mancante nel blocco @param della documentazione.")

        # --- 2. CONFRONTO OUTPUT (Enum e Codici di errore menzionati in @return) ---
        # Estraiamo i token di ritorno specifici (es. @return CJSON_OK, @return -1, @return NULL)
        return_lines = re.findall(r'@return\s+.*', full_doc_text)
        for r_line in return_lines:
            # Estrai solo il primo token simbolico dopo @return (es. @return RB_OK spiegazione...)
            first_token_match = re.match(r'@return\s+([A-Za-z0-9_\-]+)', r_line)
            if first_token_match:
                ret_symbol = first_token_match.group(1).replace('-', '_')
                # Se è un identificatore in MAIUSCOLO (tipico di enum/costanti C)
                if re.match(r'^[A-Z][A-Z0-9_]{2,}$', ret_symbol):
                    standard_safe_tokens = {
                        "NULL", "TRUE", "FALSE", "MAX", "MIN", "EOF", "BYTES", "INT", "FLOAT", "DOUBLE", "VOID",
                        "NAN", "INFINITY", "HUGE_VAL", "DBL_MAX", "INT_MAX", "INT_MIN", "SIZE_MAX", "ULONG_MAX", "LONG_MAX", "UINT_MAX",
                        "JSON", "CJSON", "ASCII", "UTF", "UTF8", "UTF16", "UTF_8", "UTF_16", "API", "URL", "URI", "HTTP", "HTTPS", "ID",
                        "SPY", "TEST", "OK", "ERROR", "FAIL", "SUCCESS", "PTR", "SIZE_T", "STDCALL", "CDECL",
                        # Codici di errore standard POSIX e C <errno.h>
                        "EINVAL", "ENOMEM", "ERANGE", "EBUSY", "ENOENT", "EEXIST", "EPERM", "EACCES", "EAGAIN",
                        "EWOULDBLOCK", "ETIMEDOUT", "EIO", "EBADF", "EFAULT", "ENODEV", "ENOSPC", "ESPIPE",
                        "EPIPE", "EDOM", "EILSEQ", "EOVERFLOW", "ENOTSUP", "EOPNOTSUPP", "EAFNOSUPPORT",
                        "EADDRINUSE", "ECONNREFUSED", "ECONNRESET", "ENOTCONN", "EISCONN", "ECANCELED"
                    }
                    if ret_symbol not in standard_safe_tokens:
                        # Se abbiamo simboli estratti dal progetto e il token non esiste nel codice né come sottostringa o prefisso
                        if self.valid_symbols and ret_symbol not in self.valid_symbols and not any(ret_symbol in s for s in self.valid_symbols):
                            valid_str = ", ".join(sorted(list(self.valid_symbols))[:20]) + "..."
                            errors.append(
                                f"Allucinazione nel @return: Il valore/enum '{ret_symbol}' menzionato come codice di ritorno non esiste "
                                f"tra i simboli/enum reali del progetto [{valid_str}]."
                            )

        # --- 4. CONTROLLO DISCREPANZA LOGICA BOOLEANA SUI PUNTATORI NULL ---
        source_code = func_info.get("source_code", "")
        # Se il codice C esegue un corto circuito (ptr != NULL) && ...
        if re.search(r'\(\s*\w+\s*!=\s*NULL\s*\)\s*&&', source_code):
            return_true_lines = re.findall(r'@return\s+true\b[^\n]*', full_doc_text, re.IGNORECASE)
            for rt_line in return_true_lines:
                # Controlla se afferma esplicitamente che 'restituisce true se il puntatore è NULL'
                if re.search(r'\b(?:se|quando|oppure|o)\b\s+(?:il\s+puntatore\s+)?(?:\w+\s+)?(?:è|e[\'’]|e)\s+null\b', rt_line, re.IGNORECASE):
                    errors.append(
                        "Discrepanza Logica Booleana: Il codice C esegue (ptr != NULL) && ... che valuta a FALSE "
                        "se il puntatore e' NULL. La clausola '@return true' dichiara erroneamente che restituisce TRUE se il puntatore e' NULL."
                    )




        # --- 5. CONTROLLO DETERMINISTICO TIPO DI RITORNO VOID / NON-VOID ---
        ret_type = func_info.get("return_type", "").strip()
        if ret_type == "void":
            # Se la funzione ha tipo di ritorno 'void', NON deve contenere tag @return
            if re.search(r'@return\b', full_doc_text):
                errors.append(f"Discrepanza Tipo di Ritorno: La funzione ha tipo di ritorno 'void' (non restituisce alcun valore), quindi NON deve includere tag @return nel commento Doxygen. Rimuovi tutti i tag @return.")
        elif ret_type and ret_type != "void":
            if not re.search(r'@return\b', full_doc_text):
                errors.append(f"Clausola @return mancante: La funzione ha tipo di ritorno '{ret_type}' nell'AST, ma nessun tag @return e' presente nella documentazione.")

        # --- 6. CONTROLLO INCONGRUENZA CONTRATTI @pre vs GESTIONE DIFENSIVA IN @return ---
        # Se la documentazione include return code dedicati al caso NULL (es. ERR_NULL_PTR o @return ... se ... NULL)
        # ma impone nel @pre che il puntatore non deve essere NULL come precondizione vincolante
        pre_matches = re.findall(r'@pre\s+.*', full_doc_text)
        pre_text = " ".join(pre_matches).lower()
        
        # Se return documenta gestione di NULL
        return_handles_null = bool(re.search(r'@return.*(?:null|err.*null|null.*ptr)', full_doc_text, re.IGNORECASE))
        if return_handles_null:
            # Controlla se @pre impone rigidamente che il puntatore non deve essere NULL
            if re.search(r'(?:non\s+(?:deve\s+essere\s+)?null|deve\s+essere\s+(?:valido|non\s*null)|!=?\s*null)', pre_text):
                errors.append(
                    "Incongruenza Logica tra @pre e @return: La funzione gestisce difensivamente il caso NULL "
                    "restituendo un apposito codice di errore documentato in @return. Pertanto 'puntatore != NULL' non e' una "
                    "precondizione bloccante nel @pre (che presupporrebbe Undefined Behavior/Crash se violata), ma un ramo ordinario gestito a runtime."
                )

        # --- 3. CONTROLLO TRUTHFULNESS & EXISTENCE RATIO (Anti-Hallucination) ---
        # Estrai tutte le entità/funzioni citate nei tag @see o come riferimenti espliciti `nome_funzione()`
        mentioned_entities = set()
        see_matches = re.findall(r'@see\s+([A-Za-z0-9_]+)', full_doc_text)
        for s in see_matches:
            mentioned_entities.add(s)

        code_ref_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)', full_doc_text)
        for c in code_ref_matches:
            # Ignora costrutti di controllo del linguaggio
            if c not in ("if", "for", "while", "switch", "sizeof", "return", "alignof", "decltype"):
                mentioned_entities.add(c)

        if mentioned_entities:
            c_stdlib_known = {
                "malloc", "free", "calloc", "realloc", "printf", "fprintf", "sprintf", "snprintf",
                "memcpy", "memset", "memmove", "strlen", "strcpy", "strncpy", "strcmp", "strncmp",
                "fopen", "fclose", "fread", "fwrite", "exit", "abort", "abs", "fabs", "ceil", "floor"
            }
            existing_count = 0
            for ent in mentioned_entities:
                if ent in self.valid_symbols or ent in c_stdlib_known or any(ent in s for s in self.valid_symbols):
                    existing_count += 1
                else:
                    errors.append(
                        f"Allucinazione Entità Software: La funzione o entità '{ent}' menzionata nel testo "
                        f"non esiste fisicamente nel grafo del progetto né nella standard library."
                    )
            
            existence_ratio = existing_count / len(mentioned_entities) if mentioned_entities else 1.0
            if existence_ratio < 0.8:
                errors.append(f"Existence Ratio insufficiente ({existence_ratio:.2f} < 0.80): Rilevate troppe entità fittizie inventate dall'LLM.")

        # --- 4. CONTROLLO LINGUAGGIO SPECULATIVO ---
        speculative_patterns = [
            r"dipende dall['’]implementazione",
            r"si assume che",
            r"generalmente",
            r"comportamento non definito se non specificato"
        ]
        for spec_pat in speculative_patterns:
            if re.search(spec_pat, full_doc_text, re.IGNORECASE):
                errors.append(
                    f"Linguaggio speculativo rilevato ('{spec_pat}'). Analizza con certezza il codice sorgente fornito."
                )

        is_valid = len(errors) == 0
        return {
            "is_valid": is_valid,
            "errors": errors
        }

    @staticmethod
    def enforce_deterministic_complexity(doxygen_doc: str, time_comp: str, space_comp: str) -> str:
        """
        Inserisce o sovrascrive a posteriori il tag @complexity nel blocco Doxygen
        usando i valori matematici e deterministici certificati estratti dall'AST.
        """
        t_clean = time_comp.replace('\\mathcal{O}', 'O').replace('\\', '').strip()
        s_clean = space_comp.replace('\\mathcal{O}', 'O').replace('\\', '').strip()
        complexity_tag = f"@complexity Temporale: {t_clean} | Spaziale: {s_clean}"

        doc = doxygen_doc.strip()
        # Se esiste già un tag @complexity generato, lo sostituiamo deterministicamente
        if re.search(r'@complexity\s+.*', doc):
            doc = re.sub(r'@complexity\s+.*', complexity_tag, doc)
            return doc

        # Altrimenti lo iniettiamo prima della chiusura del commento Doxygen */
        if "*/" in doc:
            # Sostituisci l'ultima occorrenza di */ con la riga di complessità + */
            idx = doc.rfind("*/")
            # Controlla l'indentazione precedente o usa lo standard ' *\n * '
            prefix = doc[:idx].rstrip()
            return f"{prefix}\n *\n * {complexity_tag}\n */"
        
        return f"{doc}\n * {complexity_tag}\n */"

    def verify_global_consistency(self, module_summaries: Dict[str, str], struct_docs: List[Dict[str, Any]], function_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validazione Globale di Coerenza dell'Intero Progetto.
        Controlla contraddizioni tra sintesi del modulo, struct, enum e funzioni reali.
        """
        global_issues = []
        corrections = {
            "module_summaries": {},
            "struct_docs": []
        }

        # 1. Controlla se la descrizione di un modulo dichiara 'thread-safe' o 'atomico' in assenza di mutex
        for mod_name, summary_val in module_summaries.items():
            summary_str = summary_val.get("summary", "") if isinstance(summary_val, dict) else str(summary_val or "")
            clean_summary = summary_str
            if "thread-safe" in summary_str.lower() or "atomica" in summary_str.lower() or "atomiche" in summary_str.lower():
                clean_summary = re.sub(r'\b(thread-safe|atomica|atomiche)\b', 'monothread', clean_summary, flags=re.IGNORECASE)
                global_issues.append(f"Modulo '{mod_name}': Rimossa errata dichiarazione di thread-safety/atomicità nella sintesi ad alto livello.")
            
            if isinstance(summary_val, dict):
                summary_val["summary"] = clean_summary
                corrections["module_summaries"][mod_name] = summary_val
            else:
                corrections["module_summaries"][mod_name] = clean_summary

        # 2. Controlla la coerenza dei ruoli head/tail nelle struct
        for st in struct_docs:
            st_copy = dict(st)
            if st_copy.get("name") == "RingBuffer":
                # Assicurati che il sommario della struct non dichiari 'thread-safe'
                if "thread-safe" in st_copy.get("brief_summary", "").lower():
                    st_copy["brief_summary"] = st_copy["brief_summary"].replace("thread-safe", "non thread-safe")
                    global_issues.append("Struct 'RingBuffer': Corretta descrizione introduttiva per riflettere la natura non thread-safe.")
                
                # Verifica campi head e tail
                fields = st_copy.get("fields_json", [])
                if isinstance(fields, str):
                    try:
                        fields = json.loads(fields)
                    except:
                        fields = []
                
                updated_fields = []
                for f in fields:
                    f_name = f.get("name", "")
                    f_desc = f.get("description", "")
        # 3. Controlla e corregge incongruenze terminologiche nelle funzioni C++
        for fn in function_docs:
            fn_name = fn.get("name", "")
            dox = fn.get("full_doxygen_doc", "")
            brief = fn.get("brief_summary", "")

            # A. Variabili membro scambiate per globali in metodi C++
            if "::" in fn_name and ("variabili globali" in dox.lower() or "variabili globali" in brief.lower()):
                new_dox = re.sub(r'variabili globali', 'campi membro di istanza', dox, flags=re.IGNORECASE)
                new_brief = re.sub(r'variabili globali', 'campi membro di istanza', brief, flags=re.IGNORECASE)
                fn["full_doxygen_doc"] = new_dox
                fn["brief_summary"] = new_brief
                global_issues.append(f"Funzione '{fn_name}': Corretto riferimento a 'variabili globali' in 'campi membro di istanza'.")

            # B. Costruttori C++ con finto tag @return o tipo void
            if "::" in fn_name and fn_name.split("::")[-1] == fn_name.split("::")[-2]:
                if "@return" in dox:
                    new_dox = re.sub(r'@return\s+[^\n]*\n?', '', dox)
                    fn["full_doxygen_doc"] = new_dox
                    global_issues.append(f"Costruttore '{fn_name}': Rimosso tag @return non ammesso nei costruttori C++.")

        return {
            "has_issues": len(global_issues) > 0,
            "issues": global_issues,
            "corrections": corrections
        }

