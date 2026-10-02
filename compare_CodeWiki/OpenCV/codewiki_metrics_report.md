# Valutazione Metriche: CodeWiki vs Ground Truth (OpenCV)

> **Script**: `utils/evaluate_codewiki_metrics.py`  
> **Libreria target**: OpenCV  
> **Funzioni uniche nel DB**: 8 (8 righe, varianti header/implementazione)  
> **Menzioni di metodi in CodeWiki**: 12  
> **Funzioni DB con testo CodeWiki valutato**: 8 (100.0% del DB)  

---

## 1. Copertura API

| Metrica | Valore |
|---------|--------|
| Funzioni uniche DB OpenCV | 8 |
| Menzioni di metodi nei Markdown CodeWiki | 12 |
| Menzioni senza corrispondenza nel DB | 0 |
| Funzioni DB menzionate (testo o diagramma Mermaid) | 8 |
| └── di cui solo nel diagramma Mermaid (senza testo) | 0 |
| **Documented Coverage** (funzioni con testo descrittivo) | **100.0%** (8/8) |
| Mention Coverage | 100.0% (8/8) |
| Funzioni DB non coperte | 0 |

Strategie di matching (per menzione): `exact`=8, `namespace_stripped`=4.

---

## 2. Metriche di Qualita' della Documentazione

*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n=8)*

| Metrica | n | Media | Std | Min | Max |
|---------|---|-------|-----|-----|-----|
| SBERT Cosine Similarity | 8 | 0.5446 | 0.0888 | 0.3814 | 0.6619 |
| BERTScore F1 | 8 | 0.6008 | 0.0459 | 0.5473 | 0.7034 |
| ROUGE-L | 8 | 0.2799 | 0.0928 | 0.0833 | 0.3793 |
| TF-IDF Cosine | 8 | 0.3961 | 0.1371 | 0.1406 | 0.6140 |
| METEOR | 8 | 0.4122 | 0.0808 | 0.2758 | 0.5206 |
| BLEURT Estimate | 8 | 0.4853 | 0.0833 | 0.3588 | 0.5917 |
| Semantic Concept Checklist | 8 | 0.5000 | 0.4330 | 0.0000 | 1.0000 |
| Actionability Score | 8 | 0.2500 | 0.0000 | 0.2500 | 0.2500 |
| Error Documentation Rate | 0 | N/A | N/A | N/A | N/A |
| Edge Case Coverage | 2 | 0.5000 | 0.5000 | 0.0000 | 1.0000 |
| Length Ratio (CodeWiki/GT) | 8 | 0.7712 | 0.3995 | 0.2680 | 1.7040 |

---

## 3. Distribuzione SBERT per Funzione

*(Tutte le 8 funzioni valutate, ordinate per SBERT decrescente)*

| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |
|-------------|-------------------|-------|---------|--------|---------------|
| `cvCeil` | cvCeil, fast_math::cvCeil | 0.6619 | 0.3793 | 0.5206 | 0.2500 |
| `cvFloor` | cvFloor, fast_math::cvFloor | 0.6349 | 0.3667 | 0.5008 | 0.2500 |
| `fastMalloc` | fastMalloc | 0.6228 | 0.3636 | 0.4932 | 0.2500 |
| `cvRound` | cvRound, fast_math::cvRound | 0.5624 | 0.2500 | 0.4062 | 0.2500 |
| `cvIsInf` | cvIsInf | 0.5238 | 0.2667 | 0.3952 | 0.2500 |
| `saturate_cast` | saturate_cast, saturate_cast::saturate_cast | 0.5011 | 0.2182 | 0.3597 | 0.2500 |
| `fastFree` | fastFree | 0.4683 | 0.0833 | 0.2758 | 0.2500 |
| `cvIsNaN` | cvIsNaN | 0.3814 | 0.3111 | 0.3463 | 0.2500 |

---

## 4. Interpretazione e Limiti

- **Documented Coverage del 100.0%**: CodeWiki documenta a livello di modulo,
  non per singola funzione. Le funzioni non coperte, per classe, sono:
  .
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