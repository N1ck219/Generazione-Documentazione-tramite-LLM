# 🧠 Sistema Multi-Agente ed Analisi Statica AST per Documentazione Automatica C / C++
> *Framework ibrido per la reverse-engineering, l'estrazione statica formale AST, l'ordinamento topologico bottom-up e la generazione certificata di documentazione tecnica tramite Large Language Models (LLM) ed Agenti Autonomi.*

---

## 📌 Panoramica del Progetto

Il progetto implementa un framework innovativo in grado di analizzare codebase complesse in **C e C++** (anche eterogenee, con classi, struct, template, costruttori e file makefile), superando i limiti dei tool tradizionali (come Doxygen statico o semplici wrapper LLM isolati).

L'architettura combina:
1. **Analisi Statica Deterministica (libclang AST Parser)**: estrazione a livello compilatore di firme, parametri, chiamate tra funzioni (Call Graph), complessità Big-O e modelli di memoria.
2. **Algoritmo di Tarjan & Ordinamento Topologico (Bottom-Up DAG)**: risoluzione di cicli di ricorsione mutua (Strongly Connected Components - SCC) e garanzia del principio *Dependencies-First* (le callee vengono documentate prima dei caller, propagando il contesto informativo verso l'alto).
3. **Pipeline Multi-Agente Gerarchica**: agenti specializzati (*Reader, Searcher, Writer, Module Storyteller e Lead Architect*) che cooperano con memoria persistente SQLite.
4. **Verifier Deterministico Formale (Anti-Hallucination & Consistency Audit)**: controlli formali a guardie logiche e calcolo dell'Existence Ratio ($\ge 0.80$) per azzerare le allucinazioni e garantire veridicità assoluta dei contratti software (`@param`, `@return`, `@pre`, `@post`, `@complexity`).

---

## 🏗️ Architettura della Pipeline di Elaborazione

La pipeline si articola in **5 Fasi Operative Sequenziali**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ FASE 1: Estrazione Metadati AST Clang (libclang CIndex)                     │
 │ - Parsing C/C++ AST, firme, puntatori, classi, struct, enum e #include     │
 │ - Calcolo Deterministico Big-O (Loop Depth, passaggi vector, allocazioni)   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ FASE 2: Grafo delle Dipendenze & Tarjan Bottom-Up (DAG)                     │
 │ - Costruzione Call Graph globale e File Include Map                         │
 │ - Isolamento SCC (Componenti Fortemente Connesse) con Algoritmo di Tarjan   │
 │ - Generazione grafici di complessità (Token distribution & LOC histogram)   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ FASE 3: Orchestrazione Agenti LLM (Dependencies-First)                      │
 │ - Generazione bottom-up con iniezione del contesto delle callee già note    │
 │ - Modalità Ibrida Standard o Multi-Agente (Reader->Searcher->Writer)        │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ FASE 4: Validazione Rigida a 3 Tentativi (Deterministic Verifier)           │
 │ - Match esatto parametri AST vs @param                                      │
 │ - Validazione simboli @return contro whitelist POSIX/errno e simboli reali  │
 │ - Verifica contratti logici @pre/@post e iniezione Big-O certificata        │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ FASE 5: Global Consistency Review, Lead Architect & Export                  │
 │ - Sintesi gerarchica moduli (Module Storytellers -> Lead Architect Agent)   │
 │ - Generazione automatica: DOCUMENTATION.md, FULL_DOCUMENTATION.html,        │
 │   Call Graph Interattivo Cytoscape.js e Diagrammi Mermaid UML/File/Calls    │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Controlli di Qualità: Deterministici vs LLM

Il cuore metodologico del progetto è la netta separazione tra **garanzie formali matematiche (non negoziabili)** e **capacità di astrazione semantica dell'AI**:

### 1. Controlli Deterministici (Codice Python & libclang AST)
* **Complessità Computazionale Big-O**:
  - Nessuna allucinazione LLM: la complessità temporale e spaziale è calcolata visitando l'AST Clang (profondità di annidamento cicli `for`/`while`/`do`, chiamate STL lineari `max_element`/`find`/`erase`, passaggio di `vector` per valore e copie profonde $O(W \cdot H)$).
  - Il tag `@complexity` viene sovrascritto/iniettato forzatamente dal Verifier (`enforce_deterministic_complexity`).
* **Verifica Parametri Formali (`@param`)**:
  - Confronto 1-a-1 tra i parametri dell'AST e quelli documentati. Se un parametro è omesso, rinominato o allucinato, la documentazione viene rigettata.
* **Verifica Tipo di Ritorno (`@return`)**:
  - Se la funzione è `void`, è vietata la clausola `@return`. Se restituisce un tipo non-void (`int`, `void *`, puntatori), `@return` è obbligatorio.
* **Whitelist Simboli e Costanti di Ritorno**:
  - Verifica che gli identificatori citati in `@return` esistano fisicamente tra le `enum` del progetto o nella whitelist standard POSIX/C (`EINVAL`, `ENOMEM`, `NULL`, `EOF`, `ERANGE`, ecc.).
* **Controlli di Logica Booleana su Puntatori**:
  - Intercettazione di cortocircuiti AST `(ptr != NULL) && ...` per impedire all'AI di dichiarare che la funzione *"restituisce true se il puntatore è NULL"*.
* **Rilevamento Dead Code & Nodi Orfani**:
  - Analisi di raggiungibilità statica sul grafo per identificare funzioni con $\text{in-degree} = 0$ non invocate nel flusso operativo.

### 2. Controlli e Ragionamento LLM (Agenti Intelligenti)
* **Lead Architect Agent**:
  - Ispezione combinata dei report modulari, dei file di build reali (`makefile` / `CMakeLists.txt`) e dell'AST per descrivere il dominio del problema, le istruzioni di build esatte, le specifiche di I/O e il modello di memoria.
* **Module Storytellers**:
  - Spiegazione ad alto livello dello scopo del file sorgente, diagramma del ciclo di vita e generazione di esempi d'uso minimi funzionanti (Quickstart Snippets).
* **Global Refiner**:
  - Audit di coerenza globale tra moduli: rimozione di false affermazioni di "thread-safety" o scambio di variabili membro d'istanza per "variabili globali".

---

## 🚀 Guida all'Uso e Comandi CLI

Il programma principale si avvia tramite `main.py` e supporta sia l'interfaccia interattiva da terminale che l'esecuzione diretta con flag da riga di comando.

### Sintassi dei Comandi

Il programma principale si avvia tramite `main.py` e supporta sia l'interfaccia guidata interattiva sia l'esecuzione diretta con argomenti standard da riga di comando (`argparse`).

```bash
# Modalità guidata con menu a selezione:
python main.py

# Esecuzione diretta con opzioni da terminale:
python main.py -p <PROGETTO> [-m {single,multiagent}] [-f] [-e] [--lang {en,it}]
```

### Tabella dei Parametri Disponibili

| Parametro Lungo | Parametro Breve | Valori Ammessi | Descrizione |
| :--- | :--- | :--- | :--- |
| `--project` | `-p` | Nome (es: `"Easy C"`) o Numero | Specifica direttamente il progetto da documentare saltando il menu interattivo. |
| `--mode` | `-m` | `single`, `multiagent` | Seleziona la pipeline di generazione: `single` (Ibrido Standard) o `multiagent` (Pipeline a 5 agenti: *Reader $\rightarrow$ Searcher $\rightarrow$ Writer $\rightarrow$ Verifier $\rightarrow$ Judge*). |
| `--force` | `-f` | *(flag booleano)* | **Rigenerazione Forzata (Clear DB)**: svuota il database SQLite (`documentation.db`) forzando la ri-generazione completa da zero di tutte le funzioni, struct e sintesi. |
| `--export` | `-e` | *(flag booleano)* | **Export Rapido**: rigenera istantaneamente il file `DOCUMENTATION.md`, il portale HTML ed il grafo interattivo Cytoscape.js leggendo i dati già presenti in SQLite **senza effettuare chiamate LLM** (~1 secondo). |
| `--lang` | | `en`, `it` | Lingua della documentazione tecnica e dei commenti Doxygen (default: `en`). |

---

### 🗂️ Storicizzazione Automatica delle Esecuzioni (`run_<timestamp>_<mode>`)

Per consentire audit scientifici, tracciamento storico e analisi comparative delle differenze nel tempo:
1. Ogni esecuzione genera una cartella dedicata con timestamp in `results/<progetto>/run_YYYYMMDD_HHMMSS_<mode>/` contenente:
   - `DOCUMENTATION.md`: Documentazione completa generata.
   - `interactive_call_graph.html`: Applicazione Cytoscape.js per la navigazione interattiva del grafo.
   - `extracted_metadata.json`: Metadati AST estratti dal codice C/C++.
   - `topological_execution_order.json`: Ordine bottom-up di visita.
   - `mmd_diagrams/`: Diagrammi AST e delle chiamate in sintassi Mermaid.
   - `execution_config.json`: File contenente tutte le impostazioni, i parametri e i flag passati da riga di comando.
2. Per comodità di consultazione rapida, una copia dell'ultima esecuzione è sempre disponibile e sincronizzata in `results/<progetto>/latest/`.

---

### 💡 Esempi Pratici di Utilizzo

#### 1. Esecuzione Interattiva (Menu da Terminale)
```bash
python main.py
```

#### 2. Esecuzione Diretta da Terminale
* **Analisi standard del progetto "Easy C"**:
  ```bash
  python main.py -p "Easy C"
  ```
* **Esecuzione Multi-Agente con Giudice e rigenerazione forzata da zero**:
  ```bash
  python main.py -p "Easy C" -m multiagent -f
  ```
* **Export rapido di grafici e Markdown senza chiamate API (da dati SQLite)**:
  ```bash
  python main.py -p "Easy C" -e
  ```
  ```

---

## 📂 Struttura delle Cartelle del Repository

```text
TESI_Nicola_Flego/
├── main.py                        # Entry point CLI con menu e routing progetti
├── requirements.txt               # Dipendenze Python (libclang, tqdm, google-genai, matplotlib)
├── .env                           # Configurazione API Keys (GEMINI_API_KEY)
├── dataset/                       # Dataset di Benchmark & Ground Truth per C/C++
│   ├── ground_truth.jsonl         # Dataset riga per riga (firme, codice e doc originale)
│   ├── benchmark.db               # Database SQLite indicizzato con tutte le funzioni estratte
│   └── sources/                   # Sorgenti ufficiali (cJSON.h, cJSON.c, OpenCV fast_math, ecc.)
├── src/
│   ├── extract_metadata.py        # Parser AST Clang e Calcolo Deterministico Big-O
│   ├── dependency_graph.py        # Grafo Dipendenze, Tarjan SCC e Reachability Dead Code
│   ├── doc_database.py            # Layer di persistenza SQLite (tabelle docs, struct, moduli, overview)
│   ├── doc_orchestrator.py        # Orchestratore Pipeline, Assemblaggio Documento & Export
│   ├── llm_provider.py            # Client Gemini / Mock con Rate Limiting, Key Rotation e supporto EN/IT
│   ├── verifier.py                # Verifier Formale, Anti-Hallucination & Existence Ratio
│   └── agents/                    # Pipeline Multi-Agente Specialistica (Reader, Searcher, Writer)
├── utils/
│   ├── build_dataset.py           # Downloader sorgenti ufficiali e costruttore dataset Ground Truth
│   ├── benchmark_eval.py          # Esecutore Benchmark con confronto LLM vs Ground Truth
│   ├── benchmark_metrics.py       # Parser Doxygen, metriche locali (TF-IDF, ROUGE-L, Slot F1) e grafici
│   ├── generate_interactive_graph.py  # Generatore Visualizzatore Web Cytoscape.js
│   ├── generate_full_doc_html.py      # Generatore Portale Web HTML con sidebar e CSS scuro
│   ├── generate_size_charts.py        # Generatore grafici di token e distribuzione LOC
│   └── generate_ast_diagram.py        # Generatore diagrammi AST Mermaid
├── Test_code/                     # Cartella dei progetti sorgente C/C++ da analizzare
│   ├── Easy C/
│   ├── Medium C/
│   ├── Hard C/
│   ├── ring_buffer/
│   └── tesi triennale C++/
└── results/                       # Risultati generati per ciascun progetto e benchmark
    ├── benchmark_cjson/           # Report comparativi, grafici PNG e metriche per cJSON
    └── <Nome_Progetto>/
        ├── DOCUMENTATION.md           # Relazione tecnica completa Markdown
        ├── FULL_DOCUMENTATION.html    # Portale Web autonomo consultabile da browser
        ├── interactive_call_graph.html# Call Graph interattivo (zoom, filtri STL, ricerca)
        ├── documentation.db           # Database SQLite con metadati e documentazione cache
        ├── extracted_metadata.json    # Metadati estratti dall'AST Clang
        ├── LLM_INTERACTIONS_LOG.md    # Traccia trasparente di tutti i prompt/risposte LLM
        ├── mmd_diagrams/              # Diagrammi Mermaid (Call Graph, File include, UML)
        └── analytics_charts/          # Grafici PNG (Distribuzione LOC e Consumo Token)
```

---

## 📊 Benchmark & Framework di Valutazione (Ground Truth)

Il framework integra un'architettura scientifica di **benchmark automatizzato** strutturata su **3 Livelli Metodologici** per confrontare la documentazione generata con il *Ground Truth* (GT) delle librerie ufficiali C/C++ (`cJSON` per C puro e `OpenCV` per C++):

```
                               ┌──────────────────────────────────────────────────┐
                               │       Framework di Valutazione Multi-Livello     │
                               └────────────────────────┬─────────────────────────┘
                                                        │
         ┌──────────────────────────────────────────────┼──────────────────────────────────────────────┐
         ▼                                              ▼                                              ▼
[1. Semantica & Embedding Dense]            [2. Contratti Sintattici AST]                [3. Task a Valle & Utility]
• Sentence-BERT (Cosine Sim)                • Parameter Slot-Filling (P / R / F1)        • Downstream Code Retrieval (MRR / Hit@K)
• BERTScore F1 (bert-base-uncased)          • Return Contract Match                      • LLM-as-a-Judge (Monte Carlo T=0.4)
• CodeBERTScore F1 (microsoft/codebert-base)• Deterministic Verifier (Zero Allucinazioni)• Round-Trip Differential Testing (Pytest)
• BLEURT Quality Score & ROUGE-L
```

---

### 1. Dettaglio dei 3 Livelli di Metriche

#### 🔹 Livello 1: Semantica Continua ed Embedding
- **Sentence-BERT (`all-MiniLM-L6-v2`)**: Similarità coseno semantica nello spazio vettoriale continuo tra la descrizione generata (`@brief` + `@details`) e il Ground Truth.
- **BERTScore & CodeBERTScore F1**: Valutazione token-level pesata, pre-addestrata su codice e testo tecnico per catturare la nomenclatura di programmazione.
- **BLEURT Quality Score & ROUGE-L**: Misura euristica della qualità e sovrapposizione delle sequenze lessicali con *Brevity Penalty*.

#### 🔹 Livello 2: Contratti Sintattici ed Estrazione di Fatti (AST Clang)
- **Parameter Slot-Filling (Precision, Recall, F1)**: Estrazione dei tag `@param` e confronto 1-a-1 con i parametri reali dell'AST.
- **Return Contract Match**: Conformità stringente tra il tipo restituito (`void` vs tipi con valore) e i tag `@return`.
- **Deterministic Verifier**: Controllo matematico per prevenire allucinazioni su tipi, simboli o costanti.

#### 🔹 Livello 3: Task a Valle e Validazione Comportamentale (Downstream Utility)
- **Docstring-to-Code Retrieval (MRR & Hit@K)**:
  - Usa la documentazione generata dall'LLM come query per ricercare la funzione corretta all'interno dell'intero corpus di funzioni del database.
  - Calcola il **Reciprocal Rank (RR)**, l'**MRR globale**, **Hit@1** e **Hit@5**.
- **LLM-as-a-Judge (Monte Carlo Sampling)**:
  - Giudice basato su Gemini con campionamento a temperatura controllata ($T=0.4$) su 5 iterazioni per funzione ($\mu \pm \sigma$).
  - **Prospettiva A (Faithfulness - Code+GT vs Doc)**: Aderenza alla logica del codice sorgente C/C++ ed assenza di difetti (`DEF-1`..`DEF-5`).
  - **Prospettiva B (Alignment - GT vs Doc)**: Conservazione dell'intento dell'autore originario e avvertenze (`ALIGN-1`..`ALIGN-4`).
- **Round-Trip Dual Differential Testing (Doc-to-Code Synthesis & Dual Pytest Execution)**:
  - **Sintesi Duale Parallela**:
    1. *Implementazione Doc-Driven ($f_{\text{doc}}$)*: Gemini ricostruisce il codice Python basandosi **esclusivamente sulla documentazione generata** (senza vedere il sorgente originale C/C++).
    2. *Implementazione Reference Code-Driven ($f_{\text{ref}}$)*: Gemini traspila fedelmente il codice sorgente C/C++ reale in Python (Ground Truth comportamentale).
  - **Generazione Suite di Test Adattiva & Fuzzing (Hypothesis)**:
    - *Test Semantici Adattivi (Gemini)*: libertà autonoma di dimensionamento dei test in base alla complessità della funzione (casi nominali, edge cases, valori nulli/negativi, codici di ritorno ed enum).
    - *Test Automatici di Robustezza Property-Based (Hypothesis)*: generazione automatica di oltre 50 combinazioni di input casuali ed estremi (`@given(...)`) per stress-testare invarianti e prevenire crash non gestiti.
  - **Metriche Differenziali**:
    - **Self-Consistency Pass Rate %**: percentuale di test superati dal codice sintetizzato da docstring.
    - **Reference Pass Rate %**: percentuale di test superati dall'implementazione di riferimento originale.
    - **Dual Agreement Rate %**: tasso di equivalenza comportamentale diretta tra il codice derivato dalla documentazione e il codice reale C/C++ ($f_{\text{doc}}(x) \equiv f_{\text{ref}}(x)$).

---

### 2. Comandi CLI per l'Esecuzione del Benchmark

Il benchmark può essere eseguito in modalità **guidata interattiva** oppure direttamente tramite **parametri da terminale**, integrando sia le metriche quantitative sia il Round-Trip Differential Testing in un unico comando:

```bash
# Modalità guidata con menu a selezione (libreria, numero funzioni, pipeline, strategia campionamento e Round-Trip):
python utils/benchmark_eval.py

# Esecuzione diretta completa con Round-Trip integrato (default abilitato):
python utils/benchmark_eval.py -l cJSON -n 10 --roundtrip

# Campionamento Stratificato con vincoli di complessità (copertura da 1 a 100+ LOC, riproducibile al 100%):
python utils/benchmark_eval.py -l all -n 10 --sampling stratified --seed 42 -m multiagent --roundtrip

# Campionamento Stratificato con filtro su funzioni complesse (es. almeno 15 LOC):
python utils/benchmark_eval.py -l all -n 8 --sampling stratified --min-loc 15 --seed 42 --roundtrip

# Esecuzione casuale pura con seed:
python utils/benchmark_eval.py -l http-parser -n 5 --sampling random --seed 123 --no-roundtrip

# Esecuzione offline con MockLLM (senza consumo token API):
python utils/benchmark_eval.py -l miniz -n 5 --mock --no-roundtrip
```

#### Tabella Parametri CLI del Benchmark

| Flag Lungo | Flag Breve | Default | Descrizione |
| :--- | :--- | :--- | :--- |
| `--library` | `-l` | `cJSON` | Libreria target (`cJSON`, `OpenCV`, `TinyXML-2`, `sds`, `fmt`, `miniz`, `http-parser`, `all`). |
| `--limit` | `-n` | `5` | Numero massimo di funzioni da documentare e confrontare. |
| `--sampling` | `-s` | `sequential` | **Strategia di selezione**: `sequential` (prime N per ID), `random` (casuale puro uniforme), `stratified` (casuale con vincoli: partizioni di quantili LOC logaritmici per coprire funzioni brevi, medie ed estese). |
| `--stratified` | | `False` | Scorciatoia per `--sampling stratified`. |
| `--random` | `-r` | `False` | Scorciatoia per `--sampling random`. |
| `--seed` | | `None` | Seed numerico per rendere riproducibile al 100% il campionamento casuale o stratificato. |
| `--min-loc` | | `None` | Filtro opzionale di complessità: considera solo funzioni con almeno $N$ righe di codice sorgente C/C++. |
| `--mode` | `-m` | `single` | Pipeline: `single` (Ibrido Standard) o `multiagent` (Pipeline Multi-Agente con Judge). |
| `--roundtrip` / `--no-roundtrip` | | `True` | Esegue o salta la validazione automatica Round-Trip a valle della generazione. |
| `--lang` | | `en` | Lingua della documentazione generata (`en` o `it`). |
| `--mock` | | `False` | Utilizza il MockLLM per collaudi rapidi senza consumo quote API. |

---

### 3. Storicizzazione Automatica ed Output Prodotti

Tutti gli artefatti di ciascuna esecuzione vengono salvati in una directory storicizzata con timestamp:
`results/benchmark_<libreria>/run_YYYYMMDD_HHMMSS_<mode>/` (e specchiati nella cartella `results/benchmark_<libreria>/latest/`):

- `execution_config.json`: File contenente tutte le impostazioni e i parametri passati da riga di comando o selezionati da menu (incluso il comando CLI completo per la riproducibilità esatta).
- `eval_report_<mode>.md`: Report Markdown scientifico con riepilogo globale, tabella comparativa, metriche AST/neurali, galleria completa di grafici e resoconto del Round-Trip.
- `eval_report_<mode>.json`: Archivio JSON strutturato con tutti i risultati grezzi e le metriche calcolate.
- `eval_charts_<mode>.png`: Dashboard visiva a barre ad alta risoluzione delle metriche globali del benchmark.
- `roundtrip_results.json`: *(Se attivo il Round-Trip)* Risultati dettagliati per-funzione della sintesi duale e delle asserzioni `pytest`.
- `eval_chart_roundtrip.png`: *(Se attivo il Round-Trip)* Dashboard a 3 pannelli per la validazione comportamentale (Pass Rate Doc, Dual Agreement, medie per categoria tassonomica e sintesi globale).

---

### 4. 🔬 Suite Completa di Grafici Diagnostici e Guida all'Interpretazione

Per ogni esecuzione del benchmark, la pipeline genera automaticamente una **suite di 9 grafici scientifici ad alta risoluzione (DPI 200)** studiata per l'analisi accademica comparativa, l'audit di affidabilità formale e la validazione empirica:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                      SUITE SCIENTIFICA DI GRAFICI DIAGNOSTICI (9 ARTEFATTI)                     │
├────────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│ 1. Profilo di Qualità (Radar)  │ 2. Semantica vs Round-Trip     │ 3. Dispersione & Varianza     │
│    (6 Dimensioni Normalizzate) │    (Scatter con Pearson r)     │    (Violin Plot + Jitter)     │
├────────────────────────────────┼────────────────────────────────┼───────────────────────────────┤
│ 4. Matrice di Confidenza       │ 5. Cause di Scarto Verifier    │ 6. Cross-Correlation Matrice  │
│    (Heatmap Funzione x Metrica)│    (Breakdown Omissioni & AST) │    (Pearson N x N Heatmap)    │
├────────────────────────────────┼────────────────────────────────┼───────────────────────────────┤
│ 7. Residui & Allucinazioni     │ 8. Pareto Complessità (LOC)    │ 9. Imbuto di Validazione      │
│    (Delta SBERT vs Round-Trip) │    (LOC vs Performance Rate)   │    (Pipeline Stage Flow)      │
└────────────────────────────────┴────────────────────────────────┴───────────────────────────────┘
```

#### 🕸️ 1. Profilo Multi-Dimensionale di Qualità (`eval_chart_radar.png`)
* **Cosa rappresenta**: Sintetizza le prestazioni dell'approccio lungo i **6 macro-pilastri** della documentazione tecnica:
  1. *Aderenza Contratti AST* (Media armonica Param F1 e Return Match).
  2. *Semantica Neurale Continua* (Ensemble normalizzato SBERT, BERTScore, CodeBERT).
  3. *Actionability* (Presenza di esempi di compilazione, comandi CLI, tipi ed enum d'uso pratico).
  4. *Copertura Eccezioni & Edge Cases* (EDR ed ECC su casi limite e codici di errore).
  5. *Affidabilità Formale* ($1.0 - \text{Hallucination Rate}$, garanzia anti-allucinazione AST).
  6. *Downstream Utility* (Doc-to-Code Retrieval MRR e Pass Rate Round-Trip).
* **Come leggerlo**: Un'area estesa e bilanciata verso l'esterno ($1.0$) denota un modello a tutto tondo. Asimmetrie evidenti evidenziano immediatamente se un modello è solo "eloquente" (alta semantica neurale) ma debole sui contratti software formali.

#### 🔀 2. Correlazione Semantica vs Round-Trip Pass Rate (`eval_chart_semantic_vs_roundtrip.png`)
* **Cosa rappresenta**: Scatter plot bidimensionale che mette in relazione la **Similarità Semantica Neurale** (asse X, SBERT Cosine Similarity $[0.0 - 1.0]$) con l'**Efficacia Comportamentale Reale** (asse Y, Round-Trip Pass Rate $\%$ su test `pytest`). Include la retta dei minimi quadrati (OLS) e l'indice di correlazione di Pearson ($r$).
* **Come leggerlo e interpretarlo**:
  - **$r > 0.70$ (Forte Correlazione Positiva)**: La qualità semantica percepita dai modelli linguistici riflette fedelmente la correttezza logica del codice rigenerato.
  - **$r \approx 0.00$ (Ortogonalità / Indipendenza)**: Dimostra empiricamente che le metriche NLP classiche non sono sufficienti per valutare il codice software: una documentazione apparentemente perfetta in linguaggio naturale può contenere sottili errori logici che causano il fallimento dei test funzionali.
  - **Quadrante Alto a Sinistra (Bassa SBERT, Alto Pass Rate)**: *"Parafrasi Sintetica Robusta"*. Il modello ha usato parole diverse dal Ground Truth originario, ma la semantica tecnica è ineccepibile.
  - **Quadrante Basso a Destra (Alta SBERT, Basso Pass Rate)**: *"Allucinazione Plausibile"*. Testo fluente e accademico che inganna gli embedding neurali ma nasconde difetti algoritmici.

#### 🎻 3. Distribuzione Statistica & Varianza delle Metriche (`eval_chart_distributions.png`)
* **Cosa rappresenta**: Diagramma combinato a violino (Kernel Density Estimation) e strip plot con jittering che illustra la dispersione di ciascuna metrica sull'intero corpus di funzioni valutate.
* **Legenda Scientifica Incorporata**:
  - **Area Colorata (Violino)**: Stima della densità di probabilità (forma della distribuzione).
  - **Linea Rossa Orizzontale**: Valore mediano della metrica ($50^\circ$ percentile), robusto agli outlier.
  - **Pallini Scuri (Jitter Points)**: Singole funzioni campionate. Permette di rilevare bimodalità o raggruppamenti anomali.

#### 🎯 4. Matrice di Confidenza Funzione $\times$ Metriche (`eval_chart_heatmap.png`)
* **Cosa rappresenta**: Heatmap rettangolare con griglia netta e palette divergente/continua ad alto contrasto (`YlGnBu`):
  - Ogni riga rappresenta una funzione esaminata.
  - Ogni colonna rappresenta una metrica specifica (Verifier, Param F1, Return Match, SBERT, METEOR, Actionability, Judge, RoundTrip).
  - Ogni cella riporta il punteggio numerico normalizzato $[0.0 - 1.0]$ stampato al centro con contrasto dinamico.
* **Come leggerlo**: Permette di individuare a colpo d'occhio i singoli punti deboli della codebase: righe dominate da sfumature chiare/gialle denotano funzioni critiche complesse che necessitano di maggiore attenzione o scomposizione modulare.

#### 🛡️ 5. Breakdown Cause di Scarto Verifier & Rigetti Giudice (`eval_chart_verifier_breakdown.png`)
* **Cosa rappresenta**: Istogramma orizzontale categorizzato che quantifica l'incidenza di ciascuna regola di violazione formale rilevata durante la pipeline:
  - *Superato al 1° Tentativo* (Generazione perfetta immediata).
  - *Parametri Mancanti / Discrepanti* (Disallineamento con l'AST Clang).
  - *Tipo di Ritorno Errato / Mancante* (`@return` su void o omesso su non-void).
  - *Simboli Non Validi o Allucinati* (Citazione di variabili o costanti inesistenti).
  - *Rigetto Giudice LLM* (Punteggio di fedeltà $< 4.0/5.0$).
* **Come leggerlo**: Valuta l'efficacia del *Deterministic Verifier* come scudo protettivo contro le allucinazioni prima del deployment della documentazione.

#### 🔗 6. Matrice di Cross-Correlazione delle Metriche (`eval_chart_cross_correlation.png`)
* **Cosa rappresenta**: Matrice simmetrica $N \times N$ dei coefficienti di correlazione lineare di Pearson ($r \in [-1.0, +1.0]$) tra tutte le coppie di metriche valutate (con mappa termica divergente `coolwarm`).
* **Valore per la Tesi**:
  - Individua le metriche ridondanti o collinearie (es. SBERT vs BERTScore se $r > 0.90$).
  - Dimostra l'indipendenza e la complementarietà tra metriche puramente sintattiche (Param F1), semantiche (SBERT/CodeBERT) e funzionali (Round-Trip / Giudice).

#### ⚖️ 7. Analisi dei Residui: Allucinazione Plausibile vs Parafrasi Robusta (`eval_chart_discrepancy_residuals.png`)
* **Cosa rappresenta**: Grafico a barre orizzontali divergenti incentrato sullo scostamento differenziale:
  $$\Delta = \mathrm{SBERT} - \left(\frac{\mathrm{RoundTrip\ Pass\ Rate}}{100}\right)$$
* **Classificazione dei Casi**:
  - **Barra Rossa ($\Delta > +0.05$) - Sovrastima Semantica / Allucinazione Plausibile**: Il testo della documentazione sembra eccellente agli occhi dei modelli di embedding, ma l'implementazione derivata fallisce i test esecutivi.
  - **Barra Verde ($|\Delta| \le 0.05$) - Coerenza Ideale**: Perfetta corrispondenza tra leggibilità testuale ed esecuzione algoritmica.
  - **Barra Blu ($\Delta < -0.05$) - Sottostima Semantica / Parafrasi Robusta**: Il modello ha usato termini e stili differenti dal Ground Truth (penalizzato da SBERT), ma il significato tecnico è così rigoroso che il codice derivato supera il $100\%$ dei test funzionali.

#### 📈 8. Scalabilità e Complessità del Codice sorgente (`eval_chart_complexity_pareto.png`)
* **Cosa rappresenta**: Scatter plot con linea di tendenza (OLS) che correla la complessità strutturale della funzione (Linee di Codice Sorgente C/C++ - LOC) con la performance a valle (Round-Trip Pass Rate o Similarità Semantica).
* **Valore per la Tesi**: Consente di verificare se la qualità della documentazione degrada all'aumentare delle dimensioni e della complessità della logica C/C++, comprovando la robustezza del contesto bottom-up (*Dependencies-First*).

#### ⏳ 9. Imbuto di Validazione e Transizioni della Pipeline (`eval_chart_pipeline_flow.png`)
* **Cosa rappresenta**: Diagramma a barre dell'imbuto di filtraggio progressivo a più stadi:
  $$\text{Draft LLM Generato} \longrightarrow \text{Superamento Verifier AST} \longrightarrow \text{Approvazione Giudice LLM} \longrightarrow \text{Certificazione Round-Trip}$$
* **Come leggerlo**: Illustra quantitativamente la capacità del sistema di filtrare e correggere le imperfezioni ad ogni livello, garantendo che solo la documentazione che supera l'intero percorso di certificazione formale ed empirica venga inclusa nel report finale.


---

## 📋 Requisiti di Sistema e Installazione

1. **Python 3.10+**
2. **LLVM / Clang**: librerie `libclang` configurate per il parsing C/C++.
3. **Installazione dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configurazione API Key**:
   Creare un file `.env` nella root del repository:
   ```env
   GEMINI_API_KEY="la_tua_api_key_gemini"
   ```
   *(Nota: in assenza di API key valida, il sistema utilizzerà automaticamente il `MockLLMProvider` locale per test offline senza connessione).*
