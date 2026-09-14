# Architettura di Documentazione Automatica del Codice con Orchestrazione Multi-Agente ed Analisi Statica

---

## Indice dei Contenuti
1. [Fase 1: Parsing e Analisi Strutturale del Codice C (Fondazione Deterministica)](#fase-1-parsing-e-analisi-strutturale-del-codice-c-fondazione-deterministica)
2. [Fase 2: Pianificazione Topologica Bottom-Up e Orchestrazione Multi-Agente](#fase-2-pianificazione-topologica-bottom-up-e-orchestrazione-multi-agente)
3. [Fase 3: Validazione Qualitativa Ibrida e Prevenzione delle Allucinazioni](#fase-3-validazione-qualitativa-ibrida-e-prevenzione-delle-allucinazioni)
4. [Fase 4: Astrazione Multilingua e Generalizzazione Universale](#fase-4-astrazione-multilingua-e-generalizzazione-universale)
5. [Fase 5: Integrazione Incrementale e Manutenzione Continua](#fase-5-integrazione-incrementale-e-manutenzione-continua)

---

## Fase 1: Parsing e Analisi Strutturale del Codice C (Fondazione Deterministica)

Prima di inoltrare il codice ai Large Language Models (LLM), è necessario costruire una rappresentazione strutturata e deterministica della codebase per preservare le relazioni spaziali e mitigare drasticamente il consumo di token.

### 1.1 Estrazione dei Metadati del Codice C
* **Analizzatore Statico basato su Clang (`libclang` / AST Clang):**
  * Estrazione affidabile di dichiarazioni e definizioni di funzioni.
  * Mappatura completa delle relazioni chiamante-chiamato (*caller-callee*).
  * Risoluzione ed espansione di macro di preprocessore, direttive `#define` e *signature* complete dei tipi.
* **Segmentazione dei Sorgenti (*Code Segmentation*):**
  * Scomposizione deterministica di file C complessi e di grandi dimensioni in unità logiche atomiche (funzioni indipendenti, strutture dati `struct`/`union`, `typedef` e variabili globali).

### 1.2 Costruzione del Grafo delle Dipendenze del Repository
* **Mappatura delle Interrelazioni della Codebase:**
  * Creazione di un Grafo Diretto $G = (V, E)$, dove $V$ rappresenta le unità logiche (funzioni, file, strutture) ed $E$ rappresenta le relazioni (invocazioni `call`, inclusioni `#include`, riferimenti di tipo).
* **Risoluzione delle Dipendenze Cicliche:**
  * La presenza di cicli (es. funzioni mutuamente ricorsive) impedisce l'ordinamento topologico diretto.
  * **Algoritmo di Tarjan per le Componenti Fortemente Connesse (SCC):** Rilevamento e condensazione dei cicli del grafo in singoli super-nodi (*Condensed DAG*), garantendo l'assenza di cicli a livello macroscopico.

---

## Fase 2: Pianificazione Topologica Bottom-Up e Orchestrazione Multi-Agente

Per documentare un intero repository preservando il contesto senza saturare la finestra di contesto del modello, il flusso risale il grafo delle dipendenze in modo logico ed ordinato.

```
       [Condensed Call Graph]
                 │
       [Topological Sort: Bottom-Up]
                 │
       ┌─────────▼─────────┐
       │   Reader Agent    │ ◄── Identifica firme, corpi e dipendenze
       └─────────┬─────────┘
                 │
       ┌─────────▼─────────┐
       │  Searcher Agent   │ ◄── Recupera codice/sommari dipendenze (callees)
       └─────────┬─────────┘
                 │
       ┌─────────▼─────────┐
       │   Writer Agent    │ ◄── Genera bozza Markdown (Args, Returns, Errors)
       └─────────┬─────────┘
                 │
       ┌─────────▼─────────┐
       │  Verifier Agent   │ ◄── Feedback loop / Approvazione formale
       └───────────────────┘
```

### 2.1 Ordinamento Topologico (*Dependencies-First*)
* **Elaborazione Bottom-Up:**
  * Pianificazione dell'analisi seguendo il principio *Dependencies-First*: una funzione viene analizzata e documentata solo dopo che tutte le sue dipendenze dirette (*callees*) sono già state processate.
* **Propagazione Incrementale del Contesto delle Callees:**
  * Quando l'agente documenta una funzione chiamante (*caller*), riceve nel prompt solo le signature e i sommari precedentemente generati per le sue *callees*.
  * Questo approccio incrementale trasmette il significato funzionale senza includere migliaia di righe di codice sorgente secondario.

### 2.2 Pipeline Collaborativa Multi-Agente (Paradigma DocAgent)
1. **Reader Agent:**
   * Analizza la firma e il corpo della funzione C sotto analisi per identificare quali contesti esterni (es. librerie standard `libc` o terze parti) o contesti interni (*callees*) siano necessari.
2. **Searcher Agent:**
   * Recupera deterministicamente dal repository il contesto delle dipendenze richieste o interroga sorgenti di conoscenza esterne (es. API di documentazione, man pages).
3. **Writer Agent:**
   * Genera la bozza di documentazione formattata in Markdown standard (es. formato Doxygen/Google-style), strutturando:
     * **Args:** Descrizione analitica di parametri di input/output e puntatori.
     * **Returns:** Valore di ritorno ed interpretazione dei tipi.
     * **Raises / Error Handling:** Codici di errore gestiti (es. `-1`, `NULL`, impostazione di `errno`).
4. **Verifier Agent:**
   * Valuta l'aderenza formale alle linee guida della documentazione, approvando l'output o rimandando suggerimenti correttivi (*reflective feedback loop*) al Writer.

---

## Fase 3: Validazione Qualitativa Ibrida e Prevenzione delle Allucinazioni

La documentazione generata deve essere affidabile, formalmente corretta ed esente da allucinazioni semantiche. Viene integrato un ciclo di validazione continua basato su tre pilastri:

| Metrica | Tipologia di Validazione | Meccanismo Operativo |
| :--- | :--- | :--- |
| **Completeness** | Deterministica (AST + Regex) | Verifica che il 100% dei parametri formali della firma C e del tipo di ritorno sia esplicitamente documentato. |
| **Helpfulness** | Semantica (LLM-as-a-Judge) | Valutazione della chiarezza del sommario, del contesto funzionale e della correttezza concettuale per uno sviluppatore umano. |
| **Truthfulness** | Ibrida (Entity Extraction + Graph Matching) | Calcolo dell'*Existence Ratio* per rilevare entità software fantasma menzionate nel testo. |

### 3.1 Completeness (Completezza Formale)
* Parser AST combinato con pattern matching su espressioni regolari per verificare programmaticamente che tutti i parametri formali della firma C e i valori di ritorno abbiano una descrizione puntuale nella documentazione generata.

### 3.2 Helpfulness (Utilità Pratica)
* Modulo **LLM-as-a-judge** istruito per valutare l'utilità pratica della documentazione per uno sviluppatore, analizzando:
  * Chiarezza ed esaustività del sommario operativo.
  * Esattezza dei flussi logici e delle condizioni al contorno descritte.

### 3.3 Truthfulness (Correttezza Fattuale & Anti-Hallucination)
* **Estrazione delle Entità Software:** Estrazione automatica di tutti i riferimenti a funzioni, variabili, strutture e costanti menzionati nel testo prodotto dall'LLM.
* **Calcolo dell'Existence Ratio:**
  $$	ext{Existence Ratio} =  \frac{	ext{Entità menzionate presenti nel Grafo}}{	ext{Totale Entità menzionate}}$$
* Verifica dell'effettiva esistenza fisica delle entità all'interno del grafo delle dipendenze estratto deterministicamente nella **Fase 1**.
* Qualsiasi entità non risolta viene contrassegnata come allucinazione, innescando automaticamente un ciclo correttivo di riscrittura.

### 3.4 Dependency Integrity Check (Validazione Direttive `#include`)
* Controllo deterministico a livello di preprocessore per verificare che tutti i file inclusi (`#include`) siano presenti fisicamente nel repository o appartengano alla Standard Library (C / C++ / POSIX / Win32).
* Generazione automatica di un report diagnostico integrato che evidenzia eventuali dipendenze esterne non risolte o file header mancanti con indicazione esatta della riga di codice sorgente.

---

## Fase 4: Astrazione Multilingua e Generalizzazione Universale

Per rendere l'infrastruttura indipendente dallo specifico linguaggio di programmazione, i componenti verticali vengono convertiti in un'architettura agnostica e universale.

### 4.1 Generalizzazione del Parser (Tree-Sitter)
* **Adozione di Tree-Sitter:** Sostituzione del parser Clang monolitico con Tree-Sitter, offrendo supporto nativo e incrementale per parsing AST multilingua (C, C++, Python, Java, C#, Go, Rust, JavaScript, TypeScript, ecc.).
* **Normalizzazione delle Relazioni (`depends_on`):**
  * Traduzione delle relazioni specifiche di ciascun linguaggio in un'ontologia universale unificata:
    * Invocazioni di funzione in C $
ightarrow$ `depends_on`
    * Ereditarietà di classi e implementazione di interfacce in Java/C# $
ightarrow$ `depends_on`
    * Importazione di moduli e decoratori in Python/TypeScript $
ightarrow$ `depends_on`

### 4.2 Sintesi Gerarchica Cascading (Bottom-Up)
Composizione ricorsiva della documentazione a livelli crescenti di granularità ed astrazione:

```
[Repository Level]  ──► README globale, Architettura di alto livello & Wiki navigabile
         ▲
         │ (Aggregazione)
  [Module Level]    ──► Documentazione di Directory / Package / Namespace
         ▲
         │ (Aggregazione)
   [File Level]     ──► Sommario del File & Relazioni tra componenti
         ▲
         │ (Sintesi)
 [Function Level]   ──► Documentazione atomica di Funzioni, Metodi e Classi
```

1. **Livello Funzione / Metodo:** Generazione di documentazione atomica per i singoli blocchi di codice.
2. **Livello File:** I sommari delle funzioni e le definizioni globali del file vengono aggregati per descrivere il ruolo architetturale del file.
3. **Livello Modulo / Package:** I sommari dei file appartenenti a una cartella/namespace vengono integrati per documentare il modulo logico.
4. **Livello Repository:** Generazione automatica del `README.md` principale, di diagrammi architetturali e di una documentazione Wiki completamente navigabile.

### 4.3 Compressione dei Contesti (*Sketched / Folded Representation*)
* Nella sintesi di moduli ad alto livello, i dettagli implementativi dei corpi delle funzioni o delle classi vengono nascosti (*folded*).
* All'LLM vengono fornite esclusivamente le intestazioni sintattiche, le signature e i sommari pre-calcolati (*sketched representation*), minimizzando drasticamente il footprint dei token.

---

## Fase 5: Integrazione Incrementale e Manutenzione Continua

La documentazione deve evolversi e rimanere sincronizzata in tempo reale con lo sviluppo del codice, abbattendo i costi computazionali e le latenze di rigenerazione.

### 5.1 Rilevamento Incrementale dei Cambiamenti
* Monitoraggio differenziale dei commit Git invece della rigenerazione *full-codebase*.
* Identificazione deterministica dei nodi dell'AST modificati, aggiunti o eliminati (funzioni, strutture o moduli impattati).

### 5.2 Propagazione dell'Impatto (*Change May-Impact Analysis*)
* Tramite il grafo delle dipendenze invertito, calcolo dell'albero di impatto generato dalle modifiche.
* **Regola di Propagazione:** Se la signature o il comportamento di una funzione dipendente cambia, viene propagato l'obbligo di aggiornamento della documentazione ai suoi diretti chiamanti (*callers*), lasciando inalterati i rami indipendenti del grafo.

### 5.3 Integrazione con Git Pre-commit Hook & CI/CD Pipeline
* **Git Pre-commit Hook:**
  * All'esecuzione di `git commit`, l'hook individua i file in *staging area*.
  * Attiva gli agenti solo per le entità strettamente impattate dal delta di codice.
  * Rigenera e aggiorna automaticamente i file Markdown corrispondenti.
  * Esegue lo stage automatico dei Markdown aggiornati prima di autorizzare la finalizzazione del commit.
* **Integrazione CI/CD:**
  * Controllo di consistenza in pull request (*Documentation Drift Detection*), impedendo il merge di codice non documentato o disallineato rispetto alla versione sorgente.
