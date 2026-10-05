# Valutazione Metriche: CodeWiki vs Ground Truth (http-parser)

> **Script**: `utils/evaluate_codewiki_metrics.py`  
> **Libreria target**: http-parser  
> **Funzioni uniche nel DB**: 15 (28 righe, varianti header/implementazione)  
> **Menzioni di metodi in CodeWiki**: 9  
> **Funzioni DB con testo CodeWiki valutato**: 9 (60.0% del DB)  

---

## 1. Copertura API

| Metrica | Valore |
|---------|--------|
| Funzioni uniche DB http-parser | 15 |
| Menzioni di metodi nei Markdown CodeWiki | 9 |
| Menzioni senza corrispondenza nel DB | 0 |
| Funzioni DB menzionate (testo o diagramma Mermaid) | 9 |
| └── di cui solo nel diagramma Mermaid (senza testo) | 0 |
| **Documented Coverage** (funzioni con testo descrittivo) | **60.0%** (9/15) |
| Mention Coverage | 60.0% (9/15) |
| Funzioni DB non coperte | 6 |

Strategie di matching (per menzione): `exact`=9.

---

## 2. Metriche di Qualita' della Documentazione

*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n=9)*

| Metrica | n | Media | Std | Min | Max |
|---------|---|-------|-----|-----|-----|
| SBERT Cosine Similarity | 9 | 0.6948 | 0.0709 | 0.5785 | 0.8061 |
| BERTScore F1 | 9 | 0.6791 | 0.1223 | 0.4519 | 0.8293 |
| ROUGE-L | 9 | 0.4269 | 0.2135 | 0.1739 | 0.7692 |
| TF-IDF Cosine | 9 | 0.5096 | 0.1458 | 0.3381 | 0.7715 |
| METEOR | 9 | 0.4165 | 0.2020 | 0.0375 | 0.6347 |
| Semantic Concept Checklist | 9 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| Actionability Score | 9 | 0.3444 | 0.1363 | 0.2500 | 0.6000 |
| Error Documentation Rate | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Edge Case Coverage | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Length Ratio (CodeWiki/GT) | 9 | 0.7792 | 0.3655 | 0.0880 | 1.1250 |

---

## 3. Distribuzione SBERT per Funzione

*(Tutte le 9 funzioni valutate, ordinate per SBERT decrescente)*

| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |
|-------------|-------------------|-------|---------|--------|---------------|
| `http_status_str` | http_status_str | 0.8061 | 0.7692 | 0.6250 | 0.2500 |
| `http_parser_pause` | http_parser_pause | 0.7896 | 0.2222 | 0.3288 | 0.5000 |
| `http_method_str` | http_method_str | 0.7488 | 0.7273 | 0.5270 | 0.2500 |
| `http_parser_set_max_header_size` | http_parser_set_max_header_size | 0.6951 | 0.4286 | 0.6347 | 0.5000 |
| `http_should_keep_alive` | http_should_keep_alive | 0.6867 | 0.1875 | 0.1149 | 0.2500 |
| `http_parser_version` | http_parser_version | 0.6772 | 0.1739 | 0.0375 | 0.6000 |
| `http_errno_name` | http_errno_name | 0.6365 | 0.4000 | 0.4593 | 0.2500 |
| `http_body_is_final` | http_body_is_final | 0.6343 | 0.6000 | 0.4777 | 0.2500 |
| `http_errno_description` | http_errno_description | 0.5785 | 0.3333 | 0.5439 | 0.2500 |

---

## 4. Interpretazione e Limiti

- **Documented Coverage del 60.0%**: CodeWiki documenta a livello di modulo,
  non per singola funzione. Le funzioni non coperte, per classe, sono:
  `(free functions)` (6).
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