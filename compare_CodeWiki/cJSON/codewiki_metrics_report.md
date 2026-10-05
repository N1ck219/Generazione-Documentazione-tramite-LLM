# Valutazione Metriche: CodeWiki vs Ground Truth (cJSON)

> **Script**: `utils/evaluate_codewiki_metrics.py`  
> **Libreria target**: cJSON  
> **Funzioni uniche nel DB**: 88 (154 righe, varianti header/implementazione)  
> **Menzioni di metodi in CodeWiki**: 57  
> **Funzioni DB con testo CodeWiki valutato**: 20 (22.7% del DB)  

---

## 1. Copertura API

| Metrica | Valore |
|---------|--------|
| Funzioni uniche DB cJSON | 88 |
| Menzioni di metodi nei Markdown CodeWiki | 57 |
| Menzioni senza corrispondenza nel DB | 11 |
| Funzioni DB menzionate (testo o diagramma Mermaid) | 42 |
| └── di cui solo nel diagramma Mermaid (senza testo) | 22 |
| **Documented Coverage** (funzioni con testo descrittivo) | **22.7%** (20/88) |
| Mention Coverage | 47.7% (42/88) |
| Funzioni DB non coperte | 46 |

Strategie di matching (per menzione): `exact`=46, `none`=11.

---

## 2. Metriche di Qualita' della Documentazione

*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n=20)*

| Metrica | n | Media | Std | Min | Max |
|---------|---|-------|-----|-----|-----|
| SBERT Cosine Similarity | 20 | 0.3713 | 0.1974 | 0.0688 | 0.8466 |
| BERTScore F1 | 20 | 0.4954 | 0.0782 | 0.3607 | 0.6708 |
| ROUGE-L | 20 | 0.0684 | 0.0774 | 0.0000 | 0.2500 |
| TF-IDF Cosine | 20 | 0.0845 | 0.0921 | 0.0000 | 0.2649 |
| METEOR | 20 | 0.1305 | 0.0744 | 0.0000 | 0.3074 |
| Semantic Concept Checklist | 20 | 0.9000 | 0.3000 | 0.0000 | 1.0000 |
| Actionability Score | 20 | 0.2750 | 0.0750 | 0.2500 | 0.5000 |
| Error Documentation Rate | 13 | 0.2308 | 0.4213 | 0.0000 | 1.0000 |
| Edge Case Coverage | 15 | 0.1333 | 0.3399 | 0.0000 | 1.0000 |
| Length Ratio (CodeWiki/GT) | 20 | 2.6553 | 1.9743 | 0.2250 | 7.0000 |

---

## 3. Distribuzione SBERT per Funzione

*(Tutte le 20 funzioni valutate, ordinate per SBERT decrescente)*

| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |
|-------------|-------------------|-------|---------|--------|---------------|
| `cJSON_Parse` | cJSON_Parse | 0.8466 | 0.2000 | 0.3074 | 0.2500 |
| `cJSON_Delete` | cJSON_Delete | 0.6754 | 0.0000 | 0.1266 | 0.5000 |
| `cJSON_Compare` | cJSON_Compare | 0.6393 | 0.1875 | 0.1314 | 0.2500 |
| `cJSON_Duplicate` | cJSON_Duplicate | 0.5690 | 0.0952 | 0.1515 | 0.2500 |
| `cJSON_Minify` | cJSON_Minify | 0.5688 | 0.1250 | 0.0792 | 0.5000 |
| `parse_value` | parse_value | 0.5168 | 0.0606 | 0.1026 | 0.2500 |
| `print_number` | print_number | 0.3841 | 0.2500 | 0.1271 | 0.2500 |
| `cJSON_PrintPreallocated` | cJSON_PrintPreallocated | 0.3799 | 0.0556 | 0.0521 | 0.2500 |
| `cJSON_ParseWithOpts` | cJSON_ParseWithOpts | 0.3594 | 0.1622 | 0.1970 | 0.2500 |
| `cJSON_PrintBuffered` | cJSON_PrintBuffered | 0.3184 | 0.0690 | 0.0671 | 0.2500 |
| `parse_object` | parse_object | 0.2875 | 0.0870 | 0.1531 | 0.2500 |
| `print_string` | print_string | 0.2857 | 0.0000 | 0.1293 | 0.2500 |
| `cJSON_PrintUnformatted` | cJSON_PrintUnformatted | 0.2843 | 0.0000 | 0.1936 | 0.2500 |
| `print_array` | print_array | 0.2763 | 0.0000 | 0.0000 | 0.2500 |
| `parse_string` | parse_string | 0.2343 | 0.0000 | 0.1530 | 0.2500 |
| `parse_number` | parse_number | 0.2072 | 0.0769 | 0.1381 | 0.2500 |
| `parse_array` | parse_array | 0.1990 | 0.0000 | 0.0962 | 0.2500 |
| `cJSON_Print` | cJSON_Print | 0.1983 | 0.0000 | 0.2937 | 0.2500 |
| `print_object` | print_object | 0.1279 | 0.0000 | 0.0588 | 0.2500 |
| `print_value` | print_value | 0.0688 | 0.0000 | 0.0532 | 0.2500 |

---

## 4. Interpretazione e Limiti

- **Documented Coverage del 22.7%**: CodeWiki documenta a livello di modulo,
  non per singola funzione. Le funzioni non coperte, per classe, sono:
  `(free functions)` (46).
  Altre 22 funzioni compaiono solo come firma nei diagrammi Mermaid, senza testo descrittivo.

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