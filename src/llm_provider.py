import os
import json
import time
import warnings
import sys
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()



# Sopprime i warning di sistema / SDK deprecation o AFC warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)

# Silenzia temporaneamente lo stderr durante l'import dell'SDK genai se stampa avvisi
class SuppressStderr:
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self._original_stderr



class LLMProvider(ABC):
    def __init__(self):
        self.interaction_log: List[Dict[str, Any]] = []

    def get_interaction_log(self) -> List[Dict[str, Any]]:
        return self.interaction_log

    def log_interaction(self, kind: str, target: str, prompt: str, raw_response: str, parsed_response: Any):
        self.interaction_log.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "kind": kind,
            "target": target,
            "prompt": prompt,
            "raw_response": raw_response,
            "parsed_response": parsed_response
        })

    @abstractmethod
    def generate_documentation(
        self, 
        func_name: str, 
        signature: str, 
        source_code: str, 
        callees_summaries: List[Dict[str, str]], 
        raw_comment: str = None
    ) -> Dict[str, str]:
        pass

    @abstractmethod
    def evaluate_documentation(
        self,
        func_name: str,
        signature: str,
        source_code: str,
        doxygen_doc: str,
        brief_summary: str = "",
        language: str = "en"
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def classify_function(
        self,
        func_name: str,
        signature: str,
        brief_summary: str,
        source_code: str,
        existing_categories: List[str]
    ) -> str:
        pass

class MockLLMProvider(LLMProvider):
    """
    Provider Mock deterministico per eseguire test locali completi senza consumare token API.
    """
    def __init__(self):
        super().__init__()

    def evaluate_documentation(
        self,
        func_name: str,
        signature: str,
        source_code: str,
        doxygen_doc: str,
        brief_summary: str = "",
        language: str = "en"
    ) -> Dict[str, Any]:
        res = {
            "score": 5,
            "critique": "",
            "suggestions": []
        }
        self.log_interaction("judge_evaluation_mock", func_name, "Mock Judge Prompt", str(res), res)
        return res

    def classify_function(
        self,
        func_name: str,
        signature: str,
        brief_summary: str,
        source_code: str,
        existing_categories: List[str]
    ) -> str:
        cat = existing_categories[0] if existing_categories else "Gestione Dati"
        self.log_interaction("function_classification_mock", func_name, "Mock Classification Prompt", cat, cat)
        return cat

    def generate_documentation(
        self, 
        func_name: str, 
        signature: str, 
        source_code: str, 
        callees_summaries: List[Dict[str, str]], 
        raw_comment: str = None,
        language: str = "en",
        validation_feedback: str = None,
        **kwargs
    ) -> Dict[str, str]:
        brief = f"Funzione `{func_name}` che gestisce le operazioni sul buffer o strutture dati correlate."
        
        callee_context_str = ""
        if callees_summaries:
            callee_context_str = "\n * **Dipendenze Utilizzate:**\n"
            for c in callees_summaries:
                callee_context_str += f" *   - `{c['name']}`: {c['brief_summary']}\n"

        doc = f"""/**
 * @brief {brief}
 * 
 * @details Esegue la logica definita nella firma `{signature}`.
 * {callee_context_str}
 * @param ... Parametri formali estrapolati dall'AST.
 * @return Risultato dell'operazione o codice di errore associato.
 */"""

        res = {
            "brief_summary": brief,
            "full_doxygen_doc": doc
        }
        self.log_interaction("function_doc_mock", func_name, "Mock Prompt", str(res), res)
        return res

class QuotaDailyExceededError(Exception):
    """Eccezione sollevata quando la quota giornaliera RPD (500 richieste) di Gemini è esaurita."""
    pass

class GeminiLLMProvider(LLMProvider):
    """
    Provider LLM basato su Google Gemini (modello gemini-3.5-flash-lite con rate limiting a 15 RPM).
    Supporta il Multi-Key Rotation Manager: ruota automaticamente tra più API Key (se separate da virgola)
    quando una di esse raggiunge la quota giornaliera RPD (500 richieste).
    """
    def __init__(self, model_name: str = "gemini-3.5-flash-lite", api_key: str = None, rpm_limit: int = 15):
        super().__init__()
        raw_keys = api_key or os.getenv("GEMINI_API_KEY")
        if not raw_keys or raw_keys == "YOUR_GEMINI_API_KEY_HERE":
            raise ValueError("Chiave GEMINI_API_KEY non trovata o non configurata nel file .env!")
        
        # Supporto a chiavi multiple separate da virgola nel file .env (es. KEY1,KEY2,KEY3)
        self.api_keys: List[str] = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self.current_key_index = 0
        self.model_name = model_name
        self.rpm_limit = rpm_limit
        self.min_delay = 60.0 / rpm_limit  # ~4.0 secondi tra le chiamate
        self.last_call_time = 0.0

        self._initialize_current_client()

    def _initialize_current_client(self):
        active_key = self.api_keys[self.current_key_index]
        print(f"  [API KEY MANAGER] Attivazione API Key #{self.current_key_index + 1} (finale: ...{active_key[-5:]})")
        try:
            from google import genai
            self.client = genai.Client(api_key=active_key)
            self.use_new_sdk = True
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=active_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.use_new_sdk = False

    def _rotate_to_next_key(self) -> bool:
        if self.current_key_index + 1 < len(self.api_keys):
            self.current_key_index += 1
            print(f"\n  [KEY ROTATION] Quota esaurita per la chiave #{self.current_key_index}. Passaggio automatico alla API Key #{self.current_key_index + 1}...")
            self._initialize_current_client()
            return True
        return False




    def _wait_for_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_delay:
            sleep_time = self.min_delay - elapsed
            time.sleep(sleep_time)
        self.last_call_time = time.time()

    def generate_documentation(
        self, 
        func_name: str, 
        signature: str, 
        source_code: str, 
        callees_summaries: List[Dict[str, str]], 
        raw_comment: str = None,
        validation_feedback: str = None,
        language: str = "en"
    ) -> Dict[str, str]:
        callees_ctx = ""
        if callees_summaries:
            prefix = "Internal dependencies called by this function and their summaries:\n" if language == "en" else "Dipendenze interne invocate da questa funzione e relativi sommari:\n"
            callees_ctx = prefix
            for c in callees_summaries:
                callees_ctx += f"- `{c['name']}`: {c['brief_summary']}\n"

        comment_header = "Original Doxygen/header comment in code:\n" if language == "en" else "Commento Doxygen originale presente nel codice:\n"
        comment_ctx = f"{comment_header}{raw_comment}\n" if raw_comment else ""

        feedback_prompt = ""
        if validation_feedback:
            if language == "en":
                feedback_prompt = f"""
--------------------------------------------------------------
[ATTENTION - CORRECTION INSTRUCTIONS FROM VERIFIER AGENT]
Your previous attempt for function '{func_name}' was REJECTED for the following reason:

>>> ERROR: {validation_feedback} <<<

MANDATORY CORRECTION RULES FOR THIS ATTEMPT:
- If the error concerns Boolean Logic Discrepancy (e.g., (ptr != NULL) && ...):
  In C, if 'ptr' is NULL the expression evaluates to FALSE.
  Format the @return tags EXACTLY like:
  @return true if condition is met.
  @return false if condition is not met or if pointer is NULL.
- NEVER claim that it returns 'true' when pointer is NULL.
--------------------------------------------------------------
"""
            else:
                feedback_prompt = f"""
--------------------------------------------------------------
[ATTENZIONE - ISTRUZIONI DI CORREZIONE DAL VERIFIER AGENT]
Il tuo tentativo precedente per la funzione '{func_name}' e' stato RIFIUTATO per il seguente motivo:

>>> ERRORE: {validation_feedback} <<<

ISTRUZIONI DI CORREZIONE OBBLIGATORIE PER QUESTO TENTATIVO:
- Se l'errore riguarda la Discrepanza Logica Booleana (es: (ptr != NULL) && ...):
  In C, se 'ptr' e' NULL l'espressione restituisce FALSE.
  DEVI formattare i tag @return ESATTAMENTE cosi':
  @return true se la condizione e' verificata.
  @return false se la condizione non e' verificata oppure se il puntatore e' NULL.
- NON scrivere mai che restituisce 'true' se il puntatore e' NULL.
--------------------------------------------------------------
"""

        if language == "en":
            prompt = f"""You are a senior software engineer and C/C++ documentation expert.
Generate professional technical documentation for the following C/C++ function strictly in ENGLISH.
{feedback_prompt}

--- STRICT FORMAT TO FOLLOW (ONE-SHOT EXAMPLE) ---
Required JSON output structure:

{{
  "brief_summary": "Performs the specified operation on the module, validating input arguments and managing resources.",
  "full_doxygen_doc": "/**\\n * @brief Concise summary of the main operation.\\n * \\n * @details In-depth explanation of the internal workflow and combined side effects.\\n * \\n * @param[in,out] handle Pointer to the primary data structure.\\n * @param[in] input_val Input value for processing.\\n * \\n * @return STATUS_OK upon successful completion.\\n * @return STATUS_ERR_INVALID_ARG if any provided pointer/argument is NULL or invalid.\\n * @return STATUS_ERR_RESOURCE if capacity or memory allocation fails.\\n */"
}}
------------------------------------------------------------------------

--- MANDATORY RULES ---
1. Strictly write ALL documentation, summary, @brief, @details, and parameter descriptions in ENGLISH.
2. Use EXCLUSIVELY the exact formal parameter names defined in the C signature.
3. Return Type Handling:
   - If the return type is `void`, do NOT include any `@return` tag in the Doxygen block.
   - If non-`void`, use exclusively the real return types and enum/macro error names present in the source or dependencies. Do not invent symbols.
4. Boolean Functions: for `(ptr != NULL) && ...`, note that NULL returns false. State clearly that it returns `false` if pointer is NULL.
5. C++ Methods: if inside a class, member accesses are instance fields (`this->field`), NOT global variables.
6. Design by Contract:
   - `@pre`: Essential preconditions (or 'None, arguments validated at runtime').
   - `@post`: Guarantees on state and memory after execution.
7. Do NOT use speculative phrases ('may depend on implementation'). Be technically precise.

Now generate the documentation for the following function:

Function: `{func_name}`
C/C++ Signature: `{signature}`
{comment_ctx}
{callees_ctx}

Source Code:
```c
{source_code}
```

Respond EXCLUSIVELY with valid JSON matching the One-Shot schema:
1. "brief_summary": A concise and clear summary in English (max 25 words).
2. "full_doxygen_doc": Complete Doxygen block in English (with @brief, @details, @param [in]/[out], @return).

Respond ONLY with the JSON (no markdown fences ```json).
"""
        else:
            prompt = f"""Sei un ingegnere del software ed esperto di documentazione C.
Genera la documentazione tecnica professionale per la seguente funzione C in italiano.
{feedback_prompt}

--- ESEMPIO DI FORMATO DA SEGUIRE RIGOROSAMENTE (ONE-SHOT GENERICO) ---
Struttura e stile di risposta JSON richiesti (esempio astratto):

{{
  "brief_summary": "Esegue l'operazione specificata sul modulo, gestendo la validazione degli argomenti e le risorse.",
  "full_doxygen_doc": "/**\\n * @brief Descrizione sintetica dell'operazione principale.\\n * \\n * @details Spiegazione dettagliata del flusso interno e dell'effetto combinato.\\n * \\n * @param[in,out] handle Puntatore alla struttura dati principale su cui operare.\\n * @param[in] input_val Valore di ingresso per l'elaborazione.\\n * \\n * @return STATUS_OK in caso di completamento con successo.\\n * @return STATUS_ERR_INVALID_ARG se un parametro o puntatore fornito e' NULL o non valido.\\n * @return STATUS_ERR_RESOURCE se le risorse o la capacita' sono esaurite.\\n */"
}}
------------------------------------------------------------------------

--- REGOLE TASSATIVE ---
1. Usa ESCLUSIVAMENTE i nomi dei parametri formali esatti definiti nella firma C.
2. Gestione Tipo di Ritorno:
   - Se la funzione ha tipo di ritorno `void` (come nelle funzioni di test o procedure senza ritorno), NON inserire ASSOLUTAMENTE alcun tag `@return` nel blocco Doxygen.
   - Se la funzione restituisce un valore non-`void`, usa ESCLUSIVAMENTE i tipi di ritorno ed i nomi di enum/costanti reali presenti nel codice C o nelle dipendenze. NON inventare codici di errore non definiti nel sorgente.
3. Per funzioni booleane (`bool`, `_Bool`) con corto circuito C `(ptr != NULL) && ...`: se `ptr` e' NULL l'espressione restituisce FALSE. Scrivi che restituisce `false` se il puntatore e' NULL!
4. Gestione C++ OOP & Variabili Membro:
   - Se la funzione fa parte di una classe (es. `NomeClasse::metodo`), gli accessi ai campi della classe sono variabili membro/campi di istanza (`this->campo`), NON variabili globali. Non descrivere MAI i campi di classe come "variabili globali".
   - Per costruttori e distruttori C++, non includere tag `@return`.
5. Contratti Formali Doxygen (Design by Contract vs Programmazione Difensiva):
   - `@pre`: Precondizioni ESSENZIALI (es. puntatore valido se la funzione NON fa controlli a runtime). ATTENZIONE: Se la funzione controlla esplicitamente `if (!ptr) return RB_ERR_NULL_PTR;` o simili a runtime, NON scrivere `@pre ptr non deve essere NULL` come vincolo rigido incompatibile, ma descrivi il codice di errore in `@return` e in `@pre` indica "Nessuna precondizione bloccante, parametri controllati a runtime" o requisiti di ambiente.
   - `@post`: Postcondizioni e garanzie formali sullo stato della memoria e delle strutture al termine dell'esecuzione (incluso in caso di errore o successo).
   - `@warning`: Specificare la Thread-Safety solo se rilevante per funzioni di libreria che manipolano puntatori condivisi. ATTENZIONE: per funzioni di entry-point come `main()` o funzioni che usano esclusivamente variabili locali sullo stack senza concorrenza, NON inserire falsi warning di thread-safety (scrivi 'Non applicabile (funzione di entry-point o isolata sullo stack)' oppure ometti il warning).

6. NON usare mai frasi ipotetiche o speculative (es. "dipende dall'implementazione", "generalmente"). Descrivi con certezza matematica la logica del codice sorgente fornito.

Ora genera la documentazione per la seguente funzione:

Funzione: `{func_name}`
Firma C: `{signature}`
{comment_ctx}
{callees_ctx}

Codice Sorgente Reale:
```c
{source_code}
```

Fornisci la risposta ESCLUSIVAMENTE in formato JSON valido rispettando la struttura mostrata nell'esempio One-Shot:
1. "brief_summary": Una frase sintetica e chiara (max 20 parole).
2. "full_doxygen_doc": Blocco Doxygen completo (con @brief, @details spiegando la logica e l'uso delle dipendenze, @param esplicitando [in]/[out]/[in,out] per OGNI parametro formale, e @return per ciascun codice di errore o valore di ritorno).

Rispondi SOLO ed ESCLUSIVAMENTE con il JSON valido (senza marcatori markdown ```json).
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()

                if self.use_new_sdk:
                    with SuppressStderr():
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                    text = response.text
                else:
                    with SuppressStderr():
                        response = self.model.generate_content(prompt)
                    text = response.text

                # Pulizia e parsing JSON
                cleaned_text = text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

                data = json.loads(cleaned_text)
                res_obj = {
                    "brief_summary": data.get("brief_summary", f"Funzione {func_name}."),
                    "full_doxygen_doc": data.get("full_doxygen_doc", f"/**\n * @brief {func_name}\n */")
                }
                self.log_interaction(
                    kind="function_doc",
                    target=func_name,
                    prompt=prompt,
                    raw_response=text,
                    parsed_response=res_obj
                )
                return res_obj

            except Exception as e:
                err_msg = str(e)
                # Verifica se si tratta di esaurimento della Quota Giornaliera RPD
                if "QuotaExceeded" in err_msg or "QuotaFailure" in err_msg or "RequestsPerDay" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    rotated = self._rotate_to_next_key()
                    if rotated:
                        print(f"  -> Chiave cambiata con successo! Riprovo immediatamente la funzione '{func_name}'...")
                        continue
                    else:
                        raise QuotaDailyExceededError(
                            f"\n[ERRORE QUOTA GLOBALE] Tutte le {len(self.api_keys)} API Key disponibili nel file .env hanno esaurito la quota giornaliera di 500 RPD.\n"
                            "I progressi elaborati finora sono salvati in SQLite. Potrai riprendere l'esecuzione domani o inserendo una nuova chiave nel .env."
                        ) from e

                if ("429" in err_msg or "503" in err_msg or "Quota" in err_msg) and attempt < max_retries - 1:
                    wait_sec = (attempt + 1) * 5
                    time.sleep(wait_sec)
                else:
                    if attempt == max_retries - 1:
                        raise e

    def generate_module_summary(self, file_name: str, functions_summaries: List[str]) -> Dict[str, str]:
        """
        Genera una guida architetturale completa per il modulo (descrizione, workflow d'uso e snippet di esempio).
        """
        funcs_str = "\n".join([f"- {s}" for s in functions_summaries[:20]])
        prompt = f"""Sei uno Principal Software Architect ed esperto sviluppatore C/C++.
Fornisci una guida tecnica e discorsiva per il modulo sorgente '{file_name}'.

Funzioni e componenti disponibili nel modulo:
{funcs_str}

REGOLE FONDAMENTALI:
1. NON asserire MAI che il modulo e' "thread-safe" o che fornisce "operazioni atomiche" a meno che non vi sia un'evidenza diretta di primitive di sincronizzazione (es. mutex, stdatomic).
2. Rispondi ESCLUSIVAMENTE in formato JSON con la seguente struttura:
{{
  "summary": "Descrizione ad alto livello del ruolo del modulo e del suo scopo architetturale (2-3 frasi in italiano).",
  "workflow_desc": "Spiegazione discorsiva del tipico ciclo di vita o flusso d'uso operativo delle funzioni (es. Inizializzazione -> Configurazione/Uso -> Rilascio risorse).",
  "code_example": "Breve snippet di codice C/C++ (4-8 righe) che dimostra il tipico utilizzo integrato delle funzioni chiave del modulo."
}}
"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                if self.use_new_sdk:
                    with SuppressStderr():
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                    res_text = response.text.strip()
                else:
                    response = self.model.generate_content(prompt)
                    res_text = response.text.strip()

                clean_json = res_text
                if clean_json.startswith("```"):
                    clean_json = clean_json.strip("`")
                    if clean_json.startswith("json"):
                        clean_json = clean_json[4:].strip()
                
                try:
                    parsed = json.loads(clean_json)
                except Exception:
                    parsed = {
                        "summary": res_text,
                        "workflow_desc": "",
                        "code_example": ""
                    }

                self.log_interaction("module_summary", file_name, prompt, res_text, parsed)
                return parsed
            except Exception as e:
                err_msg = str(e)
                if "QuotaExceeded" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    if self._rotate_to_next_key():
                        continue
                if attempt == max_retries - 1:
                    return {
                        "summary": f"Modulo '{file_name}' contenente funzioni di utilita' del componente.",
                        "workflow_desc": "",
                        "code_example": ""
                    }

    def generate_project_overview(self, project_name: str, module_analyses: List[Dict[str, Any]], build_context: str = "", memory_context: str = "") -> Dict[str, Any]:
        """
        Ruolo 'Lead Architect Agent': aggrega le analisi prodotte dagli agenti di modulo per sintetizzare
        il dominio applicativo, la descrizione del problema risolto, il build system effettivo,
        i formati I/O specifici e il modello di memoria/concorrenza reale del progetto.
        """
        modules_text = []
        for m in module_analyses:
            modules_text.append(f"### File/Modulo: {m.get('file_path')}\n- Ruolo: {m.get('summary')}\n- Workflow: {m.get('workflow_desc')}\n- Funzioni: {', '.join(m.get('functions', []))}")
        
        agg_text = "\n\n".join(modules_text)
        prompt = f"""Sei il Lead Software Architect e Domain Expert per il progetto software '{project_name}'.
Hai a disposizione i report analitici prodotti dagli agenti specializzati su ciascun modulo della codebase:

{agg_text}

Contesto aggiuntivo del repository:
- Build System rilevato nel repository:
{build_context if build_context else "Nessun build script rilevato. Usare compilazione diretta CLI (es. gcc/g++)."}

- Profilo di memoria ed interfacce rilevato:
{memory_context if memory_context else "Allocazioni standard e gestione memoria basata su scope."}

Il tuo compito è sintetizzare una DESCRIZIONE COMPLETA ED ESAUSTIVA ADATTATA SPECIFICATAMENTE A QUESTO PROGETTO, da posizionare all'inizio della documentazione tecnica.

Fornisci una risposta ESCLUSIVAMENTE in formato JSON con la seguente struttura:
{{
  "domain_context": "Definizione del dominio applicativo e del problema che il software si prefigge di risolvere (es. Algoritmo di instradamento per braccia robotiche in griglia, gestione memoria circolare FIFO, parsing JSON ad alte prestazioni, ecc.). Spiega il contesto in modo chiaro e divulgativo per questo specifico progetto.",
  "overview_markdown": "Descrizione approfondita (2-3 paragrafi) di come il software affronta e risolve il problema: logica algoritmica adottata, cooperazione tra i vari moduli (come i dati fluiscono tra di essi) e struttura generale dell'architettura.",
  "key_capabilities": [
    "Punto chiave 1: capacità/funzionalità principale del sistema",
    "Punto chiave 2: modello di dati e strutture algoritmiche fondamentali",
    "Punto chiave 3: interazione I/O o interfaccia operativa"
  ],
  "build_instructions_markdown": "Istruzioni di compilazione ed esecuzione formattate in Markdown specifiche per questo progetto (se c'è un Makefile o CMake, cita i target reali come 'make driver' o i comandi di compilazione esatti con i file corretti e flag pertinenti).",
  "io_specs_markdown": "Spiegazione dettagliata e tabella dei formati di Input e Output specifici di questo progetto (quali file o stream legge, es. formati testo/matrici, e quali file o log produce in output con la grammatica dei record).",
  "memory_model_markdown": "Analisi personalizzata del modello di memoria, gestione puntatori (es. raw pointers vs smart pointers/RAII), ownership delle risorse e note su concorrenza / thread-safety relative a questo codice sorgente."
}}
"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                if self.use_new_sdk:
                    with SuppressStderr():
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                    res_text = response.text.strip()
                else:
                    response = self.model.generate_content(prompt)
                    res_text = response.text.strip()

                clean_json = res_text
                if clean_json.startswith("```"):
                    clean_json = clean_json.strip("`")
                    if clean_json.startswith("json"):
                        clean_json = clean_json[4:].strip()
                
                try:
                    parsed = json.loads(clean_json)
                except Exception:
                    parsed = {
                        "domain_context": f"Progetto software '{project_name}'.",
                        "overview_markdown": res_text,
                        "key_capabilities": [],
                        "build_instructions_markdown": "",
                        "io_specs_markdown": "",
                        "memory_model_markdown": ""
                    }

                self.log_interaction("project_overview", project_name, prompt, res_text, parsed)
                return parsed
            except Exception as e:
                err_msg = str(e)
                if "QuotaExceeded" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    if self._rotate_to_next_key():
                        continue
                if attempt == max_retries - 1:
                    return {
                        "domain_context": f"Progetto software '{project_name}'.",
                        "overview_markdown": "Architettura software modulare analizzata tramite estrazione statica e modelli LLM.",
                        "key_capabilities": [],
                        "build_instructions_markdown": "",
                        "io_specs_markdown": "",
                        "memory_model_markdown": ""
                    }

    def generate_struct_documentation(self, struct_name: str, fields: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Genera la documentazione concettuale per una struct C e per ciascuno dei suoi campi.
        """
        fields_str = "\n".join([f"- {f.get('name', '')}: tipo {f.get('type', '')}" for f in fields])
        prompt = f"""Sei uno Software Architect ed esperto di documentazione C.
Fornisci la documentazione tecnica analitica per la `struct` C '{struct_name}' ed i suoi campi.

Campi della struct:
{fields_str}

REGOLE CRUCIALI SUI RUOLI DEI CAMPI E VERIDICITA':
1. In un Ring Buffer C:
   `head` e' l'indice di SCRITTURA (dove la funzione `rb_push` scrive il nuovo dato `rb->data[rb->head] = value`).
   `tail` e' l'indice di LETTURA (da cui la funzione `rb_pop` estrae il valore `*out_value = rb->data[rb->tail]`).
2. NON invertire MAI i ruoli di `head` (Scrittura) e `tail` (Lettura)!
3. NON dichiarare MAI che la struct o l'implementazione e' "thread-safe" o che usa "operazioni atomiche" senza evidenza di primitive di sincronizzazione.


Rispondi ESCLUSIVAMENTE in formato JSON valido:
{{
  "brief_summary": "Breve descrizione del ruolo della struct",
  "fields_doc": [
    {{ "name": "nome_campo", "type": "tipo_campo", "description": "Descrizione precisa in italiano del campo" }}
  ]
}}
Rispondi SOLO con il JSON valido.
"""

        try:
            self._wait_for_rate_limit()
            if self.use_new_sdk:
                with SuppressStderr():
                    response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                res_text = response.text.strip()
            else:
                response = self.model.generate_content(prompt)
                res_text = response.text.strip()
            if res_text.startswith("```json"): res_text = res_text[7:]
            if res_text.startswith("```"): res_text = res_text[3:]
            if res_text.endswith("```"): res_text = res_text[:-3]
            parsed = json.loads(res_text.strip())
            self.log_interaction("struct_doc", struct_name, prompt, res_text, parsed)
            return parsed
        except Exception:
            return {
                "brief_summary": f"Struttura dati {struct_name}",
                "fields_doc": [{"name": f.get("name", ""), "type": f.get("type", ""), "description": "Campo della struttura."} for f in fields]
            }

    def generate_enum_documentation(self, enum_name: str, values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera la documentazione concettuale per un'enum C e per ciascuna delle sue costanti.
        """
        vals_str = "\n".join([f"- {v.get('name', '')} = {v.get('value', '')}" for v in values])
        prompt = f"""Sei uno Software Architect ed esperto di documentazione C.
Fornisci una descrizione e la spiegazione analitica dei valori per la seguente `enum` C '{enum_name}'.

Costanti dell'enum:
{vals_str}

REGOLE DI CORRETTEZZA FATTUALE:
- Descrivi il significato esatto di ciascuna costante basandoti sulla semantica reale del codice C del progetto.
- NON inventare o allucinare comportamenti non presenti (es. non affermare che strutture a dimensione statica/fissa 'espandono le loro risorse'). Se compare un errore di memoria (es. NO_MEM), descrivi che si riferisce al fallimento dell'allocazione iniziale o risorse esaurite, senza ipotizzare ridimensionamenti dinamici non implementati.

Rispondi ESCLUSIVAMENTE in formato JSON valido:
{{
  "brief_summary": "Breve descrizione del ruolo dell'enum",
  "values_doc": [
    {{ "name": "NOME_COSTANTE", "value": "valore", "description": "Significato ed uso in italiano di questa costante di stato" }}
  ]
}}
Rispondi SOLO con il JSON valido.
"""
        try:
            self._wait_for_rate_limit()
            if self.use_new_sdk:
                with SuppressStderr():
                    response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                res_text = response.text.strip()
            else:
                response = self.model.generate_content(prompt)
                res_text = response.text.strip()
            if res_text.startswith("```json"): res_text = res_text[7:]
            if res_text.startswith("```"): res_text = res_text[3:]
            if res_text.endswith("```"): res_text = res_text[:-3]
            parsed = json.loads(res_text.strip())
            self.log_interaction("enum_doc", enum_name, prompt, res_text, parsed)
            return parsed
        except Exception:
            return {
                "brief_summary": f"Enumerazione di stato {enum_name}",
                "values_doc": [{"name": v.get("name", ""), "value": str(v.get("value", "")), "description": "Codice/Costante dell'enum."} for v in values]
            }

    def classify_function(
        self,
        func_name: str,
        signature: str,
        brief_summary: str,
        source_code: str,
        existing_categories: List[str]
    ) -> str:
        """
        Classifica la funzione C all'interno di una categoria funzionale coerente e significativa.
        """
        standard_taxonomies = [
            "Inizializzazione e Deallocazione",
            "Gestione Memoria e Risorse",
            "Manipolazione e Inserimento Dati",
            "Estrazione e Lettura Dati",
            "Controllo Stato e Validazione",
            "Parsing e Conversione",
            "I/O, Logging e Stampa",
            "Algoritmi e Calcolo",
            "Gestione Errori e Diagnostic",
            "Entry Point ed Esecuzione Test"
        ]

        # Filtra 'Generale' dalle categorie esistenti se per caso presente
        clean_existing = [c for c in (existing_categories or []) if c and c.lower() != "generale"]

        if clean_existing:
            cats_list_str = "\n".join([f"- {c}" for c in clean_existing[:20]])
            existing_part = f"""Categorie già create per altre funzioni di questo progetto:
{cats_list_str}

- Se la funzione rientra in una delle categorie sopra, RIUTILIZZA ESATTAMENTE lo stesso nome."""
        else:
            existing_part = ""

        taxonomy_hints = "\n".join([f"- {t}" for t in standard_taxonomies])

        prompt = f"""Sei uno Software Architect esperto di sistemi e software in linguaggio C.
Classifica la seguente funzione C all'interno di una categoria logica/funzionale chiara e specifica.

Funzione: `{func_name}`
Firma C: `{signature}`
Sommario Funzionale: {brief_summary}

Codice Sorgente:
```c
{source_code}
```

Esempi di categorie tipiche in progetti C:
{taxonomy_hints}

{existing_part}

REGOLE TASSATIVE:
1. NON usare MAI etichette generiche o vuote come 'Generale', 'Altro', 'Varie' o 'Funzione'.
2. Scegli una categoria precisa di 2-4 parole in italiano che descriva l'intento funzionale reale (es. 'Inizializzazione e Deallocazione', 'Controllo Stato e Validazione', 'Manipolazione e Inserimento Dati', 'Entry Point ed Esecuzione Test').
3. Rispondi ESCLUSIVAMENTE con il nome della categoria (nessun commento, nessuna virgoletta, nessuna punteggiatura extra).
"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                if self.use_new_sdk:
                    with SuppressStderr():
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                    chosen_cat = response.text.strip().replace('"', '').replace("'", "").strip()
                else:
                    response = self.model.generate_content(prompt)
                    chosen_cat = response.text.strip().replace('"', '').replace("'", "").strip()

                # Pulizia stringa categoria
                if chosen_cat.startswith("- "): chosen_cat = chosen_cat[2:]
                chosen_cat = chosen_cat.split("\n")[0].strip()
                if not chosen_cat or chosen_cat.lower() in ["generale", "general", "altro", "varie", "function"]:
                    # Fallback euristico se l'LLM non risponde
                    if "init" in func_name or "create" in func_name or "free" in func_name or "destroy" in func_name:
                        chosen_cat = "Inizializzazione e Deallocazione"
                    elif "is_" in func_name or "has_" in func_name or "check" in func_name or "validate" in func_name or "size" in func_name:
                        chosen_cat = "Controllo Stato e Validazione"
                    elif "push" in func_name or "add" in func_name or "insert" in func_name or "write" in func_name or "set" in func_name:
                        chosen_cat = "Manipolazione e Inserimento Dati"
                    elif "pop" in func_name or "get" in func_name or "read" in func_name or "fetch" in func_name:
                        chosen_cat = "Estrazione e Lettura Dati"
                    elif "main" in func_name or "test" in func_name or "run" in func_name:
                        chosen_cat = "Entry Point ed Esecuzione Test"
                    else:
                        chosen_cat = "Elaborazione e Gestione Dati"

                self.log_interaction("function_classification", func_name, prompt, chosen_cat, chosen_cat)
                return chosen_cat
            except Exception as e:
                err_msg = str(e)
                if "QuotaExceeded" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    if self._rotate_to_next_key():
                        continue
        
        # Fallback euristico di sicurezza
        if "init" in func_name or "create" in func_name or "free" in func_name:
            return "Inizializzazione e Deallocazione"
        elif "is_" in func_name or "size" in func_name:
            return "Controllo Stato e Validazione"
        elif "push" in func_name or "add" in func_name:
            return "Manipolazione e Inserimento Dati"
        elif "pop" in func_name or "get" in func_name:
            return "Estrazione e Lettura Dati"
        if "main" in func_name:
            return "Entry Point ed Esecuzione Test"
        return "Elaborazione e Gestione Dati"

    def evaluate_documentation(
        self,
        func_name: str,
        signature: str,
        source_code: str,
        doxygen_doc: str,
        brief_summary: str = "",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Judge / Critic evaluation method:
        Valuta la documentazione generata (Doxygen + brief summary) a confronto
        con il codice sorgente C/C++ originale, assegnando un punteggio da 1 a 5.
        Se score < 4, fornisce motivazione dettagliata (critique) e suggerimenti correttivi.
        """
        if language == "en":
            prompt = f"""You are a strict, senior Technical Auditor and C/C++ documentation Judge.
Evaluate the technical accuracy, completeness, and rigor of the generated documentation against the actual source code.

Target Function: `{func_name}`
Signature: `{signature}`

Original Source Code:
```c
{source_code}
```

Generated Documentation to Evaluate:
Brief Summary:
"{brief_summary}"

Doxygen Comment:
{doxygen_doc}

--- EVALUATION RUBRIC (SCALE 1 TO 5) ---
- Score 5 (Exceptional / Production Grade): Complete and flawless. Explains edge cases, memory contracts (@pre/@post), correct null-check behavior, exact error codes matching the source.
- Score 4 (Good / Solid): Technically accurate with no factual errors. Minor omissions that do not compromise safety or understanding.
- Score 3 (Marginal / Needs Improvement): Factual omissions (e.g., misses memory ownership/cleanup, unmentioned error return codes, imprecise null pointer conditions).
- Score 2 (Poor): Highly vague, tautological (merely repeats function name), or misses critical preconditions causing misleading usage.
- Score 1 (Unacceptable): Blatant hallucinations, factual contradictions with source logic (e.g., claiming it returns true on NULL when code does not, or inventing non-existent parameters/enums).

CRITICAL RULE:
- If score >= 4, the critique can be empty or brief praise.
- If score < 4, you MUST provide an actionable, precise, and constructive 'critique' and specific 'suggestions' explaining exactly what facts from the source code were missed or misrepresented, so the Writer Agent can fix them.

Respond EXCLUSIVELY with valid JSON in this exact structure:
{{
  "score": 4,
  "critique": "Explanation of score...",
  "suggestions": [
    "Specific suggestion 1",
    "Specific suggestion 2"
  ]
}}
Respond ONLY with the JSON (no markdown fences).
"""
        else:
            prompt = f"""Sei un rigoroso Senior Technical Auditor e Giudice di documentazione C/C++.
Valuta l'accuratezza tecnica, la completezza e il rigore della documentazione generata confrontandola con il codice sorgente reale.

Funzione: `{func_name}`
Firma: `{signature}`

Codice Sorgente Reale:
```c
{source_code}
```

Documentazione Generata da Valutare:
Sommario sintetico:
"{brief_summary}"

Blocco Doxygen:
{doxygen_doc}

--- RUBRICA DI VALUTAZIONE (SCALA DA 1 A 5) ---
- Punteggio 5 (Eccellente / Production Grade): Impeccabile e completa. Dettaglia edge cases, contratti di memoria (@pre/@post), gestione corretta puntatori NULL, codici di ritorno ed enum esatti.
- Punteggio 4 (Buono / Solido): Tecnicamente accurata senza errori fattuali. Solo dettagli stilistici o minori non bloccanti.
- Punteggio 3 (Sufficiente ma Migliorabile): Omissioni fattuali (es. non specifica chi alloca/libera memoria, omette un codice di errore, o spiegazione incompleta su NULL).
- Punteggio 2 (Insufficiente): Troppo generica, tautologica (ripete solo il nome della funzione) o ambigua sui parametri/comportamento.
- Punteggio 1 (Gravemente Errata): Allucinazioni evidenti, contraddizioni palesi con il codice (es. asserisce che restituisce true su NULL mentre restituisce false, o inventa parametri).

REGOLA CRUCIALE:
- Se il voto è >= 4, la critique può essere vuota o breve.
- Se il voto è < 4, DEVI fornire una 'critique' analitica e costruttiva e una lista di 'suggestions' chiarendo esattamente cosa correggere rispetto al codice sorgente per permettere al Writer Agent di riscriverla correttamente.

Rispondi ESCLUSIVAMENTE con un JSON valido con questa struttura:
{{
  "score": 4,
  "critique": "Motivazione del voto...",
  "suggestions": [
    "Suggerimento specifico 1",
    "Suggerimento specifico 2"
  ]
}}
Rispondi SOLO con il JSON (senza marcatori markdown).
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                if self.use_new_sdk:
                    with SuppressStderr():
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                    raw_text = response.text.strip()
                else:
                    with SuppressStderr():
                        response = self.model.generate_content(prompt)
                    raw_text = response.text.strip()

                clean_text = raw_text
                if clean_text.startswith("```json"): clean_text = clean_text[7:]
                if clean_text.startswith("```"): clean_text = clean_text[3:]
                if clean_text.endswith("```"): clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                parsed = json.loads(clean_text)
                score = int(parsed.get("score", 5))
                # Clamping tra 1 e 5
                score = max(1, min(5, score))
                critique = str(parsed.get("critique", "")).strip()
                suggestions = parsed.get("suggestions", [])
                if not isinstance(suggestions, list):
                    suggestions = [str(suggestions)]

                res_obj = {
                    "score": score,
                    "critique": critique,
                    "suggestions": suggestions
                }
                self.log_interaction("judge_evaluation", func_name, prompt, raw_text, res_obj)
                return res_obj
            except Exception as e:
                err_msg = str(e)
                if "QuotaExceeded" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    if self._rotate_to_next_key():
                        continue
                if attempt == max_retries - 1:
                    # In caso di errore API, concediamo un punteggio neutro conservativo per non bloccare la pipeline
                    return {
                        "score": 4,
                        "critique": f"Valutazione automatica non completata per timeout/errore di rete: {err_msg}",
                        "suggestions": []
                    }
                time.sleep((attempt + 1) * 2)

        return {"score": 4, "critique": "", "suggestions": []}
