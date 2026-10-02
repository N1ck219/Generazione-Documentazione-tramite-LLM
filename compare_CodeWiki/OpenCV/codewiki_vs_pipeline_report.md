# Confronto: Pipeline della tesi vs CodeWiki (OpenCV)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 8 (valutate da entrambi i sistemi) su 8 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_all\run_20260916_152453_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json`, `results\benchmark_opencv\run_20261002_143830_multiagent\eval_report_multiagent.json`  

> ⚠️ **Campione ridotto (n=8)**: le differenze non sono statisticamente affidabili.
> Per un confronto completo eseguire la pipeline sulle stesse funzioni di CodeWiki:
> `.venv/Scripts/python utils/benchmark_eval.py -l OpenCV -m multiagent --functions compare_CodeWiki/OpenCV/codewiki_function_list.txt`

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 8 | 0.6242 | 0.5446 | 0.0796 | 0.0781 |
| BERTScore F1 | 8 | 0.6227 | 0.6008 | 0.0219 | 0.4688 |
| BLEURT (stima) | 8 | 0.5676 | 0.4853 | 0.0823 | 0.0391 |
| METEOR | 8 | 0.4533 | 0.4122 | 0.0411 | 0.4609 |
| TF-IDF cosine | 8 | 0.5520 | 0.3961 | 0.1559 | 0.0078 |
| ROUGE-L | 8 | 0.2823 | 0.2799 | 0.0025 | 0.5469 |
| Concept checklist | 8 | 0.5625 | 0.5000 | 0.0625 | 1.0000 |
| Actionability | 8 | 0.8375 | 0.2500 | 0.5875 | 0.0078 |
| Error doc. rate | 0 | N/A | N/A | N/A | N/A |
| Edge case coverage | 2 | 0.5000 | 0.5000 | 0.0000 | n<6 |
| Length ratio | 8 | 1.5813 | 0.7712 | 0.8100 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 8 | 0.7111 | 0.7572 | -0.0462 | 0.6406 |
| Retrieval MRR | 8 | 0.5729 | 0.5625 | 0.0104 | 0.8125 |
| Retrieval Hit@1 | 8 | 0.3750 | 0.3750 | 0.0000 | 1.0000 |
| Retrieval Hit@5 | 8 | 1.0000 | 0.7500 | 0.2500 | 0.5000 |
| Judge A - Faithfulness | 8 | 4.1750 | 3.4500 | 0.7250 | 0.0781 |
| Judge B - Alignment | 8 | 3.8750 | 3.4750 | 0.4000 | 0.6250 |
| Judge combinato | 8 | 4.0250 | 3.4625 | 0.5625 | 0.1484 |
| Round-trip pass rate (%) | 8 | 70.9375 | 97.5000 | -26.5625 | 0.2500 |
| Dual agreement (%) | 8 | 59.5500 | 77.5000 | -17.9500 | 0.6719 |

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
| `cvFloor` | 0.6497 | 0.6349 | `results\benchmark_opencv\run_20261002_143830_multiagent\eval_report_multiagent.json` |
| `cvIsInf` | 0.4808 | 0.5238 | `results\benchmark_opencv\run_20261002_143830_multiagent\eval_report_multiagent.json` |
| `cvIsNaN` | 0.4393 | 0.3814 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `cvRound` | 0.6200 | 0.5624 | `results\benchmark_opencv\run_20261002_143830_multiagent\eval_report_multiagent.json` |
| `fastFree` | 0.7869 | 0.4683 | `results\benchmark_all\run_20260916_152453_multiagent\eval_report_multiagent.json` |
| `fastMalloc` | 0.7174 | 0.6228 | `results\benchmark_opencv\run_20261002_143830_multiagent\eval_report_multiagent.json` |
| `saturate_cast` | 0.6631 | 0.5011 | `results\benchmark_opencv\run_20261002_143830_multiagent\eval_report_multiagent.json` |

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