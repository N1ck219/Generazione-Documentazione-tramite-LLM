# Ricerca bibliografica: originalità di Doc Mutation Score e Specification Ambiguity Index

Data della ricerca: 2026-10-07. Metodo: ricerche web (standard ed estese) su mutation testing di specifiche/documentazione, ambiguità misurata con programmi campionati, valutazione della documentazione tramite round-trip.

> **Limite importante.** Gli host `arxiv.org` e `dl.acm.org` erano bloccati dal proxy di rete della sessione, quindi **non ho letto nessun PDF**. Tutto ciò che segue si basa su titoli, abstract e estratti restituiti dal motore di ricerca. Prima di citare un lavoro in tesi, apri l'articolo e controlla autori, sede di pubblicazione e quanto è davvero simile al tuo metodo. Dove ricordo metadati che non ho visto negli estratti, lo segno come **da verificare**.

## 1. Conclusione in breve

| Metrica | Ingrediente | Già presente in letteratura? | Cosa resta potenzialmente tuo |
| :--- | :--- | :--- | :--- |
| **SAI** | Campionare N programmi dalla stessa descrizione, eseguirli su input comuni, misurare il disaccordo | **Sì**, è il meccanismo di ClarifyGPT e di lavori sulla riparazione di descrizioni ambigue e sull'entropia semantica del codice | L'uso come **metrica di qualità della documentazione** di funzioni C/C++ esistenti, e la **tassonomia a 4 casi rispetto al reference** (ambiguità contro informazione nascosta) |
| **DMS** | Mutanti + test come misura della forza di una specifica | **Sì per le specifiche formali** (MutDafny, mutation analysis per contratti) e per le specifiche eseguibili (CodeSpecBench) | L'applicazione a **documentazione in linguaggio naturale** tramite suite di test generata da LLM, con **baseline signature-only (Doc Lift)** |

In nessuna ricerca ho trovato un lavoro che faccia esattamente queste combinazioni. Questo **non** prova che non esistano: la ricerca è limitata e non ho letto i testi.

**Formulazione prudente per la tesi:** non scrivere «ho inventato» il mutation testing o il campionamento per misurare l'ambiguità. Scrivi che *adatti* tecniche note al problema della valutazione della documentazione di codice C/C++ generata da LLM, e che il contributo sta nella loro combinazione, nel Doc Lift e nella scomposizione ambiguità / informazione nascosta.

## 2. Lavori vicini allo SAI

| Lavoro | Cosa fa (da abstract/estratti) | Differenza rispetto allo SAI |
| :--- | :--- | :--- |
| **ClarifyGPT** (ACM, DOI 10.1145/3660810; autori e sede esatta **da verificare**) | Campiona n soluzioni dal modello per un requisito, le esegue su input di test e confronta gli output: se coincidono il requisito è non ambiguo, altrimenti ambiguo | Obiettivo diverso: rilevare ambiguità nei *requisiti* per **fare domande di chiarimento**, non valutare la documentazione prodotta. Non usa un reference per separare le cause |
| **Automated Repair of Ambiguous Problem Descriptions** (arXiv 2505.07270) | Partiziona i programmi campionati in classi di equivalenza in base al comportamento input-output; più cluster indicano una descrizione sottospecificata | Riparazione di descrizioni di problemi (stile benchmark), non documentazione di funzioni di librerie reali |
| **Assessing the Impact of Requirement Ambiguity on LLM-based Function-Level Code Generation** (arXiv 2604.21505) | Studia la divergenza funzionale dei modelli sotto requisiti ambigui (negli estratti compare un tasso di conflitto tra modelli del 57,28%, ma non sono certo che la cifra appartenga a questo articolo: **da verificare**) | Studio empirico dell'effetto, non una metrica per documentazione |
| **Entropia semantica / funzionale per il codice** (es. arXiv 2605.28500 «Functional Entropy», 2607.12273 «Code-MUE», 2502.11620) | Cluster di programmi per comportamento di esecuzione, entropia sui cluster per stimare l'incertezza e la correttezza | Misurano l'**incertezza del modello** per predire la correttezza, non l'ambiguità di una documentazione |
| **Can docstring reformulation with an LLM improve code generation?** (ACL EACL SRW 2024) | Campiona più modelli per massimizzare la probabilità di codice corretto, usandolo per valutare/riformulare docstring | Più vicino come intento, ma misura la correttezza, non la scomposizione del disaccordo |

**Cosa dire del SAI.** Il calcolo (cluster per comportamento, disaccordo tra campioni) è noto. I punti da difendere come tuoi sono:
1. il passaggio da «richiesta dell'utente» a «documentazione generata di una funzione esistente», con il reference C/C++ traspilato disponibile;
2. la tassonomia a 4 casi (`determined_correct` / `determined_divergent` / `ambiguous_covers_ref` / `ambiguous_divergent`), che separa *ambiguità della doc* da *informazione assente dalla doc* (il tuo caso Information Hiding). Nelle ricerche non ho trovato questa scomposizione, ma non posso escluderla.

## 3. Lavori vicini al DMS

| Lavoro | Cosa fa (da abstract/estratti) | Differenza rispetto al DMS |
| :--- | :--- | :--- |
| **MutDafny** (arXiv 2511.15403) | Applica mutation testing a **specifiche formali Dafny**: i mutanti sopravvissuti indicano specifiche deboli; le specifiche uccidono in media l'82% dei mutanti | Specifiche formali verificabili, non documentazione in linguaggio naturale |
| **How much Specification is Enough? Mutation Analysis for Software Contracts** (ICSE Formalise 2021) | Mutation analysis per valutare quanto bastano i contratti | Contratti formali |
| **CodeSpecBench** (arXiv 2604.12268) | Specifiche eseguibili (pre/postcondizioni) generate da LLM, valutate su casi di test corretti e **scorretti** per misurare correttezza e **completezza** | Il concetto di «rifiutare comportamenti invalidi» è molto vicino al kill dei mutanti, ma qui l'oggetto è una specifica eseguibile, non documentazione Doxygen |
| **METAMON** (ICSE 2025, workshop LLM4Code) | Cerca incoerenze tra documentazione e comportamento con query LLM metamorfiche; 9.482 coppie metodo-documentazione Java, precisione 0,72, recall 0,48 | Rileva doc *incoerente* con il codice, non misura quanto la doc *vincola* il comportamento. Non usa mutanti |
| **Round-Trip Mutation Testing** (arXiv 2607.03223) e **Intent-Based Mutation Testing** (Hamidi, Khanfir, Papadakis; ICST 2025 workshop Mutation) | Generano mutanti passando dal codice a un'intenzione in linguaggio naturale e ritorno, o mutando l'intenzione | Usano il linguaggio naturale per **creare mutanti per valutare i test**. La direzione è opposta alla tua (mutanti del codice per valutare la documentazione) |
| **Classici (da verificare e citare)** | *Specification mutation* / mutation analysis per specifiche, invarianti (Daikon) e test adequacy | Letteratura storica da cercare direttamente (Budd & Gopal e successivi) |

**Cosa dire del DMS.** L'idea «i mutanti sopravvissuti rivelano una specifica debole» è consolidata per specifiche formali. Resta da difendere:
1. l'estensione a **documentazione in linguaggio naturale**, con la suite di test generata da un LLM come strumento di lettura della doc;
2. il **Doc Lift** contro una baseline solo-firma con lo stesso generatore di test, che controlla il confondente «qualità del generatore»;
3. l'**Adjusted Score** su un pool di mutanti uccisi da almeno una suite come approssimazione dei mutanti non equivalenti (la tecnica dei mutanti non equivalenti approssimati con un pool è nota nel mutation testing: da citare come tale).

## 4. Lavori su cui si appoggia il Round-Trip esistente

| Lavoro | Rilevanza |
| :--- | :--- |
| **Unsupervised Evaluation of Code LLMs with Round-Trip Correctness** (Allamanis, Panthaplackel, Yin, ICML 2024, PMLR 235:1050-1066) | Da citare nel capitolo sul Round-Trip. RTC valuta **il modello** (descrivi il codice, risintetizza, controlla l'equivalenza), non la documentazione: è una distinzione utile da esplicitare |
| **DocAgent** (ACL 2025 demo, aclanthology 2025.acl-demo.44) | Valuta la documentazione su Completeness, Helpfulness (LLM-judge) e Truthfulness (esistenza dei simboli). La Truthfulness è molto vicina al tuo Existence Ratio |
| **SWD-Bench** (arXiv 2604.06793) | Valuta la documentazione di repository tramite question answering guidato dalle funzionalità; stesso spirito di «documentazione come informazione sufficiente a ricostruire il comportamento» |
| **TestExplora** (arXiv 2602.10471) | Usa la documentazione come oracolo per trovare bug: vicino all'idea di doc come specifica |

## 5. Cosa fare adesso

1. **Leggere i PDF** dei cinque lavori più vicini: ClarifyGPT, Automated Repair of Ambiguous Problem Descriptions, MutDafny, CodeSpecBench, METAMON. Sono quelli che un relatore potrebbe contrapporre.
2. **Completare la ricerca** con le basi che qui non ho potuto interrogare (Google Scholar, ACM DL, IEEE Xplore, DBLP): parole chiave `specification mutation`, `documentation quality execution-based`, `documentation sufficiency`, `semantic entropy code`.
3. **Inserire nella tesi** una sezione «Lavori correlati» con le tabelle sopra e una frase di posizionamento sul contributo (§1).
4. **Validare empiricamente** le due metriche (correlazione con Judge e Dual Agreement, test di sensibilità): è la parte che rende difendibile un contributo anche se le idee di base sono note.
