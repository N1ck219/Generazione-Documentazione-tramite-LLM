# Confronto: Pipeline della tesi vs CodeWiki (cJSON)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 20 (valutate da entrambi i sistemi) su 20 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json`, `results\benchmark_cjson\run_20261002_131207_multiagent\eval_report_multiagent.json`, `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json`  

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 20 | 0.5435 | 0.3714 | 0.1721 | 0.0022 |
| BERTScore F1 | 20 | 0.5523 | 0.4954 | 0.0569 | 0.0073 |
| BLEURT (stima) | 20 | 0.4770 | 0.3410 | 0.1360 | 0.0012 |
| METEOR | 20 | 0.3192 | 0.2199 | 0.0993 | 0.0083 |
| TF-IDF cosine | 20 | 0.2733 | 0.0845 | 0.1889 | 0.0006 |
| ROUGE-L | 20 | 0.0949 | 0.0684 | 0.0265 | 0.3300 |
| Concept checklist | 20 | 0.9500 | 0.9000 | 0.0500 | 0.3173 |
| Actionability | 20 | 0.8700 | 0.2500 | 0.6200 | 0.0001 |
| Error doc. rate | 13 | 1.0000 | 0.2308 | 0.7692 | 0.0020 |
| Edge case coverage | 15 | 0.6556 | 0.1333 | 0.5222 | 0.0050 |
| Length ratio | 20 | 10.1664 | 2.6553 | 7.5111 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 20 | 0.6573 | 0.7161 | -0.0588 | 0.4749 |
| Retrieval MRR | 20 | 0.8333 | 0.3105 | 0.5229 | 0.0004 |
| Retrieval Hit@1 | 20 | 0.7000 | 0.1500 | 0.5500 | 0.0009 |
| Retrieval Hit@5 | 20 | 1.0000 | 0.4500 | 0.5500 | 0.0009 |
| Judge A - Faithfulness | 20 | 4.6900 | 3.3300 | 1.3600 | 0.0001 |
| Judge B - Alignment | 20 | 4.7200 | 3.1700 | 1.5500 | 0.0002 |
| Judge combinato | 20 | 4.7050 | 3.2500 | 1.4550 | 0.0001 |
| Round-trip pass rate (%) | 20 | 61.1900 | 52.4950 | 8.6950 | 0.4774 |
| Dual agreement (%) | 20 | 34.3950 | 18.3700 | 16.0250 | 0.0883 |

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 0.0000 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `cJSON_Compare` | 0.8502 | 0.6393 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `cJSON_Delete` | 0.6105 | 0.6754 | `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json` |
| `cJSON_Duplicate` | 0.6189 | 0.5690 | `results\benchmark_cjson\run_20261002_131207_multiagent\eval_report_multiagent.json` |
| `cJSON_Minify` | 0.6702 | 0.5688 | `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json` |
| `cJSON_Parse` | 0.7111 | 0.8466 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `cJSON_ParseWithOpts` | 0.5714 | 0.3594 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `cJSON_Print` | 0.6334 | 0.1983 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `cJSON_PrintBuffered` | 0.7338 | 0.3184 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `cJSON_PrintPreallocated` | 0.5861 | 0.3799 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `cJSON_PrintUnformatted` | 0.7597 | 0.2843 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `parse_array` | 0.2673 | 0.1990 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `parse_number` | 0.4013 | 0.2072 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `parse_object` | 0.2036 | 0.2875 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `parse_string` | 0.5201 | 0.2343 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `parse_value` | 0.3513 | 0.5168 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `print_array` | 0.4883 | 0.2763 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `print_number` | 0.3855 | 0.3841 | `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json` |
| `print_object` | 0.4692 | 0.1279 | `results\benchmark_cjson\run_20261002_135239_multiagent\eval_report_multiagent.json` |
| `print_string` | 0.6373 | 0.2857 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `print_value` | 0.4004 | 0.0688 | `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json` |

## Round-trip: dettaglio per funzione

| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |
|----------|-----------------------|------------------------|---------------|---------------|----------|
| `cJSON_Compare` | 0.0 (6) | 0.0 (0) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: sintesi vuota, timeout, test falliscono sul reference |
| `cJSON_Delete` | 100.0 (5) | 100.0 (7) | 100.0 | 14.3 | - |
| `cJSON_Duplicate` | 100.0 (5) | 16.7 (6) | 20.0 | 16.7 | - |
| `cJSON_Minify` | 83.3 (6) | 100.0 (6) | 33.3 | 100.0 | - |
| `cJSON_Parse` | 85.7 (7) | 100.0 (8) | 42.9 | 50.0 | - |
| `cJSON_ParseWithOpts` | 71.4 (7) | 80.0 (5) | 28.6 | 40.0 | - |
| `cJSON_Print` | 100.0 (8) | 77.8 (9) | 37.5 | 22.2 | - |
| `cJSON_PrintBuffered` | 85.7 (7) | 57.1 (7) | 57.1 | 0.0 | - |
| `cJSON_PrintPreallocated` | 85.7 (7) | 25.0 (8) | 85.7 | 0.0 | - |
| `cJSON_PrintUnformatted` | 100.0 (9) | 50.0 (8) | 0.0 | 37.5 | pipeline: test falliscono sul reference |
| `parse_array` | 0.0 (7) | 66.7 (6) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `parse_number` | 0.0 (7) | 100.0 (8) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: test falliscono sul reference |
| `parse_object` | 14.3 (7) | 60.0 (5) | 14.3 | 20.0 | - |
| `parse_string` | 14.3 (7) | 33.3 (6) | 14.3 | 0.0 | CodeWiki: test falliscono sul reference |
| `parse_value` | 100.0 (9) | 0.0 (7) | 100.0 | 0.0 | CodeWiki: test falliscono sul reference |
| `print_array` | 0.0 (7) | 0.0 (0) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: timeout, test falliscono sul reference |
| `print_number` | 100.0 (8) | 83.3 (6) | 87.5 | 66.7 | - |
| `print_object` | 66.7 (6) | 100.0 (5) | 16.7 | 0.0 | - |
| `print_string` | 16.7 (6) | 0.0 (0) | 0.0 | 0.0 | pipeline: test falliscono sul reference; CodeWiki: timeout, test falliscono sul reference |
| `print_value` | 100.0 (6) | 0.0 (8) | 50.0 | 0.0 | CodeWiki: test falliscono sul reference |

### Funzioni senza test eseguiti

Un pass rate 0% con **0 test eseguiti** non misura la qualita' della documentazione: i test non sono nemmeno partiti.

| Funzione | Sistema | Causa | Test generati passano sul reference |
|----------|---------|-------|-------------------------------------|
| `cJSON_Compare` | CodeWiki | sintesi vuota, timeout, test falliscono sul reference | 0.0% |
| `print_array` | CodeWiki | timeout, test falliscono sul reference | 0.0% |
| `print_string` | CodeWiki | timeout, test falliscono sul reference | 0.0% |

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 6, CodeWiki 8.

### Medie escludendo le funzioni senza test eseguiti

Sulle 17 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 71.0 | 61.8 | 0.5177 |
| Dual agreement (%) | 40.5 | 21.6 | 0.0883 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| Behavioral / Contract Failure | 13 | 25.0 | 33 | 68.8 |
| Missing Symbol / Environment | 31 | 59.6 | 2 | 4.2 |
| Interface / Signature Mismatch | 7 | 13.5 | 8 | 16.7 |
| Other Execution Error | 0 | 0.0 | 5 | 10.4 |
| Test Harness / Generator Bug | 1 | 1.9 | 0 | 0.0 |
| **Totale** | **52** | | **48** | |

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
  Retrieval: stesso corpus cJSON della pipeline; query = testo della documentazione.
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 0.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*