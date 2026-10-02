# Resoconto Accademico e Stato dell'Arte per la Tesi di Laurea Magistrale
**Candidato:** Nicola Flego  
**Titolo di Progetto:** Generazione Automatica e Certificata di Documentazione per Codebase C/C++ tramite Orchestrazione Multi-Agente ed Analisi Statica AST  
**Data Documento:** 26 Settembre 2026  

---

## Indice Generale
1. [Quadro Concettuale e Rassegna Sistematica della Letteratura (Paper Analizzati)](#1-quadro-concettuale-e-rassegna-sistematica-della-letteratura-paper-analizzati)
2. [Tassonomia Dettagliata delle Metriche Implementate e Formule Matematiche](#2-tassonomia-dettagliata-delle-metriche-implementate-e-formule-matematiche)
3. [Verifiche, Suite di Test Sperimentali e Prove Empiriche di Robustezza](#3-verifiche-suite-di-test-sperimentali-e-prove-empiriche-di-robustezza)
4. [Risultati del Benchmark Reale di Produzione](#4-risultati-del-benchmark-reale-di-produzione)
5. [Stato di Avanzamento, Gap Rilevati e Roadmap dei Prossimi Passi (TODO)](#5-stato-di-avanzamento-gap-rilevati-e-roadmap-dei-prossimi-passi-todo)

---

## 1. Quadro Concettuale e Rassegna Sistematica della Letteratura (Paper Analizzati)

L'indagine bibliografica svolta nella cartella `Paper/` comprende 47 lavori scientifici cardine. Di seguito viene presentata la disamina dei filoni di ricerca e il contributo trasposto direttamente nell'architettura della tesi:

### 1.1 Modelli Multi-Agente e Generazione di Documentazione a Livello Repository
* **DocAgent: A Multi-Agent System for Automated Code Documentation** (Apple, Meta AI, Google DeepMind, 2024):
  - *Cosa è stato tratto:* Modello concettuale di cooperazione tra agenti specializzati con separazione dei ruoli (*Reader, Searcher, Writer, Verifier*). Ha ispirato l'introduzione della triade qualitativa *Completeness*, *Helpfulness*, e *Truthfulness*, nonché il ciclo di validazione difensiva sul codice.
* **CodeWiki** (2024):
  - *Cosa è stato tratto:* Modello gerarchico di delega (*Repository Manager Agent* $\rightarrow$ *Module Agents* $\rightarrow$ *Function Leaf Agents*). La sintesi risale in modalità bottom-up producendo documentazione strutturata a più livelli (funzione, file, modulo, repository con README e diagrammi Mermaid/Cytoscape).
* **RepoAgent** (2024):
  - *Cosa è stato tratto:* Il paradigma di *Continuous Documentation*. L'integrazione di un *ChangeDetector* con hook di pre-commit Git e flussi CI/CD per rigenerare in modo differenziale solo i nodi AST impattati da ciascun commit, prevenendo il *Documentation Drift*.
* **RepoSummary: Feature-Oriented Summarization** (Zhu et al., PKU, 2025):
  - *Cosa è stato tratto:* L'uso dell'analisi delle dipendenze congiunta a matrici semantiche per identificare i *bounded contexts* architetturali e clusterizzare funzioni in epiche logiche.
* **AutoGen Enabling Next-Gen LLM Applications** (Microsoft, 2023) & **SWE-agent**:
  - *Cosa è stato tratto:* Progettazione di protocolli di comunicazione asincroni e strutturati tra agenti basati su feedback correttivi ciclici.

### 1.2 Rappresentazione Strutturale del Codice, Grafo delle Chiamate e Contesto di Progetto
* **PROCONSUL: Project Context for Code Summarization with LLMs** (Lomshakov et al., 2024):
  - *Cosa è stato tratto:* Ha dimostrato che fornire all'LLM il contesto circostante (le firme e i contratti delle funzioni chiamate *callees*) migliora sensibilmente la qualità della documentazione rispetto all'analisi della sola funzione isolata. Nella tesi, questo principio è implementato rigidamente mediante il grafo orientato $G=(V, E)$.
* **GraphCodeBERT: Pre-training Code Representations with Data Flow** (Guo et al., 2021) & **CodeBERT** (Feng et al., 2020):
  - *Cosa è stato tratto:* Dimostrazione che le strutture sintattiche e i flussi di dati migliorano l'allineamento semantico codice-testo. Utilizzo di `microsoft/codebert-base` come metrica di embedding specializzata (*CodeBERTScore*).
* **CodePlan: Repository-level Coding using LLMs and Planning** (Bansal et al., Microsoft Research, 2023):
  - *Cosa è stato tratto:* Risoluzione dell'ordine di elaborazione su grafi complessi e gestione di catene di modifiche interdipendenti.
* **Hierarchical Repository-Level Code Summarization** & **Project-Level Encoding for Neural Source Code**:
  - *Cosa è stato tratto:* Compressione dei contesti intermedi (*folded representation* o *sketched signature*): omettere il body implementativo completo e fornire solo firme e brief pre-calcolati per evitare il superamento dei token limit.

### 1.3 Teoria del Refactoring, Slicing ed Analisi Statica Formale
* **Program Slicing** (Weiser, 1984) & **Automated Method-Extraction Refactoring by Using Block-Based Slicing**:
  - *Cosa è stato tratto:* Teoria dell'isolamento dei blocchi logici atomici e individuazione di variabili dipendenti per segmentare il sorgente e identificare porzioni di codice orfane o dead-code (funzioni a $\text{in-degree} = 0$).
* **Together We Go Further: LLMs and IDE Static Analysis** (2024):
  - *Cosa è stato tratto:* L'accoppiamento vincente tra la potenza statistico-linguistica dell'LLM e il rigore deterministico dei compilatori (AST Clang / libclang), dove l'analizzatore statico funge da guardia di sicurezza non aggirabile.

### 1.4 Tecniche di Prompting Atomico e Micro-Modelli
* **A Prompt Learning Framework for Source Code Summarization (PromptCS)**:
  - *Cosa è stato tratto:* Analisi del *continuous prompting* e del bilanciamento tra fine-tuning e zero/few-shot prompting contestuale.
* **Large Language Models are Few-Shot Summarizers** & **Automatic Code Documentation Generation Using GPT-3**:
  - *Cosa è stato tratto:* Formulazione strutturata dei template con delimitatori chiari (`@brief`, `@param[in,out]`, `@return`, `@pre`, `@warning`).

### 1.5 Valutazione della Generazione di Linguaggio Naturale (NLG) ed LLM-as-a-Judge
* **G-EVAL: NLG Evaluation using GPT-4 with Better Human Alignment** (Liu et al., 2023):
  - *Cosa è stato tratto:* Metodologia Monte Carlo per stabilizzare i giudizi degli LLM. Nella tesi è implementata tramite 5 iterazioni a $T=0.4$ su Gemini, estraendo media e deviazione standard ($\mu \pm \sigma$).
* **JudgeLM: Fine-Tuned Large Language Models as Scalable Judges** (Zhu et al., 2023) & **MT-Bench-101**:
  - *Cosa è stato tratto:* Definizione di rubriche di valutazione analitiche (punteggi da 1 a 5 con catalogazione specifica dei difetti `DEF-1`..`DEF-5` e dell'allineamento `ALIGN-1`..`ALIGN-4`).
* **AssetOpsBench: A Real-World Evaluation Benchmark**:
  - *Cosa è stato tratto:* Criteri di benchmark realistici su codice industriale multilivello (cJSON, OpenCV, TinyXML-2, sds, miniz, http-parser).

---

## 2. Tassonomia Dettagliata delle Metriche Implementate e Formule Matematiche

Il framework articola la misurazione della qualità su **4 Livelli Gerarchici e Ortogonali**:

```
                       ┌──────────────────────────────────────────────┐
                       │     Framework di Valutazione Metrologica     │
                       └──────────────────────┬───────────────────────┘
                                              │
         ┌─────────────────────┬──────────────┴───────┬─────────────────────┐
         ▼                     ▼                      ▼                     ▼
[1. Formale & AST]   [2. Qualità & Action]  [3. Neurale & Judge]   [4. Round-Trip Testing]
• Verifier Pass Rate • Hallucination Rate   • Sentence-BERT        • Code Synthesis
• Parameter F1       • Actionability Score  • BERTScore / CodeBERT • Black-Box Test Gen
• Return Match       • Error Doc Rate (EDR) • METEOR / BLEURT      • Dual Agreement Rate
• Existence Ratio    • Edge Case Cov (ECC)  • Monte Carlo Judge    • Error Diagnostics
```

### Livello 1: Formale e Contratti Sintattici AST (libclang)
1. **Funzioni Valide al Verifier (%)**:
   $$\text{Verifier Pass Rate} = \frac{N_{\text{funzioni con is\_valid=True}}}{N_{\text{totale funzioni valutate}}} \times 100$$
   Valuta il superamento di tutti i vincoli formali in [`src/verifier.py`](file:///d:/python/TESI_Nicola_Flego/src/verifier.py).
2. **Parameter Slot-Filling (Precision, Recall, F1)**:
   Sia $\mathcal{P}_{\text{AST}}$ l'insieme dei parametri formali estratti dall'AST e $\mathcal{P}_{\text{Doc}}$ l'insieme dei tag `@param`:
   $$\text{Precision} = \frac{|\mathcal{P}_{\text{AST}} \cap \mathcal{P}_{\text{Doc}}|}{|\mathcal{P}_{\text{Doc}}|}, \quad \text{Recall} = \frac{|\mathcal{P}_{\text{AST}} \cap \mathcal{P}_{\text{Doc}}|}{|\mathcal{P}_{\text{AST}}|}, \quad \text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
3. **Return Contract Match**:
   $$\text{Return Match} = \begin{cases} 
   1.0 & \text{se } \text{tipo AST} = \text{void} \land |\text{Returns}_{\text{Doc}}| = 0 \\
   1.0 & \text{se } \text{tipo AST} \neq \text{void} \land |\text{Returns}_{\text{Doc}}| \ge 1 \\
   0.0 & \text{altrimenti (violazione del contratto)}
   \end{cases}$$
4. **Deterministic Complexity Enforcement**:
   Calcolo della complessità temporale e spaziale basato sull'ispezione ad albero dell'AST (profondità di cicli `for`/`while`/`do`, chiamate STL complesse, passaggi per valore). Il tag `@complexity` viene iniettato deterministicamente.

### Livello 2: Qualità Software, Completezza ed Actionability
1. **Hallucination Rate Globale (%) & Existence Ratio**:
   $$\text{Existence Ratio} = \frac{N_{\text{entità menzionate presenti nel Grafo o stdlib}}}{N_{\text{totale entità software menzionate}}}$$
   $$\text{Hallucination Rate} = \frac{N_{\text{simboli allucinati rilevati dal Verifier}}}{N_{\text{totale entità documentate}}} \times 100$$
2. **Actionability Score (AS) [0.0 - 1.0]**:
   Combina 4 pilastri operativi di ingegneria del software:
   $$\text{AS} = 0.35 \cdot S_{\text{directionality}} + 0.20 \cdot S_{\text{brief}} + 0.25 \cdot S_{\text{return}} + 0.20 \cdot S_{\text{memory\_safety}}$$
   dove $S_{\text{directionality}}$ misura l'uso di `[in]`, `[out]`, `[in,out]`, e $S_{\text{memory\_safety}}$ rileva la presenza di clausole di ownership, puntatori e `@pre`/`@warning`.
3. **Error Documentation Rate (EDR) [0% - 100%]**:
   $$\text{EDR} = \frac{\text{Rami di Errore nel Sorgente Coperti nella Doc}}{\text{Totale Rami di Errore Rilevati nel Sorgente C/C++}} \times 100$$
4. **Edge Case Coverage (ECC) [0% - 100%]**:
   Rapporto di copertura delle guardie fisiche (`null_guard`, `zero_negative_guard`, `empty_boundary_guard`).

### Livello 3: Metriche Semantiche Neurali ed LLM-as-a-Judge
1. **Sentence-BERT (SBERT) Cosine Similarity**:
   $$\text{SBERT Sim} = \frac{\mathbf{e}_{\text{gen}} \cdot \mathbf{e}_{\text{GT}}}{\|\mathbf{e}_{\text{gen}}\| \|\mathbf{e}_{\text{GT}}\|}, \quad \text{con } \mathbf{e} \in \mathbb{R}^{384} \text{ via } \texttt{all-MiniLM-L6-v2}$$
2. **BERTScore & CodeBERTScore (P, R, F1)**:
   Allineamento pesato token-to-token con Greedy Matching e pesi IDF su `bert-base-uncased` e `microsoft/codebert-base`.
3. **METEOR Score**:
   Misura lessicale avanzata con corrispondenze esatte, stemming (Porter) e sinonimi WordNet, corretta con penalità di frammentazione.
4. **LLM-as-a-Judge (Monte Carlo Sampling)**:
   Valutazione a 5 iterazioni ($T=0.4$):
   $$\text{Faithfulness} \in [1, 5], \quad \text{Alignment} \in [1, 5], \quad \text{Combined} = \frac{\text{Faithfulness} + \text{Alignment}}{2}$$
   Integra una politica di rigenerazione guidata con critica: se $\text{score} < 4$, la motivazione del Judge viene passata al Writer Agent per una riscrittura protetta (fino a 3 iterazioni).
5. **Fréchet Embedding Distance (FID / Wasserstein-2)**:
   Distanza tra le distribuzioni multivariate degli embedding della documentazione generata e di riferimento:
   $$\text{FID} = \|\mu_1 - \mu_2\|_2^2 + \text{Tr}\left(\Sigma_1 + \Sigma_2 - 2(\Sigma_1 \Sigma_2)^{1/2}\right)$$

### Livello 4: Downstream Utility e Round-Trip Differential Testing
1. **Downstream Code Retrieval (MRR & Hit@K)**:
   Utilizza la documentazione generata come query per identificare la funzione corretta nel database del progetto:
   $$\text{RR} = \frac{1}{\text{rank}_{\text{target}}}, \quad \text{MRR} = \frac{1}{|Q|}\sum_{i=1}^{|Q|} \text{RR}_i, \quad \text{Hit@1}, \text{Hit@5}$$
2. **Round-Trip Dual Differential Testing (Doc-to-Code Synthesis & Dual Pytest Execution)**:
   - **Sintesi da Docstring ($f_{\text{doc}}$)**: L'LLM Coder rigenera l'implementazione Python basandosi **esclusivamente sulla documentazione generata** e sullo scaffold di contesto, senza vedere il codice C/C++ originale.
   - **Implementazione di Riferimento ($f_{\text{ref}}$)**: Traspilazione diretta del codice sorgente reale C/C++ in Python.
   - **Suite di Test Black-Box (Pytest + Hypothesis)**: Generazione di casi nominali, edge cases e fuzzing con oltre 50 campioni (`@given`).
   - **Dual Assertion**: Esecuzione speculare a parità di test.
     - *Self-Consistency Pass Rate (%)*: percentuale di test passati da $f_{\text{doc}}$.
     - *Dual Agreement Rate (%)*: concordanza test-per-test tra $f_{\text{doc}}$ e $f_{\text{ref}}$ ($f_{\text{doc}}(x) \equiv f_{\text{ref}}(x)$).
3. **Tassonomia a 3 Categorie del Round-Trip**:
   - **Stateless / Primitive**: funzioni puramente matematiche o scalari ($y = f(x)$); concordanza fisiologica elevatissima ($80\% - 100\%$).
   - **Pointer / Buffer-Driven**: manipolazione di memoria grezza (`char*`, offset, puntatori mutabili `int* out`); modellate con contenitori a elemento singolo (`[0]`).
   - **Stateful / Object-Graph**: metodi di classe con incapsulamento (TinyXML-2) o grafi ricorsivi (cJSON). Dimostra il principio di *Information Hiding*: $f_{\text{doc}}$ raggiunge il 100% di Self-Consistency rispettando il contratto pubblico, ma diverge legittimamente dall'implementazione privata di $f_{\text{ref}}$.

---

## 3. Verifiche, Suite di Test Sperimentali e Prove Empiriche di Robustezza

Per verificare la validità scientifica dell'intero framework, sono state condotte molteplici campagne di collaudo empirico sistematico (raccolte negli script dedicati in `utils/` e nei report in `results/metrics_validation/`):

### 3.1 Suite di Test Funzionale Unit/Integration (Pytest)
- **`tests/test_extraction.py`**: Validazione deterministica del parser AST libclang su struct, enum, prototipi, inclusioni e grafo delle chiamate (*caller-callee*). Esito: **PASSATO al 100%**.
- **`tests/test_judge_agent.py`**: Verifica della pipeline multi-agente (*Reader $\rightarrow$ Searcher $\rightarrow$ Writer $\rightarrow$ Judge*), del mock judge deterministico e del loop di rigenerazione con iniezione del feedback critico. Esito: **PASSATO al 100%** (3/3 test passati).

### 3.2 Studio di Sensibilità e Vulnerabilità delle Metriche (`verify_metric_sensitivity.py`)
Lo studio ha testato le metriche su 4 categorie concettuali controllate:
* **EQUIVALENT**: stessa logica, implementazione diversa.
* **ADVERSARIAL**: codice quasi identico (95% token), ma operatore invertito (`<` vs `>`, `==` vs `!=`, estremi scambiati).
* **DOMAIN_SIMILAR**: stesso ambito tematico, algoritmi diversi.
* **ORTHOGONAL**: domini completamente disgiunti.

#### Risultati Emergenti (La 'Cecità Logica' o Adversarial Inversion Paradox):
Definendo $\Delta = \text{Score}(\text{ADVERSARIAL}) - \text{Score}(\text{EQUIVALENT})$:
- **ROUGE-L**: $\Delta = \mathbf{+0.303}$
- **TF-IDF**: $\Delta = \mathbf{+0.291}$
- **SBERT**: $\Delta = \mathbf{+0.147}$ (0.956 su Adversarial vs 0.809 su Equivalent)
- **BERTScore**: $\Delta = \mathbf{+0.176}$ (0.938 su Adversarial vs 0.762 su Equivalent)
- **CodeBERT**: $\Delta = \mathbf{+0.103}$ (0.970 su Adversarial vs 0.867 su Equivalent)

> [!CAUTION]
> **Rilevanza per la Tesi:** Tutte le metriche lessicali e neurali basate su token/embedding falliscono drammaticamente sui bug logici ($\Delta > 0$): premiano una funzione con un bug catastrofico rispetto a una parafrasi corretta, perché valutano la vicinanza superficiale dei caratteri. Questa è la dimostrazione inconfutabile della necessità del **Round-Trip Testing dinamico**.

### 3.3 Studio Specifico sulla Documentazione Tecnica (`verify_doc_metrics.py`)
Analisi comparativa SBERT vs BERTScore su 5 comportamenti linguistici:
1. **PARAPHRASE**: SBERT (0.617) e BERTScore F1 (0.668) colgono bene la variazione lessicale dove ROUGE-L crolla (<0.10).
2. **CRITICAL_NEGATION** (es. *"The caller must free"* vs *"The caller must not free"*):
   - SBERT assegna **0.918**, BERTScore F1 assegna **0.902**! Nessuna metrica di NLP generico penalizza l'inversione di contratto.
3. **ROLE_SWAP** (*"from src to dest"* vs *"from dest to src"*): Punteggi oltre **0.84 - 0.89** (cecità ai ruoli direzionali).
4. **VERBOSITY_FLUFF**: La Precision di BERTScore cala (0.542) rivelando token superflui, mentre la Recall resta alta (0.734).
5. **Score Compression di BERTScore**: Su testi ortogonali SBERT scende a **0.049**, mentre BERTScore rimane compresso a **0.501**.

### 3.4 Studio XAI (Explainable AI: Meccanismi Interni) (`explain_metric_internals.py`)
- **Greedy Matching di BERTScore**: L'algoritmo calcola una matrice di similarità 2D. Il token `not` aggiunto non penalizza l'allineamento degli altri token identici; la Recall resta al 100% e la Precision cala solo di $\frac{1}{N}$.
- **Mean Pooling di SBERT**:
  $$\mathbf{u} = \frac{1}{L} \sum_{i=1}^{L} \mathbf{h}_i$$
  I token concettuali pesanti dominano la norma vettoriale. La negazione `not` incide solo per il 5-8% dell'orientamento finale, venendo 'dilavata' dal pooling.
- **Mappe di Self-Attention**: L'attenzione dell'operatore `<` si distribuisce solo sui token adiacenti (`(`, `b`), senza condizionare i pesi latenti globali.

### 3.5 Rappresentazione Canonica Intermedia (IR) (`verify_canonical_representation.py`)
- La conversione preventiva del codice C e Python in **Pseudocodice Algoritmico** e in **Flowchart Mermaid** elimina il gap sintattico cross-language: SBERT sul fattoriale sale da **0.593** a **0.844**, e BERTScore F1 da **0.645** a **0.857**.
- Tuttavia, la normalizzazione non risolve il paradosso dei bug logici (< vs >), confermando che il problema risiede nella cecità logica intrinseca di BERT e non nella disparità dei linguaggi.

### 3.6 Limiti Fisici di Contesto e Troncamento dei Token (`verify_token_truncation.py`)
- **SBERT (`all-MiniLM-L6-v2`)**: limite massimo rigido a **256 token**.
- **BERTScore e CodeBERT**: limite massimo a **512 token**.
- **The Truncation Trap**: Quando due funzioni superano i 512 token e condividono il prefisso ma hanno una coda completamente diversa, SBERT e BERTScore assegnano **1.000**, poiché l'intera coda viene troncata via prima del calcolo dell'attenzione.

### 3.7 Confronto Diretto: Neurale vs LLM-Judge vs Round-Trip (`verify_judge_and_roundtrip.py`)
Sul caso *Ricerca Minimo (C corretto vs Python invertito Max)*:
- SBERT: `0.830` (Fallimento)
- CodeBERT: `0.864` (Fallimento)
- **LLM-Judge**: `2.0/5` (0.250) con diagnosi esplicita (*"DEF-4: Contract/Direction Mismatch, completely reverses logic"*).
- **Round-Trip Pytest**: **0.0% Pass Rate** (0/5 superati) (Rilevazione perfetta della rottura comportamentale).

---

## 4. Risultati del Benchmark Reale di Produzione

Dall'ultima esecuzione completa del benchmark consolidato (`results/benchmark_all/latest/`, campionamento casuale uniforme su tutte le librerie, pipeline multi-agente con 15 funzioni):

| Indicatore Chiave | Risultato Conseguito | Significato Scientifico |
|---|:---:|---|
| **Funzioni Valide al Verifier** | **93.3%** (14/15) | Rigore contrattuale e superamento delle guardie formali AST |
| **Hallucination Rate Globale** | **0.0%** | Zero simboli o entità inventate nella documentazione |
| **Parameter F1-Score (vs AST)** | **1.0** | Corrispondenza biunivoca perfetta parametri documentati vs reali |
| **Return Contract Match** | **0.9333** | Conformità quasi totale sulle clausole di ritorno |
| **Actionability Score (AS)** | **0.8133 / 1.0** | Documentazione pronta per la produzione con direzionalità e contratti |
| **Error Documentation Rate (EDR)**| **100.0%** | Copertura totale dei rami di errore presenti nei sorgenti C/C++ |
| **Edge Case Coverage (ECC)** | **91.1%** | Intercettazione sistematica di puntatori NULL e boundary check |
| **LLM-Judge Faithfulness [1-5]** | **4.24 / 5.0** | Alta aderenza tecnica certificata dal Giudice Monte Carlo |
| **LLM-Judge Alignment [1-5]** | **4.63 / 5.0** | Fedeltà all'intento progettuale dell'autore originale |
| **Judge Punteggio Combinato** | **4.43 / 5.0** | Qualità globale ai massimi livelli della scala |
| **Code Retrieval MRR** | **0.7861** | Capacità discriminante della documentazione come motore di ricerca |
| **Code Retrieval Hit@1 / Hit@5** | **66.7% / 93.3%** | La funzione target è rintracciata al primo posto o nella top 5 |
| **Round-Trip Pass Rate (Doc Synth)**| **65.1%** | Tasso di autosufficienza esecutiva del codice generato da docstring |
| **Round-Trip Dual Agreement** | **41.3%** | Accordo differenziale stretto (influenzato da *Information Hiding*) |
| **Sentence-BERT Cosine Sim** | **0.5997** | Allineamento concettuale denso con la doc originale |
| **CodeBERTScore F1** | **0.7463** | Fedeltà a livello di nomenclatura software |
| **Concept Checklist Score** | **0.90** | Preservazione dei fatti semantici critici (memoria, bound, errori) |

### Diagnostica dei Fallimenti Round-Trip
L'analisi automatizzata degli errori (`roundtrip_error_report.md`) evidenzia:
1. **Behavioral / Contract Failure (40.0%)**: discrepanze logiche fini sui valori di ritorno nei casi limite.
2. **Interface / Signature Mismatch (30.0%)**: convenzioni sui parametri posizionali o di tipo.
3. **Other Execution Error (16.7%)**: eccezioni interne di Hypothesis o asserzioni.
4. **Missing Symbol / Environment (13.3%)**: dipendenze esterne o macro non iniettate nello scaffold.

---

## 5. Stato di Avanzamento, Gap Rilevati e Roadmap dei Prossimi Passi (TODO)

### 5.1 Cosa è Stato Completato con Successo
1. **Parser Statico AST con libclang**: Estrazione completa di funzioni, firme, struct, enum, macro, include, complessità deterministica Big-O e modelli di memoria per C e C++.
2. **Grafo delle Dipendenze & Tarjan SCC**: Risoluzione delle ricorsioni mutue, ordinamento topologico Bottom-Up (*Dependencies-First*) e rilevamento del Dead Code.
3. **Pipeline Multi-Agente Specialistica**: Agenti *Reader*, *Searcher*, *Writer*, *Verifier* e *Judge* con protocollo di rigenerazione guidata e audit globale (*Lead Architect*, *Module Storyteller*).
4. **Framework di Metriche a 4 Livelli**: Metriche AST, metriche software/actionability, metriche neurali dense e framework di Round-Trip Differential Testing (Pytest + Hypothesis).
5. **Suite Completa di Validazione Sperimentale e XAI**: Dimostrazione formale del limite di BERTScore/SBERT sui bug logici e giustificazione empirica della necessità del testing dinamico.
6. **Reportistica Multimodale**: Generazione automatica di `DOCUMENTATION.md`, portali HTML completi, grafi interattivi Cytoscape.js e dashboard grafiche diagnostiche a 200 DPI.

### 5.2 Cosa Manca e Roadmap dei Prossimi Passi (Estratto da `TODO.md` e `RoadMap.md`)
* [ ] **Profiling Temporale e Benchmark di Latenza**: Misurazione e confronto dettagliato dei tempi di esecuzione tra la pipeline standard `single` e la pipeline multi-agente `multiagent`, con scomposizione per fase (parsing AST, chiamate LLM, esecuzione Pytest).
* [ ] **Grafico Analitico Voto vs Lunghezza / Complessità (LOC)**: Visualizzazione della correlazione tra il punteggio assegnato dal Judge o il Round-Trip Pass Rate e la lunghezza/complessità della funzione documentata, per analizzare la tenuta del modello sui blocchi monolitici.
* [ ] **Arricchimento del Contesto Esterno (Context Scaffold 2.0)**: Fornire un contesto ancora più ricco e completo delle classi helper e delle funzioni esterne durante la sintesi del Round-Trip, al fine di azzerare i residui `NameError` e `AttributeError` (che costituiscono il 13.3% dei fallimenti attuali).
* [ ] **Self-Refinement / Loop di Correzione Automatica (Doc-to-Code Feedback Loop)**: Implementare un ciclo ricorsivo in cui il Coder riceve il traceback e il log di fallimento dei test Pytest e tenta autonomamente un ri-allineamento correttivo del codice generato.
* [ ] **Generalizzazione Multilingua con Tree-Sitter**: Estendere il parser oltre C/C++ (Java, Python, Rust, Go) secondo la Fase 4 della Roadmap.
* [ ] **Integrazione Pre-Commit Hook CI/CD e Drift Detection**: Implementazione operativa del monitoraggio dei commit Git (Fase 5 della Roadmap) per bloccare merge di codice con discrepanze documentali.

---
*Relazione predisposta per la redazione della tesi magistrale di Nicola Flego.*
