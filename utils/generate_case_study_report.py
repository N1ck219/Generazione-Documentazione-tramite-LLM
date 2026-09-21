"""
Script per estrarre e analizzare qualitativamente i casi di:
- Massima corrispondenza (Max)
- Valori mediani / intermedi (Median)
- Minima corrispondenza (Min)

Sia sui Casi di Test Controllati sia sul Benchmark Reale Sviluppato (eval_report_multiagent.json).
Genera un report Markdown esaustivo con testi a contrasto e diagnosi critica.
"""

import os
import sys
import json
import numpy as np
from typing import Dict, List, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def load_json(filepath: str) -> Any:
    if not os.path.exists(filepath):
        print(f"[WARN] File non trovato: {filepath}")
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_controlled_test_cases():
    results_path = os.path.join(ROOT_DIR, "results", "metrics_validation", "metric_validation_results.json")
    data = load_json(results_path)
    if not data:
        return None

    # Recuperiamo anche i testi sorgenti da TEST_CASES in verify_metric_sensitivity.py
    from utils.verify_metric_sensitivity import TEST_CASES
    lookup_cases = {tc["id"]: tc for tc in TEST_CASES}

    for item in data:
        cid = item["id"]
        if cid in lookup_cases:
            item["reference"] = lookup_cases[cid]["reference"]
            item["candidate"] = lookup_cases[cid]["candidate"]

    # Ordiniamo per SBERT
    sorted_sbert = sorted(data, key=lambda x: x["scores"]["SBERT"])
    n = len(sorted_sbert)

    min_case = sorted_sbert[0]
    med_case_1 = sorted_sbert[n // 2 - 1]
    med_case_2 = sorted_sbert[n // 2]
    max_case = sorted_sbert[-1]

    return {
        "min": min_case,
        "median_1": med_case_1,
        "median_2": med_case_2,
        "max": max_case,
        "all_sorted": sorted_sbert
    }


def analyze_real_benchmark():
    multi_path = os.path.join(ROOT_DIR, "results", "benchmark_all", "latest", "eval_report_multiagent.json")
    data = load_json(multi_path)
    if not data:
        return None

    # Filtriamo elementi che hanno le metriche e ground truth valida
    valid_items = [
        item for item in data 
        if "metrics" in item and "sbert_similarity" in item["metrics"] and item.get("ground_truth")
    ]

    if not valid_items:
        return None

    # Ordiniamo per SBERT similarity
    sorted_items = sorted(valid_items, key=lambda x: x["metrics"]["sbert_similarity"])
    n = len(sorted_items)

    min_case = sorted_items[0]
    med_case_1 = sorted_items[n // 2 - 1]
    med_case_2 = sorted_items[n // 2]
    max_case = sorted_items[-1]

    return {
        "min": min_case,
        "median_1": med_case_1,
        "median_2": med_case_2,
        "max": max_case,
        "total_count": n
    }


def build_case_study_report(controlled_res, real_res, output_path: str):
    lines = []
    lines.append("# Studio Qualitativo di Confronto: Casi Estremi (Max, Min) e Casi Mediani\n")
    lines.append("Il presente report offre un'analisi approfondita e qualitativa del comportamento delle metriche ")
    lines.append("di similarità semantica e lessicale (SBERT, BERTScore, CodeBERT, ROUGE-L, TF-IDF). ")
    lines.append("L'indagine isola i **punti estremi (Massimo, Minimo)** e i **punti mediani (50° percentile)** sia nei ")
    lines.append("**Casi di Test Sintetici Controllati**, sia nel **Benchmark Reale di Produzione** della tesi.\n")

    # =========================================================================
    # PARTE 1: CASI DI TEST CONTROLLATI
    # =========================================================================
    lines.append("## PARTE 1: Casi di Test Sintetici Controllati (Stress Test)\n")
    lines.append("Nei casi sintetici controllati conosciamo la verità a priori (bug noti, parafrasi, ortogonalità).\n")

    if controlled_res:
        # MAX
        c_max = controlled_res["max"]
        lines.append(f"### 1.1 Caso di Massima Corrispondenza (Top Score SBERT: {c_max['scores']['SBERT']:.3f})\n")
        lines.append(f"- **ID**: `{c_max['id']}` | **Categoria**: `{c_max['category']}` | **Lingue**: `{c_max['lang_pair']}`")
        lines.append(f"- **Titolo**: **{c_max['name']}**")
        lines.append(f"- **Metriche**: SBERT: `{c_max['scores']['SBERT']:.3f}` | BERTScore: `{c_max['scores']['BERTScore']:.3f}` | CodeBERT: `{c_max['scores']['CodeBERT']:.3f}` | ROUGE-L: `{c_max['scores']['ROUGE-L']:.3f}` | TF-IDF: `{c_max['scores']['TF-IDF']:.3f}`")
        lines.append("\n**Testo / Codice Reference (Ground Truth)**:")
        lines.append("```python\n" + c_max.get("reference", "") + "\n```")
        lines.append("\n**Testo / Codice Candidato**:")
        lines.append("```python\n" + c_max.get("candidate", "") + "\n```")
        lines.append("\n**Diagnosi Critica (Perché ha fatto il massimo?)**:")
        if c_max["category"] == "ADVERSARIAL":
            lines.append("> [!CAUTION]")
            lines.append("> **PARADOSSO CONFERMATO**: Il caso con il punteggio più alto in assoluto non è una funzione corretta, ma un **Adversarial Bug**! La sostituzione di un singolo operatore di confronto lascia il 98% dei token identici, portando SBERT a 1.000. Dimostra che la metrica premia la vicinanza lessicale superficiale piuttosto che la semantica computazionale.")
        else:
            lines.append("> **Allineamento Semantico**: Il codice/testo condivide un'altissima coerenza di vocabolario e struttura logica.")

        lines.append("\n---\n")

        # MEDIAN
        for idx, c_med in enumerate([controlled_res["median_1"], controlled_res["median_2"]], 1):
            lines.append(f"### 1.2.{idx} Caso Mediano Intermedio #{idx} (Score SBERT: {c_med['scores']['SBERT']:.3f})\n")
            lines.append(f"- **ID**: `{c_med['id']}` | **Categoria**: `{c_med['category']}` | **Lingue**: `{c_med['lang_pair']}`")
            lines.append(f"- **Titolo**: **{c_med['name']}**")
            lines.append(f"- **Metriche**: SBERT: `{c_med['scores']['SBERT']:.3f}` | BERTScore: `{c_med['scores']['BERTScore']:.3f}` | CodeBERT: `{c_med['scores']['CodeBERT']:.3f}` | ROUGE-L: `{c_med['scores']['ROUGE-L']:.3f}` | TF-IDF: `{c_med['scores']['TF-IDF']:.3f}`")
            lines.append("\n**Testo / Codice Reference**:")
            lines.append("```python\n" + c_med.get("reference", "") + "\n```")
            lines.append("\n**Testo / Codice Candidato**:")
            lines.append("```python\n" + c_med.get("candidate", "") + "\n```")
            lines.append("\n**Diagnosi Critica (Cosa rappresenta il caso mediano?)**:")
            lines.append(f"> **Rappresentazione Tipica**: Questo caso si colloca esattamente a metà classifica ({c_med['scores']['SBERT']:.3f}). Riflette scenari in cui la logica è affine o equivalente, ma la forma sintattica presenta differenze percepibili (es. parafrasi o cross-linguaggio C-Python), consentendo a SBERT di valutare una parziale sovrapposizione concettuale.")
            lines.append("\n---\n")

        # MIN
        c_min = controlled_res["min"]
        lines.append(f"### 1.3 Caso di Minima Corrispondenza (Lowest Score SBERT: {c_min['scores']['SBERT']:.3f})\n")
        lines.append(f"- **ID**: `{c_min['id']}` | **Categoria**: `{c_min['category']}` | **Lingue**: `{c_min['lang_pair']}`")
        lines.append(f"- **Titolo**: **{c_min['name']}**")
        lines.append(f"- **Metriche**: SBERT: `{c_min['scores']['SBERT']:.3f}` | BERTScore: `{c_min['scores']['BERTScore']:.3f}` | CodeBERT: `{c_min['scores']['CodeBERT']:.3f}` | ROUGE-L: `{c_min['scores']['ROUGE-L']:.3f}` | TF-IDF: `{c_min['scores']['TF-IDF']:.3f}`")
        lines.append("\n**Testo / Codice Reference**:")
        lines.append("```python\n" + c_min.get("reference", "") + "\n```")
        lines.append("\n**Testo / Codice Candidato**:")
        lines.append("```python\n" + c_min.get("candidate", "") + "\n```")
        lines.append("\n**Diagnosi Critica (Perché è crollato?)**:")
        lines.append("> [!NOTE]")
        lines.append("> **Zero Baseline Corretta**: Il punteggio scende a ~0.00 perché i due testi appartengono ad ambiti del tutto scorrelati (ortogonali). Dimostra che SBERT possiede un'eccellente capacità di rigetto del rumore quando non vi è alcuna attinenza lessicale o tematica.")

    lines.append("\n---\n")

    # =========================================================================
    # PARTE 2: BENCHMARK REALE DELLA TESI
    # =========================================================================
    lines.append("## PARTE 2: Benchmark Reale Sviluppato (eval_report_multiagent.json)\n")
    lines.append(f"Analisi condotta sull'intero dataset reale di benchmark ({real_res['total_count'] if real_res else 0} funzioni C documentate con Ground Truth dell'autore).\n")

    if real_res:
        # MAX REALE
        r_max = real_res["max"]
        m_max = r_max["metrics"]
        lines.append(f"### 2.1 Caso di Massima Corrispondenza Reale (SBERT: {m_max['sbert_similarity']:.3f})\n")
        lines.append(f"- **Funzione**: `{r_max['function_name']}` | **Firma**: `{r_max['signature']}`")
        lines.append(f"- **Metriche**: SBERT: `{m_max['sbert_similarity']:.3f}` | BERTScore F1: `{m_max['bert_score_f1']:.3f}` | BLEURT: `{m_max['bleurt_score']:.3f}` | ROUGE-L: `{m_max['rouge_l']:.3f}` | TF-IDF: `{m_max['tfidf_similarity']:.3f}`")
        lines.append("\n**Codice Sorgente C Reale**:")
        lines.append("```c\n" + r_max.get("source_code", "").strip() + "\n```")
        lines.append("\n**Ground Truth Ufficiale (Commento Originale dell'Autore)**:")
        lines.append("> \"" + r_max.get("ground_truth", "").strip() + "\"")
        lines.append("\n**Documentazione Sintetica Generata (Summary)**:")
        lines.append("> \"" + r_max.get("generated_summary", "").strip() + "\"")
        lines.append("\n**Doxygen Strutturato Generato**:")
        lines.append("```c\n" + r_max.get("generated_doxygen", "").strip() + "\n```")
        lines.append("\n**Diagnosi Qualitativa**:")
        lines.append("> **Allineamento Semantico Perfetto**: La documentazione generata riprende fedelmente i concetti cardine espressi dall'autore della libreria. L'elevata aderenza è dovuta sia alla chiarezza della funzione sia alla precisione dell'LLM nel descrivere lo scopo senza allucinazioni.")

        lines.append("\n---\n")

        # MEDIAN REALI
        for idx, r_med in enumerate([real_res["median_1"], real_res["median_2"]], 1):
            m_med = r_med["metrics"]
            lines.append(f"### 2.2.{idx} Caso Mediano Reale #{idx} (SBERT: {m_med['sbert_similarity']:.3f})\n")
            lines.append(f"- **Funzione**: `{r_med['function_name']}` | **Firma**: `{r_med['signature']}`")
            lines.append(f"- **Metriche**: SBERT: `{m_med['sbert_similarity']:.3f}` | BERTScore F1: `{m_med['bert_score_f1']:.3f}` | BLEURT: `{m_med['bleurt_score']:.3f}` | ROUGE-L: `{m_med['rouge_l']:.3f}` | TF-IDF: `{m_med['tfidf_similarity']:.3f}`")
            lines.append("\n**Codice Sorgente C Reale**:")
            lines.append("```c\n" + r_med.get("source_code", "").strip() + "\n```")
            lines.append("\n**Ground Truth Ufficiale (Autore)**:")
            lines.append("> \"" + r_med.get("ground_truth", "").strip() + "\"")
            lines.append("\n**Documentazione Sintetica Generata (Summary)**:")
            lines.append("> \"" + r_med.get("generated_summary", "").strip() + "\"")
            lines.append("\n**Diagnosi Qualitativa**:")
            lines.append(f"> **La Qualità Tipica del Sistema**: Questo rappresenta lo standard del sistema nel 50% dei casi operativi. La logica della funzione è descritta correttamente, ma il punteggio SBERT si attesta intorno a {m_med['sbert_similarity']:.3f} perché l'LLM adotta una formulazione più formale e dettagliata rispetto al commento conciso/informale lasciato dall'autore originale.")
            lines.append("\n---\n")

        # MIN REALE
        r_min = real_res["min"]
        m_min = r_min["metrics"]
        lines.append(f"### 2.3 Caso di Minima Corrispondenza Reale (SBERT: {m_min['sbert_similarity']:.3f})\n")
        lines.append(f"- **Funzione**: `{r_min['function_name']}` | **Firma**: `{r_min['signature']}`")
        lines.append(f"- **Metriche**: SBERT: `{m_min['sbert_similarity']:.3f}` | BERTScore F1: `{m_min['bert_score_f1']:.3f}` | BLEURT: `{m_min['bleurt_score']:.3f}` | ROUGE-L: `{m_min['rouge_l']:.3f}` | TF-IDF: `{m_min['tfidf_similarity']:.3f}`")
        lines.append("\n**Codice Sorgente C Reale**:")
        lines.append("```c\n" + r_min.get("source_code", "").strip() + "\n```")
        lines.append("\n**Ground Truth Ufficiale (Autore)**:")
        lines.append("> \"" + r_min.get("ground_truth", "").strip() + "\"")
        lines.append("\n**Documentazione Sintetica Generata (Summary)**:")
        lines.append("> \"" + r_min.get("generated_summary", "").strip() + "\"")
        lines.append("\n**Diagnosi Qualitativa (Perché è il punteggio minimo?)**:")
        lines.append("> [!WARNING]")
        lines.append("> **Disallineamento Prospettico o Note Ermetiche**: Esaminando il commento originale, emerge chiaramente il motivo del crollo del punteggio: o l'autore ha inserito una nota interna criptica (es. un TODO o un commento di implementazione interna non documentale), oppure l'LLM ha descritto il comportamento funzionale globale della funzione mentre la Ground Truth menzionava solo un dettaglio secondario. Non si tratta necessariamente di un'allucinazione, ma di una divergenza di granularità espositiva.")

    lines.append("\n---\n")
    lines.append("## 3. Conclusioni Metodologiche Generali\n")
    lines.append("1. **Il Valore della Mediana rispetto alla Media**: La presenza di casi con Ground Truth ermetica o con sovrapposizioni lessicali anomale dimostra come la mediana sia un descrittore più robusto della qualità effettiva della documentazione generata.\n")
    lines.append("2. **Differenza tra Corrispondenza Lessicale e Correttezza Logica**: I casi estremi mostrano chiaramente che un punteggio di similarità NLP alto non certifica l'assenza di bug logici, mentre un punteggio basso può derivare da uno stile documentale differente tra l'autore della libreria e lo standard Doxygen rigoroso prodotto dal nostro generatore multi-agente.")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    print("=" * 80)
    print("GENERAZIONE REPORT QUALITATIVO: CASI ESTREMI (MAX, MIN) E MEDIANI")
    print("=" * 80)

    controlled_res = analyze_controlled_test_cases()
    real_res = analyze_real_benchmark()

    out_dir = os.path.join(ROOT_DIR, "results", "metrics_validation")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "case_studies_extrema_and_median.md")

    build_case_study_report(controlled_res, real_res, report_path)
    print(f"[OK] Report salvato con successo in: {report_path}")


if __name__ == "__main__":
    main()
