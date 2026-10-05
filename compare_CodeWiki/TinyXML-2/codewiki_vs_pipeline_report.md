# Confronto: Pipeline della tesi vs CodeWiki (TinyXML-2)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 51 (valutate da entrambi i sistemi) su 51 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json`, `results\benchmark_tinyxml-2\run_20261003_132708_multiagent\eval_report_multiagent.json`  

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 51 | 0.5969 | 0.5502 | 0.0467 | 0.0439 |
| BERTScore F1 | 51 | 0.5843 | 0.5783 | 0.0060 | 0.1958 |
| METEOR | 51 | 0.3013 | 0.2607 | 0.0406 | 0.1038 |
| TF-IDF cosine | 51 | 0.4507 | 0.3034 | 0.1473 | 0.0004 |
| ROUGE-L | 51 | 0.1601 | 0.2216 | -0.0615 | 0.3409 |
| Concept checklist | 51 | 0.8987 | 0.6863 | 0.2124 | 0.0011 |
| Actionability | 51 | 0.9588 | 0.4382 | 0.5206 | 0.0000 |
| Error doc. rate | 12 | 1.0000 | 0.0000 | 1.0000 | 0.0005 |
| Edge case coverage | 7 | 0.7143 | 0.0000 | 0.7143 | 0.0625 |
| Length ratio | 51 | 9.5408 | 1.0964 | 8.4444 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 51 | 0.7689 | 0.7729 | -0.0040 | 0.9142 |
| Retrieval MRR | 51 | 0.6574 | 0.4153 | 0.2421 | 0.0002 |
| Retrieval Hit@1 | 51 | 0.4902 | 0.2745 | 0.2157 | 0.0076 |
| Retrieval Hit@5 | 51 | 0.9020 | 0.5294 | 0.3725 | 0.0000 |
| Judge A - Faithfulness | 50 | 4.2520 | 3.3020 | 0.9500 | 0.0000 |
| Judge B - Alignment | 50 | 4.6760 | 2.4400 | 2.2360 | 0.0000 |
| Judge combinato | 50 | 4.4640 | 2.8710 | 1.5930 | 0.0000 |
| Round-trip pass rate (%) | 51 | 61.3471 | 64.9824 | -3.6353 | 0.5705 |
| Dual agreement (%) | 51 | 36.7961 | 38.1431 | -1.3471 | 0.8903 |

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
| `XMLElement::BoolAttribute` | 0.7331 | 0.5244 | `results\benchmark_tinyxml-2\run_20261003_132708_multiagent\eval_report_multiagent.json` |
| `XMLElement::DeleteAttribute` | 0.4249 | 0.7912 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::DoubleAttribute` | 0.7332 | 0.5456 | `results\benchmark_tinyxml-2\run_20261003_132708_multiagent\eval_report_multiagent.json` |
| `XMLElement::FindAttribute` | 0.5241 | 0.4301 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::FirstAttribute` | 0.4551 | 0.3761 | `results\benchmark_tinyxml-2\run_20261001_180647_multiagent\eval_report_multiagent.json` |
| `XMLElement::FloatAttribute` | 0.7351 | 0.5540 | `results\benchmark_tinyxml-2\run_20261003_132708_multiagent\eval_report_multiagent.json` |
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
| `XMLElement::UnsignedAttribute` | 0.7577 | 0.5584 | `results\benchmark_tinyxml-2\run_20261003_132708_multiagent\eval_report_multiagent.json` |
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
| `XMLElement::BoolAttribute` | 0.0 (6) | 0.0 (8) | 0.0 | 0.0 | pipeline: sintesi vuota, test falliscono sul reference; CodeWiki: sintesi vuota |
| `XMLElement::DeleteAttribute` | 33.3 (6) | 75.0 (4) | 33.3 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLElement::DoubleAttribute` | 100.0 (7) | 100.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::FindAttribute` | 100.0 (7) | 85.7 (7) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `XMLElement::FirstAttribute` | 20.0 (5) | 20.0 (5) | 20.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `XMLElement::FloatAttribute` | 100.0 (7) | 100.0 (7) | 28.6 | 28.6 | - |
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
| `XMLElement::UnsignedAttribute` | 100.0 (9) | 100.0 (7) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
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

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 24, CodeWiki 25.

### Medie escludendo le funzioni senza test eseguiti

Sulle 51 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 61.3 | 65.0 | 0.5705 |
| Dual agreement (%) | 36.8 | 38.1 | 0.8903 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| Missing Symbol / Environment | 54 | 51.9 | 61 | 65.6 |
| Behavioral / Contract Failure | 29 | 27.9 | 30 | 32.3 |
| Other Execution Error | 10 | 9.6 | 2 | 2.2 |
| Interface / Signature Mismatch | 11 | 10.6 | 0 | 0.0 |
| **Totale** | **104** | | **93** | |

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
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 0.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*