# 📐 Framework di Valutazione e Benchmark della Documentazione C/C++: Guida Tecnica alle Metriche

Questo documento illustra nel dettaglio tutte le metriche quantitative, semantiche, formali e comportamentali impiegate nel sistema di benchmark per valutare la documentazione tecnica generata automaticamente rispetto al *Ground Truth* (la documentazione d'autore di librerie industriali C/C++) e all'AST (*Abstract Syntax Tree*) estratto da Clang.

---

## 🏛️ Tassonomia Metodologica a 4 Livelli

Per garantire una valutazione scientifica rigorosa, il framework scompone l'analisi in **4 livelli complementari**:

1. **Livello Formale & Contratti AST**: verifica deterministica delle firme, parametri e vincoli di ritorno.
2. **Livello Qualità Software & Actionability**: misurazione della completezza operativa per lo sviluppatore (casi limite, rami d'errore, assenza di allucinazioni).
3. **Livello Valutativo Semantico & LLM-as-a-Judge**: allineamento concettuale denso (S-BERT, BERTScore, METEOR) e audit critico multi-prospettiva tramite un modello arbitro a campionamento Monte Carlo.
4. **Livello di Downstream Utility & Validazione Comportamentale**: capacità della documentazione di servire compiti a valle (Code Retrieval e sintesi del codice con test Pytest differenziali via Round-Trip).

---

## 1. Livello Formale & Contratti AST

### 🔹 Funzioni Valide al Verifier (%)
* **Descrizione Tecnica**: Percentuale di blocchi Doxygen generati che superano l'intero audit formale a guardie logiche implementato in [`src/verifier.py`](file:///d:/python/TESI_Nicola_Flego/src/verifier.py) senza sollevare errori fatali.
* **Come viene Calcolata**:
  $$\text{Verifier Pass Rate} = \frac{N_{\text{funzioni con is\_valid=True}}}{N_{\text{totale funzioni valutate}}} \times 100$$
  I controlli includono: presenza di tutti i `@param` dell'AST, corrispondenza del `@return` con il tipo restituito, conformità dei codici d'errore menzionati con gli header reali/POSIX e superamento della soglia di *Existence Ratio* ($\ge 0.80$).
* **Come Interpretare**:
  - **100%**: Nessuna documentazione viola i contratti software o introduce allucinazioni bloccanti.
  - **< 90%**: Presenza di discrepanze formali tra AST e commento generato (es. parametri omessi o clausole inventate).

---

### 🔹 Parameter F1-Score (Precision & Recall vs AST)
* **Descrizione Tecnica**: Misura la fedeltà e completezza dello slot-filling sui parametri di input della funzione confrontando l'insieme dei tag `@param` estratti dal Doxygen con l'insieme dei parametri formali dell'AST Clang.
* **Come viene Calcolata**:
  Sia $\mathcal{P}_{\text{AST}}$ l'insieme dei parametri formali estratti dall'AST e $\mathcal{P}_{\text{Doc}}$ l'insieme dei parametri documentati nei tag `@param`:
  $$\text{Precision} = \frac{|\mathcal{P}_{\text{AST}} \cap \mathcal{P}_{\text{Doc}}|}{|\mathcal{P}_{\text{Doc}}|}, \quad \text{Recall} = \frac{|\mathcal{P}_{\text{AST}} \cap \mathcal{P}_{\text{Doc}}|}{|\mathcal{P}_{\text{AST}}|}$$
  $$\text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
  *(Se l'header C++ omette il nome nel prototipo, es. `LoadFile(FILE*)`, il sistema valida l'associazione posizionale e di tipo per evitare penalizzazioni ingiustificate).*
* **Come Interpretare**:
  - **1.0**: Corrispondenza biunivoca perfetta. Ogni parametro reale è documentato e nessun parametro inesistente è stato inventato.
  - **< 1.0**: Presenza di parametri allucinati (bassa Precision) o parametri reali dimenticati nel commento (bassa Recall).

---

### 🔹 Return Contract Match
* **Descrizione Tecnica**: Valuta la correttezza del contratto sul valore di ritorno verificando la stretta coerenza tra il tipo di ritorno della firma C/C++ e la presenza/assenza della clausola `@return`.
* **Come viene Calcolata**:
  $$\text{Return Match} = \begin{cases} 
  1.0 & \text{se tipo AST} = \text{void} \land |\text{Returns}_{\text{Doc}}| = 0 \\
  1.0 & \text{se tipo AST} \neq \text{void} \land |\text{Returns}_{\text{Doc}}| \ge 1 \\
  0.0 & \text{altrimenti (presenza di @return in funzione void o assenza in non-void)}
  \end{cases}$$
* **Come Interpretare**:
  - **1.0**: Piena conformità contrattuale (nessuna clausola `@return` superflua o mancante).
  - **0.0**: Grave difetto di specifica (es. la funzione è `void` ma promette di restituire un valore, oppure restituisce un puntatore/codice d'errore ma non lo documenta).

---

## 2. Livello Qualità Software & Actionability

### 🔹 Hallucination Rate Globale (%)
* **Descrizione Tecnica**: Percentuale di simboli, entità software, macro o costanti menzionate nella documentazione che non hanno riscontro fisico nel grafo AST del progetto, negli include o negli standard POSIX/C.
* **Come viene Calcolata**:
  $$\text{Hallucination Rate} = \frac{N_{\text{simboli allucinati rilevati dal Verifier}}}{N_{\text{totale entità documentate}}} \times 100$$
* **Come Interpretare**:
  - **0.0%**: Valore ideale. Zero entità inventate; ogni tipo, funzione citata o codice di ritorno esiste fisicamente nella codebase.
  - **> 5.0%**: Rischio di allucinazione: l'LLM cita funzioni ausiliarie o macro inesistenti (es. citare `Write()` su una classe che espone solo `Print()`).

---

### 🔹 Actionability Score (AS) [0.0 - 1.0]
* **Descrizione Tecnica**: Misura se uno sviluppatore possiede tutte le informazioni operative necessarie per invocare la funzione in modo sicuro e corretto senza dover ispezionare il codice sorgente.
* **Come viene Calcolata**: Somma pesata di 4 requisiti di ingegneria del software:
  1. **Direzionalità Parametri (35%)**: percentuale di tag `@param` corredati da modificatore semantico esplicito (`[in]`, `[out]`, `[in,out]`).
  2. **Chiarezza del Brief (20%)**: presenza di un tag `@brief` descrittivo ($\ge 15$ caratteri).
  3. **Contratto di Ritorno (25%)**: descrizione dettagliata degli scenari di output o assenza pulita se `void`.
  4. **Pre-condizioni e Sicurezza di Memoria (20%)**: presenza di tag `@pre`, `@warning` o clausole esplicite su ownership, validità dei puntatori e buffer boundaries.
* **Come Interpretare**:
  - **0.80 - 1.0**: Documentazione di livello industriale (Production-Ready), completa di direzionalità, contratti e avvertenze di memoria.
  - **< 0.60**: Documentazione generica o incompleta (priva di dettagli su chi alloca o libera la memoria o su come interpretare i puntatori).

---

### 🔹 Error Documentation Rate (EDR) [0% - 100%]
* **Descrizione Tecnica**: Verifica se i rami di errore fisicamente presenti nel codice sorgente C/C++ (es. `if (!ptr) return NULL;`, `return XML_ERROR_FILE_NOT_FOUND;`, `return -1;`) sono stati esplicitamente intercettati e descritti nelle clausole della documentazione.
* **Come viene Calcolata**:
  $$\text{EDR} = \frac{\text{Rami di Errore nel Sorgente Coperti nella Doc}}{\text{Totale Rami di Errore Rilevati nel Sorgente C/C++}} \times 100$$
* **Come Interpretare**:
  - **100%**: Tutti gli scenari di fallimento o codici d'errore gestiti dalla funzione sono chiaramente spiegati al chiamante.
  - **< 50%**: Grave carenza documentale: la funzione può fallire restituendo codici di errore o puntatori nulli ma la documentazione non ne avverte l'utilizzatore.

---

### 🔹 Edge Case Coverage (ECC) [0% - 100%]
* **Descrizione Tecnica**: Valuta la copertura dei casi limite del software: controlli su puntatori nulli (`null_guard`), valori numerici negativi o zero (`zero_negative_guard`), e stringhe vuote o boundary (`empty_boundary_guard`).
* **Come viene Calcolata**: Rapporto tra le tipologie di guardie presenti nell'implementazione fisica e quelle esplicitamente menzionate nelle descrizioni (`@details`, `@pre`, `@warning` o `@param`).
* **Come Interpretare**:
  - **100%**: Piena consapevolezza delle condizioni al contorno (robustezza difensiva).
  - **< 70%**: Omissione di casi limite critici che potrebbero indurre lo sviluppatore chiamante a causare crash o *Undefined Behavior*.

---

## 3. Livello Valutativo Semantico & LLM-as-a-Judge

### 🔹 LLM-Judge (Faithfulness, Alignment e Punteggio Combinato) [1.0 - 5.0]
* **Descrizione Tecnica**: Valutazione critica automatizzata eseguita da un modello LLM indipendente (Gemini) strutturata secondo un protocollo **Monte Carlo a 5 iterazioni per funzione ($T=0.4$)** per garantire stabilità statistica e calcolare media e deviazione standard ($\mu \pm \sigma$).
* **Le due Prospettive**:
  1. **Faithfulness (Code + GT vs Doc) [1-5]**: Valuta l'aderenza tecnica alla logica reale del codice C/C++ e l'assenza di difetti (`DEF-1`..`DEF-5`: allucinazioni, tipi errati, omissioni di complessità o incoerenze di memoria).
  2. **Alignment (GT vs Doc) [1-5]**: Valuta quanto la documentazione generata conservi l'intento dell'autore originario, il dominio applicativo e le avvertenze speciali espresse nel Ground Truth.
* **Punteggio Combinato**: Media geometrica/ponderata delle due prospettive:
  $$\text{Judge Combined} = 0.5 \times \text{Score}_{\text{Faithfulness}} + 0.5 \times \text{Score}_{\text{Alignment}}$$
* **Come Interpretare**:
  - **4.5 - 5.0**: Eccellenza tecnica. Nessun difetto logico rilevato, completa fedeltà all'implementazione e all'intento d'autore.
  - **3.0 - 4.4**: Buona documentazione ma con lievi ambiguità (es. omessa specifica se il buffer viene riallocato in-place o copiato).
  - **< 3.0**: Presenza di difetti concettuali o contraddizioni rispetto al comportamento del codice sorgente.

---

### 🔹 Sentence-BERT (SBERT) Cosine Similarity
* **Descrizione Tecnica**: Calcola la similarità coseno vettoriale nello spazio semantico denso generato dal modello `all-MiniLM-L6-v2` tra la documentazione generata (`@brief` + `@details`) e il testo del *Ground Truth*.
* **Come viene Calcolata**:
  $$\text{SBERT Sim} = \frac{\mathbf{e}_{\text{gen}} \cdot \mathbf{e}_{\text{GT}}}{\|\mathbf{e}_{\text{gen}}\| \|\mathbf{e}_{\text{GT}}\|}$$
* **Come Interpretare**:
  - **> 0.75**: Elevata convergenza semantica (i due testi esprimono gli stessi concetti operativi, anche se formulati con parole diverse).
  - **0.50 - 0.75**: Buona concordanza di dominio.
  - **< 0.50**: Disallineamento semantico o descrizione incentrata su aspetti differenti della funzione.

---

### 🔹 BERTScore & CodeBERTScore F1
* **Descrizione Tecnica**: Metriche di similarità neurale basate sull'allineamento dei singoli token contestualizzati (rispettivamente con `bert-base-uncased` e `microsoft/codebert-base`), ponderate con pesi IDF.
* **Come Interpretare**:
  - Catturano sfumature sintattiche e di nomenclatura tecnica che le metriche lessicali standard ignorano.
  - Valori attorno a **0.70 - 0.85** rappresentano la norma per documentazione tecnica ricca e ben strutturata.

---

### 🔹 METEOR Score (Synonyms, Stems & Word Order)
* **Descrizione Tecnica**: Misura di sovrapposizione lessicale avanzata che supera i limiti del BLEU. Calcola l'accuratezza dell'unione di parole considerando non solo la corrispondenza esatta, ma anche **forme flesse/stemming** e **sinonimi** via WordNet, applicando una penalità di frammentazione se l'ordine delle parole è alterato.
* **Come Interpretare**:
  - **> 0.50**: Ottimo allineamento lessicale e sintattico con la docstring originale.
  - **0.30 - 0.50**: Concetti espressi con parafrasi corrette ma con lessico alternativo.

---

### 🔹 BLEURT Quality Score
* **Descrizione Tecnica**: Estimatore neurale di qualità basato su un transformer pre-addestrato specificamente su giudizi umani di coerenza e naturalezza del testo.
* **Come Interpretare**: Valori $\ge 0.60$ indicano testo fluente, naturale, grammaticalmente impeccabile e altamente leggibile per un ingegnere software.

---

### 🔹 Concept Checklist Score (Semantic Facts)
* **Descrizione Tecnica**: Verifica l'avvenuta estrazione dei fatti tecnici fondamentali categorizzati in 5 macro-aree semantiche:
  1. *Ownership & Memory*: `alloc`, `free`, `delete`, `leak`, `heap`.
  2. *Null & Pointer Safety*: `null`, `nullptr`, `null-terminated`, `valid pointer`.
  3. *Error Contract*: `error`, `fail`, `success`, `status`, `return code`.
  4. *Mutation & Immutability*: `modify`, `const`, `read-only`, `in-place`, `append`.
  5. *Bounds & Range*: `bound`, `range`, `limit`, `capacity`, `overflow`.
* **Come viene Calcolata**: Percentuale di concetti attivi nel *Ground Truth* che sono stati preservati ed esplicitati nella documentazione generata.
* **Come Interpretare**:
  - **0.70 - 1.0**: Nessun fatto architetturale chiave o vincolo di memoria è stato tralasciato.

---

### 🔹 Metriche Lessicali Classiche (TF-IDF Cosine, ROUGE-L, Recall Chiavi GT)
* **TF-IDF Cosine Similarity**: Somiglianza vettoriale pesata in base alla frequenza dei termini tecnici rari.
* **ROUGE-L**: Misura della più lunga sottosequenza comune (*Longest Common Subsequence*) normalizzata.
* **Recall Chiavi Ground Truth**: Percentuale di parole informative originarie dell'autore presenti nel nuovo testo.
* **Come Interpretare**: Fungono da *baseline* lessicale. Valori moderati di ROUGE-L (~0.30-0.40) uniti a valori alti di S-BERT/Judge (~0.75-4.8) sono il segno distintivo di un modello che **non copia meccanicamente il testo**, ma lo astrae, arricchisce e formalizza in Doxygen standard.

---

### 🔹 Fréchet Embedding Distance (FID / Wasserstein-2)
* **Descrizione Tecnica**: Calcola la distanza di Fréchet tra la distribuzione gaussiana multivariata delle feature degli embedding del Ground Truth $(\mu_1, \Sigma_1)$ e quella della documentazione generata $(\mu_2, \Sigma_2)$:
  $$\text{FID} = \|\mu_1 - \mu_2\|_2^2 + \text{Tr}\left(\Sigma_1 + \Sigma_2 - 2(\Sigma_1 \Sigma_2)^{1/2}\right)$$
* **Come Interpretare**:
  - Più la distanza è vicina a **0.0**, più la distribuzione concettuale generata è identica per varietà, registro e densità semantica a quella della documentazione ufficiale.

---

## 4. Livello di Downstream Utility & Validazione Comportamentale

### 🔹 Downstream Code Retrieval (MRR & Hit@K)
* **Descrizione Tecnica**: Valuta se la documentazione prodotta è abbastanza discriminante e descrittiva da permettere a un modello bi-encoder di ritrovare la funzione C/C++ target corretta all'interno dell'intero database di funzioni del progetto (senza conoscere in anticipo il nome della funzione).
* **Come viene Calcolata**:
  - Usando la documentazione generata come query, si calcola la similarità rispetto a tutte le funzioni del database e si stila una classifica per pertinenza.
  - **Rank Target ($r$)**: posizione in classifica della funzione reale.
  - **Reciprocal Rank (RR)**: $\frac{1}{r}$.
  - **MRR (Mean Reciprocal Rank)**: Media dei Reciprocal Rank su tutte le funzioni.
  - **Hit@1**: percentuale di volte in cui la funzione target è arrivata al 1° posto assoluto.
  - **Hit@5**: percentuale di volte in cui la funzione target è finita nelle prime 5 posizioni.
* **Come Interpretare**:
  - **MRR > 0.60, Hit@1 $\ge 50\%$, Hit@5 $\ge 80\%$**: La documentazione cattura l'essenza funzionale della componente in modo inequivocabile, rendendola indicizzabile e rintracciabile nei motori di ricerca di codice semantico.

---

### 🔹 Round-Trip Differential Testing (Doc-to-Code Synthesis & Dual Pytest Execution)
* **Descrizione Tecnica**: Il test di validazione comportamentale definitivo. Verifica se la documentazione tecnica generata è **eseguibile, autosufficiente e operativamente non ambigua**:
  1. **Sintesi da Docstring ($f_{\text{doc}}$)**: Un modello LLM riceve **esclusivamente la documentazione Doxygen generata** (senza mai vedere il codice sorgente C/C++) e sintetizza un'implementazione Python funzionale aderente ai contratti documentati.
  2. **Implementazione di Riferimento ($f_{\text{ref}}$)**: Il codice C/C++ originale viene traspilato in Python come Ground Truth comportamentale.
  3. **Generazione Test Pure Black-Box (Pytest + Hypothesis)**: La suite di test unitari e property-based viene generata adottando un paradigma **esclusivamente Black-Box**, basato unicamente sulla firma e sui contratti esposti nella docstring (senza ispezionare le variabili interne né di $f_{\text{doc}}$ né di $f_{\text{ref}}$). Include asserzioni su casi nominali, boundary/edge cases e fuzzing con oltre 50 input casuali.
  4. **Esecuzione Differenziale & Dual Assertion**: Entrambe le implementazioni vengono eseguite a specchio a parità di input:
     - Si verifica se $f_{\text{doc}}$ soddisfa la propria specifica contrattuale.
     - Si verifica se per ogni input $x$, $f_{\text{doc}}(x) \equiv f_{\text{ref}}(x)$ sia nei valori di ritorno che nelle mutazioni di output.

* **Metriche di Risultato**:
  - **Self-Consistency Pass Rate (%)**: percentuale di test superati dall'implementazione derivata da documentazione ($f_{\text{doc}}$). Misura la coerenza logica interna del contratto.
  - **Dual Agreement Rate (%)**: tasso di equivalenza comportamentale rigorosa tra il codice derivato dalla documentazione e il codice reale originale ($f_{\text{doc}}(x) \equiv f_{\text{ref}}(x)$).
  - **Media Combinata Round-Trip (%)**: media aritmetica $(\text{Pass Rate Doc} + \text{Dual Agreement})/2$, che esprime la qualità complessiva di sintesi ed equivalenza.

---

### 🏷️ Tassonomia Funzionale a 3 Categorie del Round-Trip

Poiché librerie C/C++ diverse presentano paradigmi computazionali eterogenei, il framework disaggrega automaticamente le funzioni in **3 macro-categorie tassonomiche** per spiegare in modo rigoroso le prestazioni differenziali:

#### 1. 🟢 Stateless / Primitive
* **Definizione e Caratteristiche**: Funzioni puramente matematiche, scalari o di utilità prive di memoria interna persistente e prive di puntatori a strutture opache complesse (es. funzioni di saturazione aritmetica di OpenCV come `cvIsNaN`, `saturate_cast`, reset di algoritmi di calcolo, o utility su stringhe elementari).
* **Aspettativa e Comportamento**: Presentano il massimo grado di allineamento comportamentale. Essendo formalmente definite da relazioni $y = f(x)$, la docstring cattura l'intero spazio degli stati e il **Dual Agreement Rate** converge verso valori elevati ($\ge 80\% - 100\%$).

#### 2. 🟡 Pointer / Buffer-Driven
* **Definizione e Caratteristiche**: Funzioni caratteristiche del C a basso livello che operano su buffer di memoria grezzi (`char*`, `unsigned char*`, `size_t len`) e puntatori di input/output (es. `int* out`, `char** endptr`) per restituire valori ausiliari o codici di stato (es. parser HTTP di `http-parser`, compressione/decompressione `miniz`, manipolazione stringhe binarie `sds`).
* **Aspettativa e Comportamento**: La sintesi richiede la modellazione Python dei puntatori C tramite contenitori mutabili a elemento singolo (`out = [0]`). La divergenza può insorgere su dettagli implementativi fini non esposti nel contratto (es. esatta posizione di scorrimento del puntatore al parsing d'errore o gestione di delimitatori multipli).

#### 3. 🟣 Stateful / Object-Graph
* **Definizione e Caratteristiche**: Metodi appartenenti a classi C++ con stato interno incapsulato (`::`, es. metodi DOM di `TinyXML-2` come `XMLElement::QueryInt64Attribute`) oppure funzioni C che manipolano grafi di puntatori e strutture dati ad albero/nodo eterogenee (es. `cJSON*`).
* **Aspettativa e Comportamento**: È il dominio tipico del principio di **Information Hiding**. La documentazione d'autore e i blocchi Doxygen descrivono intenzionalmente *l'interfaccia pubblica* (contratto esterno) e nascondono l'architettura dei campi privati (es. se gli attributi XML sono salvati internamente come lista doppiamente concatenata di oggetti `XMLAttribute` con nodi sentinella o in un albero bilanciato).
* **Spiegazione Scientifica del Gap**: In questa categoria, la funzione generata da docstring ($f_{\text{doc}}$) può superare il 100% dei propri test di contratto (**Self-Consistency Pass Rate** elevato), ma mostrare un **Dual Agreement Rate** contenuto se confrontata con la traspilazione del sorgente originale ($f_{\text{ref}}$). La discrepanza non riflette un errore della documentazione, bensì la fisiologica indipendenza dell'implementazione interna rispetto al contratto astratto.

---

### 🔹 Judge / Critic Agent Evaluation (Pipeline Multi-Agente Specialistica)
* **Descrizione Tecnica**: Nella modalità multi-agente (`--multiagent`), dopo che il blocco Doxygen supera la validazione deterministica formale dell'AST Verifier, interviene un agente di audit dedicato (**Judge / Critic Agent**). Il Giudice confronta in modo critico la documentazione generata con l'implementazione C/C++ originale, valutando la completezza dei contratti, la chiarezza sulle pre/post-condizioni, la gestione dei puntatori NULL e dei codici di errore.
* **Scala di Valutazione (1 - 5)**:
  - **5 (Eccellente / Production Grade)**: Impeccabile e completa. Contratti chiari (@pre/@post), gestione esaustiva di edge cases e puntatori NULL.
  - **4 (Buono / Solido)**: Tecnicamente accurata senza errori fattuali. Differenze solo minori o stilistiche.
  - **3 (Sufficiente ma Migliorabile)**: Omissioni fattuali (es. gestione memoria/ownership non specificata, codici di errore omessi, spiegazione incompleta su NULL).
  - **2 (Insufficiente / Generica)**: Tautologica o vaga; si limita a parafrasare il nome della funzione senza spiegare i parametri o gli effetti collaterali.
  - **1 (Gravemente Errata)**: Allucinazioni fattuali o contraddizioni dirette con la logica sorgente.
* **Politica di Rigenerazione con Critica Guidata**:
  - **Soglia di Accettazione**: $\ge 4$.
  - Se il voto scende **sotto il 4** ($\text{score} < 4$), il Judge formula una **critica costruttiva e puntuale** con suggerimenti correttivi specifici. Questa motivazione viene iniettata nel contesto del **Writer Agent**, che riscrive la documentazione correggendo le lacune evidenziate fino al raggiungimento dello standard qualitativo richiesto (fino a un massimo di 3 tentativi protetti).

---

## 🔬 Sezione 4: Guida alla Lettura della Suite dei Grafici Diagnostici

Il framework genera automaticamente una suite completa di **grafici scientifici (DPI 200)** per ogni sessione di benchmark, fornendo una visione d'insieme sia quantitativa che causale:

### 📊 Dashboard Diagnostica Round-Trip (`eval_chart_roundtrip.png`)
* **Architettura a 3 Pannelli Coordinati**:
  1. **Pannello Superiore**: Confronto orizzontale a barre affiancate per ciascuna funzione tra **Pass Rate Doc ($f_{\text{doc}}$)** e **Dual Agreement ($f_{\text{doc}} \equiv f_{\text{ref}}$)**. Le funzioni sono raggruppate e separate visivamente tramite banner cromatici distintivi corrispondenti alle 3 categorie tassonomiche (*Stateless / Primitive*, *Pointer / Buffer-Driven*, *Stateful / Object-Graph*), con linee guida tratteggiate indicanti le medie di ciascuna metrica e la media finale complessiva.
  2. **Pannello Inferiore Sinistro**: Medie aggregate disaggregate per categoria funzionale, evidenziando il differenziale di resa esecutiva tra funzioni pure, manipolazioni a buffer e metodi ad albero di oggetti/stato interno.
  3. **Pannello Inferiore Destro**: Sintesi globale a 3 indicatori cardine: **Pass Rate Doc**, **Dual Agreement Rate** e **Media Finale Combinata**, offrendo un quadro immediato e oggettivo della solidità della documentazione generata.

### 🩺 Dashboard Diagnostica Cause di Errore Round-Trip (`eval_chart_roundtrip_errors.png`)
* **Architettura a 2 Pannelli Coordinati**:
  1. **Pannello Sinistro (Distribuzione Tassonomica degli Errori)**: Grafico a barre orizzontali ad alto contrasto con color-coding semantico per classificare la causa prima dei fallimenti dei test:
     - *Missing Symbol / Environment*: funzioni ausiliarie, tipi o costanti non forniti nello scaffold generato.
     - *Interface / Signature Mismatch*: discrepanze su numero/nomi dei parametri o tipi.
     - *Behavioral / Contract Failure*: il calcolo o la logica non rispetta le asserzioni di contratto.
     - *Test Harness / Generator Bug*: anomalie interne dei test generati (es. `DID NOT RAISE` o parametri errati di Hypothesis).
  2. **Pannello Destro (Top Funzioni con Errori)**: Classifica delle funzioni critiche che hanno registrato il maggior numero di test falliti, indicando chiaramente il tasso $k/N$ e la tipologia di errore prevalente.
* **Report Separato Dettagliato (`roundtrip_error_report.md`)**: File Markdown dedicato generato automaticamente a ogni run, completo di tabelle di riepilogo e sezioni a scomparsa con il messaggio di errore completo e testuale per ogni singolo test fallito.

### 1. 🕸️ Radar / Spider Chart Multi-Dimensionale (`eval_chart_radar.png`)
- **Assi**: Aderenza AST, Semantica Neurale, Actionability, Copertura Eccezioni, Affidabilità Formale, Downstream Utility.
- **Scopo**: Visualizzare il bilanciamento globale del generatore: un poligono regolare e prossimo a $1.0$ comprova l'eccellenza simultanea sia sintattica che semantica.

### 2. 🔀 Scatter Plot Correlazione Semantica vs Round-Trip (`eval_chart_semantic_vs_roundtrip.png`)
- **Assi**: Asse X = Sentence-BERT Cosine Similarity $[0.0 - 1.0]$; Asse Y = Round-Trip Pass Rate $\%$ (con retta OLS e indice $r$ di Pearson).
- **Interpretazione**:
  - Punti in alto a sinistra: *Parafrasi Robusta* (lessico alternativo ma logica impeccabile).
  - Punti in basso a destra: *Allucinazione Plausibile* (eloquente ma fallace all'esecuzione).

### 3. 🎻 Violin & Strip Distribution Plot (`eval_chart_distributions.png`)
- **Elementi Grafici**:
  - **Area Colorata (Violino)**: Stima della densità di probabilità (KDE) della metrica.
  - **Linea Rossa**: Mediana ($50^\circ$ percentile).
  - **Pallini Scuri con Jitter**: Singole funzioni analizzate. Evidenzia la stabilità e la varianza statistica del metodo.

### 4. 🎯 Heatmap Matrice di Confidenza Funzione $\times$ Metriche (`eval_chart_heatmap.png`)
- **Caratteristiche**: Palette continua ad alto contrasto `YlGnBu` con numeri centrati e separatori netti.
- **Scopo**: Audit rapido a matrice per isolare le funzioni critiche della codebase che necessitano di refactoring o documentazione guidata.

### 5. 🛡️ Breakdown Cause di Scarto Verifier & Rigetti del Giudice (`eval_chart_verifier_breakdown.png`)
- **Categorie**: Parametri Errati, Return Type Errato, Simboli Allucinati, Rigetto Giudice ($\text{score} < 4$), Superato al 1° Tentativo.
- **Scopo**: Quantificare il valore difensivo del Verifier deterministico nell'azzerare le imperfezioni prima dell'approvazione finale.

### 6. 🔗 Matrice di Cross-Correlazione delle Metriche (`eval_chart_cross_correlation.png`)
- **Caratteristiche**: Matrice $N \times N$ Pearson $r$ con mappa divergente `coolwarm`.
- **Scopo Accademico**: Mostrare l'ortogonalità tra le metriche di similarità puramente lessicale/neurale e quelle di utilità esecutiva reale (Round-Trip).

### 7. ⚖️ Analisi dei Residui: Allucinazione Plausibile vs Parafrasi Robusta (`eval_chart_discrepancy_residuals.png`)
- **Definizione**: Residuo $\Delta = \mathrm{SBERT} - (\mathrm{RoundTrip\ Pass\ Rate} / 100)$.
- **Barre**:
  - **Rosse ($\Delta > +0.05$)**: Sovrastima Semantica (alta affinità testuale, ma fallimento a runtime).
  - **Verdi ($|\Delta| \leq 0.05$)**: Perfetto allineamento teoria-pratica.
  - **Blu ($\Delta < -0.05$)**: Sottostima Semantica (sintassi diversa ma successo esecutivo pieno).

### 8. 📈 Scalabilità Pareto: Complessità Codice (LOC) vs Performance (`eval_chart_complexity_pareto.png`)
- **Assi**: Asse X = Linee di Codice Sorgente C/C++ (LOC); Asse Y = Round-Trip Pass Rate % o SBERT.
- **Scopo**: Validare che la pipeline mantenga alte prestazioni anche all'aumentare delle dimensioni e della complessità computazionale della funzione documentata.

### 9. ⏳ Imbuto di Validazione e Transizioni della Pipeline (`eval_chart_pipeline_flow.png`)
- **Stadi**: $\text{Draft LLM} \rightarrow \text{Verifier AST} \rightarrow \text{LLM-Judge} \rightarrow \text{Round-Trip Pass}$.
- **Scopo**: Evidenziare quantitativamente come ciascun filtro della pipeline multi-stadio contribuisca alla certificazione della documentazione generata.

---

## 🎯 Sezione 5: Strategie di Campionamento e Stress Test per Complessità (LOC)

Per garantire esperimenti scientificamente solidi e perfettamente riproducibili, il framework implementa **3 Strategie di Selezione delle Funzioni**:

### 1. 🔢 Sequenziale (`--sampling sequential`)
- Seleziona le prime $N$ funzioni ordinate per identificativo deterministico. Ideale per test di regressione locali e verifiche rapide.

### 2. 🎲 Casuale Puro (`--sampling random`, con `--seed`)
- Estrae un campione casuale uniforme dall'intero pool. Se si specifica `--seed <N>`, il generatore pseudo-casuale garantisce che lo stesso identico sottoinsieme di funzioni venga valutato su diverse pipeline (es. `single` vs `multiagent`), consentendo un confronto equo e oggettivo.

### 3. 📊 Stratificato per Quantili di Lunghezza LOC (`--sampling stratified`, con `--seed` e `--min-loc`)
- **Principio Matematico**: Il pool di funzioni viene ordinato per righe di codice sorgente (LOC). Lo spettro dimensionale viene suddiviso in $N$ bin logaritmici/quantili contigui ed equi-distribuiti, estraendo esattamente **una funzione per ciascun intervallo di complessità**.
- **Perché è Cruciale per la Tesi**:
  - Evita che il dataset sia dominato da sole funzioni one-liner o getter/setter banali (1 – 5 LOC).
  - Distribuisce i punti in modo uniforme lungo tutto l'asse orizzontale del **Pareto Complexity Plot** (`eval_chart_complexity_pareto.png`), coprendo funzioni brevi, medie, complesse e di parser (da 1 a 1500+ LOC).
  - È riproducibile al 100% fissando il parametro `--seed`.
- **Filtro Opzionale `--min-loc <N>`**: consente di escludere funzioni troppo brevi e concentrare lo stress test solo su blocchi logici complessi (es. `--min-loc 20`).

---

## 📦 Librerie del Dataset di Benchmark (Ground Truth)

Il database consolidato (`dataset/benchmark.db`, oltre 500 funzioni con codice e documentazione originaria) include:
1. **`cJSON`** (C puro): manipolazione alberi JSON, formattazione e parsing ricorsivo.
2. **`OpenCV core`** (C++): funzioni matematiche veloci, saturazione e primitive di calcolo numerico.
3. **`TinyXML-2`** (C++): classi DOM XML, gerarchie di nodi e serializzatori.
4. **`sds`** (C puro): stringhe dinamiche di Redis con gestione raw memory ed header binari.
5. **`fmt`** (C++): libreria di formattazione sicura a compile-time.
6. **`miniz`** (C puro): algoritmi di compressione/decompressione lossless Deflate/Inflate (ad alta intensità ciclica).
7. **`http-parser`** (C puro): parser HTTP/1.1 a macchina a stati finiti ad alte prestazioni (Node.js/Joyent).


