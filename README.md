# Documentazione automatica di codice C / C++ con analisi statica AST e agenti LLM

> Pipeline che estrae i fatti del codice con il compilatore (libclang), ordina le funzioni dalle foglie del call graph verso l'alto, fa scrivere la documentazione Doxygen a un LLM e la controlla con un verificatore deterministico. Include un framework di benchmark contro Ground Truth e un confronto con CodeWiki.

---

## 1. Panoramica

Il progetto ha due parti che condividono i moduli di base:

| Parte | Cosa fa | Entry point |
| :--- | :--- | :--- |
| **Pipeline di documentazione** | Prende un progetto C/C++ da `Test_code/`, ne estrae i metadati dall'AST, costruisce il call graph, genera e verifica la documentazione funzione per funzione e produce un report Markdown/HTML. | `main.py` |
| **Benchmark e valutazione** | Genera la documentazione per funzioni di librerie reali (cJSON, TinyXML-2, sds, miniz, http-parser, fmt, OpenCV) che hanno già una documentazione d'autore (Ground Truth) e la misura con metriche lessicali, neurali, strutturali e comportamentali. | `utils/benchmark_eval.py` |
| **Confronto con CodeWiki** | Mappa la documentazione prodotta da CodeWiki sulle stesse funzioni del benchmark e la confronta con quella della pipeline. | `compare_codewiki.py` |

Il principio di fondo è separare ciò che si può **calcolare in modo deterministico** (firme, parametri, chiamate, complessità, esistenza dei simboli) da ciò che richiede un **LLM** (descrivere lo scopo, i casi limite, il flusso d'uso). Il primo gruppo non viene mai delegato al modello: o lo si passa al modello come dato, o lo si usa per respingerne l'output.

---

## 2. Pipeline di documentazione (`main.py`)

`process_project()` esegue quattro passi per un progetto e salva tutto in `results/<progetto>/run_<timestamp>_<mode>/`:

```
 Test_code/<progetto>/*.c|.cpp|.h|.hpp
        │
        ▼
 [1] extract_metadata.py ──► extracted_metadata.json  (+ diagrammi AST in mmd_diagrams/)
        │
        ▼
 [2] dependency_graph.py ──► call graph, grafo degli #include (.mmd)
        │
        ▼
 [3] Tarjan + Kahn ────────► topological_execution_order.json  (callee prima dei caller)
        │
        ▼
 [4] doc_orchestrator.py ──► SQLite (documentation.db) ──► DOCUMENTATION.md / FULL_DOCUMENTATION.html
                              ▲                                   interactive_call_graph.html
                 llm_provider + agents + verifier
```

### 2.1 Scoperta dei file

`discover_projects()` elenca le sottocartelle di `Test_code/`. `find_c_source_files()` scorre il progetto ricorsivamente e separa i sorgenti (`.c .cpp .cc .cxx .c++`) dagli header (`.h .hpp .hh .hxx .h++`); la cartella di ogni file diventa una directory di include (`-I`) per il parsing.

### 2.2 Estrazione dei metadati (`src/extract_metadata.py`)

`CCodeExtractor` usa `libclang` (su Windows cerca `C:\Program Files\LLVM\bin`) e parsa **ogni file separatamente**.

**Scelta del linguaggio.** Il file è trattato come C++ se l'estensione è C++, oppure se è un `.h` che nei primi 40 KB contiene `namespace`, `class`, `template<`, `public:`, `private:` o `protected:`. Argomenti di parsing: C++ → `-x c++ -std=c++17 -DCV_EXPORTS=`; C → `-x c -std=c11`. Il parsing usa `PARSE_DETAILED_PROCESSING_RECORD` per vedere anche le macro e gli `#include`.

**Cosa viene estratto** (solo da cursori che appartengono al file target, così gli header di sistema vengono ignorati):

| Elemento | Campi salvati |
| :--- | :--- |
| `includes` | file incluso, riga |
| `typedefs` | nome, tipo sottostante (anche `using X = Y`) |
| `enums` | nome, costanti con valore |
| `structs` / `classes` | nome, campi (nome e tipo), commento grezzo (solo se è una definizione) |
| `macros` | nome (le macro che iniziano con `__` sono scartate) |
| `functions` | nome, tipo di ritorno, parametri, `is_definition`, `callees`, riga, commento grezzo, codice sorgente, complessità temporale e spaziale |

Per le funzioni vengono riconosciuti `FUNCTION_DECL`, `CXX_METHOD`, `CONSTRUCTOR`, `DESTRUCTOR` e `FUNCTION_TEMPLATE`. I metodi di classe vengono qualificati (`Classe::metodo`); costruttori e distruttori hanno tipo di ritorno vuoto. La visita entra ricorsivamente in namespace, classi e struct.

**Callees.** Se la funzione è una definizione, l'AST del corpo viene percorso cercando i nodi `CALL_EXPR`. Il nome della chiamata viene qualificato con la classe del metodo referenziato, quando c'è, e le chiamate duplicate vengono scartate.

**Codice sorgente.** Il testo esatto della funzione è ritagliato dal file con l'`extent` del cursore (righe di inizio e fine).

**Complessità Big-O deterministica.** Una seconda visita dell'AST calcola:

- la profondità massima di annidamento di `for` / `while` / `do`;
- la presenza di allocazione dinamica (`malloc`, `calloc`, `realloc`, `aligned_alloc`, `new`);
- la chiamata a operazioni lineari della STL (`max_element`, `min_element`, `find`, `count`, `erase`, `remove`) oppure a funzioni il cui nome contiene `Trova`, `Ordina` o `Suddivisione` (euristica pensata per i progetti didattici in italiano di `Test_code/`).

Una chiamata lineare porta la profondità effettiva a 1 (se 0) oppure la incrementa di 1. Un parametro `vector` passato per valore e un ritorno per valore di un container contano come allocazione e come passata lineare; un ritorno `vector<vector<…>>` forza `O(N^2)` con la nota «copia profonda matrice». Il risultato è una stringa tipo `O(1)`, `O(N)`, `O(N^k)` per il tempo e `O(1)` oppure `O(N)` (allocazione/copia dinamica) per lo spazio. È un'**euristica sintattica**, non una dimostrazione di complessità.

Per ogni file viene anche generato un diagramma AST in Mermaid (`utils/generate_ast_diagram.py`, profondità massima 3) in `mmd_diagrams/ast_<file>.mmd`.

### 2.3 Grafo delle dipendenze e ordine bottom-up (`src/dependency_graph.py`)

`DependencyGraph` tiene la lista di adiacenza caller → callee, il grafo inverso e i metadati dei nodi.

1. **Costruzione.** Prima si registrano tutte le funzioni, poi si aggiungono gli archi leggendo i `callees` (anche quelli verso funzioni esterne al progetto, che diventano nodi senza metadati).
2. **Tarjan.** `tarjan_scc()` trova le componenti fortemente connesse. Una SCC con più nodi è un gruppo di funzioni mutuamente ricorsive.
3. **Ordinamento topologico.** `get_topological_order_bottom_up()` costruisce il DAG condensato delle SCC, ne inverte gli archi e applica l'algoritmo di Kahn. Il risultato è una lista di SCC ordinata in modo che **le funzioni chiamate vengano prima di quelle chiamanti**: al momento di documentare un caller, i riassunti delle sue callee sono già nel database.
4. **Dead code.** `get_dead_code_nodes()` elenca le funzioni senza chiamanti (in-degree 0), escludendo `main`, `app_main`, `DllMain`, `WinMain`, i nomi che iniziano per `test_` o `Unity` e i `::main`.
5. **Esportazioni Mermaid.**
   - `export_mermaid()` → call graph globale, raggruppato in sottografi per file; esclude le funzioni della libreria standard (`malloc`, `printf`, `std::…`, …) e i simboli che iniziano per `__`; i simboli C++ come gli operatori sono sostituiti da identificatori sicuri (`operator<<` → `op_lshift`, …).
   - `export_module_call_graph()` → sottografo di un solo modulo, con funzioni interne, dipendenze esterne e libreria standard in tre sottografi distinti.
   - `export_file_dependency_mermaid()` → grafo degli `#include` tra i file del progetto (gli include di sistema `<...>` sono ignorati).

### 2.4 Generazione della documentazione (`src/doc_orchestrator.py`)

`DocOrchestrator.run_documentation_pipeline()` legge `extracted_metadata.json` e `topological_execution_order.json`, tiene solo le funzioni che sono definizioni e le visita **nell'ordine topologico**.

Per ogni funzione:

1. **Misure di dimensione** (righe non vuote, caratteri, token stimati ≈ caratteri/3.8 + 180) raccolte per i grafici di distribuzione (`utils/generate_size_charts.py` → `analytics_charts/`).
2. **Cache.** Se la documentazione esiste già in SQLite, la funzione viene saltata: questo permette di riprendere un'esecuzione interrotta.
3. **Firma.** Ricostruita da tipo di ritorno, nome e parametri (`void` se non ci sono parametri; per costruttori e distruttori non c'è tipo di ritorno).
4. **Ciclo di generazione e verifica, fino a 3 tentativi:**
   - *Modalità `single`* — una sola chiamata `generate_documentation()` con firma, sorgente, commento originale e riassunti delle callee prese da SQLite.
   - *Modalità `multiagent`* — Reader → Searcher → Writer (vedi §2.5), poi Verifier e, se il Verifier passa, Judge.
   - Il **Verifier** (§2.6) controlla il risultato. Se fallisce, gli errori vengono concatenati e passati al tentativo successivo come `validation_feedback`.
   - In modalità `multiagent` il **Judge** assegna un voto da 1 a 5. Con voto < 4 (e tentativi residui) la bozza è respinta e la critica del Judge viene passata al Writer.
   - Ogni tentativo (feedback ricevuto, testo generato, errori, voto del Judge) viene scritto in `verifier_debug_log.json`.
5. **Salvataggio.** Solo se la documentazione supera la verifica:
   - il tag `@complexity` viene **sovrascritto o iniettato** con i valori dell'AST (`enforce_deterministic_complexity`), qualunque cosa abbia scritto il modello;
   - un'ulteriore chiamata LLM assegna la funzione a una categoria funzionale (`classify_function`), riusando le categorie già create (categorizzazione incrementale);
   - il tutto è salvato in SQLite.
   Se dopo 3 tentativi la verifica non passa, la funzione **non viene salvata** (nessuna documentazione è meglio di una documentazione falsa).

Terminato il ciclo sulle funzioni:

- **Struct/class ed enum**: una chiamata LLM per tipo (`generate_struct_documentation`, `generate_enum_documentation`) per descrivere il tipo e i singoli campi/costanti.
- **Riassunto per modulo**: `generate_module_summary()` produce ruolo del file, flusso operativo e un esempio d'uso (quickstart). Il prompt vieta di dichiarare «thread-safe» o «atomico» senza prove di primitive di sincronizzazione.
- **Revisione di coerenza globale**: `verify_global_consistency()` (§2.6).
- **Log delle interazioni**: tutti i prompt e le risposte sono salvati in `llm_prompts_and_responses.json` e `LLM_INTERACTIONS_LOG.md`.
- **Esportazione** in `DOCUMENTATION.md` (§2.7).

### 2.5 Gli agenti (`src/agents/`)

| Agente | Cosa fa nel codice |
| :--- | :--- |
| `ReaderAgent` | Prepara un «fact sheet» della funzione (precondizioni, operazioni, casi limite, condizioni di errore, valore di successo). *Nota: il prompt JSON viene costruito ma la chiamata effettiva passa da `generate_documentation()` e il `brief_summary` risultante è usato come fact sheet.* |
| `SearcherAgent` | Non usa l'LLM: aggiunge al fact sheet i riassunti delle callee letti da SQLite (`get_callees_summaries`). Nel benchmark riceve un DB vuoto (`MockMemoryDB`), perché le funzioni sono valutate in isolamento. |
| `WriterAgent` | Compone il blocco Doxygen: unisce il fact sheet (passato come commento originale) con il feedback del Verifier (`[VERIFIER AST FEEDBACK]`) e quello del Judge (`[JUDGE AGENT CRITIQUE…]`) e chiama il provider. |
| `JudgeAgent` | Chiede al provider un voto 1–5 (rubrica: 5 impeccabile, 4 solido, 3 lacunoso, 2 generico, 1 errato o con allucinazioni) con critica e suggerimenti. Se il provider non implementa la valutazione risponde 5. |

Il **Verifier** non è un agente LLM: è codice Python (§2.6).

### 2.6 Il Verifier deterministico (`src/verifier.py`)

`DocumentationVerifier` costruisce l'insieme dei **simboli validi** del progetto (funzioni, struct, enum con le loro costanti, macro, typedef) e poi applica queste regole a ogni documentazione generata:

| # | Controllo | Come funziona |
| :--- | :--- | :--- |
| 1 | **Parametri** | Ogni parametro formale dell'AST deve comparire in un tag `@param[...] nome`. Parametri mancanti → rifiuto. |
| 2 | **Simboli in `@return`** | Se il primo token dopo `@return` è un identificatore MAIUSCOLO (stile enum/costante) deve esistere tra i simboli del progetto, oppure far parte di una whitelist standard (`NULL`, `EOF`, `INT_MAX`, `EINVAL`, `ENOMEM`, `ERANGE`, …). |
| 3 | **Tipo di ritorno** | Se la funzione è `void`, `@return` è vietato; se non è `void`, `@return` è obbligatorio. |
| 4 | **Booleani su puntatori** | Se il sorgente contiene `(ptr != NULL) && …` e la documentazione afferma «`@return true` se il puntatore è NULL», viene rifiutata. |
| 5 | **`@pre` contro `@return`** | Se `@return` documenta la gestione difensiva di NULL ma `@pre` impone «non NULL» come precondizione bloccante, c'è un'incongruenza. |
| 6 | **Existence Ratio** | Raccoglie le entità citate in `@see` e come `nome()` nel testo; quelle che non esistono tra i simboli del progetto né nella libreria standard note sono segnalate come allucinazioni. Se la frazione di entità esistenti è < 0.80 la documentazione è rifiutata. |
| 7 | **Linguaggio speculativo** | Rifiuta frasi come «dipende dall'implementazione», «si assume che», «generalmente». |

`enforce_deterministic_complexity()` inserisce `@complexity Temporale: … | Spaziale: …` con i valori dell'AST.

`verify_global_consistency()` è la revisione finale, anch'essa deterministica (espressioni regolari, nessuna chiamata LLM):
- sostituisce «thread-safe» / «atomica» con «monothread» nei riassunti dei moduli;
- corregge «variabili globali» in «campi membro di istanza» nei metodi C++;
- elimina un `@return` spurio dai costruttori;
- per la struct `RingBuffer` (progetto di esempio) corregge le affermazioni di thread-safety.

### 2.7 Persistenza ed export

**SQLite** (`src/doc_database.py`, file `documentation.db`) con cinque tabelle: `function_docs` (firma, tipo di ritorno, brief, Doxygen completo, complessità, categoria), `module_docs` (riassunto, flusso, esempio), `project_overview`, `struct_docs`, `enum_docs`. `clean_invalid_docs()` ripulisce record non validi all'avvio; `clear_database()` azzera tutto con `--force`.

**`DOCUMENTATION.md`** viene assemblato da `_export_markdown_documentation()` con queste sezioni:

0. **Panoramica del progetto** (dominio, funzionalità, build, formati di I/O, modello di memoria): una chiamata LLM, `generate_project_overview()`, riceve i riassunti dei moduli, i file di build trovati nel repository (`makefile`, `Makefile`, `CMakeLists.txt`, `meson.build`) e un riepilogo AST (puntatori grezzi, smart pointer, container STL).
1. **Mappe architetturali**: link al call graph interattivo Cytoscape.js (`utils/generate_interactive_graph.py`), diagramma UML delle classi in Mermaid, mappa degli `#include`, call graph globale (solo se ≤ 35 funzioni), **verifica degli `#include`** (ogni include è classificato come file interno, header standard C/C++/POSIX oppure dipendenza esterna non trovata), analisi del dead code, modello di memoria e concorrenza.
2. **Indice dei moduli** con ruolo, flusso operativo, quickstart e indice delle funzioni con categoria.
3. **Tipi di dato**: tabelle di campi di struct/class e costanti di enum.
4. **Dettaglio delle funzioni**: per ogni modulo un call graph locale, poi per ogni funzione firma, complessità AST, callee e caller come link incrociati ricavati dal grafo, e il blocco Doxygen.

Un passaggio finale normalizza i backtick spuri. Poi `utils/generate_full_doc_html.py` produce `FULL_DOCUMENTATION.html`, un portale autonomo con barra laterale.

### 2.8 Modalità e opzioni

```bash
python main.py                                   # menu interattivo (numero progetto + opzioni 'm', 'f', 'e')
python main.py -p "Easy C"                       # modalità single
python main.py -p "Easy C" -m multiagent -f      # multi-agente, rigenerazione da zero
python main.py -p "Easy C" -e                    # solo export da SQLite, senza LLM
```

| Opzione | Effetto |
| :--- | :--- |
| `-p` / `--project` | Nome o numero del progetto in `Test_code/`. |
| `-m` / `--mode` | `single` (un solo prompt + Verifier) o `multiagent` (Reader→Searcher→Writer→Verifier→Judge). |
| `-f` / `--force` | Svuota il database e rigenera tutto. Senza `-f` il database dell'esecuzione precedente (`results/<progetto>/documentation.db`) viene copiato nella nuova cartella e le funzioni già documentate sono saltate. |
| `-e` / `--export` | Rigenera solo Markdown, HTML e grafo dai dati già in SQLite. |
| `--lang` | `en` o `it`. Viene salvata in `execution_config.json`; nella pipeline di `main.py` il provider usa il default inglese, mentre `benchmark_eval.py` la inoltra davvero al prompt. |

Ogni esecuzione crea `results/<progetto>/run_<timestamp>_<mode>/` con `DOCUMENTATION.md`, `FULL_DOCUMENTATION.html`, `interactive_call_graph.html`, `extracted_metadata.json`, `topological_execution_order.json`, `execution_config.json`, `mmd_diagrams/` e `documentation.db`. I file principali sono copiati anche in `results/<progetto>/latest/`.

### 2.9 Il provider LLM (`src/llm_provider.py`)

- `GeminiLLMProvider`: modello `gemini-3.5-flash-lite`, **15 richieste al minuto** (pausa minima 60/15 s tra le chiamate), tre tentativi con attesa crescente su errori 429/503. `GEMINI_API_KEY` può contenere più chiavi separate da virgola: quando una esaurisce la quota giornaliera il provider passa alla successiva; finite tutte, solleva `QuotaDailyExceededError` e i progressi restano in SQLite.
- `MockLLMProvider`: usato in assenza di chiave, restituisce testo fittizio per prove offline.
- Il prompt di `generate_documentation()` contiene un esempio one-shot di blocco Doxygen e regole tassative: nomi di parametro esatti, nessun `@return` per `void`, nessun simbolo inventato, `NULL` → `false` nei booleani con cortocircuito, campi di classe ≠ variabili globali, `@pre`/`@post`, casi limite in `@details`, niente linguaggio speculativo. In caso di rifiuto, il testo del Verifier viene inserito nel prompt come «istruzioni di correzione».
- Ogni interazione è registrata (tipo, target, prompt, risposta grezza, risposta parsata).

---

## 3. Dataset e Ground Truth (`utils/build_dataset.py`)

Scarica da GitHub i sorgenti di sette librerie (cJSON, OpenCV `fast_math/cvstd/saturate`, TinyXML-2, sds, fmt, miniz, http-parser) in `dataset/sources/`, estrae le funzioni con `CCodeExtractor` e le associa alla **documentazione d'autore** letta dai commenti nei sorgenti.

- Il commento Doxygen/di blocco viene ripulito (`clean_doxygen_comment`) e deve superare `is_valid_ground_truth`.
- `doc_origin = "own"`: la funzione ha un commento proprio adiacente.
- `doc_origin = "group"`: la funzione fa parte di un blocco di dichiarazioni contigue che condividono un commento (ad es. «These calls create a cJSON item…» sopra `cJSON_CreateNull/True/False/…`). Il commento viene esteso ai membri e si aggiunge in coda `Variant: <parte variabile del nome>`. Il gruppo è accettato solo se i nomi formano una *famiglia* (`is_name_family`), per non attribuire a una funzione il commento di un'altra.
- Risultato: `dataset/benchmark.db` (tabella `benchmark_functions`: libreria, linguaggio, file, nome, firma, tipo di ritorno, parametri, sorgente, commento grezzo, `cleaned_doc`, complessità) e `dataset/ground_truth.jsonl`.

`python utils/build_dataset.py` riscrive il dataset; `--no-group-comments` usa solo i commenti propri, `--output-dir` scrive altrove.

---

## 4. Benchmark: documentazione generata contro Ground Truth (`utils/benchmark_eval.py`)

### 4.1 Selezione delle funzioni (`get_benchmark_candidates`)

Legge da `benchmark.db` le funzioni con Ground Truth non vuoto. Strategie di campionamento:

- `sequential`: le prime N per id;
- `random`: campione uniforme (con `--seed`);
- `stratified`: ordina per LOC, divide l'intervallo in N classi con **limiti logaritmici** e sceglie una funzione a caso per classe, così da coprire funzioni brevi, medie e lunghe.

Filtri: `--min-loc`, oppure `--functions <file>` con un elenco esplicito di nomi (usato dal confronto con CodeWiki; se una funzione compare sia in `.h` sia in `.cpp` si tiene la versione di implementazione).

### 4.2 Generazione

Per ogni funzione si usa lo stesso ciclo della pipeline (fino a 3 tentativi con Verifier e, in `multiagent`, Judge), ma in isolamento: nessuna callee nel contesto. Il Verifier riceve i simboli reali estratti dagli header della libreria (enum, struct, macro, typedef) e le funzioni del DB.

### 4.3 Metriche calcolate per ogni funzione (`utils/benchmark_metrics.py`)

Il testo confrontato col Ground Truth è `brief_summary + @brief + @details` (senza i tag), dopo il parsing strutturato del Doxygen (`parse_doxygen_block`: brief, details, `@param` con direzione, `@return`, `@warning`).

**Similarità con il Ground Truth**

| Metrica | Implementazione |
| :--- | :--- |
| SBERT | Coseno tra embedding `all-MiniLM-L6-v2`, troncato a [0,1]. |
| BERTScore F1 | `bert_score` con `bert-base-uncased`, su CPU, in batch. |
| CodeBERTScore F1 | Stesso calcolo con `microsoft/codebert-base` (layer 10). |
| ROUGE-L | LCS implementata a mano su token senza stopword. |
| TF-IDF coseno | Coseno tra vettori di frequenza dei termini. |
| METEOR | NLTK con stemmer e WordNet. |
| Jaccard, token recall, length ratio, brevity penalty | Sovrapposizione di token e rapporto di lunghezza (penalità stile BLEU). |
| Concept checklist | Presenza dei concetti attivi nel Ground Truth (ownership, null-safety, errori, mutazione, limiti) anche nel testo generato. |
| Distanza di Fréchet | Distanza tra le distribuzioni di embedding GT e generate (solo a livello di corpus). |

**Contratti rispetto all'AST**

| Metrica | Implementazione |
| :--- | :--- |
| Param Precision/Recall/F1 | Confronto tra i nomi dei `@param` e quelli dell'AST; gestisce i parametri anonimi dei prototipi. |
| Return match | `void` ⇒ nessun `@return`; non-`void` ⇒ almeno un `@return`. |
| Hallucination rate | Errori del Verifier che parlano di allucinazione, rapportati ai simboli documentati. |

**Qualità intrinseca** (non richiede il Ground Truth)

| Metrica | Implementazione |
| :--- | :--- |
| EDR (error documentation) | Se il sorgente ha rami di errore (`return NULL/-1/0/false`, `return …ERR`), la documentazione deve nominare l'errore. |
| ECC (edge-case coverage) | Guardie rilevate nel sorgente (NULL, zero/negativo, stringa vuota) e quante sono citate nel testo. |
| Actionability | Punteggio pesato: direzione dei parametri (35%), `@brief` chiaro (20%), `@return` dettagliato (25%), precondizioni/avvertenze (20%). |

**Task a valle**

- **Code retrieval (MRR, Hit@1/3/5).** La documentazione generata fa da query; il corpus è l'insieme delle funzioni della libreria rappresentate come `nome: firma`. Si ordinano per similarità SBERT e si misura la posizione della funzione corretta (reciprocal rank).
- **LLM-as-a-Judge (`utils/llm_judge.py`).** Gemini con temperatura 0.4 e risposta JSON, **5 round per prospettiva**, con «reasoning» prima del voto. Prospettiva A (*Faithfulness*, codice + GT contro documentazione) cerca i difetti `DEF-1…5` (errori non documentati, ownership ambigua, descrizione tautologica, direzioni errate, invenzioni). Prospettiva B (*Alignment*, GT contro documentazione) cerca `ALIGN-1…4` (avvertenze perse, intento distorto, rumore, superficialità). Si riportano media e deviazione standard per prospettiva e la media delle due medie come punteggio combinato.
- **Round-Trip Differential Testing** (§4.4).

### 4.4 Round-Trip Differential Testing (`utils/roundtrip_eval.py`)

Misura se la documentazione basta a ricostruire il comportamento della funzione. Per ogni funzione:

1. **Scaffold di contesto** (`src/context_scaffold.py`): la libreria viene inferita dal nome/firma; dall'header principale si estraggono con libclang enum, struct e macro da passare ai prompt, e si prepara un *runtime* Python con mock (funzioni C di libreria, classi di cJSON, TinyXML-2, http-parser, sds, miniz e utility OpenCV, tutte derivate da `TolerantBaseMock`, che restituisce un mock a qualunque attributo mancante).
2. **Sintesi dalla documentazione** ($f_{doc}$): il «Coder» scrive la funzione in Python vedendo **solo** la documentazione, la firma e lo scaffold (metodi C++ → classe con costruttore tollerante; puntatori di output → liste mutabili; `ctypes` vietato).
3. **Sintesi dal sorgente** ($f_{ref}$): lo stesso modello traspone il codice C/C++ reale in Python.
4. **Suite di test** (pytest) scritta dal «Tester» a partire dalla sola documentazione: numero adattivo di test `test_semantic_*` (tipicamente 4–10) più 1–2 test `test_auto_property_*` con **Hypothesis** (`max_examples=50`). Regole del prompt: black-box, nessuna `pytest.raises` se la documentazione non dichiara eccezioni, nessuna fixture.
5. **Esecuzione**: i test girano in un file temporaneo con timeout di 25 s, prima su $f_{doc}$ e poi su $f_{ref}$. Le sintesi sono controllate con `ast.parse` e, in caso di errore di sintassi, il modello è richiamato una volta per correggerle.
6. **Metriche**: *pass rate* di $f_{doc}$ (self-consistency), *reference pass rate* di $f_{ref}$ e *dual agreement* (frazione di test con lo stesso esito, passato su entrambe, sul totale).
7. **Classificazione della funzione** (`classify_function_type`): *Stateful / Object-Graph* (metodi C++, nodi cJSON/XML), *Pointer / Buffer-Driven* (puntatori, buffer, `size_t`), *Stateless / Primitive*.

#### 4.4.1 Metriche sulla forza del contratto (opzionali)

Due metriche aggiuntive, attivabili con `--mutation` e `--ambiguity`, misurano **quanto la documentazione determina il comportamento**, non quanto assomigli al Ground Truth. Definizioni e interpretazione in `METRICHE_BENCHMARK_GUIDA.md`.

- **Doc Mutation Score** (`utils/code_mutator.py`, `utils/doc_mutation_score.py`): dal reference si generano mutanti AST di primo ordine; si misura quanti ne uccide la suite scritta dalla sola documentazione. Una suite *signature-only* (stesso generatore, nessuna doc) isola il contributo della documentazione (*Doc Lift*).
- **Specification Ambiguity Index** (`utils/spec_ambiguity.py`): N sintesi indipendenti (temperatura 0.8) dalla stessa documentazione eseguite su sonde comuni; il disaccordo tra implementazioni misura l'ambiguità. Con il reference ogni sonda è classificata come *determinata corretta*, *determinata ma divergente* (informazione nascosta) o *ambigua*.

`utils/roundtrip_error_analysis.py` classifica i test falliti in una tassonomia: simbolo/ambiente mancante, mismatch di interfaccia, fallimento di contratto comportamentale, bug del test harness, errore di sintassi, timeout, altro. Questo separa gli errori attribuibili alla documentazione da quelli causati dalla catena di valutazione.

### 4.5 Output di un run

`results/benchmark_<libreria>/run_<timestamp>_<mode>/` (copiato in `latest/`):

- `execution_config.json` con il comando esatto per riprodurre il run;
- `eval_report_<mode>.json` (dati grezzi) e `.md` (report);
- `eval_charts_<mode>.png` e i grafici avanzati (tabella sotto);
- se il round-trip è attivo: `roundtrip_results.json`, `eval_chart_roundtrip.png`, `roundtrip_error_report.md`, `eval_chart_roundtrip_errors.png`.

| Grafico (`utils/plot_advanced_benchmark.py`) | Cosa mostra |
| :--- | :--- |
| Radar | Sei dimensioni: contratti AST, semantica neurale, actionability, copertura di errori/edge case, affidabilità formale (1 − hallucination rate), utilità a valle (retrieval + round-trip). |
| Semantica vs round-trip | Scatter SBERT / pass rate con retta OLS e correlazione di Pearson: dice se «suona bene» e «funziona» vanno insieme. |
| Distribuzioni | Violin plot con punti sovrapposti e mediana, per ogni metrica. |
| Heatmap | Funzione × metrica, valori in [0,1]. |
| Cause di scarto del Verifier | Quante funzioni passano al primo tentativo e quante cadono per parametri, ritorno, simboli o Judge. |
| Correlazione tra metriche | Matrice di Pearson per individuare metriche ridondanti. |
| Residui | Differenza tra SBERT e pass rate: separa le «allucinazioni plausibili» (testo fluente ma codice sbagliato) dalle «parafrasi robuste». |
| Complessità | LOC contro prestazioni, per vedere se la qualità degrada sulle funzioni lunghe. |
| Imbuto di validazione | Bozza → Verifier → Judge → Round-Trip. |

### 4.6 Comandi

```bash
python utils/benchmark_eval.py                                        # guidato
python utils/benchmark_eval.py -l cJSON -n 10 --roundtrip
python utils/benchmark_eval.py -l all -n 10 --sampling stratified --seed 42 -m multiagent --roundtrip
python utils/benchmark_eval.py -l miniz -n 5 --mock --no-roundtrip     # offline
```

| Flag | Default | Significato |
| :--- | :--- | :--- |
| `-l` / `--library` | `cJSON` | `cJSON`, `OpenCV`, `TinyXML-2`, `sds`, `fmt`, `miniz`, `http-parser`, `all`. |
| `-n` / `--limit` | `5` | Numero di funzioni. |
| `-s` / `--sampling` | `sequential` | `sequential`, `random`, `stratified` (scorciatoie `--random`, `--stratified`). |
| `--seed`, `--min-loc`, `--functions` | – | Riproducibilità e filtri (§4.1). |
| `-m` / `--mode` | `single` | `single` o `multiagent`. |
| `--roundtrip` / `--no-roundtrip` | attivo | Esegue o salta il round-trip. |
| `--mutation`, `--ambiguity` | off | Con il round-trip: Doc Mutation Score e Specification Ambiguity Index (§4.4.1). |
| `--lang` | `en` | Lingua della documentazione. |
| `--mock` | off | `MockLLMProvider`, nessun costo API. |

---

## 5. Confronto con CodeWiki (`compare_codewiki.py`)

Per ogni libreria in `compare_CodeWiki/<Libreria>/` che esista anche in `benchmark.db`, cinque passi in sequenza:

| Passo | Modulo | Cosa fa |
| :--- | :--- | :--- |
| `parse` | `utils/parse_codewiki_to_benchmark.py` | Legge i Markdown di CodeWiki (due stili: per classe e per funzione), estrae le descrizioni dei metodi e le **associa alle funzioni del DB**; produce il mapping e un rapporto di copertura. |
| `metrics` | `utils/evaluate_codewiki_metrics.py` | Calcola le metriche NLP/statiche (SBERT, BERTScore, METEOR, EDR, ECC…) della documentazione CodeWiki contro il Ground Truth. |
| `pipeline` | `utils/benchmark_eval.py` | Documenta con la pipeline le funzioni della libreria (tutte con Ground Truth, oppure solo quelle di CodeWiki con `--pipeline-scope codewiki`) in batch da 12; riprende dalle funzioni già presenti in `results/`. Se un run contiene punteggi di ripiego del Judge (quota esaurita), i punteggi dei record toccati sono rimossi, oppure il report intero è scartato (`.invalid`) se i record toccati superano il 60%. |
| `advanced` | `utils/evaluate_codewiki_advanced.py` | Applica a CodeWiki le stesse metriche avanzate della pipeline (retrieval, CodeBERTScore, Judge a 5 round, round-trip) con la stessa configurazione, con cache incrementale. |
| `compare` | `utils/plot_codewiki_comparison.py`, `plot_codewiki_extra.py`, `plot_codewiki_overall.py` | Grafici e report del confronto sulle funzioni in comune, test di Wilcoxon, vittorie/pareggi/sconfitte per metrica, riepilogo tra librerie. |

```bash
python compare_codewiki.py                                  # tutte le librerie, tutti i passi
python compare_codewiki.py -l cJSON sds                     # solo alcune librerie
python compare_codewiki.py --list                           # librerie disponibili
python compare_codewiki.py --dry-run                        # piano senza eseguire
python compare_codewiki.py --steps parse,metrics,compare    # solo la parte offline
python compare_codewiki.py --pipeline-scope codewiki
```

Output: `compare_CodeWiki/<Libreria>/` (mapping, metriche, `charts/`, `codewiki_vs_pipeline_report.md`), `compare_CodeWiki/SUMMARY.md` e `compare_CodeWiki/overall/` (`OVERALL_REPORT.md` e grafici complessivi). I passi `pipeline` e `advanced` richiedono l'API Gemini; con `--mock` il primo è saltato (per non inquinare `results/`) e il secondo scrive su un file `_mock`.

---

## 6. Validazione delle metriche

Gli script in `utils/` che iniziano per `verify_`, `evaluate_nlp_`, `evaluate_stress_` e `evaluate_judge_` non valutano la pipeline: valutano **le metriche stesse**, su casi controllati, per capire che cosa misurano davvero.

| Script | Domanda a cui risponde |
| :--- | :--- |
| `verify_metric_sensitivity.py`, `evaluate_nlp_5classes_crossdomain.py` | Come reagiscono SBERT, BERTScore, CodeBERTScore, ROUGE-L, TF-IDF a coppie *equivalenti*, *avversarie* (stessa sintassi, logica opposta), *dello stesso dominio*, *ortogonali*, *prolisse*; in C-C, Python-Python e C-Python. Il «paradosso avversario» è il caso in cui un bug riceve un punteggio più alto del codice equivalente. |
| `verify_doc_metrics.py` | SBERT contro BERTScore su parafrasi, negazioni critiche, scambio di ruoli tra parametri, verbosità. |
| `verify_judge_and_roundtrip.py`, `evaluate_judge_roundtrip_5classes.py` | Judge e round-trip sugli stessi casi controllati (30 casi: 6 domini × 5 classi). |
| `verify_token_truncation.py`, `evaluate_nlp_token_length_sensitivity.py` | Limiti di lunghezza dei modelli (SBERT 256 token, BERT/CodeBERT 512) e «cecità» alle differenze oltre la soglia. |
| `evaluate_stress_test_limits.py` | Inversione min/max, negazione di un carattere, off-by-one, ridenominazione dei simboli, allucinazioni mascherate da testo forbito. |
| `verify_canonical_representation.py` | Se confrontare pseudocodice o diagrammi di flusso invece del codice grezzo migliora le metriche cross-language. |
| `explain_metric_internals.py` | Ispezione interna: allineamento token-a-token di BERTScore, contributo dei token in SBERT, pesi di attenzione sulle negazioni. |
| `generate_*_plots.py`, `generate_metrics_validation_pdf.py`, `generate_case_study_report.py` | Grafici a 300 DPI, PDF di sintesi e studio qualitativo di casi massimi/mediani/minimi (output in `results/metrics_validation/`). |

---

## 7. Struttura del repository

```text
TESI_Nicola_Flego/
├── main.py                          # CLI della pipeline di documentazione
├── compare_codewiki.py              # confronto CodeWiki vs pipeline
├── src/
│   ├── extract_metadata.py          # parser AST libclang + complessità Big-O
│   ├── dependency_graph.py          # call graph, Tarjan, Kahn, dead code, export Mermaid
│   ├── doc_orchestrator.py          # ciclo di generazione/verifica + assemblaggio documento
│   ├── doc_database.py              # persistenza SQLite
│   ├── llm_provider.py              # Gemini / Mock, rate limit, rotazione chiavi, prompt
│   ├── verifier.py                  # verificatore deterministico
│   ├── context_scaffold.py          # tipi e mock di libreria per il round-trip
│   ├── parse_ast.py                 # utilità di stampa dell'AST
│   └── agents/                      # Reader, Searcher, Writer, Judge
├── utils/                           # benchmark, metriche, round-trip, judge, CodeWiki, grafici, validazione
├── dataset/                         # benchmark.db, ground_truth.jsonl, sources/ (sorgenti delle librerie)
├── Test_code/                       # progetti C/C++ da documentare con main.py
├── compare_CodeWiki/                # documentazione CodeWiki e risultati del confronto, per libreria
├── results/                         # output: <progetto>/, benchmark_<libreria>/, metrics_validation/
├── tests/                           # test_extraction.py, test_judge_agent.py
├── thesis/                          # sorgenti LaTeX della tesi
└── Paper/                           # materiale bibliografico
```
