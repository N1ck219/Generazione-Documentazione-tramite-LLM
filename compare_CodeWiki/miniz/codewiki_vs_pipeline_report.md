# Confronto: Pipeline della tesi vs CodeWiki (miniz)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 14 (valutate da entrambi i sistemi) su 14 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json`, `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json`  

> ⚠️ **Campione ridotto (n=14)**: le differenze non sono statisticamente affidabili.
> Per un confronto completo eseguire la pipeline sulle stesse funzioni di CodeWiki:
> `.venv/Scripts/python utils/benchmark_eval.py -l miniz -m multiagent --functions compare_CodeWiki/miniz/codewiki_function_list.txt`

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 14 | 0.4421 | 0.3961 | 0.0460 | 0.4263 |
| BERTScore F1 | 14 | 0.5176 | 0.4825 | 0.0351 | 0.0676 |
| METEOR | 14 | 0.1664 | 0.0852 | 0.0811 | 0.0002 |
| TF-IDF cosine | 14 | 0.1811 | 0.1208 | 0.0603 | 0.0640 |
| ROUGE-L | 14 | 0.0876 | 0.0867 | 0.0009 | 0.9375 |
| Concept checklist | 14 | 0.7857 | 0.7143 | 0.0714 | 0.3173 |
| Actionability | 14 | 0.9250 | 0.2500 | 0.6750 | 0.0007 |
| Error doc. rate | 8 | 0.8750 | 0.1250 | 0.7500 | 0.0703 |
| Edge case coverage | 9 | 0.6667 | 0.0000 | 0.6667 | 0.0312 |
| Length ratio | 14 | 6.9786 | 4.6758 | 2.3028 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 14 | 0.6004 | 0.7101 | -0.1096 | 0.4631 |
| Retrieval MRR | 14 | 0.5420 | 0.3734 | 0.1686 | 0.1307 |
| Retrieval Hit@1 | 14 | 0.3571 | 0.2143 | 0.1429 | 0.3173 |
| Retrieval Hit@5 | 14 | 0.9286 | 0.5714 | 0.3571 | 0.0253 |
| Judge A - Faithfulness | 14 | 4.5000 | 3.5429 | 0.9571 | 0.0014 |
| Judge B - Alignment | 14 | 4.4857 | 3.2571 | 1.2286 | 0.0018 |
| Judge combinato | 14 | 4.4929 | 3.4000 | 1.0929 | 0.0010 |
| Round-trip pass rate (%) | 14 | 76.4000 | 81.7143 | -5.3143 | 0.9527 |
| Dual agreement (%) | 14 | 51.5571 | 54.1357 | -2.5786 | 0.6784 |

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 12.3814 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `mz_compress` | 0.3114 | 0.1670 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_compressBound` | 0.7334 | 0.6693 | `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json` |
| `mz_deflate` | 0.0972 | 0.2744 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_deflateBound` | 0.6713 | 0.4634 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_deflateEnd` | 0.3042 | 0.3729 | `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json` |
| `mz_deflateInit` | 0.3207 | 0.1209 | `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json` |
| `mz_deflateInit2` | 0.0899 | 0.0895 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_deflateReset` | 0.7558 | 0.3767 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `mz_inflate` | 0.5211 | 0.3994 | `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json` |
| `mz_inflateEnd` | 0.5613 | 0.3940 | `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json` |
| `mz_inflateInit` | 0.5565 | 0.4630 | `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json` |
| `mz_inflateInit2` | 0.4010 | 0.5474 | `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json` |
| `mz_inflateReset` | 0.5778 | 0.6974 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `mz_uncompress` | 0.2876 | 0.5096 | `results\benchmark_miniz\run_20261003_110923_multiagent\eval_report_multiagent.json` |

## Round-trip: dettaglio per funzione

| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |
|----------|-----------------------|------------------------|---------------|---------------|----------|
| `mz_compress` | 100.0 (5) | 80.0 (5) | 100.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `mz_compressBound` | 100.0 (5) | 100.0 (6) | 100.0 | 100.0 | - |
| `mz_deflate` | 0.0 (1) | 75.0 (4) | 0.0 | 75.0 | pipeline: test falliscono sul reference |
| `mz_deflateBound` | 100.0 (5) | 100.0 (5) | 100.0 | 100.0 | - |
| `mz_deflateEnd` | 100.0 (5) | 100.0 (4) | 100.0 | 100.0 | - |
| `mz_deflateInit` | 12.5 (8) | 100.0 (7) | 12.5 | 14.3 | - |
| `mz_deflateInit2` | 57.1 (7) | 85.7 (7) | 14.3 | 28.6 | - |
| `mz_deflateReset` | 100.0 (6) | 100.0 (5) | 66.7 | 80.0 | - |
| `mz_inflate` | 75.0 (4) | 60.0 (5) | 75.0 | 20.0 | - |
| `mz_inflateEnd` | 100.0 (5) | 80.0 (5) | 100.0 | 80.0 | - |
| `mz_inflateInit` | 25.0 (4) | 20.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference |
| `mz_inflateInit2` | 100.0 (5) | 60.0 (5) | 20.0 | 60.0 | - |
| `mz_inflateReset` | 100.0 (6) | 100.0 (6) | 33.3 | 33.3 | - |
| `mz_uncompress` | 100.0 (5) | 83.3 (6) | 0.0 | 66.7 | pipeline: test falliscono sul reference |

### Funzioni senza test eseguiti

Nessuna: tutte le funzioni hanno eseguito almeno un test in entrambi i sistemi.

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 3, CodeWiki 1.

### Medie escludendo le funzioni senza test eseguiti

Sulle 14 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 76.4 | 81.7 | 0.9527 |
| Dual agreement (%) | 51.6 | 54.1 | 0.6784 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| Missing Symbol / Environment | 13 | 92.9 | 4 | 30.8 |
| Behavioral / Contract Failure | 1 | 7.1 | 8 | 61.5 |
| Interface / Signature Mismatch | 0 | 0.0 | 1 | 7.7 |
| **Totale** | **14** | | **13** | |

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
  Retrieval: stesso corpus miniz della pipeline; query = testo della documentazione.
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 0.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*