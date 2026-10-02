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
    - match_score      : 1.0 per exact/exact_ci, 0.98 per namespace_stripped, 0.95 per
                         inherited, 0.0 per "none"
    - match_strategy   : "exact", "exact_ci", "inherited" (metodo dichiarato in una
                         classe base, es. XMLDocument::Accept -> XMLNode::Accept) o "none"
    - db_ids           : tutti gli id DB della funzione (varianti .h e .cpp)

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
import argparse
from typing import Dict, List, Optional, Tuple

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.codewiki_config import (
    DB_PATH,
    class_bases,
    is_class_style,
    is_header_file,
    is_impl_file,
    lib_paths,
    resolve_library,
)

# File da ignorare nella directory CodeWiki (documentazione di servizio e output del confronto)
SKIP_FILES = {"overview.md", "module_tree.json", "first_module_tree.json", "metadata.json"}
SKIP_PREFIXES = ("codewiki_",)


# ── Utilities di pulizia testo ─────────────────────────────────────────────────

def clean_backtick_name(text: str) -> str:
    """Rimuove backtick e parentesi da un nome di metodo come `GetDocument()` → GetDocument."""
    return re.sub(r"[`()\[\]]", "", text).strip()


# ── Parser dei file Markdown CodeWiki ─────────────────────────────────────────

def parse_class_style_markdown(filepath: str) -> List[Dict]:
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


# ── Parser per librerie C / funzioni libere ───────────────────────────────────
# CodeWiki non usa una struttura fissa per le librerie C: le funzioni compaiono in
# bullet ("- **`cJSON_Parse(const char *v)`**: ..."), tabelle, titoli di sezione
# ("### `cJSON_Parse`") e diagrammi Mermaid. Si estraggono gli identificatori che
# compaiono come SOGGETTO (prima del separatore di un bullet, prima cella di una
# tabella, titolo di sezione); i nomi citati solo nella descrizione ("wrapper di
# `cJSON_ParseWithOpts`") non sono soggetti e vengono ignorati.

_IDENT = r"~?[A-Za-z_][A-Za-z0-9_]*"
_QUALIFIED_RE = re.compile(rf"{_IDENT}(?:::{_IDENT})*")
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_BULLET_RE = re.compile(r"^(\s*)[*\-+]\s+(.*)$")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
_TABLE_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARATORS = (":", " – ", " — ", " - ", " → ", " -> ", "$\\rightarrow$")
_SECTION_DESC_MAX_CHARS = 1200


def _split_head_description(text: str) -> Tuple[str, str]:
    """Divide un bullet in (soggetto, descrizione) al primo separatore fuori dai backtick."""
    spans = [(m.start(), m.end()) for m in _BACKTICK_RE.finditer(text)]

    def inside(pos: int) -> bool:
        return any(a <= pos < b for a, b in spans)

    best = None
    for sep in _SEPARATORS:
        start = 0
        while True:
            i = text.find(sep, start)
            if i == -1:
                break
            if not inside(i):
                if best is None or i < best[0]:
                    best = (i, sep)
                break
            start = i + 1
    if best is None:
        return text, ""
    i, sep = best
    return text[:i], text[i + len(sep):].strip()


def _identifiers_from_token(token: str) -> List[Tuple[str, bool]]:
    """
    Da un token tra backtick estrae (nome, ha_sintassi_di_chiamata).
    `cJSON_Parse(const char *v)` -> [("cJSON_Parse", True)]
    `const char *cJSON_Version(void)` -> [("cJSON_Version", True)]
    `fmt::format` -> [("fmt::format", False)]
    Token con spazi e senza parentesi (tipi, frasi) non sono funzioni.
    """
    token = token.strip().strip("*").strip()
    if "(" in token:
        pre = token.split("(", 1)[0]
        if not pre or pre[-1].isspace():
            return []  # "Floating-Point Value (T)": una frase, non una chiamata
        found = _QUALIFIED_RE.findall(pre)
        return [(found[-1], True)] if found else []
    if _QUALIFIED_RE.fullmatch(token):
        return [(token, False)]
    return []


def _subjects(head: str) -> List[Tuple[str, bool]]:
    out: List[Tuple[str, bool]] = []
    for m in _BACKTICK_RE.finditer(head):
        out.extend(_identifiers_from_token(m.group(1)))
    return out


def _fence_state(line: str, in_fence: bool) -> Tuple[bool, bool]:
    """(in_fence_dopo_la_riga, la_riga_e_un_delimitatore)."""
    if line.strip().startswith("```"):
        return (not in_fence), True
    return in_fence, False


def _section_text(lines: List[str], start: int) -> str:
    """Testo (esclusi i blocchi di codice) dalla riga `start` fino al titolo successivo."""
    body, fence = [], False
    for line in lines[start:]:
        if not fence and _HEADING_RE.match(line):
            break
        fence, delim = _fence_state(line, fence)
        if not delim and not fence and line.strip():
            body.append(line.strip())
    return " ".join(body)[:_SECTION_DESC_MAX_CHARS].strip()


def parse_function_style_markdown(filepath: str) -> List[Dict]:
    """
    Estrae le menzioni di funzioni da un file Markdown CodeWiki di una libreria C o con
    funzioni libere. Ogni record ha: mention (nome come scritto da CodeWiki, eventualmente
    qualificato), method_name, description, doc_source ("bullet", "mention" se senza testo
    descrittivo, "mermaid"), call_syntax (il nome compare con parentesi) e context_block.
    """
    filename = os.path.basename(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    records: List[Dict] = []
    seen = set()

    def add(mention: str, description: str, doc_source: str, context: str, call_syntax: bool):
        key = (mention, description)
        if key in seen:
            return
        seen.add(key)
        records.append({
            "class_name": None,
            "method_name": mention.split("::")[-1],
            "mention": mention,
            "raw_method_signature": mention,
            "description": description,
            "doc_source": doc_source,
            "context_block": context,
            "source_file": filename,
            "call_syntax": call_syntax,
        })

    section = ""
    in_fence = False
    for i, line in enumerate(lines):
        in_fence, is_delim = _fence_state(line, in_fence)
        if is_delim or in_fence:
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            section = heading.group(1).strip()
            subjects = _subjects(section)
            if subjects:
                # il testo della sezione descrive i soggetti del titolo
                text = _section_text(lines, i + 1)
                for name, call in subjects:
                    add(name, text, "bullet" if text else "mention", section, call)
            continue

        bullet = _BULLET_RE.match(line)
        if bullet:
            indent, text = len(bullet.group(1)), bullet.group(2).strip()
            # righe di continuazione: piu' rientrate del bullet e non a loro volta bullet
            for nxt in lines[i + 1:i + 6]:
                if (nxt.strip() and not _BULLET_RE.match(nxt) and not _HEADING_RE.match(nxt)
                        and not nxt.strip().startswith("```")
                        and len(nxt) - len(nxt.lstrip()) > indent):
                    text += " " + nxt.strip()
                else:
                    break
            head, desc = _split_head_description(text)
            only_names = not re.sub(r"[*\s,/;&]|\band\b|\bor\b", "", _BACKTICK_RE.sub("", head))
            if not _subjects(head) and desc and not re.sub(
                    r"[*\s,/;&.]|\band\b|\bor\b|\betc\b", "", _BACKTICK_RE.sub("", desc)):
                # "- **Etichetta**: `f1()`, `f2()`": elenco di nomi sotto un'etichetta, senza descrizioni
                for name, call in _subjects(desc):
                    add(name, "", "mention", section, call)
                continue
            for name, call in _subjects(head):
                if desc:
                    add(name, desc, "bullet", section, call)
                elif only_names:
                    # il bullet e' solo un elenco di nomi, senza testo descrittivo
                    add(name, "", "mention", section, call)
            continue

        table = _TABLE_RE.match(line)
        if table:
            cells = [c.strip() for c in table.group(1).split("|")]
            if cells and not re.fullmatch(r"[\s:\-]*", cells[0]):
                desc = " ".join(c for c in cells[1:] if c and not re.fullmatch(r"[\s:\-]*", c))
                for name, call in _subjects(cells[0]):
                    add(name, desc, "bullet" if desc else "mention", section, call)

    # Metodi nei diagrammi Mermaid classDiagram: "+nome(params) Tipo" dentro "class X { }"
    mermaid_class_re = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
    mermaid_method_re = re.compile(r"^\s*[+\-#~]\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    in_mermaid, cur_class = False, None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```mermaid"):
            in_mermaid, cur_class = True, None
            continue
        if stripped == "```" and in_mermaid:
            in_mermaid, cur_class = False, None
            continue
        if not in_mermaid:
            continue
        cm = mermaid_class_re.match(line)
        if cm:
            cur_class = cm.group(1)
            continue
        mm = mermaid_method_re.match(line)
        if mm and cur_class:
            add(f"{cur_class}::{mm.group(1)}",
                f"[da diagramma Mermaid] Funzione `{mm.group(1)}` ({cur_class}).",
                "mermaid", "Mermaid Class Diagram", False)

    return records


def list_codewiki_markdown(codewiki_dir: str) -> List[str]:
    """
    File .md con la documentazione CodeWiki. overview.md e' usato solo se la libreria non
    ha altri file di modulo (es. librerie a modulo singolo come fmt o http-parser).
    """
    all_md = [f for f in os.listdir(codewiki_dir) if f.endswith(".md")
              and not f.startswith(SKIP_PREFIXES)]
    modules = [f for f in all_md if f not in SKIP_FILES]
    if modules:
        return sorted(modules)
    return ["overview.md"] if "overview.md" in all_md else []


def extract_all_codewiki_methods(codewiki_dir: str, library: str) -> List[Dict]:
    """Processa i file Markdown CodeWiki della libreria e aggrega i record."""
    all_records: List[Dict] = []
    md_files = list_codewiki_markdown(codewiki_dir)
    if not md_files:
        print(f"[WARN] Nessun file .md trovato in: {codewiki_dir}")
        return []

    parser_fn = parse_class_style_markdown if is_class_style(library) else parse_function_style_markdown
    for md_file in md_files:
        records = parser_fn(os.path.join(codewiki_dir, md_file))
        print(f"  [{md_file}] -> {len(records)} menzioni estratte")
        all_records.extend(records)

    return all_records


# ── Caricamento del database di benchmark ──────────────────────────────────────

def load_benchmark_functions(db_path: str, library: str) -> List[Dict]:
    """Carica tutte le funzioni della libreria target dal database di benchmark."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, library, filename, function_name, signature, return_type,
               parameters, source_code, cleaned_doc, raw_comment
        FROM benchmark_functions
        WHERE LOWER(library) = LOWER(?)
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
            "filename": row["filename"],
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
    Raggruppa le righe DB per nome canonico ("ClassName::MethodName" in C++, nome della
    funzione in C). Le varianti header/implementazione della stessa funzione condividono
    lo stesso Ground Truth: come rappresentante si usa la variante header (presente per
    ogni funzione), conservando l'elenco completo degli id in "db_ids". Il source_code
    viene invece preso dalla variante di implementazione (.cpp/.c) quando esiste, perche'
    l'header contiene spesso solo la dichiarazione e renderebbe EDR/ECC non calcolabili.
    """
    groups: Dict[str, Dict] = {}
    for fn in db_functions:
        name = fn["function_name"]
        if name not in groups:
            groups[name] = dict(fn, db_ids=[fn["db_id"]])
            continue
        g = groups[name]
        g["db_ids"].append(fn["db_id"])
        if is_header_file(fn.get("filename")) and not is_header_file(g.get("filename")):
            impl_source = g["source_code"]
            g.update(fn)
            g["source_code"] = impl_source
        elif is_impl_file(fn.get("filename")) and fn["source_code"]:
            g["source_code"] = fn["source_code"]
    return groups


def match_codewiki_to_db(
    codewiki_record: Dict,
    db_groups: Dict[str, Dict],
    bases: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Optional[Dict], float, str]:
    """
    Tenta di far corrispondere un record CodeWiki a una funzione nel DB.

    Strategie (in ordine di priorita'):
    1. Exact match sul nome ("ClassName::MethodName" oppure nome della funzione C)
    2. Case-insensitive exact match
    3. Namespace stripped (solo funzioni libere): "fmt::format" -> "format"
    4. Inherited (solo classi): stesso metodo dichiarato in una classe base (class_bases)

    Returns: (db_group_or_None, score, strategy_label)
    """
    bases = bases or {}
    class_name = codewiki_record.get("class_name")
    mention = codewiki_record["mention"]

    # 1. Exact
    if mention in db_groups:
        return db_groups[mention], 1.0, "exact"

    # 2. Case-insensitive exact
    lower_index = {name.lower(): g for name, g in db_groups.items()}
    if mention.lower() in lower_index:
        return lower_index[mention.lower()], 1.0, "exact_ci"

    if class_name is None:
        # 3. Namespace/qualificatore iniziale rimosso (fmt::format -> format).
        # Si accorcia solo da sinistra: nessun match per solo nome di metodo di una classe.
        parts = mention.split("::")
        for i in range(1, len(parts)):
            cand = "::".join(parts[i:])
            if cand in db_groups:
                return db_groups[cand], 0.98, "namespace_stripped"
            if cand.lower() in lower_index:
                return lower_index[cand.lower()], 0.98, "namespace_stripped"
    else:
        # 4. Metodo ereditato da una classe base
        method_name = codewiki_record["method_name"]
        for base in bases.get(class_name, []):
            base_name = f"{base}::{method_name}"
            if base_name in db_groups:
                return db_groups[base_name], 0.95, "inherited"

    # Nessun match: la funzione non e' nel DB (tipicamente perche' priva di un commento
    # Doxygen proprio, quindi senza Ground Truth). Nessun matching fuzzy.
    return None, 0.0, "none"


# ── Assembla il JSON finale ────────────────────────────────────────────────────

def build_output_records(
    codewiki_methods: List[Dict],
    db_functions: List[Dict],
    library: str,
) -> Tuple[List[Dict], set]:
    """
    Combina le descrizioni CodeWiki con i metadati del DB di benchmark.
    Restituisce (output_records, db_matched_names).
    """
    db_groups = group_db_functions(db_functions)
    bases = class_bases(library)
    output = []
    db_matched_names = set()

    for record in codewiki_methods:
        if record.get("class_name"):
            record["mention"] = f"{record['class_name']}::{record['method_name']}"
        db_fn, score, strategy = match_codewiki_to_db(record, db_groups, bases)

        # Parser per funzioni libere: un identificatore non presente nel DB e senza sintassi
        # di chiamata e' quasi certamente un tipo/struct/campo, non una funzione mancante.
        if db_fn is None and not record.get("class_name") and not record.get("call_syntax", True):
            continue

        out = {
            # Identita'
            "library": library,
            "function_name": record["mention"],
            "class_name": record.get("class_name"),
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
    library: str,
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
        if r["matched"] and r["doc_source"] == "bullet" and r["codewiki_doc"].strip()
    }
    mention_pct = (len(db_matched_names) / total_db * 100) if total_db > 0 else 0.0
    doc_pct = (len(documented) / total_db * 100) if total_db > 0 else 0.0

    strategy_counts: Dict[str, int] = {}
    for r in output_records:
        s = r["match_strategy"]
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    print()
    print("=" * 65)
    print(f"  REPORT DI COPERTURA: CodeWiki → benchmark.db ({library})")
    print("=" * 65)
    print(f"  Righe nel DB (varianti header/implementazione): {len(db_functions)}")
    print(f"  Funzioni uniche nel DB:                 {total_db}")
    print(f"  Menzioni di funzioni in CodeWiki:       {total_codewiki}")
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
        print(f"\n  Menzioni CodeWiki non presenti nel DB, senza Ground Truth ({len(unmatched)}):")
        for r in unmatched:
            print(f"    - {r['function_name']}")

    uncovered = sorted(db_names - db_matched_names)
    if uncovered:
        print(f"\n  Funzioni DB non coperte da CodeWiki ({len(uncovered)}):")
        for name in uncovered:
            print(f"    - {name}")
    print()


# ── Punto di ingresso ──────────────────────────────────────────────────────────

def run(library: str) -> Optional[str]:
    """
    Mappa la documentazione CodeWiki di `library` sul benchmark.db.
    Restituisce il percorso del JSON prodotto, oppure None se non c'e' nulla da mappare.
    """
    canonical = resolve_library(library)
    if canonical is None:
        print(f"[ERRORE] '{library}' non e' presente in {DB_PATH}")
        return None
    library = canonical
    paths = lib_paths(library)

    print("=" * 65)
    print("  parse_codewiki_to_benchmark.py")
    print(f"  Target Library : {library}")
    print(f"  CodeWiki Dir   : {paths.dir}")
    print(f"  Database       : {DB_PATH}")
    print(f"  Output JSON    : {paths.mapped_json}")
    print("=" * 65)
    print()

    if not os.path.isdir(paths.dir):
        print(f"[ERRORE] Cartella CodeWiki non trovata: {paths.dir}")
        return None

    # 1. Parsing Markdown CodeWiki
    print("[1/4] Parsing dei file Markdown CodeWiki...")
    codewiki_methods = extract_all_codewiki_methods(paths.dir, library)
    print(f"      Totale menzioni estratte: {len(codewiki_methods)}")
    print()

    if not codewiki_methods:
        print(f"[ERRORE] Nessuna menzione estratta. Verifica i file in {paths.dir}")
        return None

    # 2. Carica funzioni dal database
    print("[2/4] Caricamento funzioni dal benchmark.db...")
    db_functions = load_benchmark_functions(DB_PATH, library)
    print(f"      Trovate {len(db_functions)} funzioni per '{library}'")
    print()

    if not db_functions:
        print(f"[ERRORE] Nessuna funzione trovata per '{library}' in {DB_PATH}")
        return None

    # 3. Mapping CodeWiki → DB
    print("[3/4] Mapping CodeWiki → benchmark.db...")
    output_records, db_matched_names = build_output_records(codewiki_methods, db_functions, library)
    print(f"      Record output generati: {len(output_records)}")
    print()

    # 4. Salva JSON
    print(f"[4/4] Salvataggio JSON in: {paths.mapped_json}")
    with open(paths.mapped_json, "w", encoding="utf-8") as f:
        json.dump(output_records, f, ensure_ascii=False, indent=2)
    print(f"      Salvato con successo ({os.path.getsize(paths.mapped_json):,} bytes)")
    print()

    # Report finale
    print_coverage_report(library, output_records, db_functions, db_matched_names)
    return paths.mapped_json


def main():
    # La console Windows (cp1252) non gestisce tutti i caratteri Unicode
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Mappa la documentazione CodeWiki di una libreria sulle funzioni del benchmark.db"
    )
    parser.add_argument("-l", "--library", default="TinyXML-2",
                        help="Libreria da mappare (default: TinyXML-2); per tutte usa compare_codewiki.py")
    args = parser.parse_args()
    if run(args.library) is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
