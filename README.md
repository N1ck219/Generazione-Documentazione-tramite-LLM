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

```bash
python main.py [NUMERO_PROGETTO] [FLAG_OPZIONALI]
```

### Tabella dei Flag Disponibili

| Flag CLI | Flag Breve | Descrizione |
| :--- | :--- | :--- |
| `--export` | `-e` o `e` | **Export Rapido**: rigenera istantaneamente il file `DOCUMENTATION.md`, il portale `FULL_DOCUMENTATION.html` ed il grafo interattivo Cytoscape.js leggendo i dati già presenti in SQLite **senza effettuare chiamate LLM** (tempo: ~1 secondo). |
| `--multiagent` | `-m` o `m` | **Pipeline Multi-Agente**: attiva la cooperazione completa tra 4 agenti dedicati (*Reader* $\rightarrow$ *Searcher* $\rightarrow$ *Writer* $\rightarrow$ *Verifier*) invece del generatore ibrido singolo. |
| `--force` | `-f` o `f` | **Rigenerazione Forzata (Clear DB)**: svuota il database SQLite (`documentation.db`) forzando la ri-generazione completa da zero di tutte le funzioni, struct e sintesi. |

---

### 💡 Esempi Pratici di Utilizzo

#### 1. Esecuzione Interattiva (Menu da Terminale)
```bash
python main.py
```
Mostra l'elenco dei progetti disponibili in `Test_code/` e attende la scelta dell'utente:
```text
Progetti disponibili trovati in 'Test_code':
  [1] Easy C
  [2] Hard C
  [3] Medium C
  [4] ring_buffer
  [5] tesi triennale C++

Seleziona il progetto (o 'q' per uscire): 5
```

#### 2. Esecuzione Rapida con Argomenti Diretti
* **Analisi standard del Progetto 5**:
  ```bash
  python main.py 5
  ```
* **Rigenerazione Forzata da Zero (Clear Cache) per il Progetto 5**:
  ```bash
  python main.py 5 -f
  # oppure
  python main.py 5 f
  ```
* **Esecuzione in Modalità Multi-Agente per il Progetto 2**:
  ```bash
  python main.py 2 -m
  # oppure
  python main.py 2 m
  ```
* **Multi-Agente con Rigenerazione Forzata da Zero**:
  ```bash
  python main.py 5 -m -f
  # oppure
  python main.py 5 m f
  ```
* **Export Istantaneo di Report e Grafi (senza consumare token LLM)**:
  ```bash
  python main.py 5 -e
  # oppure
  python main.py 5 e
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

### 2. Comandi CLI per l'Esecuzione dei Test

#### A. Benchmark Standard (Semantica, AST, Retrieval ed LLM-Judge)
```bash
# Esecuzione completa su cJSON (ad es. 25 funzioni)
python utils/benchmark_eval.py -l cJSON -n 25 -m single --lang en

# Esecuzione su TinyXML-2 (C++)
python utils/benchmark_eval.py -l TinyXML-2 -n 20 --lang en

# Esecuzione offline con MockLLM (senza consumo quote API)
python utils/benchmark_eval.py -l cJSON -n 3 --mock
```

#### B. Benchmark con Dual Round-Trip Differential Testing Integrato
Aggiungendo il flag `--roundtrip`, il benchmark esegue sia la pipeline completa di metriche che la doppia sintesi di codice (Doc vs Reference C/C++) con esecuzione di `pytest` e `hypothesis`:
```bash
python utils/benchmark_eval.py -l cJSON -n 25 -m single --lang en --roundtrip
```

#### C. Esecuzione Separata del Round-Trip Dual Differential Testing
È possibile validare il comportamento a valle in modo completamente indipendente leggendo un qualsiasi file `eval_report_*.json` già prodotto:
```bash
# Esecuzione adattiva libera con test di robustezza Hypothesis (Default consigliato)
python utils/roundtrip_eval.py -j results/benchmark_cjson/eval_report_single.json -n 25

# Esecuzione con numero fisso di test semantici (es. 15 test per funzione)
python utils/roundtrip_eval.py -j results/benchmark_cjson/eval_report_single.json -n 25 -t 15
```

---

### 3. Output Prodotti dal Benchmark
Tutti gli artefatti vengono salvati in `results/benchmark_<libreria>/`:
- `eval_report_<mode>.md`: Report Markdown scientifico con riepilogo globale, tabella comparativa e schede dettagliate per ogni funzione con le motivazioni del Giudice e i rank di Retrieval.
- `eval_charts_<mode>.png`: Dashboard visiva a due pannelli ad alta risoluzione:
  1. Bar chart orizzontale multi-barra (Param F1, SBERT, BERTScore, CodeBERT, Code Retrieval RR, LLM-Judge, ROUGE-L).
  2. Bar chart di sintesi con le medie normalizzate e il punteggio del Judge.
- `eval_report_<mode>.json`: Archivio JSON strutturato per ulteriori elaborazioni o per alimentare il runner di Round-Trip.


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
