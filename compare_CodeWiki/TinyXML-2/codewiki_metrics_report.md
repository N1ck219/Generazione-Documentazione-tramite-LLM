# Valutazione Metriche: CodeWiki vs Ground Truth (TinyXML-2)

> **Script**: `utils/evaluate_codewiki_metrics.py`  
> **Libreria target**: TinyXML-2  
> **Funzioni uniche nel DB**: 140 (216 righe, varianti header/implementazione)  
> **Menzioni di metodi in CodeWiki**: 148  
> **Funzioni DB con testo CodeWiki valutato**: 51 (36.4% del DB)  

---

## 1. Copertura API

| Metrica | Valore |
|---------|--------|
| Funzioni uniche DB TinyXML-2 | 140 |
| Menzioni di metodi nei Markdown CodeWiki | 148 |
| Menzioni senza corrispondenza nel DB | 24 |
| Funzioni DB menzionate (testo o diagramma Mermaid) | 75 |
| └── di cui solo nel diagramma Mermaid (senza testo) | 24 |
| **Documented Coverage** (funzioni con testo descrittivo) | **36.4%** (51/140) |
| Mention Coverage | 53.6% (75/140) |
| Funzioni DB non coperte | 65 |

Strategie di matching (per menzione): `exact`=120, `inherited`=4, `none`=24.

---

## 2. Metriche di Qualita' della Documentazione

*(Solo sulle funzioni DB con testo CodeWiki e Ground Truth, n=51)*

| Metrica | n | Media | Std | Min | Max |
|---------|---|-------|-----|-----|-----|
| SBERT Cosine Similarity | 51 | 0.5502 | 0.1574 | 0.2860 | 0.9239 |
| BERTScore F1 | 51 | 0.5783 | 0.1244 | 0.3497 | 0.8466 |
| ROUGE-L | 51 | 0.2216 | 0.2260 | 0.0000 | 0.8000 |
| TF-IDF Cosine | 51 | 0.3034 | 0.2462 | 0.0000 | 0.9129 |
| METEOR | 51 | 0.3859 | 0.1821 | 0.1430 | 0.8256 |
| BLEURT Estimate | 51 | 0.4727 | 0.1635 | 0.2570 | 0.8575 |
| Semantic Concept Checklist | 51 | 0.6863 | 0.4640 | 0.0000 | 1.0000 |
| Actionability Score | 51 | 0.4971 | 0.2953 | 0.2500 | 0.8500 |
| Error Documentation Rate | 12 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Edge Case Coverage | 7 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Length Ratio (CodeWiki/GT) | 51 | 1.0964 | 1.1353 | 0.0940 | 4.5000 |

---

## 3. Distribuzione SBERT per Funzione

*(Tutte le 51 funzioni valutate, ordinate per SBERT decrescente)*

| Funzione DB | Menzioni CodeWiki | SBERT | ROUGE-L | METEOR | Actionability |
|-------------|-------------------|-------|---------|--------|---------------|
| `XMLText::CData` | XMLText::CData | 0.9239 | 0.7273 | 0.8256 | 0.8500 |
| `XMLText::SetCData` | XMLText::SetCData | 0.8625 | 0.5000 | 0.6813 | 0.2500 |
| `XMLElement::SetName` | XMLElement::SetName | 0.8555 | 0.5714 | 0.7135 | 0.2500 |
| `XMLAttribute::GetLineNum` | XMLAttribute::GetLineNum | 0.8410 | 0.6250 | 0.7330 | 0.8500 |
| `XMLElement::DeleteAttribute` | XMLElement::DeleteAttribute | 0.7912 | 0.4000 | 0.5956 | 0.2500 |
| `XMLAttribute::Name` | XMLAttribute::Name | 0.7455 | 0.8000 | 0.7728 | 0.8500 |
| `XMLAttribute::Value` | XMLAttribute::Value | 0.7225 | 0.6667 | 0.6946 | 0.8500 |
| `XMLElement::SetText` | XMLElement::SetText | 0.7197 | 0.4444 | 0.5820 | 0.2500 |
| `XMLNode::DeleteChildren` | XMLNode::DeleteChildren | 0.7193 | 0.0000 | 0.3597 | 0.8500 |
| `XMLNode::GetDocument` | XMLNode::GetDocument | 0.7191 | 0.4444 | 0.5817 | 0.8500 |
| `XMLNode::DeleteChild` | XMLNode::DeleteChild | 0.7166 | 0.2857 | 0.5011 | 0.2500 |
| `XMLAttribute::SetAttribute` | XMLAttribute::SetAttribute | 0.6825 | 0.6000 | 0.6412 | 0.2500 |
| `XMLAttribute::Next` | XMLAttribute::Next | 0.6659 | 0.6667 | 0.6663 | 0.8500 |
| `XMLNode::InsertAfterChild` | XMLNode::InsertAfterChild | 0.6577 | 0.1000 | 0.3788 | 0.2500 |
| `XMLNode::InsertEndChild` | XMLNode::InsertEndChild | 0.5935 | 0.1176 | 0.3556 | 0.2500 |
| `XMLNode::InsertFirstChild` | XMLNode::InsertFirstChild | 0.5900 | 0.1176 | 0.3538 | 0.2500 |
| `XMLNode::ShallowClone` | XMLNode::ShallowClone | 0.5841 | 0.1333 | 0.3587 | 0.2500 |
| `XMLNode::FirstChildElement` | XMLNode::FirstChildElement | 0.5758 | 0.3158 | 0.4458 | 0.2500 |
| `XMLElement::InsertNewChildElement` | XMLElement::InsertNewChildElement | 0.5731 | 0.2857 | 0.4294 | 0.2500 |
| `XMLNode::DeepClone` | XMLNode::DeepClone | 0.5724 | 0.1455 | 0.3589 | 0.2500 |
| `XMLNode::Parent` | XMLNode::Parent | 0.5594 | 0.2500 | 0.4047 | 0.8500 |
| `XMLElement::UnsignedAttribute` | XMLElement::UnsignedAttribute | 0.5584 | 0.1176 | 0.3380 | 0.2500 |
| `XMLElement::Name` | XMLElement::Name | 0.5562 | 0.4000 | 0.4781 | 0.8500 |
| `XMLElement::FloatAttribute` | XMLElement::FloatAttribute | 0.5540 | 0.1176 | 0.3358 | 0.2500 |
| `XMLElement::IntAttribute` | XMLElement::IntAttribute | 0.5478 | 0.1250 | 0.3364 | 0.2500 |
| `XMLElement::DoubleAttribute` | XMLElement::DoubleAttribute | 0.5456 | 0.1176 | 0.3316 | 0.2500 |
| `XMLNode::NextSiblingElement` | XMLNode::NextSiblingElement | 0.5428 | 0.3333 | 0.4380 | 0.2500 |
| `XMLNode::ShallowEqual` | XMLNode::ShallowEqual | 0.5298 | 0.1379 | 0.3339 | 0.2500 |
| `XMLElement::BoolAttribute` | XMLElement::BoolAttribute | 0.5244 | 0.1176 | 0.3210 | 0.2500 |
| `XMLElement::SetAttribute` | XMLElement::SetAttribute | 0.5242 | 0.1333 | 0.3287 | 0.2500 |
| `XMLNode::LastChildElement` | XMLNode::LastChildElement | 0.5223 | 0.3158 | 0.4191 | 0.2500 |
| `XMLNode::PreviousSiblingElement` | XMLNode::PreviousSiblingElement | 0.5182 | 0.3333 | 0.4257 | 0.2500 |
| `XMLAttribute::IntValue` | XMLAttribute::IntValue | 0.5141 | 0.1379 | 0.3260 | 0.8500 |
| `XMLElement::GetText` | XMLElement::GetText | 0.4976 | 0.1031 | 0.3004 | 0.8500 |
| `XMLNode::SetValue` | XMLNode::SetValue | 0.4624 | 0.2500 | 0.3562 | 0.2500 |
| `XMLNode::Value` | XMLNode::Value | 0.4506 | 0.2778 | 0.3642 | 0.8500 |
| `XMLAttribute::UnsignedValue` | XMLAttribute::UnsignedValue | 0.4442 | 0.0000 | 0.2221 | 0.8500 |
| `XMLAttribute::FloatValue` | XMLAttribute::FloatValue | 0.4341 | 0.0000 | 0.2170 | 0.8500 |
| `XMLElement::FindAttribute` | XMLElement::FindAttribute | 0.4301 | 0.0000 | 0.2150 | 0.2500 |
| `XMLAttribute::DoubleValue` | XMLAttribute::DoubleValue | 0.4139 | 0.0000 | 0.2069 | 0.8500 |
| `XMLNode::LastChild` | XMLNode::LastChild | 0.4074 | 0.0000 | 0.2037 | 0.8500 |
| `XMLNode::FirstChild` | XMLNode::FirstChild | 0.3949 | 0.0000 | 0.1974 | 0.8500 |
| `XMLNode::NextSibling` | XMLNode::NextSibling | 0.3807 | 0.0000 | 0.1903 | 0.8500 |
| `XMLNode::PreviousSibling` | XMLNode::PreviousSibling | 0.3783 | 0.0000 | 0.1892 | 0.8500 |
| `XMLAttribute::BoolValue` | XMLAttribute::BoolValue | 0.3764 | 0.0000 | 0.1882 | 0.8500 |
| `XMLElement::FirstAttribute` | XMLElement::FirstAttribute | 0.3761 | 0.0000 | 0.1880 | 0.8500 |
| `XMLElement::Attribute` | XMLElement::Attribute | 0.3622 | 0.0857 | 0.2240 | 0.2500 |
| `XMLElement::InsertNewComment` | XMLElement::InsertNewComment | 0.2860 | 0.0000 | 0.1430 | 0.2500 |
| `XMLElement::InsertNewText` | XMLElement::InsertNewText | 0.2860 | 0.0000 | 0.1430 | 0.2500 |
| `XMLElement::InsertNewDeclaration` | XMLElement::InsertNewDeclaration | 0.2860 | 0.0000 | 0.1430 | 0.2500 |
| `XMLElement::InsertNewUnknown` | XMLElement::InsertNewUnknown | 0.2860 | 0.0000 | 0.1430 | 0.2500 |

---

## 4. Interpretazione e Limiti

- **Documented Coverage del 36.4%**: CodeWiki documenta a livello di modulo,
  non per singola funzione. Le funzioni non coperte, per classe, sono:
  `XMLElement` (16), `XMLDocument` (13), `XMLHandle` (10), `XMLNode` (10), `XMLUtil` (7), `XMLAttribute` (6), `XMLPrinter` (3).
  Altre 24 funzioni compaiono solo come firma nei diagrammi Mermaid, senza testo descrittivo.

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