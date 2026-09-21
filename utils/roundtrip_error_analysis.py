"""
Modulo di analisi diagnostica e classificazione degli errori del Round-Trip Evaluation.

Questo modulo analizza l'output di esecuzione dei test (pytest) generato dal Round-Trip
(sintesi di codice a partire dalla documentazione) e categorizza i fallimenti secondo una
tassonomia utile all'analisi della tesi:
  - Missing Symbol / Environment: simboli non definiti (NameError), import o attributi mancanti
  - Interface / Signature Mismatch: parametri errati, argomenti inattesi, TypeError di invocazione
  - Behavioral / Contract Failure: fallimenti di asserzione su calcoli, logica, contratti
  - Test Harness / Generator Bug: anomalie di test setup o asserzioni su eccezioni non sollevate
  - Syntax / Compilation Error: errori sintattici nel codice sintetizzato
  - Timeout / Hang: timeout di esecuzione dei test
  - Other Execution Error: altri errori di runtime non catalogati altrove
"""

import os
import re
from typing import Dict, Any, List, Optional
from collections import defaultdict


def classify_pytest_failure(test_name: str, error_msg: str) -> Dict[str, str]:
    """
    Classifica un singolo test fallito in base alla tipologia di errore e al messaggio.
    """
    err = error_msg.strip()

    # 1. Syntax / Import Error
    if "SyntaxError" in err or "IndentationError" in err:
        return {
            "category": "Syntax / Compilation Error",
            "subtype": "SyntaxError",
            "description": "Errore sintattico o di indentazione nel codice generato dall'LLM."
        }

    # 2. Missing Symbol / Environment
    if "NameError" in err:
        m = re.search(r"NameError:\s*(?:name\s*)?['\"]?(\w+)['\"]?", err)
        symbol = m.group(1) if m else "unknown"
        return {
            "category": "Missing Symbol / Environment",
            "subtype": "NameError",
            "description": f"Simbolo non definito '{symbol}': funzione ausiliaria, costante o modulo non fornito nello scaffold."
        }
    if "ModuleNotFoundError" in err or "No module named" in err:
        m = re.search(r"No module named\s*['\"]?([^'\"]+)['\"]?", err)
        mod = m.group(1) if m else "unknown"
        return {
            "category": "Missing Symbol / Environment",
            "subtype": "ModuleNotFoundError",
            "description": f"Modulo '{mod}' mancante nell'ambiente o non importato."
        }
    if "AttributeError" in err:
        return {
            "category": "Missing Symbol / Environment",
            "subtype": "AttributeError",
            "description": "Attributo o metodo mancante su modulo o oggetto invocato."
        }

    # 3. Interface / Signature / Type Mismatch
    if "TypeError" in err:
        if any(w in err for w in ["argument", "positional", "keyword", "got an unexpected", "required positional"]):
            return {
                "category": "Interface / Signature Mismatch",
                "subtype": "Signature Mismatch",
                "description": "Discrepanza nel numero o nome dei parametri attesi vs ricevuti."
            }
        return {
            "category": "Interface / Signature Mismatch",
            "subtype": "TypeError",
            "description": "Tipo di dato non compatibile nelle operazioni interne o negli argomenti."
        }
    if "ValueError" in err and any(w in err for w in ["unpack", "not enough values", "too many values"]):
        return {
            "category": "Interface / Signature Mismatch",
            "subtype": "Unpack / Return Shape Mismatch",
            "description": "La struttura dei valori restituiti non corrisponde all'unண்ட-packing atteso dal test."
        }

    # 4. Test Harness / Generator Bug
    if "DID NOT RAISE" in err or "Failed: DID NOT RAISE" in err:
        return {
            "category": "Test Harness / Generator Bug",
            "subtype": "DID NOT RAISE",
            "description": "Il test si aspettava che la funzione sollevasse un'eccezione che non è stata lanciata."
        }

    # 5. Behavioral / Contract Failure
    if "assert " in err or "AssertionError" in err:
        return {
            "category": "Behavioral / Contract Failure",
            "subtype": "AssertionError",
            "description": "Il valore restituito non soddisfa l'asserzione (logica o calcolo difforme dalla specifica)."
        }
    if "IndexError" in err or "KeyError" in err:
        return {
            "category": "Behavioral / Contract Failure",
            "subtype": "Container Bounds Error",
            "description": "Accesso errato a indici o chiavi durante l'esecuzione logica."
        }

    # 6. Timeout
    if "Timeout" in err or "timed out" in err.lower():
        return {
            "category": "Timeout / Hang",
            "subtype": "Timeout",
            "description": "Esecuzione interrotta per superamento del tempo limite consentito."
        }

    # 7. Other Execution Error
    first_word = err.split(":")[0].strip() if ":" in err else err.split()[0].strip() if err.split() else "Unknown"
    first_word = first_word.rstrip(".")
    if first_word.startswith("NameErr"):
        return {
            "category": "Missing Symbol / Environment",
            "subtype": "NameError",
            "description": "Simbolo non definito: funzione ausiliaria, costante o modulo non fornito nello scaffold."
        }
    if "hypothesis" in first_word.lower():
        return {
            "category": "Test Harness / Generator Bug",
            "subtype": "Hypothesis Harness Error",
            "description": "Errore di configurazione o esecuzione del generatore di proprietà Hypothesis nei test."
        }
    return {
        "category": "Other Execution Error",
        "subtype": first_word,
        "description": f"Eccezione di runtime generica: {first_word}."
    }


def parse_pytest_failures_from_output(test_output: str) -> List[Dict[str, str]]:
    """
    Estrae i singoli fallimenti dalla sezione 'short test summary info' di pytest.
    """
    failures = []
    if not test_output:
        return failures

    lines = test_output.splitlines()
    in_summary = False
    for line in lines:
        if "short test summary info" in line:
            in_summary = True
            continue
        if in_summary:
            if line.startswith("===") or line.startswith("---"):
                if len(failures) > 0:
                    break
                continue
            line_s = line.strip()
            if line_s.startswith("FAILED ") or line_s.startswith("ERROR "):
                # es. FAILED test_foo.py::test_bar - NameError: name 'np' is not defined
                parts = line_s.split(" - ", 1)
                header = parts[0]
                reason = parts[1] if len(parts) > 1 else ""
                # Rimuovi eventuale trailing ellissi artificiale se presente all'inizio dell'eccezione
                reason_clean = reason.strip()
                
                # estrai nome del test
                test_ident = header.replace("FAILED ", "").replace("ERROR ", "").strip()
                if "::" in test_ident:
                    test_name = test_ident.split("::")[-1]
                else:
                    test_name = test_ident

                failures.append({
                    "test_identifier": test_ident,
                    "test_name": test_name,
                    "raw_reason": reason
                })

    return failures


def analyze_roundtrip_errors(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analizza la lista dei risultati di un'esecuzione roundtrip e produce
    statistiche aggregate, categorizzazione e breakdown dettagliato degli errori.
    """
    total_evaluated = len(results)
    successful_syntheses = 0
    failed_syntheses = 0
    perfect_passes = 0
    failing_functions = 0

    category_counts = defaultdict(int)
    subtype_counts = defaultdict(int)
    function_error_breakdown = []

    for r in results:
        func_name = r.get("function_name", "unknown")
        library = r.get("library")
        if not library or library == "unknown":
            # Euristica intelligente di inferenza libreria dal prefisso
            fn_low = func_name.lower()
            if fn_low.startswith("cjson"):
                library = "cJSON"
            elif fn_low.startswith("xml") or "::" in func_name and any(x in fn_low for x in ["element", "node", "printer", "doc", "handle"]):
                library = "tinyxml2"
            elif fn_low.startswith("sds"):
                library = "sds"
            elif fn_low.startswith("http_"):
                library = "http-parser"
            elif fn_low.startswith("mz_"):
                library = "miniz"
            elif fn_low.startswith("cv") or fn_low.startswith("mat"):
                library = "OpenCV"
            else:
                library = "General"
        exec_info = r.get("execution", {})
        tests_passed = exec_info.get("passed", exec_info.get("tests_passed", 0))
        tests_failed = exec_info.get("failed", exec_info.get("tests_failed", 0))
        total_tests = exec_info.get("total_tests", tests_passed + tests_failed)
        test_output = exec_info.get("test_output", "")
        error_msg = r.get("error")
        synth_success = r.get("synthesis_success", bool(r.get("synthesized_code") or test_output))

        if not synth_success:
            failed_syntheses += 1
            cat_info = {
                "category": "Syntax / Compilation Error",
                "subtype": "Synthesis Failed",
                "description": f"L'LLM non ha generato codice valido o ha sollevato un'eccezione: {error_msg}"
            }
            category_counts[cat_info["category"]] += 1
            subtype_counts[cat_info["subtype"]] += 1
            function_error_breakdown.append({
                "function_name": func_name,
                "library": library,
                "synthesis_success": False,
                "tests_passed": 0,
                "tests_failed": 1,
                "total_tests": 1,
                "failures": [{
                    "test_name": "synthesis",
                    "category": cat_info["category"],
                    "subtype": cat_info["subtype"],
                    "description": cat_info["description"],
                    "raw_reason": error_msg or "Sintesi fallita"
                }]
            })
            continue

        successful_syntheses += 1

        if tests_failed == 0 and total_tests > 0:
            perfect_passes += 1
            continue

        if tests_failed > 0 or total_tests == 0:
            failing_functions += 1
            parsed_failures = parse_pytest_failures_from_output(test_output)
            
            classified_failures = []
            if parsed_failures:
                for pf in parsed_failures:
                    clf = classify_pytest_failure(pf["test_name"], pf["raw_reason"])
                    category_counts[clf["category"]] += 1
                    subtype_counts[clf["subtype"]] += 1
                    classified_failures.append({
                        "test_name": pf["test_name"],
                        "category": clf["category"],
                        "subtype": clf["subtype"],
                        "description": clf["description"],
                        "raw_reason": pf["raw_reason"]
                    })
            else:
                # Nessun singolo test estratto da short summary, ma tests_failed > 0 o timeout
                cat = "Timeout / Hang" if "timeout" in test_output.lower() else "Other Execution Error"
                category_counts[cat] += max(tests_failed, 1)
                subtype_counts[cat] += max(tests_failed, 1)
                classified_failures.append({
                    "test_name": "general_execution",
                    "category": cat,
                    "subtype": cat,
                    "description": "Fallimento generale dell'esecuzione dei test o timeout",
                    "raw_reason": test_output[:200] if test_output else "Nessun output"
                })

            function_error_breakdown.append({
                "function_name": func_name,
                "library": library,
                "synthesis_success": True,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "total_tests": total_tests,
                "failures": classified_failures
            })

    total_error_events = sum(category_counts.values())

    categories_summary = []
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_error_events * 100.0) if total_error_events > 0 else 0.0
        categories_summary.append({
            "category": cat,
            "count": count,
            "percentage": round(pct, 1)
        })

    subtypes_summary = []
    for sub, count in sorted(subtype_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_error_events * 100.0) if total_error_events > 0 else 0.0
        subtypes_summary.append({
            "subtype": sub,
            "count": count,
            "percentage": round(pct, 1)
        })

    # Ordina le funzioni con più errori per prime
    function_error_breakdown.sort(key=lambda x: x["tests_failed"], reverse=True)

    return {
        "summary": {
            "total_evaluated": total_evaluated,
            "successful_syntheses": successful_syntheses,
            "failed_syntheses": failed_syntheses,
            "perfect_passes": perfect_passes,
            "failing_functions": failing_functions,
            "total_error_events": total_error_events
        },
        "categories": categories_summary,
        "subtypes": subtypes_summary,
        "function_breakdown": function_error_breakdown
    }


def generate_roundtrip_error_report_markdown(
    analysis: Dict[str, Any],
    title: str = "Round-Trip Error Diagnostic Report",
    chart_filename: str = ""
) -> str:
    """
    Genera il contenuto Markdown del report di diagnosi degli errori.
    """
    sm = analysis.get("summary", {})
    categories = analysis.get("categories", [])
    subtypes = analysis.get("subtypes", [])
    breakdown = analysis.get("function_breakdown", [])

    lines = []
    lines.append(f"# {title}\n")
    lines.append("> Diagnosi automatica della tipologia degli errori riscontrati durante il Round-Trip Doc-to-Code.\n")

    if chart_filename:
        lines.append("## 📈 Dashboard Grafica degli Errori\n")
        lines.append(f"![Distribuzione Errori Round-Trip]({chart_filename})\n\n")

    # 1. Riepilogo Esecuzione
    lines.append("## 1. Riepilogo Esecuzione\n")
    lines.append("| Metrica | Valore | Note |")
    lines.append("|---|---|---|")
    lines.append(f"| **Funzioni Valutate** | `{sm.get('total_evaluated', 0)}` | Totale funzioni sottoposte al round-trip |")
    lines.append(f"| **Sintesi Riuscite** | `{sm.get('successful_syntheses', 0)}` | Codice Python generato ed eseguibile |")
    lines.append(f"| **Sintesi Fallite** | `{sm.get('failed_syntheses', 0)}` | Eccezioni o risposte vuote in fase di sintesi |")
    lines.append(f"| **Test 100% Passati** | `{sm.get('perfect_passes', 0)}` | Funzioni con tutti i test superati con successo |")
    lines.append(f"| **Funzioni con Errori** | `{sm.get('failing_functions', 0)}` | Funzioni con almeno 1 test fallito |")
    lines.append(f"| **Totale Fallimenti Test** | `{sm.get('total_error_events', 0)}` | Eventi di errore / asserzioni fallite registrate |")
    lines.append("")

    # 2. Tassonomia degli Errori
    lines.append("## 2. Distribuzione Tipologie di Errore\n")
    if not categories:
        lines.append("*Nessun errore riscontrato durante l'esecuzione!*\n")
    else:
        lines.append("| Tipologia Errore (Macro Categoria) | N. Occorrenze | Percentuale (%) | Descrizione Operativa |")
        lines.append("|---|---|---|---|")
        for c in categories:
            cat_name = c["category"]
            desc = ""
            if "Missing Symbol" in cat_name:
                desc = "Dipendenze, costanti, funzioni ausiliarie o moduli non inclusi nello scaffold."
            elif "Interface" in cat_name:
                desc = "Incompatibilità nella firma (parametri mancanti, argomenti inattesi, tipi)."
            elif "Behavioral" in cat_name:
                desc = "La logica/calcolo non produce il valore atteso dal test (discrepanza di contratto)."
            elif "Test Harness" in cat_name:
                desc = "Problemi nei test sintetizzati o mancata eccezione attesa (DID NOT RAISE)."
            elif "Syntax" in cat_name:
                desc = "Codice Python non valido sintatticamente generato dall'LLM."
            elif "Timeout" in cat_name:
                desc = "I test hanno ecceduto il tempo limite di esecuzione."
            else:
                desc = "Altre eccezioni di runtime durante l'esecuzione del codice generato."
            lines.append(f"| **{cat_name}** | `{c['count']}` | **{c['percentage']}%** | {desc} |")
        lines.append("")

    # 3. Sottotipi
    if subtypes:
        lines.append("### Dettaglio per Sottotipo di Errore\n")
        lines.append("| Sottotipo / Eccezione | N. Occorrenze | Percentuale (%) |")
        lines.append("|---|---|---|")
        for s in subtypes[:10]:
            lines.append(f"| `{s['subtype']}` | `{s['count']}` | {s['percentage']}% |")
        lines.append("")

    # 4. Funzioni con Maggior Numero di Errori
    lines.append("## 3. Top Funzioni per Numero di Errori\n")
    if not breakdown:
        lines.append("*Tutte le funzioni hanno superato i test senza errori.*\n")
    else:
        lines.append("| Libreria | Funzione | Test Falliti / Totali | Principali Tipologie di Errore |")
        lines.append("|---|---|---|---|")
        for item in breakdown[:15]:
            fail_types = {f["category"] for f in item.get("failures", [])}
            types_str = ", ".join(f"`{t}`" for t in sorted(fail_types)) if fail_types else "Nessuno"
            lines.append(f"| **{item.get('library', '-')}** | `{item.get('function_name', '-')}` | `{item.get('tests_failed', 0)} / {item.get('total_tests', 0)}` | {types_str} |")
        lines.append("")

    # 5. Dettaglio Errori per Funzione
    lines.append("## 4. Dettaglio dei Fallimenti per Funzione (con Errore Esatto Ricevuto)\n")
    if not breakdown:
        lines.append("*Nessun dettaglio da mostrare.*")
    else:
        for item in breakdown:
            f_name = item.get("function_name", "unknown")
            lib = item.get("library", "unknown")
            failures = item.get("failures", [])
            lines.append(f"<details><summary><b>{lib} :: {f_name}</b> ({len(failures)} errori)</summary>\n")
            lines.append("| Test Fallito | Categoria | Sottotipo | Errore Ricevuto (Messaggio Completo) |")
            lines.append("|---|---|---|---|")
            for fl in failures:
                t_name = fl.get("test_name", "test")
                cat = fl.get("category", "-")
                sub = fl.get("subtype", "-")
                reason = fl.get("raw_reason", "").replace("\n", " ").strip()
                # Mantieni leggibilità e mostra l'errore effettivo completo
                if not reason:
                    reason = "Nessun messaggio di errore esplicito registrato"
                lines.append(f"| `{t_name}` | **{cat}** | `{sub}` | `{reason}` |")
            lines.append("\n</details>\n")

    # 6. Conclusioni e Raccomandazioni
    lines.append("## 5. Raccomandazioni per il Miglioramento della Sintesi\n")
    missing_sym = next((c["count"] for c in categories if "Missing Symbol" in c["category"]), 0)
    sig_mismatch = next((c["count"] for c in categories if "Interface" in c["category"]), 0)
    behavioral = next((c["count"] for c in categories if "Behavioral" in c["category"]), 0)

    if missing_sym > 0:
        lines.append(f"- **Simboli Mancanti ({missing_sym} occorrenze)**: Fornire nei prompt o nello scaffold i moduli di utilità, costanti e funzioni helper correlate della libreria da cui la funzione dipende.\n")
    if sig_mismatch > 0:
        lines.append(f"- **Discrepanze di Firma/Tipi ({sig_mismatch} occorrenze)**: Migliorare l'estrazione e il rendering dei tipi e nomi esatti dei parametri nella docstring per evitare mismatch di invocazione.\n")
    if behavioral > 0:
        lines.append(f"- **Contratti Comportamentali ({behavioral} occorrenze)**: Arricchire la docstring con casi d'uso concreti, contratti di pre/post condizione ed esempi numerici/esplicativi.\n")

    return "\n".join(lines)


def save_roundtrip_error_report(
    analysis: Dict[str, Any],
    output_md_path: str,
    output_json_path: Optional[str] = None,
    title: str = "Round-Trip Error Diagnostic Report",
    chart_filename: str = ""
) -> str:
    """
    Salva il report Markdown (ed eventualmente JSON) dell'analisi errori su disco.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_md_path)), exist_ok=True)
    md_content = generate_roundtrip_error_report_markdown(analysis, title=title, chart_filename=chart_filename)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    if output_json_path:
        import json
        os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

    return output_md_path
