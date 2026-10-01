"""
parse_codewiki_to_benchmark.py
-------------------------------
Script adattatore che mappa la documentazione generata da CodeWiki
(file Markdown a livello di modulo/classe nella cartella compare_CodeWiki/)
alle singole funzioni/metodi presenti nel database di benchmark (benchmark.db)
per la libreria TinyXML-2.

L'output è un file JSON compatibile con il framework di metriche della tesi:
    compare_CodeWiki/codewiki_mapped_functions.json

Ogni record del JSON contiene:
    - function_name    : nome canonico nel formato "ClassName::MethodName"
    - db_id            : id del record in benchmark.db (None se non trovato)
    - class_name       : classe estratta dal markdown CodeWiki
    - method_name      : nome del metodo estratto dal markdown CodeWiki
    - signature        : firma dal benchmark.db (se disponibile)
    - return_type      : tipo di ritorno dal benchmark.db (se disponibile)
    - parameters       : parametri JSON dal benchmark.db (se disponibili)
    - source_code      : codice sorgente dal benchmark.db (se disponibile)
    - cleaned_doc      : documentazione originale (Ground Truth) dal benchmark.db
    - codewiki_doc     : testo descrittivo estratto dal Markdown di CodeWiki
    - codewiki_context : contesto del modulo/sezione CodeWiki da cui è estratto
    - source_file      : nome del file Markdown CodeWiki sorgente
    - doc_source       : "bullet" (testo reale CodeWiki) o "mermaid" (solo menzione
                         nel classDiagram, senza testo descrittivo)
    - matched          : True se trovato nel benchmark.db, False altrimenti
    - match_score      : 1.0 per exact/exact_ci, 0.95 per inherited; per "none" è
                         la similarità del candidato DB più vicino (solo diagnostica)
    - match_strategy   : "exact", "exact_ci", "inherited" (metodo dichiarato in una
                         classe base, es. XMLDocument::Accept -> XMLNode::Accept) o "none"
    - db_ids           : tutti gli id DB della funzione (varianti .h e .cpp)
    - closest_db_candidate : per i non matchati, la funzione DB più simile (revisione manuale)

Nota: nel DB molte funzioni compaiono due volte (dichiarazione nel .h e
definizione nel .cpp) con lo stesso Ground Truth. L'unità di confronto è
quindi il nome canonico "ClassName::MethodName", non l'id.
Il matching fuzzy e quello per solo nome metodo sono stati rimossi perché
producevano falsi positivi (es. PushDepth -> Parse, VisitEnter -> CStr).

Alla fine viene stampato un report di copertura:
    - N funzioni totali in DB per TinyXML-2
    - N funzioni di DB matchate da CodeWiki
    - N funzioni estratte da CodeWiki (con e senza match)
    - Coverage % (funzioni DB coperte da CodeWiki)
"""

import os
import re
import sys
import json
import sqlite3
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# ── Percorsi ──────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEWIKI_DIR = os.path.join(ROOT_DIR, "compare_CodeWiki")
DB_PATH = os.path.join(ROOT_DIR, "dataset", "benchmark.db")
OUTPUT_JSON = os.path.join(CODEWIKI_DIR, "codewiki_mapped_functions.json")

# Libreria target nel database
TARGET_LIBRARY = "TinyXML-2"

# Gerarchia di ereditarietà di TinyXML-2 (classe derivata -> classi base).
# Usata per il matching "inherited": un metodo descritto da CodeWiki su una
# classe derivata viene associato alla dichiarazione nella classe base.
CLASS_BASES = {
    "XMLDocument": ["XMLNode"],
    "XMLElement": ["XMLNode"],
    "XMLText": ["XMLNode"],
    "XMLComment": ["XMLNode"],
    "XMLDeclaration": ["XMLNode"],
    "XMLUnknown": ["XMLNode"],
    "XMLPrinter": ["XMLVisitor"],
}

# File da ignorare nella directory CodeWiki
SKIP_FILES = {"overview.md", "module_tree.json", "first_module_tree.json", "metadata.json",
              "codewiki_metrics_report.md"}


# ── Utilities di pulizia testo ─────────────────────────────────────────────────

def clean_backtick_name(text: str) -> str:
    """Rimuove backtick e parentesi da un nome di metodo come `GetDocument()` → GetDocument."""
    return re.sub(r"[`()\[\]]", "", text).strip()


def similarity(a: str, b: str) -> float:
    """Calcola la similarità tra due stringhe in [0.0, 1.0]."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ── Parser dei file Markdown CodeWiki ─────────────────────────────────────────

def parse_codewiki_markdown(filepath: str) -> List[Dict]:
    """
    Effettua il parsing di un singolo file Markdown prodotto da CodeWiki.

    Struttura attesa nei file:
        ### ClassName
        ...testo introduttivo della classe...
        * `MethodName()`: descrizione sintetica del metodo
        * `OtherMethod()`, `AltMethod()`: descrizione alternativa

    Produce una lista di record con:
        {class_name, method_name, description, context_block, source_file}
    """
    records = []
    filename = os.path.basename(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    current_class = None
    current_section = None

    # Regex per i bullet con nomi di metodo in backtick
    # Esempi:
    #   * `GetDocument()`: Returns a pointer...
    #   *   `InsertEndChild()`, `InsertFirstChild()`: Methods for...
    METHOD_BULLET_RE = re.compile(
        r"^\s*[\*\-]\s+"                   # bullet point
        r"(`[^`]+`(?:,\s*`[^`]+`)*)"       # uno o più nomi in backtick
        r"\s*[:–\-]\s*"                     # separatore (:, –, -)
        r"(.+)$"                            # descrizione
    )

    # Intestazione di classe specifica (### ClassName)
    CLASS_HEADER_RE = re.compile(r"^###\s+`?([A-Za-z_][A-Za-z0-9_:]*)`?\s*$")
    # Qualsiasi intestazione markdown
    SECTION_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)")

    for i, line in enumerate(lines):
        section_match = SECTION_HEADER_RE.match(line)
        if section_match:
            level = len(section_match.group(1))
            section_title = section_match.group(2).strip()

            class_match = CLASS_HEADER_RE.match(line)
            if class_match:
                # Nuova classe trovata a livello ###
                current_class = class_match.group(1).strip().rstrip(":")
                current_section = section_title
            else:
                current_section = section_title
                # Se torniamo a un livello # o ## azzeriamo la classe corrente
                if level <= 2:
                    current_class = None
            continue

        # Controlla se è un bullet con metodo
        bullet_match = METHOD_BULLET_RE.match(line)
        if bullet_match and current_class:
            raw_names_str = bullet_match.group(1)
            description = bullet_match.group(2).strip()

            # Raccoglie righe di descrizione multiriga (righe successive rientranti)
            extended_desc_lines = [description]
            for j in range(i + 1, min(i + 6, len(lines))):
                next_line = lines[j]
                if (next_line.startswith("      ") or next_line.startswith("\t")) and not next_line.strip().startswith("*"):
                    extended_desc_lines.append(next_line.strip())
                else:
                    break
            full_description = " ".join(extended_desc_lines).strip()

            # Estrai tutti i nomi di metodo in backtick
            names_in_backticks = re.findall(r"`([^`]+)`", raw_names_str)

            for raw_name in names_in_backticks:
                # Pulisce il nome rimuovendo const/override/argomenti tipizzati
                method_base = clean_backtick_name(raw_name)
                method_base = re.sub(r"\s*(const|override|noexcept|=\s*0|final)\s*$", "", method_base).strip()
                method_name = method_base.split("(")[0].strip()

                if not method_name or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", method_name):
                    continue

                records.append({
                    "class_name": current_class,
                    "method_name": method_name,
                    "raw_method_signature": raw_name,
                    "description": full_description,
                    "doc_source": "bullet",
                    "context_block": current_section or "",
                    "source_file": filename,
                })

    # ── Fallback: estrai metodi dai diagrammi Mermaid classDiagram ────────────
    # CodeWiki usa:  +MethodName(params) ReturnType  all'interno di class Foo {}
    mermaid_class_re = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
    mermaid_method_re = re.compile(r"^\s*[+\-#~]\s*([A-Za-z_][A-Za-z0-9_]*)\s*[\(\(]")
    in_mermaid = False
    mermaid_current_class = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```mermaid"):
            in_mermaid = True
            mermaid_current_class = None
            continue
        if stripped == "```" and in_mermaid:
            in_mermaid = False
            mermaid_current_class = None
            continue
        if not in_mermaid:
            continue

        cm = mermaid_class_re.match(line)
        if cm:
            mermaid_current_class = cm.group(1)
            continue

        mm = mermaid_method_re.match(line)
        if mm and mermaid_current_class:
            method_name = mm.group(1).strip()
            # Evita duplicati con i bullet già estratti
            existing = {r["method_name"] for r in records if r["class_name"] == mermaid_current_class}
            if method_name not in existing:
                records.append({
                    "class_name": mermaid_current_class,
                    "method_name": method_name,
                    "raw_method_signature": stripped,
                    "description": (
                        f"[da diagramma Mermaid] Metodo `{method_name}` "
                        f"della classe `{mermaid_current_class}`."
                    ),
                    "doc_source": "mermaid",
                    "context_block": "Mermaid Class Diagram",
                    "source_file": filename,
                })

    return records


def extract_all_codewiki_methods(codewiki_dir: str) -> List[Dict]:
    """Processa tutti i file Markdown nella directory CodeWiki e aggrega i record."""
    all_records = []
    md_files = [
        f for f in os.listdir(codewiki_dir)
        if f.endswith(".md") and f not in SKIP_FILES
    ]

    if not md_files:
        print(f"[WARN] Nessun file .md trovato in: {codewiki_dir}")
        return []

    for md_file in sorted(md_files):
        filepath = os.path.join(codewiki_dir, md_file)
        records = parse_codewiki_markdown(filepath)
        print(f"  [{md_file}] -> {len(records)} metodi estratti")
        all_records.extend(records)

    return all_records


# ── Caricamento del database di benchmark ──────────────────────────────────────

def load_benchmark_functions(db_path: str, library: str) -> List[Dict]:
    """Carica tutte le funzioni della libreria target dal database di benchmark."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, library, function_name, signature, return_type,
               parameters, source_code, cleaned_doc, raw_comment
        FROM benchmark_functions
        WHERE library = ?
        ORDER BY id
        """,
        (library,),
    ).fetchall()
    conn.close()

    functions = []
    for row in rows:
        params = []
        if row["parameters"]:
            try:
                params = json.loads(row["parameters"])
            except (json.JSONDecodeError, TypeError):
                params = []
        functions.append({
            "db_id": row["id"],
            "function_name": row["function_name"],
            "signature": row["signature"],
            "return_type": row["return_type"],
            "parameters": params,
            "source_code": row["source_code"] or "",
            "cleaned_doc": row["cleaned_doc"] or "",
            "raw_comment": row["raw_comment"] or "",
        })

    return functions


# ── Logica di Matching ─────────────────────────────────────────────────────────

def group_db_functions(db_functions: List[Dict]) -> Dict[str, Dict]:
    """
    Raggruppa le righe DB per nome canonico "ClassName::MethodName".
    Le varianti .h/.cpp della stessa funzione condividono lo stesso Ground Truth:
    come rappresentante si usa la variante .h (presente per ogni funzione),
    conservando l'elenco completo degli id in "db_ids". Il source_code viene
    invece preso dalla variante .cpp quando esiste, perché il .h contiene spesso
    solo la dichiarazione e renderebbe EDR/ECC non calcolabili.
    """
    groups: Dict[str, Dict] = {}
    for fn in db_functions:
        name = fn["function_name"]
        if name not in groups:
            groups[name] = dict(fn, db_ids=[fn["db_id"]])
            continue
        g = groups[name]
        g["db_ids"].append(fn["db_id"])
        if "_h_" in fn["db_id"] and "_h_" not in g["db_id"]:
            cpp_source = g["source_code"]
            g.update(fn)
            g["source_code"] = cpp_source
        elif "_cpp_" in fn["db_id"] and fn["source_code"]:
            g["source_code"] = fn["source_code"]
    return groups


def match_codewiki_to_db(
    codewiki_record: Dict,
    db_groups: Dict[str, Dict],
) -> Tuple[Optional[Dict], float, str, Optional[str]]:
    """
    Tenta di far corrispondere un record CodeWiki a una funzione nel DB.

    Strategie (in ordine di priorità):
    1. Exact match su "ClassName::MethodName"
    2. Case-insensitive exact match
    3. Inherited: stesso metodo dichiarato in una classe base (CLASS_BASES)

    Returns: (db_group_or_None, score, strategy_label, closest_candidate)
    """
    class_name = codewiki_record["class_name"]
    method_name = codewiki_record["method_name"]
    canonical = f"{class_name}::{method_name}"

    # 1. Exact
    if canonical in db_groups:
        return db_groups[canonical], 1.0, "exact", None

    # 2. Case-insensitive exact
    lower_index = {name.lower(): g for name, g in db_groups.items()}
    if canonical.lower() in lower_index:
        return lower_index[canonical.lower()], 1.0, "exact_ci", None

    # 3. Metodo ereditato da una classe base
    for base in CLASS_BASES.get(class_name, []):
        base_name = f"{base}::{method_name}"
        if base_name in db_groups:
            return db_groups[base_name], 0.95, "inherited", None

    # Nessun match: registra il candidato più vicino solo come diagnostica
    best_name, best_score = None, 0.0
    for name in db_groups:
        s = similarity(canonical, name)
        if s > best_score:
            best_name, best_score = name, s
    return None, round(best_score, 4), "none", best_name


# ── Assembla il JSON finale ────────────────────────────────────────────────────

def build_output_records(
    codewiki_methods: List[Dict],
    db_functions: List[Dict],
) -> Tuple[List[Dict], set]:
    """
    Combina le descrizioni CodeWiki con i metadati del DB di benchmark.
    Restituisce (output_records, db_matched_names).
    """
    db_groups = group_db_functions(db_functions)
    output = []
    db_matched_names = set()

    for record in codewiki_methods:
        db_fn, score, strategy, closest = match_codewiki_to_db(record, db_groups)

        out = {
            # Identità
            "function_name": f"{record['class_name']}::{record['method_name']}",
            "class_name": record["class_name"],
            "method_name": record["method_name"],
            "raw_method_signature": record.get("raw_method_signature", ""),
            # Documentazione CodeWiki
            "codewiki_doc": record["description"],
            "doc_source": record["doc_source"],
            "codewiki_context": record.get("context_block", ""),
            "source_file": record["source_file"],
            # Risultato del matching
            "matched": db_fn is not None,
            "match_score": score,
            "match_strategy": strategy,
            "closest_db_candidate": closest,
            # Campi dal DB (None se non matchato)
            "db_id": db_fn["db_id"] if db_fn else None,
            "db_ids": db_fn["db_ids"] if db_fn else [],
            "db_function_name": db_fn["function_name"] if db_fn else None,
            "signature": db_fn["signature"] if db_fn else None,
            "return_type": db_fn["return_type"] if db_fn else None,
            "parameters": db_fn["parameters"] if db_fn else [],
            "source_code": db_fn["source_code"] if db_fn else "",
            "cleaned_doc": db_fn["cleaned_doc"] if db_fn else "",
        }
        output.append(out)

        if db_fn is not None:
            db_matched_names.add(db_fn["function_name"])

    return output, db_matched_names


# ── Report di copertura ────────────────────────────────────────────────────────

def print_coverage_report(
    output_records: List[Dict],
    db_functions: List[Dict],
    db_matched_names: set,
):
    db_names = {fn["function_name"] for fn in db_functions}
    total_db = len(db_names)
    total_codewiki = len(output_records)
    matched_codewiki = sum(1 for r in output_records if r["matched"])
    unmatched_codewiki = total_codewiki - matched_codewiki
    documented = {
        r["db_function_name"] for r in output_records
        if r["matched"] and r["doc_source"] == "bullet"
    }
    mention_pct = (len(db_matched_names) / total_db * 100) if total_db > 0 else 0.0
    doc_pct = (len(documented) / total_db * 100) if total_db > 0 else 0.0

    strategy_counts: Dict[str, int] = {}
    for r in output_records:
        s = r["match_strategy"]
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    print()
    print("=" * 65)
    print("  REPORT DI COPERTURA: CodeWiki → benchmark.db (TinyXML-2)")
    print("=" * 65)
    print(f"  Righe nel DB (varianti .h/.cpp):        {len(db_functions)}")
    print(f"  Funzioni uniche nel DB:                 {total_db}")
    print(f"  Menzioni di metodi in CodeWiki:         {total_codewiki}")
    print(f"  ├── Matchate al DB:                     {matched_codewiki}")
    print(f"  └── Non trovate nel DB (surplus):       {unmatched_codewiki}")
    print(f"  Funzioni DB menzionate (anche Mermaid): {len(db_matched_names)} / {total_db}  ({mention_pct:.1f}%)")
    print(f"  Funzioni DB con testo descrittivo:      {len(documented)} / {total_db}  ({doc_pct:.1f}%)")
    print()
    print("  Strategie di matching:")
    for strategy, count in sorted(strategy_counts.items()):
        print(f"    {strategy:22s}: {count}")
    print("=" * 65)

    unmatched = [r for r in output_records if not r["matched"]]
    if unmatched:
        print(f"\n  Menzioni CodeWiki senza match ({len(unmatched)}), con candidato DB più vicino:")
        for r in unmatched:
            print(f"    - {r['function_name']:35s} ~ {r['closest_db_candidate']} ({r['match_score']})")

    uncovered = sorted(db_names - db_matched_names)
    if uncovered:
        print(f"\n  Funzioni DB non coperte da CodeWiki ({len(uncovered)}):")
        for name in uncovered:
            print(f"    - {name}")
    print()


# ── Punto di ingresso ──────────────────────────────────────────────────────────

def main():
    # La console Windows (cp1252) non gestisce tutti i caratteri Unicode
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 65)
    print("  parse_codewiki_to_benchmark.py")
    print(f"  Target Library : {TARGET_LIBRARY}")
    print(f"  CodeWiki Dir   : {CODEWIKI_DIR}")
    print(f"  Database       : {DB_PATH}")
    print(f"  Output JSON    : {OUTPUT_JSON}")
    print("=" * 65)
    print()

    # 1. Parsing Markdown CodeWiki
    print("[1/4] Parsing dei file Markdown CodeWiki...")
    codewiki_methods = extract_all_codewiki_methods(CODEWIKI_DIR)
    print(f"      Totale metodi estratti: {len(codewiki_methods)}")
    print()

    if not codewiki_methods:
        print("[ERRORE] Nessun metodo estratto. Verifica i file in compare_CodeWiki/")
        sys.exit(1)

    # 2. Carica funzioni dal database
    print("[2/4] Caricamento funzioni dal benchmark.db...")
    db_functions = load_benchmark_functions(DB_PATH, TARGET_LIBRARY)
    print(f"      Trovate {len(db_functions)} funzioni per '{TARGET_LIBRARY}'")
    print()

    if not db_functions:
        print(f"[ERRORE] Nessuna funzione trovata per '{TARGET_LIBRARY}' in {DB_PATH}")
        sys.exit(1)

    # 3. Mapping CodeWiki → DB
    print("[3/4] Mapping CodeWiki → benchmark.db...")
    output_records, db_matched_names = build_output_records(codewiki_methods, db_functions)
    print(f"      Record output generati: {len(output_records)}")
    print()

    # 4. Salva JSON
    print(f"[4/4] Salvataggio JSON in: {OUTPUT_JSON}")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_records, f, ensure_ascii=False, indent=2)
    print(f"      Salvato con successo ({os.path.getsize(OUTPUT_JSON):,} bytes)")
    print()

    # Report finale
    print_coverage_report(output_records, db_functions, db_matched_names)


if __name__ == "__main__":
    main()

