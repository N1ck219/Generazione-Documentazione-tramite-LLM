# Confronto CodeWiki vs pipeline della tesi - riepilogo per libreria

> Generato da `compare_codewiki.py` il 2026-10-03 14:25. Dettagli, grafici e report completi in `compare_CodeWiki/<Libreria>/`.

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
| OpenCV | 8 | 0.615 / 0.545 | 0.620 / 0.601 | 0.446 / 0.412 | 4.112 / 3.462 | 83.438 / 97.500 | 0.573 / 0.562 |
| TinyXML-2 | 51 | 0.597 / 0.550 | 0.584 / 0.578 | 0.379 / 0.386 | 4.464 / 2.871 | 61.347 / 64.982 | 0.657 / 0.415 |
| cJSON | 20 | 0.543 / 0.371 | 0.552 / 0.495 | 0.319 / 0.220 | 4.705 / 3.250 | 61.190 / 52.495 | 0.833 / 0.310 |
| fmt | 1 | 0.732 / 0.248 | 0.603 / 0.336 | 0.509 / 0.124 | 4.800 / 2.000 | 100.000 / 100.000 | 1.000 / 0.200 |
| http-parser | 9 | 0.636 / 0.695 | 0.592 / 0.679 | 0.400 / 0.561 | 4.522 / 4.122 | 87.689 / 90.344 | 0.926 / 0.870 |
| miniz | 14 | 0.442 / 0.396 | 0.518 / 0.482 | 0.265 / 0.241 | 4.493 / 3.400 | 76.400 / 81.714 | 0.542 / 0.373 |
| sds | 35 | 0.704 / 0.628 | 0.595 / 0.591 | 0.438 / 0.423 | 4.563 / 3.500 | 46.709 / 50.380 | 0.471 / 0.490 |

## Stato dell'ultima esecuzione

| Libreria | parse | metrics | pipeline | advanced | compare |
|----------|---|---|---|---|---|
| OpenCV | - | - | - | - | - |
| TinyXML-2 | - | - | - | - | - |
| cJSON | - | - | - | - | - |
| fmt | - | - | - | - | ok (22s) - 14 file generati |
| http-parser | - | - | - | - | - |
| miniz | - | - | - | - | - |
| sds | - | - | - | - | - |
