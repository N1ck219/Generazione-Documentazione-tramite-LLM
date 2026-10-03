# Confronto: Pipeline della tesi vs CodeWiki (fmt)

> **Script**: `utils/plot_codewiki_comparison.py`  
> **Funzioni confrontate**: 1 (valutate da entrambi i sistemi) su 1 documentate da CodeWiki  
> **Run della pipeline usati**: `results\benchmark_fmt\run_20261003_104529_multiagent\eval_report_multiagent.json`  

> ⚠️ **Campione ridotto (n=1)**: le differenze non sono statisticamente affidabili.
> Per un confronto completo eseguire la pipeline sulle stesse funzioni di CodeWiki:
> `.venv/Scripts/python utils/benchmark_eval.py -l fmt -m multiagent --functions compare_CodeWiki/fmt/codewiki_function_list.txt`

## Metriche medie sulle funzioni in comune

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| SBERT | 1 | 0.7323 | 0.2484 | 0.4839 | n<6 |
| BERTScore F1 | 1 | 0.6026 | 0.3361 | 0.2665 | n<6 |
| BLEURT (stima) | 1 | 0.6474 | 0.1657 | 0.4817 | n<6 |
| METEOR | 1 | 0.5090 | 0.1242 | 0.3848 | n<6 |
| TF-IDF cosine | 1 | 0.5742 | 0.0000 | 0.5742 | n<6 |
| ROUGE-L | 1 | 0.2857 | 0.0000 | 0.2857 | n<6 |
| Concept checklist | 1 | 1.0000 | 1.0000 | 0.0000 | n<6 |
| Actionability | 1 | 0.8500 | 0.2500 | 0.6000 | n<6 |
| Error doc. rate | 0 | N/A | N/A | N/A | N/A |
| Edge case coverage | 0 | N/A | N/A | N/A | N/A |
| Length ratio | 1 | 2.9600 | 0.2400 | 2.7200 | n<6 |

## Metriche avanzate (LLM-as-judge, round-trip, retrieval, CodeBERTScore)

| Metrica | n | Pipeline | CodeWiki | Δ (Pipeline − CodeWiki) | Wilcoxon p |
|---------|---|----------|----------|--------------------------|------------|
| CodeBERTScore F1 | 1 | 0.7677 | 0.6822 | 0.0855 | n<6 |
| Retrieval MRR | 1 | 1.0000 | 0.2000 | 0.8000 | n<6 |
| Retrieval Hit@1 | 1 | 1.0000 | 0.0000 | 1.0000 | n<6 |
| Retrieval Hit@5 | 1 | 1.0000 | 1.0000 | 0.0000 | n<6 |
| Judge A - Faithfulness | 1 | 4.8000 | 3.0000 | 1.8000 | n<6 |
| Judge B - Alignment | 1 | 4.8000 | 1.0000 | 3.8000 | n<6 |
| Judge combinato | 1 | 4.8000 | 2.0000 | 2.8000 | n<6 |
| Round-trip pass rate (%) | 1 | 100.0000 | 100.0000 | 0.0000 | n<6 |
| Dual agreement (%) | 1 | 100.0000 | 100.0000 | 0.0000 | n<6 |

Metriche della pipeline non applicabili a CodeWiki:

| Metrica | Pipeline | Motivo |
|---------|----------|--------|
| Param F1 | 1.0000 | richiede tag @param, assenti in CodeWiki |
| Return match | 1.0000 | richiede tag @return, assenti in CodeWiki |
| Hallucination rate | 0.0000 | deriva dal Verifier Doxygen della pipeline |

## Dettaglio per funzione (SBERT)

| Funzione | Pipeline | CodeWiki | Run pipeline |
|----------|----------|----------|--------------|
| `format` | 0.7323 | 0.2484 | `results\benchmark_fmt\run_20261003_104529_multiagent\eval_report_multiagent.json` |

## Round-trip: dettaglio per funzione

| Funzione | Pass % pipeline (test) | Pass % CodeWiki (test) | Dual pipeline | Dual CodeWiki | Anomalie |
|----------|-----------------------|------------------------|---------------|---------------|----------|
| `format` | 100.0 (6) | 100.0 (5) | 100.0 | 100.0 | - |

### Funzioni senza test eseguiti

Nessuna: tutte le funzioni hanno eseguito almeno un test in entrambi i sistemi.

Funzioni in cui la suite di test fallisce *tutta* anche sul codice reference (suite probabilmente inaffidabile): pipeline 0, CodeWiki 0.

### Medie escludendo le funzioni senza test eseguiti

Sulle 1 funzioni con test eseguiti in entrambi i sistemi:

| Metrica | Pipeline | CodeWiki | Wilcoxon p |
|---------|----------|----------|------------|
| Round-trip pass rate (%) | 100.0 | 100.0 | n<6 |
| Dual agreement (%) | 100.0 | 100.0 | n<6 |

### Tipologie di errore (test falliti)

Stessa classificazione di `utils/roundtrip_error_analysis.py`, applicata a entrambi i sistemi sulle stesse funzioni. Il dettaglio dei singoli errori e' in `codewiki_advanced_results.json` (CodeWiki) e nei `roundtrip_results.json` dei run (pipeline).

| Tipologia | Pipeline | % | CodeWiki | % |
|-----------|----------|---|----------|---|
| **Totale** | **0** | | **0** | |

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
  Retrieval: stesso corpus fmt della pipeline; query = testo della documentazione.
- Funzioni documentate da CodeWiki ma non ancora valutate dalla pipeline: 0.

*Report generato automaticamente da `utils/plot_codewiki_comparison.py`*