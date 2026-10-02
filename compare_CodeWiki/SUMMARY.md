# Confronto CodeWiki vs pipeline della tesi - riepilogo per libreria

> Generato da `compare_codewiki.py` il 2026-10-02 15:55. Dettagli, grafici e report completi in `compare_CodeWiki/<Libreria>/`.

## Copertura di CodeWiki

| Libreria | Funzioni DB | Menzionate | Con testo descrittivo | Documented coverage |
|----------|-------------|------------|-----------------------|---------------------|
| OpenCV | 8 | 8 | 8 | 100.0% |
| TinyXML-2 | 140 | 75 | 51 | 36.4% |
| cJSON | 88 | 42 | 20 | 22.7% |
| fmt | 12 | 1 | 1 | 8.3% |
| http-parser | 15 | 9 | 9 | 60.0% |
| miniz | 21 | 17 | 14 | 66.7% |
| sds | 39 | 35 | 35 | 89.7% |

## Pipeline vs CodeWiki (medie sulle funzioni in comune, formato `pipeline / CodeWiki`)

| Libreria | n | SBERT | BERTScore F1 | METEOR | Judge combinato (1-5) | Round-trip pass % | Retrieval MRR |
|----------|---|-------|--------------|--------|-----------------------|-------------------|---------------|
| OpenCV | 8 | 0.624 / 0.545 | 0.623 / 0.601 | 0.453 / 0.412 | 4.025 / 3.462 | 70.938 / 97.500 | 0.573 / 0.562 |
| TinyXML-2 | 47 | 0.585 / 0.551 | 0.581 / 0.581 | 0.369 / 0.391 | 4.453 / 2.890 | 60.185 / 64.130 | 0.650 / 0.443 |
| cJSON | 20 | 0.543 / 0.371 | 0.552 / 0.495 | 0.319 / 0.220 | 4.705 / 3.250 | 61.190 / 52.495 | 0.833 / 0.310 |
| miniz | 7 | 0.432 / 0.352 | N/A | 0.269 / 0.238 | N/A | N/A | N/A |

## Stato dell'ultima esecuzione

| Libreria | parse | metrics | pipeline | advanced | compare |
|----------|---|---|---|---|---|
| OpenCV | ok (0s) | ok (70s) | ok (576s) - 5 funzioni documentate | ok (581s) - compare_CodeWiki\OpenCV\codewiki_advanced_results.json | ok (11s) - 10 file generati |
| TinyXML-2 | ok (0s) | ok (51s) | ERRORE | - | - |
| cJSON | ok (0s) | ok (45s) | ok (0s) - nulla da fare (tutte le funzioni gia' documentate dalla pipeline) | ok (23s) - compare_CodeWiki\cJSON\codewiki_advanced_results.json | ok (23s) - 10 file generati |
| fmt | ok (0s) | ok (6s) | ERRORE | - | - |
| http-parser | ok (0s) | ok (15s) | ERRORE | - | - |
| miniz | ok (0s) | ok (34s) | ERRORE | - | - |
| sds | ok (0s) | ok (52s) | ERRORE | - | - |
