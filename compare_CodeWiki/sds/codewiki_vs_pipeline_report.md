# Confronto: Pipeline della tesi vs CodeWiki (sds)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 35 (valutate da entrambi i sistemi) su 35 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260921_175447_multiagent\eval_report_multiagent.json`, `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json`, `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json`, `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json`  

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 35 | 0.7035 | 0.6279 | 0.0756 | 0.0356 |
| BERTScore F1 | 35 | 0.5951 | 0.5914 | 0.0037 | 0.7158 |
| BLEURT (stima) | 35 | 0.5953 | 0.4970 | 0.0982 | 0.0008 |
| METEOR | 35 | 0.4376 | 0.4233 | 0.0143 | 0.5545 |
| TF-IDF cosine | 35 | 0.4437 | 0.3338 | 0.1099 | 0.0008 |
| ROUGE-L | 35 | 0.1717 | 0.2187 | -0.0470 | 0.2776 |
| Concept checklist | 35 | 0.7762 | 0.6286 | 0.1476 | 0.0050 |
| Actionability | 35 | 0.8100 | 0.2671 | 0.5429 | 0.0000 |
| Error doc. rate | 10 | 0.9000 | 0.2000 | 0.7000 | 0.0391 |
| Edge case coverage | 22 | 0.8182 | 0.1591 | 0.6591 | 0.0002 |
| Length ratio | 35 | 3.9491 | 0.5096 | 3.4395 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 35 | 0.7500 | 0.7611 | -0.0111 | 0.2192 |
| Retrieval MRR | 35 | 0.4708 | 0.4901 | -0.0192 | 0.7799 |
| Retrieval Hit@1 | 35 | 0.2857 | 0.4000 | -0.1143 | 0.2059 |
| Retrieval Hit@5 | 35 | 0.6857 | 0.5714 | 0.1143 | 0.2482 |
| Judge A - Faithfulness | 35 | 4.6000 | 3.7143 | 0.8857 | 0.0000 |
| Judge B - Alignment | 35 | 4.5257 | 3.2857 | 1.2400 | 0.0000 |
| Judge combinato | 35 | 4.5629 | 3.5000 | 1.0629 | 0.0000 |
| Round-trip pass rate (%) | 35 | 46.7086 | 50.3800 | -3.6714 | 0.8192 |
| Dual agreement (%) | 35 | 29.2257 | 33.3371 | -4.1114 | 0.3952 |

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 0.0000 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `sdsAllocSize` | 0.8255 | 0.8649 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdsIncrLen` | 0.6963 | 0.7326 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdsMakeRoomFor` | 0.6057 | 0.6808 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `sdsRemoveFreeSpace` | 0.6281 | 0.6976 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdsalloc` | 0.3886 | 0.1984 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdscat` | 0.7502 | 0.8124 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdscatfmt` | 0.6115 | 0.4808 | `results\benchmark_all\run_20260921_175447_multiagent\eval_report_multiagent.json` |
| `sdscatlen` | 0.7216 | 0.7762 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdscatprintf` | 0.6570 | 0.3912 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdscatrepr` | 0.7292 | 0.5111 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `sdscatsds` | 0.7153 | 0.7012 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdscatvprintf` | 0.5370 | 0.3796 | `results\benchmark_sds\run_20261003_120009_multiagent\eval_report_multiagent.json` |
| `sdsclear` | 0.7118 | 0.6417 | `results\benchmark_all\run_20260921_175447_multiagent\eval_report_multiagent.json` |
| `sdscmp` | 0.9122 | 0.7498 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdscpy` | 0.7586 | 0.6612 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdscpylen` | 0.7321 | 0.8477 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdsdup` | 0.7414 | 0.9165 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdsempty` | 0.7339 | 0.6791 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdsfree` | 0.7189 | 0.7131 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdsfreesplitres` | 0.5094 | 0.1007 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdsfromlonglong` | 0.7148 | 0.7385 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdsgrowzero` | 0.7250 | 0.7709 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `sdsjoin` | 0.7660 | 0.8511 | `results\benchmark_sds\run_20261003_121306_multiagent\eval_report_multiagent.json` |
| `sdsjoinsds` | 0.6914 | 0.7127 | `results\benchmark_all\run_20260921_175447_multiagent\eval_report_multiagent.json` |
| `sdsmapchars` | 0.8004 | 0.7129 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdsnew` | 0.8197 | 0.9329 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdsnewlen` | 0.7013 | 0.7538 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdsrange` | 0.7245 | 0.5849 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdssplitargs` | 0.7654 | 0.6194 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `sdssplitlen` | 0.7950 | 0.7484 | `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json` |
| `sdstolower` | 0.7969 | 0.3289 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdstoupper` | 0.8281 | 0.3080 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdstrim` | 0.6564 | 0.3060 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdsull2str` | 0.3801 | 0.4929 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |
| `sdsupdatelen` | 0.7743 | 0.5793 | `results\benchmark_sds\run_20261003_122734_multiagent\eval_report_multiagent.json` |

## Round-trip: dettaglio per funzione

| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |
|----------|-----------------------|------------------------|---------------|---------------|----------|
| `sdsAllocSize` | 60.0 (5) | 20.0 (5) | 0.0 | 20.0 | pipeline: test falliscono sul reference; CodeWiki: sintesi vuota |
| `sdsIncrLen` | 0.0 (5) | 0.0 (0) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: timeout, test falliscono sul reference |
| `sdsMakeRoomFor` | 16.7 (6) | 0.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `sdsRemoveFreeSpace` | 40.0 (5) | 100.0 (5) | 0.0 | 100.0 | pipeline: test falliscono sul reference |
| `sdsalloc` | 100.0 (6) | 100.0 (6) | 100.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `sdscat` | 0.0 (6) | 0.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference |
| `sdscatfmt` | 0.0 (7) | 16.7 (6) | 0.0 | 16.7 | pipeline: test falliscono sul reference |
| `sdscatlen` | 0.0 (5) | 83.3 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `sdscatprintf` | 100.0 (7) | 0.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `sdscatrepr` | 0.0 (5) | 0.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference |
| `sdscatsds` | 100.0 (7) | 33.3 (6) | 0.0 | 33.3 | pipeline: test falliscono sul reference |
| `sdscatvprintf` | 50.0 (6) | 0.0 (5) | 33.3 | 0.0 | CodeWiki: test falliscono sul reference |
| `sdsclear` | 20.0 (5) | 50.0 (4) | 20.0 | 50.0 | - |
| `sdscmp` | 100.0 (8) | 100.0 (8) | 100.0 | 100.0 | - |
| `sdscpy` | 0.0 (6) | 100.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `sdscpylen` | 0.0 (6) | 0.0 (5) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `sdsdup` | 40.0 (5) | 60.0 (5) | 40.0 | 60.0 | - |
| `sdsempty` | 50.0 (6) | 50.0 (6) | 50.0 | 50.0 | - |
| `sdsfree` | 100.0 (6) | 100.0 (5) | 100.0 | 100.0 | - |
| `sdsfreesplitres` | 100.0 (6) | 100.0 (6) | 100.0 | 100.0 | - |
| `sdsfromlonglong` | 100.0 (5) | 100.0 (6) | 100.0 | 100.0 | - |
| `sdsgrowzero` | 33.3 (6) | 0.0 (6) | 33.3 | 0.0 | CodeWiki: test falliscono sul reference |
| `sdsjoin` | 100.0 (6) | 100.0 (7) | 100.0 | 100.0 | - |
| `sdsjoinsds` | 16.7 (6) | 0.0 (0) | 16.7 | 0.0 | CodeWiki: timeout, test falliscono sul reference |
| `sdsmapchars` | 71.4 (7) | 66.7 (6) | 42.9 | 50.0 | - |
| `sdsnew` | 20.0 (5) | 100.0 (5) | 20.0 | 20.0 | - |
| `sdsnewlen` | 100.0 (5) | 100.0 (6) | 100.0 | 100.0 | - |
| `sdsrange` | 0.0 (7) | 33.3 (6) | 0.0 | 16.7 | pipeline: test falliscono sul reference |
| `sdssplitargs` | 100.0 (6) | 66.7 (6) | 16.7 | 16.7 | - |
| `sdssplitlen` | 33.3 (6) | 0.0 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `sdstolower` | 66.7 (6) | 50.0 (6) | 33.3 | 16.7 | - |
| `sdstoupper` | 100.0 (6) | 33.3 (6) | 16.7 | 16.7 | - |
| `sdstrim` | 16.7 (6) | 0.0 (8) | 0.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `sdsull2str` | 0.0 (0) | 100.0 (5) | 0.0 | 0.0 | pipeline: timeout; CodeWiki: test falliscono sul reference |
| `sdsupdatelen` | 0.0 (0) | 100.0 (5) | 0.0 | 100.0 | pipeline: timeout |

### Funzioni senza test eseguiti

Un pass rate 0% con **0 test eseguiti** non misura la qualita' della documentazione: i test non sono nemmeno partiti.

| Funzione | Sistema | Causa | Test generati passano sul reference |
|----------|---------|-------|-------------------------------------|
| `sdsIncrLen` | CodeWiki | timeout, test falliscono sul reference | 0.0% |
| `sdsjoinsds` | CodeWiki | timeout, test falliscono sul reference | 0.0% |
| `sdsull2str` | Pipeline | timeout | 0.0% |
| `sdsupdatelen` | Pipeline | timeout | 0.0% |

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 14, CodeWiki 13.

### Medie escludendo le funzioni senza test eseguiti

Sulle 31 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 52.2 | 50.4 | 0.6809 |
| Dual agreement (%) | 32.5 | 34.4 | 0.5552 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| Behavioral / Contract Failure | 56 | 57.1 | 42 | 46.2 |
| Interface / Signature Mismatch | 19 | 19.4 | 32 | 35.2 |
| Missing Symbol / Environment | 18 | 18.4 | 9 | 9.9 |
| Other Execution Error | 5 | 5.1 | 8 | 8.8 |
| **Totale** | **98** | | **91** | |

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
  Retrieval: stesso corpus sds della pipeline; query = testo della documentazione.
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 0.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*