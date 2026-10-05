# Confronto: Pipeline della tesi vs CodeWiki (OpenCV)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 8 (valutate da entrambi i sistemi) su 8 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_all\run_20260916_152453_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json`, `results\benchmark_opencv\run_20261003_103957_multiagent\eval_report_multiagent.json`  

> ⚠️ **Campione ridotto (n=8)**: le differenze non sono statisticamente affidabili.
> Per un confronto completo eseguire la pipeline sulle stesse funzioni di CodeWiki:
> `.venv/Scripts/python utils/benchmark_eval.py -l OpenCV -m multiagent --functions compare_CodeWiki/OpenCV/codewiki_function_list.txt`

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 8 | 0.6151 | 0.5446 | 0.0706 | 0.1484 |
| BERTScore F1 | 8 | 0.6203 | 0.6008 | 0.0195 | 0.4609 |
| METEOR | 8 | 0.2900 | 0.2067 | 0.0832 | 0.0156 |
| TF-IDF cosine | 8 | 0.5668 | 0.3961 | 0.1707 | 0.0078 |
| ROUGE-L | 8 | 0.2777 | 0.2799 | -0.0022 | 0.2969 |
| Concept checklist | 8 | 0.5625 | 0.5000 | 0.0625 | 1.0000 |
| Actionability | 8 | 0.9062 | 0.2812 | 0.6250 | 0.0078 |
| Error doc. rate | 0 | N/A | N/A | N/A | N/A |
| Edge case coverage | 2 | 0.5000 | 0.5000 | 0.0000 | n<6 |
| Length ratio | 8 | 1.5880 | 0.7712 | 0.8168 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 8 | 0.7139 | 0.7572 | -0.0434 | 0.8438 |
| Retrieval MRR | 8 | 0.5729 | 0.5625 | 0.0104 | 0.8125 |
| Retrieval Hit@1 | 8 | 0.3750 | 0.3750 | 0.0000 | 1.0000 |
| Retrieval Hit@5 | 8 | 1.0000 | 0.7500 | 0.2500 | 0.5000 |
| Judge A - Faithfulness | 8 | 4.3000 | 3.4500 | 0.8500 | 0.0234 |
| Judge B - Alignment | 8 | 3.9250 | 3.4750 | 0.4500 | 0.3438 |
| Judge combinato | 8 | 4.1125 | 3.4625 | 0.6500 | 0.0391 |
| Round-trip pass rate (%) | 8 | 83.4375 | 97.5000 | -14.0625 | 0.5000 |
| Dual agreement (%) | 8 | 59.5500 | 77.5000 | -17.9500 | 0.6250 |

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 0.0000 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `cvCeil` | 0.6366 | 0.6619 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `cvFloor` | 0.6231 | 0.6349 | `results\benchmark_opencv\run_20261003_103957_multiagent\eval_report_multiagent.json` |
| `cvIsInf` | 0.5130 | 0.5238 | `results\benchmark_opencv\run_20261003_103957_multiagent\eval_report_multiagent.json` |
| `cvIsNaN` | 0.4393 | 0.3814 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `cvRound` | 0.5843 | 0.5624 | `results\benchmark_opencv\run_20261003_103957_multiagent\eval_report_multiagent.json` |
| `fastFree` | 0.7869 | 0.4683 | `results\benchmark_all\run_20260916_152453_multiagent\eval_report_multiagent.json` |
| `fastMalloc` | 0.7486 | 0.6228 | `results\benchmark_opencv\run_20261003_103957_multiagent\eval_report_multiagent.json` |
| `saturate_cast` | 0.5892 | 0.5011 | `results\benchmark_opencv\run_20261003_103957_multiagent\eval_report_multiagent.json` |

## Round-trip: dettaglio per funzione

| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |
|----------|-----------------------|------------------------|---------------|---------------|----------|
| `cvCeil` | 87.5 (8) | 100.0 (5) | 87.5 | 100.0 | CodeWiki: sintesi vuota |
| `cvFloor` | 100.0 (8) | 80.0 (5) | 100.0 | 80.0 | - |
| `cvIsInf` | 100.0 (6) | 100.0 (6) | 100.0 | 100.0 | - |
| `cvIsNaN` | 100.0 (9) | 100.0 (5) | 88.9 | 60.0 | - |
| `cvRound` | 100.0 (6) | 100.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `fastFree` | 80.0 (5) | 100.0 (4) | 0.0 | 100.0 | pipeline: test falliscono sul reference |
| `fastMalloc` | 100.0 (5) | 100.0 (6) | 100.0 | 100.0 | - |
| `saturate_cast` | 0.0 (8) | 100.0 (5) | 0.0 | 80.0 | pipeline: test falliscono sul reference |

### Funzioni senza test eseguiti

Nessuna: tutte le funzioni hanno eseguito almeno un test in entrambi i sistemi.

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 3, CodeWiki 1.

### Medie escludendo le funzioni senza test eseguiti

Sulle 8 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 83.4 | 97.5 | 0.5000 |
| Dual agreement (%) | 59.5 | 77.5 | 0.6250 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| Missing Symbol / Environment | 7 | 70.0 | 0 | 0.0 |
| Interface / Signature Mismatch | 2 | 20.0 | 0 | 0.0 |
| Behavioral / Contract Failure | 1 | 10.0 | 1 | 100.0 |
| **Totale** | **10** | | **1** | |

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
  Retrieval: stesso corpus OpenCV della pipeline; query = testo della documentazione.
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 0.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*