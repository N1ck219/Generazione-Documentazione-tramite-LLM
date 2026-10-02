# Valutazione Metriche: CodeWiki vs Ground Truth (sds)

> **Script**: `utils/evaluate_codewiki_metrics.py`  
> **Libreria target**: sds  
> **Funzioni uniche nel DB**: 39 (74 righe, varianti header/implementazione)  
> **Menzioni di metodi in CodeWiki**: 46  
> **Funzioni DB con testo CodeWiki valutato**: 35 (89.7% del DB)  

---

## 1. Copertura API

| Metrica | Valore |
|---------|--------|
| Funzioni uniche DB sds | 39 |
| Menzioni di metodi nei Markdown CodeWiki | 46 |
| Menzioni senza corrispondenza nel DB | 8 |
| Funzioni DB menzionate (testo o diagramma Mermaid) | 35 |
| └── di cui solo nel diagramma Mermaid (senza testo) | 0 |
| **Documented Coverage** (funzioni con testo descrittivo) | **89.7%** (35/39) |
| Mention Coverage | 89.7% (35/39) |
| Funzioni DB non coperte | 4 |

Strategie di matching (per menzione): `exact`=38, `none`=8.

---

## 2. Metriche di Qualita' della Documentazione

*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n=35)*

| Metrica | n | Media | Std | Min | Max |
|---------|---|-------|-----|-----|-----|
| SBERT Cosine Similarity | 35 | 0.6279 | 0.2034 | 0.1007 | 0.9329 |
| BERTScore F1 | 35 | 0.5914 | 0.1024 | 0.4116 | 0.8891 |
| ROUGE-L | 35 | 0.2187 | 0.1702 | 0.0000 | 0.7143 |
| TF-IDF Cosine | 35 | 0.3338 | 0.2002 | 0.0000 | 0.7826 |
| METEOR | 35 | 0.4233 | 0.1708 | 0.0992 | 0.8236 |
| BLEURT Estimate | 35 | 0.4970 | 0.1733 | 0.1144 | 0.8566 |
| Semantic Concept Checklist | 35 | 0.6286 | 0.4142 | 0.0000 | 1.0000 |
| Actionability Score | 35 | 0.2671 | 0.1000 | 0.2500 | 0.8500 |
| Error Documentation Rate | 10 | 0.2000 | 0.4000 | 0.0000 | 1.0000 |
| Edge Case Coverage | 22 | 0.1591 | 0.3157 | 0.0000 | 1.0000 |
| Length Ratio (CodeWiki/GT) | 35 | 0.5096 | 0.4251 | 0.0600 | 2.0000 |

---

## 3. Distribuzione SBERT per Funzione

*(Tutte le 35 funzioni valutate, ordinate per SBERT decrescente)*

| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |
|-------------|-------------------|-------|---------|--------|---------------|
| `sdsnew` | sdsnew | 0.9329 | 0.7143 | 0.8236 | 0.2500 |
| `sdsdup` | sdsdup | 0.9165 | 0.5714 | 0.7440 | 0.2500 |
| `sdsAllocSize` | sdsAllocSize | 0.8649 | 0.5000 | 0.6825 | 0.2500 |
| `sdsjoin` | sdsjoin | 0.8511 | 0.2222 | 0.5366 | 0.2500 |
| `sdscpylen` | sdscpylen | 0.8477 | 0.4762 | 0.6620 | 0.2500 |
| `sdscat` | sdscat | 0.8124 | 0.2759 | 0.5442 | 0.2500 |
| `sdscatlen` | sdscatlen | 0.7762 | 0.2778 | 0.5270 | 0.2500 |
| `sdsgrowzero` | sdsgrowzero | 0.7709 | 0.2222 | 0.4966 | 0.2500 |
| `sdsnewlen` | sdsnewlen | 0.7538 | 0.1370 | 0.4454 | 0.2500 |
| `sdscmp` | sdscmp | 0.7498 | 0.1200 | 0.4349 | 0.2500 |
| `sdssplitlen` | sdssplitlen | 0.7484 | 0.1176 | 0.4330 | 0.2500 |
| `sdsfromlonglong` | sdsfromlonglong | 0.7385 | 0.5000 | 0.6193 | 0.2500 |
| `sdsIncrLen` | sdsIncrLen | 0.7326 | 0.1304 | 0.4315 | 0.2500 |
| `sdsfree` | sdsfree | 0.7131 | 0.2105 | 0.4618 | 0.2500 |
| `sdsmapchars` | sdsmapchars | 0.7129 | 0.1333 | 0.4231 | 0.2500 |
| `sdsjoinsds` | sdsjoinsds | 0.7127 | 0.4615 | 0.5871 | 0.2500 |
| `sdscatsds` | sdscatsds | 0.7012 | 0.1538 | 0.4275 | 0.2500 |
| `sdsRemoveFreeSpace` | sdsRemoveFreeSpace | 0.6976 | 0.1509 | 0.4243 | 0.2500 |
| `sdsMakeRoomFor` | sdsMakeRoomFor | 0.6808 | 0.2424 | 0.4616 | 0.2500 |
| `sdsempty` | sdsempty | 0.6791 | 0.3333 | 0.5062 | 0.8500 |
| `sdscpy` | sdscpy | 0.6612 | 0.3333 | 0.4972 | 0.2500 |
| `sdsclear` | sdsclear | 0.6417 | 0.0952 | 0.3685 | 0.2500 |
| `sdssplitargs` | sdssplitargs | 0.6194 | 0.1163 | 0.3678 | 0.2500 |
| `sdsrange` | sdsrange | 0.5849 | 0.1429 | 0.3639 | 0.2500 |
| `sdsupdatelen` | sdsupdatelen | 0.5793 | 0.1791 | 0.3792 | 0.2500 |
| `sdscatrepr` | sdscatrepr | 0.5111 | 0.2381 | 0.3746 | 0.2500 |
| `sdsull2str` | sdsull2str | 0.4929 | 0.1111 | 0.3020 | 0.2500 |
| `sdscatfmt` | sdscatfmt | 0.4808 | 0.1053 | 0.2931 | 0.2500 |
| `sdscatprintf` | sdscatprintf | 0.3912 | 0.0351 | 0.2132 | 0.2500 |
| `sdscatvprintf` | sdscatvprintf | 0.3796 | 0.1538 | 0.2667 | 0.2500 |
| `sdstolower` | sdstolower | 0.3289 | 0.0000 | 0.1645 | 0.2500 |
| `sdstoupper` | sdstoupper | 0.3080 | 0.0000 | 0.1540 | 0.2500 |
| `sdstrim` | sdstrim | 0.3060 | 0.0385 | 0.1722 | 0.2500 |
| `sdsalloc` | sdsalloc | 0.1984 | 0.0000 | 0.0992 | 0.2500 |
| `sdsfreesplitres` | sdsfreesplitres | 0.1007 | 0.1538 | 0.1273 | 0.2500 |

---

## 4. Interpretazione e Limiti

- **Documented Coverage del 89.7%**: CodeWiki documenta a livello di modulo,
  non per singola funzione. Le funzioni non coperte, per classe, sono:
  `(free functions)` (4).
  Altre 0 funzioni compaiono solo come firma nei diagrammi Mermaid, senza testo descrittivo.

- **Unita' di conteggio**: nel DB molte funzioni compaiono due volte (dichiarazione nell'header e
  definizione nel file di implementazione) con lo stesso Ground Truth; il conteggio usa le funzioni uniche.
  Le descrizioni CodeWiki multiple di una stessa funzione sono concatenate.

- **Matching conservativo**: sono ammessi solo match esatti sul nome canonico, la rimozione
  del namespace iniziale (`fmt::format` -> `format`) e, per i metodi ereditati/ridefiniti,
  il match con la dichiarazione della classe base (es. `XMLDocument::Accept` ->
  `XMLNode::Accept`). Nessun matching fuzzy ne' per solo nome di metodo.

- **EDR / ECC**: calcolati solo sulle funzioni il cui codice (file di implementazione se disponibile)
  contiene rami di errore o guardie su casi limite (colonna *n*); altrove non applicabili.

- **Actionability Score**: la documentazione CodeWiki e' in prosa libera senza tag Doxygen
  (`@param [in/out]`, `@return`, `@pre`). Questo abbassa strutturalmente l'Actionability Score
  rispetto alla pipeline della tesi, che genera commenti Doxygen formali e verificati.

- **Granularita'**: SBERT/METEOR confrontano brevi snippet (tipicamente 1-2 frasi, spesso
  condivisi da un gruppo di metodi, es. "Methods for traversing the DOM tree") con la
  `cleaned_doc` originale, piu' lunga e specifica: i valori tendono ad essere moderati.

---
*Report generato automaticamente da `utils/evaluate_codewiki_metrics.py`*