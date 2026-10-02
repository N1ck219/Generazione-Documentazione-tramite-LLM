# Valutazione Metriche: CodeWiki vs Ground Truth (fmt)

> **Script**: `utils/evaluate_codewiki_metrics.py`  
> **Libreria target**: fmt  
> **Funzioni uniche nel DB**: 12 (12 righe, varianti header/implementazione)  
> **Menzioni di metodi in CodeWiki**: 1  
> **Funzioni DB con testo CodeWiki valutato**: 1 (8.3% del DB)  

---

## 1. Copertura API

| Metrica | Valore |
|---------|--------|
| Funzioni uniche DB fmt | 12 |
| Menzioni di metodi nei Markdown CodeWiki | 1 |
| Menzioni senza corrispondenza nel DB | 0 |
| Funzioni DB menzionate (testo o diagramma Mermaid) | 1 |
| └── di cui solo nel diagramma Mermaid (senza testo) | 0 |
| **Documented Coverage** (funzioni con testo descrittivo) | **8.3%** (1/12) |
| Mention Coverage | 8.3% (1/12) |
| Funzioni DB non coperte | 11 |

Strategie di matching (per menzione): `namespace_stripped`=1.

---

## 2. Metriche di Qualita' della Documentazione

*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n=1)*

| Metrica | n | Media | Std | Min | Max |
|---------|---|-------|-----|-----|-----|
| SBERT Cosine Similarity | 1 | 0.2484 | 0.0000 | 0.2484 | 0.2484 |
| BERTScore F1 | 1 | 0.3361 | 0.0000 | 0.3361 | 0.3361 |
| ROUGE-L | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| TF-IDF Cosine | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| METEOR | 1 | 0.1242 | 0.0000 | 0.1242 | 0.1242 |
| BLEURT Estimate | 1 | 0.1657 | 0.0000 | 0.1657 | 0.1657 |
| Semantic Concept Checklist | 1 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| Actionability Score | 1 | 0.2500 | 0.0000 | 0.2500 | 0.2500 |
| Error Documentation Rate | 0 | N/A | N/A | N/A | N/A |
| Edge Case Coverage | 0 | N/A | N/A | N/A | N/A |
| Length Ratio (CodeWiki/GT) | 1 | 0.2400 | 0.0000 | 0.2400 | 0.2400 |

---

## 3. Distribuzione SBERT per Funzione

*(Tutte le 1 funzioni valutate, ordinate per SBERT decrescente)*

| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |
|-------------|-------------------|-------|---------|--------|---------------|
| `format` | fmt::format | 0.2484 | 0.0000 | 0.1242 | 0.2500 |

---

## 4. Interpretazione e Limiti

- **Documented Coverage del 8.3%**: CodeWiki documenta a livello di modulo,
  non per singola funzione. Le funzioni non coperte, per classe, sono:
  `(free functions)` (6), `format_int` (4), `writer` (1).
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