# Confronto: Pipeline della tesi vs CodeWiki (TinyXML-2)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 47 (valutate da entrambi i sistemi) su 51 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json`  

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 47 | 0.5847 | 0.5506 | 0.0341 | 0.1244 |
| BERTScore F1 | 47 | 0.5813 | 0.5813 | 0.0000 | 0.4091 |
| BLEURT (stima) | 47 | 0.5177 | 0.4795 | 0.0382 | 0.1271 |
| METEOR | 47 | 0.3693 | 0.3905 | -0.0212 | 0.8135 |
| TF-IDF cosine | 47 | 0.4424 | 0.2983 | 0.1440 | 0.0011 |
| ROUGE-L | 47 | 0.1539 | 0.2304 | -0.0766 | 0.1473 |
| Concept checklist | 47 | 0.9326 | 0.7447 | 0.1879 | 0.0030 |
| Actionability | 47 | 0.8362 | 0.5181 | 0.3181 | 0.0000 |
| Error doc. rate | 12 | 1.0000 | 0.0000 | 1.0000 | 0.0005 |
| Edge case coverage | 7 | 0.7143 | 0.0000 | 0.7143 | 0.0625 |
| Length ratio | 47 | 10.1805 | 1.1654 | 9.0151 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 47 | 0.7690 | 0.7745 | -0.0054 | 0.7710 |
| Retrieval MRR | 47 | 0.6496 | 0.4429 | 0.2066 | 0.0010 |
| Retrieval Hit@1 | 47 | 0.4894 | 0.2979 | 0.1915 | 0.0201 |
| Retrieval Hit@5 | 47 | 0.8936 | 0.5745 | 0.3191 | 0.0003 |
| Judge A - Faithfulness | 47 | 4.2511 | 3.3128 | 0.9383 | 0.0000 |
| Judge B - Alignment | 47 | 4.6553 | 2.4681 | 2.1872 | 0.0000 |
| Judge combinato | 47 | 4.4532 | 2.8904 | 1.5628 | 0.0000 |
| Round-trip pass rate (%) | 47 | 60.1851 | 64.1298 | -3.9447 | 0.5705 |
| Dual agreement (%) | 47 | 39.3191 | 40.7809 | -1.4617 | 0.8903 |

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 0.0000 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `XMLAttribute::BoolValue` | 0.5270 | 0.3764 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::DoubleValue` | 0.5103 | 0.4139 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::FloatValue` | 0.6529 | 0.4341 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::GetLineNum` | 0.7119 | 0.8410 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::IntValue` | 0.6183 | 0.5141 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::Name` | 0.4271 | 0.7455 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::Next` | 0.5518 | 0.6659 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::SetAttribute` | 0.4092 | 0.6825 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::UnsignedValue` | 0.6133 | 0.4442 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLAttribute::Value` | 0.4846 | 0.7225 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::Attribute` | 0.5528 | 0.3622 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::DeleteAttribute` | 0.4249 | 0.7912 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::FindAttribute` | 0.5241 | 0.4301 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::FirstAttribute` | 0.4551 | 0.3761 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::GetText` | 0.5826 | 0.4976 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::InsertNewChildElement` | 0.7853 | 0.5731 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::InsertNewComment` | 0.3002 | 0.2860 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::InsertNewDeclaration` | 0.3415 | 0.2860 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::InsertNewText` | 0.3490 | 0.2860 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::InsertNewUnknown` | 0.3319 | 0.2860 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::IntAttribute` | 0.7655 | 0.5478 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::Name` | 0.6303 | 0.5562 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::SetAttribute` | 0.5257 | 0.5242 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::SetName` | 0.4410 | 0.8555 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::SetText` | 0.4878 | 0.7197 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::DeepClone` | 0.7254 | 0.5724 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::DeleteChild` | 0.6029 | 0.7166 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::DeleteChildren` | 0.6071 | 0.7193 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::FirstChild` | 0.6523 | 0.3949 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::FirstChildElement` | 0.5526 | 0.5758 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::GetDocument` | 0.6973 | 0.7191 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::InsertAfterChild` | 0.7108 | 0.6577 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::InsertEndChild` | 0.7429 | 0.5935 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::InsertFirstChild` | 0.6609 | 0.5900 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::LastChild` | 0.6837 | 0.4074 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::LastChildElement` | 0.6539 | 0.5223 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::NextSibling` | 0.6687 | 0.3807 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::NextSiblingElement` | 0.7278 | 0.5428 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::Parent` | 0.6178 | 0.5594 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::PreviousSibling` | 0.6942 | 0.3783 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::PreviousSiblingElement` | 0.7270 | 0.5182 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::SetValue` | 0.4340 | 0.4624 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::ShallowClone` | 0.7524 | 0.5841 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::ShallowEqual` | 0.7320 | 0.5298 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLNode::Value` | 0.4811 | 0.4506 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLText::CData` | 0.6895 | 0.9239 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLText::SetCData` | 0.6646 | 0.8625 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |

## Round-trip: dettaglio per funzione

| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |
|----------|-----------------------|------------------------|---------------|---------------|----------|
| `XMLAttribute::BoolValue` | 75.0 (8) | 0.0 (7) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLAttribute::DoubleValue` | 100.0 (8) | 100.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLAttribute::FloatValue` | 100.0 (7) | 100.0 (7) | 100.0 | 100.0 | - |
| `XMLAttribute::GetLineNum` | 100.0 (3) | 100.0 (4) | 100.0 | 100.0 | - |
| `XMLAttribute::IntValue` | 100.0 (7) | 50.0 (8) | 100.0 | 50.0 | - |
| `XMLAttribute::Name` | 100.0 (5) | 100.0 (4) | 0.0 | 100.0 | pipeline: test falliscono sul reference |
| `XMLAttribute::Next` | 100.0 (4) | 100.0 (5) | 100.0 | 100.0 | - |
| `XMLAttribute::SetAttribute` | 100.0 (5) | 0.0 (6) | 100.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLAttribute::UnsignedValue` | 100.0 (8) | 0.0 (6) | 100.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLAttribute::Value` | 100.0 (4) | 100.0 (5) | 100.0 | 100.0 | - |
| `XMLElement::Attribute` | 100.0 (6) | 100.0 (7) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::DeleteAttribute` | 33.3 (6) | 75.0 (4) | 33.3 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLElement::FindAttribute` | 100.0 (7) | 85.7 (7) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::FirstAttribute` | 20.0 (5) | 20.0 (5) | 20.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLElement::GetText` | 20.0 (5) | 100.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::InsertNewChildElement` | 57.1 (7) | 0.0 (6) | 57.1 | 0.0 | - |
| `XMLElement::InsertNewComment` | 0.0 (5) | 0.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::InsertNewDeclaration` | 0.0 (5) | 100.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::InsertNewText` | 0.0 (5) | 0.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::InsertNewUnknown` | 0.0 (5) | 20.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::IntAttribute` | 100.0 (7) | 100.0 (7) | 14.3 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLElement::Name` | 100.0 (5) | 100.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::SetAttribute` | 100.0 (7) | 16.7 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::SetName` | 0.0 (6) | 0.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::SetText` | 0.0 (1) | 0.0 (1) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLNode::DeepClone` | 50.0 (2) | 16.7 (6) | 50.0 | 16.7 | - |
| `XMLNode::DeleteChild` | 100.0 (4) | 100.0 (5) | 100.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLNode::DeleteChildren` | 20.0 (5) | 100.0 (3) | 20.0 | 100.0 | - |
| `XMLNode::FirstChild` | 100.0 (4) | 100.0 (5) | 100.0 | 100.0 | - |
| `XMLNode::FirstChildElement` | 100.0 (4) | 100.0 (5) | 100.0 | 100.0 | - |
| `XMLNode::GetDocument` | 0.0 (5) | 20.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLNode::InsertAfterChild` | 0.0 (7) | 0.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLNode::InsertEndChild` | 0.0 (6) | 100.0 (5) | 0.0 | 60.0 | - |
| `XMLNode::InsertFirstChild` | 83.3 (6) | 100.0 (5) | 83.3 | 80.0 | - |
| `XMLNode::LastChild` | 100.0 (5) | 100.0 (4) | 100.0 | 100.0 | - |
| `XMLNode::LastChildElement` | 0.0 (7) | 100.0 (5) | 0.0 | 100.0 | pipeline: test falliscono sul reference |
| `XMLNode::NextSibling` | 60.0 (5) | 100.0 (4) | 60.0 | 100.0 | - |
| `XMLNode::NextSiblingElement` | 0.0 (6) | 100.0 (4) | 0.0 | 100.0 | pipeline: test falliscono sul reference |
| `XMLNode::Parent` | 60.0 (5) | 50.0 (6) | 60.0 | 50.0 | - |
| `XMLNode::PreviousSibling` | 100.0 (4) | 100.0 (4) | 100.0 | 100.0 | - |
| `XMLNode::PreviousSiblingElement` | 100.0 (4) | 0.0 (1) | 100.0 | 0.0 | - |
| `XMLNode::SetValue` | 33.3 (6) | 0.0 (6) | 33.3 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLNode::ShallowClone` | 100.0 (5) | 100.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLNode::ShallowEqual` | 100.0 (5) | 100.0 (5) | 0.0 | 100.0 | pipeline: test falliscono sul reference |
| `XMLNode::Value` | 16.7 (6) | 100.0 (4) | 16.7 | 100.0 | - |
| `XMLText::CData` | 100.0 (4) | 60.0 (5) | 100.0 | 60.0 | - |
| `XMLText::SetCData` | 0.0 (5) | 100.0 (4) | 0.0 | 100.0 | pipeline: test falliscono sul reference |

### Funzioni senza test eseguiti

Nessuna: tutte le funzioni hanno eseguito almeno un test in entrambi i sistemi.

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 21, CodeWiki 23.

### Medie escludendo le funzioni senza test eseguiti

Sulle 47 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 60.2 | 64.1 | 0.5705 |
| Dual agreement (%) | 39.3 | 40.8 | 0.8903 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| Missing Symbol / Environment | 54 | 55.1 | 61 | 71.8 |
| Behavioral / Contract Failure | 24 | 24.5 | 22 | 25.9 |
| Interface / Signature Mismatch | 11 | 11.2 | 0 | 0.0 |
| Other Execution Error | 9 | 9.2 | 2 | 2.4 |
| **Totale** | **98** | | **85** | |

## Note metodologiche

- Le metriche semantiche della pipeline sono quelle salvate nei suoi report (stesse funzioni
  di `utils/benchmark_metrics.py`, calcolate su `@brief` + `@details` vs GT); per CodeWiki
  il candidato e' il testo dei bullet Markdown associati alla funzione.
- EDR ed ECC sono ricalcolate per entrambi i sistemi sullo stesso codice (file di
  implementazione se presente) e considerate solo dove il codice contiene rami di errore / guardie.
- Il test di Wilcoxon (appaiato, a due code) e' riportato solo per n >= 6.
- Judge e round-trip CodeWiki usano la stessa configurazione della pipeline
  (gemini-3.5-flash-lite, judge T=0.4 con 5 round per prospettiva, `RoundTripEvaluator`),
  le stesse righe del DB (firma, codice, GT) e come documentazione il testo CodeWiki.
  Retrieval: stesso corpus TinyXML-2 della pipeline; query = testo della documentazione.
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 4.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*