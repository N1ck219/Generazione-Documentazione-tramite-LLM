# Valutazione Metriche: CodeWiki vs Ground Truth (miniz)

> **Script**: `utils/evaluate_codewiki_metrics.py`  
> **Libreria target**: miniz  
> **Funzioni uniche nel DB**: 21 (36 righe, varianti header/implementazione)  
> **Menzioni di metodi in CodeWiki**: 25  
> **Funzioni DB con testo CodeWiki valutato**: 14 (66.7% del DB)  

---

## 1. Copertura API

| Metrica | Valore |
|---------|--------|
| Funzioni uniche DB miniz | 21 |
| Menzioni di metodi nei Markdown CodeWiki | 25 |
| Menzioni senza corrispondenza nel DB | 3 |
| Funzioni DB menzionate (testo o diagramma Mermaid) | 17 |
| └── di cui solo nel diagramma Mermaid (senza testo) | 3 |
| **Documented Coverage** (funzioni con testo descrittivo) | **66.7%** (14/21) |
| Mention Coverage | 81.0% (17/21) |
| Funzioni DB non coperte | 4 |

Strategie di matching (per menzione): `exact`=22, `none`=3.

---

## 2. Metriche di Qualita' della Documentazione

*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n=14)*

| Metrica | n | Media | Std | Min | Max |
|---------|---|-------|-----|-----|-----|
| SBERT Cosine Similarity | 14 | 0.3961 | 0.1789 | 0.0895 | 0.6974 |
| BERTScore F1 | 14 | 0.4825 | 0.0617 | 0.3870 | 0.5962 |
| ROUGE-L | 14 | 0.0867 | 0.0745 | 0.0000 | 0.2308 |
| TF-IDF Cosine | 14 | 0.1208 | 0.0830 | 0.0000 | 0.2425 |
| METEOR | 14 | 0.0852 | 0.0448 | 0.0206 | 0.1630 |
| Semantic Concept Checklist | 14 | 0.7143 | 0.4518 | 0.0000 | 1.0000 |
| Actionability Score | 14 | 0.2500 | 0.0000 | 0.2500 | 0.2500 |
| Error Documentation Rate | 8 | 0.1250 | 0.3307 | 0.0000 | 1.0000 |
| Edge Case Coverage | 9 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Length Ratio (CodeWiki/GT) | 14 | 4.6758 | 7.2202 | 0.3160 | 22.6670 |

---

## 3. Distribuzione SBERT per Funzione

*(Tutte le 14 funzioni valutate, ordinate per SBERT decrescente)*

| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |
|-------------|-------------------|-------|---------|--------|---------------|
| `mz_inflateReset` | mz_inflateReset | 0.6974 | 0.0741 | 0.1630 | 0.2500 |
| `mz_compressBound` | mz_compressBound | 0.6693 | 0.0000 | 0.0206 | 0.2500 |
| `mz_inflateInit2` | mz_inflateInit2 | 0.5474 | 0.0233 | 0.1101 | 0.2500 |
| `mz_uncompress` | mz_uncompress | 0.5096 | 0.0476 | 0.0830 | 0.2500 |
| `mz_deflateBound` | mz_deflateBound | 0.4634 | 0.2308 | 0.1617 | 0.2500 |
| `mz_inflateInit` | mz_inflateInit | 0.4630 | 0.0656 | 0.0867 | 0.2500 |
| `mz_inflate` | mz_inflate | 0.3994 | 0.0930 | 0.1060 | 0.2500 |
| `mz_inflateEnd` | mz_inflateEnd | 0.3940 | 0.0308 | 0.0568 | 0.2500 |
| `mz_deflateReset` | mz_deflateReset | 0.3767 | 0.1905 | 0.0638 | 0.2500 |
| `mz_deflateEnd` | mz_deflateEnd | 0.3729 | 0.1818 | 0.1389 | 0.2500 |
| `mz_deflate` | mz_deflate | 0.2744 | 0.1333 | 0.0645 | 0.2500 |
| `mz_compress` | mz_compress | 0.1670 | 0.1429 | 0.0296 | 0.2500 |
| `mz_deflateInit` | mz_deflateInit | 0.1209 | 0.0000 | 0.0806 | 0.2500 |
| `mz_deflateInit2` | mz_deflateInit2 | 0.0895 | 0.0000 | 0.0276 | 0.2500 |

---

## 4. Interpretazione e Limiti

- **Documented Coverage del 66.7%**: CodeWiki documenta a livello di modulo,
  non per singola funzione. Le funzioni non coperte, per classe, sono:
  `(free functions)` (4).
  Altre 3 funzioni compaiono solo come firma nei diagrammi Mermaid, senza testo descrittivo.

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