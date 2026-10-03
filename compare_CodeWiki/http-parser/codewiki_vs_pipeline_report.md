# Confronto: Pipeline della tesi vs CodeWiki (http-parser)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 9 (valutate da entrambi i sistemi) su 9 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260921_175447_multiagent\eval_report_multiagent.json`, `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json`  

> ⚠️ **Campione ridotto (n=9)**: le differenze non sono statisticamente affidabili.
> Per un confronto completo eseguire la pipeline sulle stesse funzioni di CodeWiki:
> `.venv/Scripts/python utils/benchmark_eval.py -l http-parser -m multiagent --functions compare_CodeWiki/http-parser/codewiki_function_list.txt`

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 9 | 0.6356 | 0.6948 | -0.0592 | 0.2031 |
| BERTScore F1 | 9 | 0.5923 | 0.6791 | -0.0868 | 0.0977 |
| BLEURT (stima) | 9 | 0.5541 | 0.6273 | -0.0731 | 0.2031 |
| METEOR | 9 | 0.3998 | 0.5608 | -0.1610 | 0.0391 |
| TF-IDF cosine | 9 | 0.5221 | 0.5096 | 0.0125 | 1.0000 |
| ROUGE-L | 9 | 0.1639 | 0.4269 | -0.2629 | 0.0117 |
| Concept checklist | 9 | 1.0000 | 1.0000 | 0.0000 | N/A |
| Actionability | 9 | 0.8444 | 0.3167 | 0.5278 | 0.0078 |
| Error doc. rate | 1 | 0.0000 | 0.0000 | 0.0000 | n<6 |
| Edge case coverage | 1 | 0.0000 | 0.0000 | 0.0000 | n<6 |
| Length ratio | 9 | 6.2983 | 0.7792 | 5.5191 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 9 | 0.7478 | 0.8327 | -0.0848 | 0.0078 |
| Retrieval MRR | 9 | 0.9259 | 0.8704 | 0.0556 | 1.0000 |
| Retrieval Hit@1 | 9 | 0.8889 | 0.7778 | 0.1111 | 1.0000 |
| Retrieval Hit@5 | 9 | 1.0000 | 1.0000 | 0.0000 | N/A |
| Judge A - Faithfulness | 9 | 4.5111 | 4.1556 | 0.3556 | 0.2031 |
| Judge B - Alignment | 9 | 4.5333 | 4.0889 | 0.4444 | 0.1250 |
| Judge combinato | 9 | 4.5222 | 4.1222 | 0.4000 | 0.0781 |
| Round-trip pass rate (%) | 9 | 87.6889 | 90.3444 | -2.6556 | 0.8750 |
| Dual agreement (%) | 8 | 85.0500 | 70.1750 | 14.8750 | 0.3750 |

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 0.0000 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `http_body_is_final` | 0.3922 | 0.6343 | `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json` |
| `http_errno_description` | 0.6075 | 0.5785 | `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json` |
| `http_errno_name` | 0.5702 | 0.6365 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `http_method_str` | 0.6645 | 0.7488 | `results\benchmark_all\run_20260921_175447_multiagent\eval_report_multiagent.json` |
| `http_parser_pause` | 0.6337 | 0.7896 | `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json` |
| `http_parser_set_max_header_size` | 0.4820 | 0.6951 | `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json` |
| `http_parser_version` | 0.9011 | 0.6772 | `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json` |
| `http_should_keep_alive` | 0.6763 | 0.6867 | `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json` |
| `http_status_str` | 0.7928 | 0.8061 | `results\benchmark_http-parser\run_20261003_113600_multiagent\eval_report_multiagent.json` |

## Round-trip: dettaglio per funzione

| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |
|----------|-----------------------|------------------------|---------------|---------------|----------|
| `http_body_is_final` | 100.0 (6) | 75.0 (4) | 83.3 | 50.0 | - |
| `http_errno_description` | 100.0 (4) | 100.0 (5) | 100.0 | 40.0 | - |
| `http_errno_name` | 71.4 (7) | 100.0 (5) | 71.4 | 0.0 | CodeWiki: test falliscono sul reference |
| `http_method_str` | 100.0 (7) | 100.0 (10) | 100.0 | 100.0 | - |
| `http_parser_pause` | 40.0 (5) | 100.0 (6) | 40.0 | 100.0 | - |
| `http_parser_set_max_header_size` | 100.0 (5) | 100.0 (5) | 100.0 | 100.0 | - |
| `http_parser_version` | 100.0 (5) | 100.0 (5) | 100.0 | 100.0 | - |
| `http_should_keep_alive` | 100.0 (7) | 71.4 (7) | 85.7 | 71.4 | - |
| `http_status_str` | 77.8 (9) | 66.7 (6) | N/A | 66.7 | - |

### Funzioni senza test eseguiti

Nessuna: tutte le funzioni hanno eseguito almeno un test in entrambi i sistemi.

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 0, CodeWiki 1.

### Medie escludendo le funzioni senza test eseguiti

Sulle 9 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 87.7 | 90.3 | 0.8750 |
| Dual agreement (%) | 85.1 | 70.2 | 0.3750 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| Behavioral / Contract Failure | 4 | 57.1 | 5 | 100.0 |
| Test Harness / Generator Bug | 2 | 28.6 | 0 | 0.0 |
| Other Execution Error | 1 | 14.3 | 0 | 0.0 |
| **Totale** | **7** | | **5** | |

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
  Retrieval: stesso corpus http-parser della pipeline; query = testo della documentazione.
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 0.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*