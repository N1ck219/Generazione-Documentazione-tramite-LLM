# Confronto: Pipeline della tesi vs CodeWiki (miniz)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 7 (valutate da entrambi i sistemi) su 14 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json`, `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json`  

> ⚠️ **Campione ridotto (n=7)**: le differenze non sono statisticamente affidabili.
> Per un confronto completo eseguire la pipeline sulle stesse funzioni di CodeWiki:
> `.venv/Scripts/python utils/benchmark_eval.py -l miniz -m multiagent --functions compare_CodeWiki/miniz/codewiki_function_list.txt`

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 7 | 0.4321 | 0.3525 | 0.0795 | 0.2969 |
| BERTScore F1 | 0 | N/A | N/A | N/A | N/A |
| BLEURT (stima) | 7 | 0.4075 | 0.3215 | 0.0860 | 0.1562 |
| METEOR | 7 | 0.2694 | 0.2380 | 0.0314 | 0.2969 |
| TF-IDF cosine | 7 | 0.2040 | 0.1516 | 0.0524 | 0.2188 |
| ROUGE-L | 7 | 0.1067 | 0.1235 | -0.0168 | 0.8125 |
| Concept checklist | 7 | 0.7143 | 0.7143 | 0.0000 | N/A |
| Actionability | 7 | 0.8929 | 0.2500 | 0.6429 | 0.0156 |
| Error doc. rate | 5 | 0.8000 | 0.2000 | 0.6000 | n<6 |
| Edge case coverage | 5 | 0.4000 | 0.0000 | 0.4000 | n<6 |
| Length ratio | 7 | 3.1181 | 1.2987 | 1.8194 | N/A |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

*Non ancora calcolate per CodeWiki: eseguire*
`.venv/Scripts/python utils/evaluate_codewiki_advanced.py -l miniz`
*(oppure `evaluate_codewiki_metrics.py --full`).*

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 24.7629 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `mz_compress` | 0.3114 | 0.1670 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_deflate` | 0.0972 | 0.2744 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_deflateBound` | 0.6713 | 0.4634 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_deflateInit2` | 0.0899 | 0.0895 | `results\benchmark_all\run_20260917_175114_multiagent\eval_report_multiagent.json` |
| `mz_deflateReset` | 0.7558 | 0.3767 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |
| `mz_inflate` | 0.5211 | 0.3994 | `results\benchmark_all\run_20260921_155351_multiagent\eval_report_multiagent.json` |
| `mz_inflateReset` | 0.5778 | 0.6974 | `results\benchmark_all\run_20260917_161553_multiagent\eval_report_multiagent.json` |

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
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 7.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*