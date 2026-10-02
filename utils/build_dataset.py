"""
Script per la costruzione del dataset di benchmark (Ground Truth).
Scarica i file sorgente C/C++ (cJSON per C, OpenCV core per C++),
effettua il parsing AST con Clang integrato con un resolver di commenti di documentazione, ed estrae:
- Nome funzione
- Firma completa
- Codice sorgente dell'implementazione
- Documentazione originale (commenti Doxygen / commenti di blocco C di riferimento)
- Metriche AST (complessità Big-O stimata)
Salva i risultati in dataset/ground_truth.jsonl e dataset/benchmark.db.

Ground Truth: ogni funzione deve avere una documentazione originale valida.
  - doc_origin = "own":   commento proprio della funzione (adiacente alla dichiarazione/definizione).
  - doc_origin = "group": la funzione non ha un commento proprio ma fa parte di un blocco di
    dichiarazioni contigue che condividono un commento (es. "These calls create a cJSON item of
    the appropriate type." sopra cJSON_CreateNull/True/False/Bool/...). Il commento del gruppo viene
    esteso ai suoi membri e in coda a cleaned_doc si aggiunge "Variant: <parte variabile del nome>"
    (es. cJSON_CreateBool -> "Variant: Bool"). Il gruppo e' accettato solo se i nomi dei membri
    formano una famiglia (vedi is_name_family), per non attribuire a una funzione il commento di
    una funzione diversa.

Uso:
  .venv/Scripts/python utils/build_dataset.py                     # riscrive dataset/
  .venv/Scripts/python utils/build_dataset.py --output-dir DIR    # anteprima in un'altra cartella
  .venv/Scripts/python utils/build_dataset.py --no-group-comments # solo commenti propri
"""

import os
import sys
import json
import sqlite3
import urllib.request
import re
from typing import List, Dict, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.extract_metadata import CCodeExtractor

DATASET_DIR = os.path.join(ROOT_DIR, "dataset")
SOURCES_DIR = os.path.join(DATASET_DIR, "sources")
DB_PATH = os.path.join(DATASET_DIR, "benchmark.db")
JSONL_PATH = os.path.join(DATASET_DIR, "ground_truth.jsonl")

SOURCES = [
    {
        "library": "cJSON",
        "language": "c",
        "files": [
            {
                "filename": "cJSON.h",
                "url": "https://raw.githubusercontent.com/DaveGamble/cJSON/master/cJSON.h"
            },
            {
                "filename": "cJSON.c",
                "url": "https://raw.githubusercontent.com/DaveGamble/cJSON/master/cJSON.c"
            }
        ]
    },
    {
        "library": "OpenCV",
        "language": "cpp",
        "files": [
            {
                "filename": "fast_math.hpp",
                "url": "https://raw.githubusercontent.com/opencv/opencv/4.x/modules/core/include/opencv2/core/fast_math.hpp"
            },
            {
                "filename": "cvstd.hpp",
                "url": "https://raw.githubusercontent.com/opencv/opencv/4.x/modules/core/include/opencv2/core/cvstd.hpp"
            },
            {
                "filename": "saturate.hpp",
                "url": "https://raw.githubusercontent.com/opencv/opencv/4.x/modules/core/include/opencv2/core/saturate.hpp"
            }
        ]
    },
    {
        "library": "TinyXML-2",
        "language": "cpp",
        "files": [
            {
                "filename": "tinyxml2.h",
                "url": "https://raw.githubusercontent.com/leethomason/tinyxml2/master/tinyxml2.h"
            },
            {
                "filename": "tinyxml2.cpp",
                "url": "https://raw.githubusercontent.com/leethomason/tinyxml2/master/tinyxml2.cpp"
            }
        ]
    },
    {
        "library": "sds",
        "language": "c",
        "files": [
            {
                "filename": "sds.h",
                "url": "https://raw.githubusercontent.com/antirez/sds/master/sds.h"
            },
            {
                "filename": "sds.c",
                "url": "https://raw.githubusercontent.com/antirez/sds/master/sds.c"
            }
        ]
    },
    {
        "library": "fmt",
        "language": "cpp",
        "files": [
            {
                "filename": "format.h",
                "url": "https://raw.githubusercontent.com/fmtlib/fmt/master/include/fmt/format.h"
            }
        ]
    },
    {
        "library": "miniz",
        "language": "c",
        "files": [
            {
                "filename": "miniz.h",
                "url": "https://raw.githubusercontent.com/richgel999/miniz/master/miniz.h"
            },
            {
                "filename": "miniz.c",
                "url": "https://raw.githubusercontent.com/richgel999/miniz/master/miniz.c"
            }
        ]
    },
    {
        "library": "http-parser",
        "language": "c",
        "files": [
            {
                "filename": "http_parser.h",
                "url": "https://raw.githubusercontent.com/nodejs/http-parser/master/http_parser.h"
            },
            {
                "filename": "http_parser.c",
                "url": "https://raw.githubusercontent.com/nodejs/http-parser/master/http_parser.c"
            }
        ]
    }
]

def ensure_directories():
    os.makedirs(DATASET_DIR, exist_ok=True)
    os.makedirs(SOURCES_DIR, exist_ok=True)

def download_file(url: str, dest_path: str):
    print(f"-> Scaricamento: {url} -> {dest_path}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())

def clean_doxygen_comment(raw: str) -> str:
    """Pulisce la docstring Doxygen rimuovendo marcatori /**, /*!, *, ecc."""
    if not raw:
        return ""
    lines = raw.strip().splitlines()
    cleaned = []
    for line in lines:
        l = line.strip()
        l = re.sub(r"^(/\*\*|/\*!|/\*|///|//!|\*/|\*) ?", "", l)
        l = l.rstrip("*/").rstrip()
        if l:
            cleaned.append(l)
    return "\n".join(cleaned).strip()

def is_valid_ground_truth(cleaned: str) -> bool:
    """
    Verifica se il commento estratto e' una documentazione valida e non un placeholder o mero rimando.
    Scarta commenti come '@overload', 'See ...', 'Assignment', o spiegazioni banali sotto i 20 caratteri.
    """
    if not cleaned or len(cleaned.strip()) < 20:
        return False
    
    lowered = cleaned.lower().strip()
    
    # Riconoscimento ed esclusione di rimandi, overload e placeholder
    placeholder_patterns = [
        r"^@overload\b",
        r"^see\s+[a-zA-Z0-9_]+$",
        r"^see\s+also\b",
        r"^assignment\b",
        r"^constructor\b",
        r"^destructor\b",
        r"^not\s+supported\b",
        r"^internal\s+use\b",
        r"^todo\b"
    ]
    for pat in placeholder_patterns:
        if re.search(pat, lowered):
            return False
            
    return True

def extract_c_comments_from_file(file_path: str) -> Dict[str, str]:
    """
    Estrae i blocchi di commento posti prima delle dichiarazioni o definizioni
    di funzione in un file C (header o file .c, es. cJSON.h, sds.c).
    """
    comments = {}
    if not os.path.exists(file_path):
        return comments
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    current_comments = []
    inside_block_comment = False
    
    for i, line in enumerate(lines):
        s = line.strip()
        
        # Commento su singola riga /* ... */
        if s.startswith("/*") and s.endswith("*/") and len(s) > 4:
            current_comments = [s]
            inside_block_comment = False
            # Ispezioniamo le righe successive (entro 8 righe) per trovare la funzione
            cmt_text = s
            next_block = " ".join([lines[k].strip() for k in range(i + 1, min(i + 9, len(lines))) if lines[k].strip()])
            
            m_cjson = re.search(r"CJSON_PUBLIC\([^)]+\)\s*([a-zA-Z0-9_]+)", next_block)
            if m_cjson:
                comments[m_cjson.group(1)] = cmt_text
                continue
            
            m_miniz = re.search(r"MINIZ_EXPORT\s+(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\(", next_block)
            if m_miniz:
                comments[m_miniz.group(1)] = cmt_text
                continue

            m_func = re.search(r"^(?:(?:static|inline|extern|const|unsigned|signed|size_t|uint[0-9]+_t|int[0-9]+_t|void|struct\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)\s+[*&]*)+([a-zA-Z0-9_]+)\s*\(", next_block)
            if m_func:
                fn = m_func.group(1)
                if fn not in ("if", "for", "while", "switch", "return", "sizeof"):
                    comments[fn] = cmt_text
                    continue
            continue

        # Inizio blocco commento multi-riga
        if s.startswith("/*"):
            current_comments = [s]
            inside_block_comment = True
            continue
            
        if inside_block_comment:
            current_comments.append(s)
            if s.endswith("*/"):
                inside_block_comment = False
                # Ispezioniamo le righe successive (entro 8 righe) per trovare il nome della funzione
                cmt_text = "\n".join(current_comments)
                # Combina le prossime righe per gestire dichiarazioni su più righe
                next_block = " ".join([lines[k].strip() for k in range(i + 1, min(i + 9, len(lines))) if lines[k].strip()])
                
                # 1. Match macro CJSON_PUBLIC
                m_cjson = re.search(r"CJSON_PUBLIC\([^)]+\)\s*([a-zA-Z0-9_]+)", next_block)
                if m_cjson:
                    comments[m_cjson.group(1)] = cmt_text
                    continue
                
                # 2. Match macro MINIZ_EXPORT
                m_miniz = re.search(r"MINIZ_EXPORT\s+(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\(", next_block)
                if m_miniz:
                    comments[m_miniz.group(1)] = cmt_text
                    continue

                # 3. Match generico definizione/dichiarazione funzione C (anche multi-linea)
                m_func = re.search(r"^(?:(?:static|inline|extern|const|unsigned|signed|size_t|uint[0-9]+_t|int[0-9]+_t|void|struct\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)\s+[*&]*)+([a-zA-Z0-9_]+)\s*\(", next_block)
                if m_func:
                    fn = m_func.group(1)
                    if fn not in ("if", "for", "while", "switch", "return", "sizeof"):
                        comments[fn] = cmt_text
                        continue
            continue
            
    return comments

# ── Commenti di gruppo ────────────────────────────────────────────────────────

VARIANT_LABEL = "Variant"
MIN_FAMILY_COMMON_TOKENS = 3


def name_tokens(name: str) -> List[str]:
    """Token di un nome qualificato: 'XMLUtil::ToInt64' -> [XML, Util, To, Int, 64]."""
    out: List[str] = []
    for part in re.split(r"::|_+", name):
        out += re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", part)
    return out


def split_family(names: List[str]):
    """
    Prefisso e suffisso comuni (in token) e variante di ogni membro.
    Restituisce (n_prefisso, n_suffisso, {nome: variante}).
    """
    toks = [name_tokens(n) for n in names]
    pre = 0
    while all(len(t) > pre for t in toks) and len({t[pre] for t in toks}) == 1:
        pre += 1
    suf = 0
    while (all(len(t) - pre > suf for t in toks)
           and len({t[len(t) - 1 - suf] for t in toks}) == 1):
        suf += 1
    variants = {n: " ".join(t[pre:len(t) - suf]) for n, t in zip(names, toks)}
    return pre, suf, variants


def is_name_family(names: List[str]):
    """
    I membri di un blocco sono varianti della stessa funzione solo se i loro nomi hanno almeno
    MIN_FAMILY_COMMON_TOKENS token comuni (prefisso + suffisso) e ciascuno ha una variante
    distinta (al massimo una puo' essere vuota: il membro "base", es. cJSON_Parse).
    Respinge ad esempio XMLDocument::Print/Accept, XMLPrinter::Print/Write, cJSON_GetObjectItem/HasObjectItem.
    Restituisce {nome: variante} se e' una famiglia, altrimenti None.
    """
    if len(names) < 2:
        return None
    pre, suf, variants = split_family(names)
    if pre + suf < MIN_FAMILY_COMMON_TOKENS:
        return None
    vals = list(variants.values())
    if len(set(vals)) != len(vals) or sum(1 for v in vals if not v) > 1:
        return None
    return variants


def _is_decl_line(s: str) -> bool:
    return (s.endswith((";", ",", ")")) or s.startswith(("CJSON_PUBLIC", "MINIZ_EXPORT"))
            or (s.endswith("}") and "{" in s))


def _comment_block(lines: List[str], i: int):
    """Blocco di commento che termina alla riga i: (indice_riga_iniziale, testo)."""
    j = i
    if lines[i].strip().startswith("//"):
        while j - 1 >= 0 and lines[j - 1].strip().startswith("//"):
            j -= 1
    else:
        while j >= 0 and "/*" not in lines[j]:
            j -= 1
    j = max(j, 0)
    return j, "\n".join(l.strip() for l in lines[j:i + 1])


def find_group_comment(lines: List[str], line_no: int):
    """
    Risale dalla dichiarazione (riga 1-based) per righe contigue, senza righe vuote, fino al primo
    commento valido saltando quelli troppo poveri (es. "/* raw json */").
    Restituisce (riga_del_commento, testo) oppure None.
    """
    i = line_no - 2
    while 0 <= i < len(lines):
        s = lines[i].strip()
        if s == "":
            return None
        if s.endswith("*/") or s.startswith("//"):
            j, text = _comment_block(lines, i)
            if not lines[j].strip().startswith(("/*", "//")):
                # commento in coda a una riga di codice (es. "decl(...); /* nota */"): e' una
                # dichiarazione, non il commento di un gruppo
                i -= 1
                continue
            if is_valid_ground_truth(clean_doxygen_comment(text)):
                return j + 1, text
            i = j - 1
            continue
        if _is_decl_line(s):
            i -= 1
            continue
        return None
    return None


def collect_group_docs(lines: List[str], functions: List[Dict[str, Any]]) -> Dict[str, tuple]:
    """
    {nome_funzione: (commento_di_gruppo, variante)} per le funzioni di un file che appartengono a
    una famiglia di dichiarazioni sotto un commento comune.
    """
    groups: Dict[int, List[tuple]] = {}
    for func in functions:
        if not func.get("line"):
            continue
        found = find_group_comment(lines, func["line"])
        if found:
            groups.setdefault(found[0], []).append((func["name"], found[1]))

    out: Dict[str, tuple] = {}
    for members in groups.values():
        names = list(dict.fromkeys(n for n, _ in members))
        variants = is_name_family(names)
        if variants is None:
            continue
        text = members[0][1]
        for n in names:
            out[n] = (text, variants[n])
    return out


def extract_c_header_comments(header_path: str) -> Dict[str, str]:
    return extract_c_comments_from_file(header_path)

def init_database(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_functions (
            id TEXT PRIMARY KEY,
            library TEXT,
            language TEXT,
            filename TEXT,
            function_name TEXT,
            signature TEXT,
            return_type TEXT,
            parameters TEXT,
            source_code TEXT,
            raw_comment TEXT,
            cleaned_doc TEXT,
            time_complexity TEXT,
            space_complexity TEXT,
            doc_origin TEXT DEFAULT 'own'
        )
    """)
    # DB creati prima dell'introduzione di doc_origin
    cols = [r[1] for r in cur.execute("PRAGMA table_info(benchmark_functions)")]
    if "doc_origin" not in cols:
        cur.execute("ALTER TABLE benchmark_functions ADD COLUMN doc_origin TEXT DEFAULT 'own'")
    conn.commit()
    conn.close()

def save_to_database(db_path: str, records: List[Dict[str, Any]]):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Pulisce la tabella per garantire un dataset allineato e privo di orfani
    cur.execute("DELETE FROM benchmark_functions;")
    for r in records:
        cur.execute("""
            INSERT OR REPLACE INTO benchmark_functions (
                id, library, language, filename, function_name, signature,
                return_type, parameters, source_code, raw_comment, cleaned_doc,
                time_complexity, space_complexity, doc_origin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["id"],
            r["library"],
            r["language"],
            r["filename"],
            r["function_name"],
            r["signature"],
            r["return_type"],
            json.dumps(r["parameters"], ensure_ascii=False),
            r["source_code"],
            r["raw_comment"],
            r["cleaned_doc"],
            r["time_complexity"],
            r["space_complexity"],
            r.get("doc_origin", "own")
        ))
    conn.commit()
    conn.close()

def build_dataset(group_comments: bool = True):
    ensure_directories()
    init_database(DB_PATH)
    
    extractor = CCodeExtractor()
    all_records = []
    
    # Commenti candidati per (libreria, funzione), nell'ordine dei file (header prima, poi .c).
    # Per ogni funzione si usa l'ultimo candidato valido: un commento povero nel .c (es. "Create
    # basic types:") non deve far perdere una documentazione valida presente nell'header.
    doc_registry = {}
    doc_candidates: Dict[tuple, List[str]] = {}
    # Commenti di gruppo per (libreria, funzione): (commento, variante)
    group_registry: Dict[tuple, tuple] = {}

    for src_group in SOURCES:
        lib = src_group["library"]
        lang = src_group["language"]
        lib_dir = os.path.join(SOURCES_DIR, lib)
        os.makedirs(lib_dir, exist_ok=True)

        # 1. Download dei file sorgente
        for f_info in src_group["files"]:
            filename = f_info["filename"]
            target_path = os.path.join(lib_dir, filename)
            if not os.path.exists(target_path):
                download_file(f_info["url"], target_path)

        # 2. Estrazione commenti preliminare dagli header
        for f_info in src_group["files"]:
            target_path = os.path.join(lib_dir, f_info["filename"])
            if lang == "c":
                c_comments = extract_c_comments_from_file(target_path)
                for fn, cmt in c_comments.items():
                    doc_registry[(lib, fn)] = cmt
                    doc_candidates.setdefault((lib, fn), []).append(cmt)
            elif target_path.endswith((".h", ".hpp")):
                # Estrazione AST Clang per file C++ (OpenCV, TinyXML-2, fmt)
                try:
                    extra_args = ['-x', 'c++'] if target_path.endswith('.h') and lang == 'cpp' else None
                    meta = extractor.extract_metadata(target_path, include_dirs=[lib_dir], extra_args=extra_args)
                    for func in meta.get("functions", []):
                        fn = func["name"]
                        if func.get("raw_comment"):
                            doc_registry[(lib, fn)] = func["raw_comment"]
                except Exception as e:
                    print(f"[WARN] Errore estrazione header {target_path}: {e}")

        # 3. Estrazione completa e associazione codice + documentazione
        for f_info in src_group["files"]:
            filename = f_info["filename"]
            target_path = os.path.join(lib_dir, filename)
            
            print(f"\n[INFO] Elaborazione file: {filename} ({lib})...")
            try:
                extra_args = ['-x', 'c++'] if target_path.endswith('.h') and lang == 'cpp' else None
                meta = extractor.extract_metadata(target_path, include_dirs=[lib_dir], extra_args=extra_args)
            except Exception as e:
                print(f"[ERROR] Impossibile parsare {target_path}: {e}")
                continue

            if group_comments:
                with open(target_path, "r", encoding="utf-8", errors="ignore") as fh:
                    file_lines = fh.read().splitlines()
                for gname, gdoc in collect_group_docs(file_lines, meta.get("functions", [])).items():
                    group_registry.setdefault((lib, gname), gdoc)

            for func in meta.get("functions", []):
                fname = func["name"]
                
                raw_comment = func.get("raw_comment") or doc_registry.get((lib, fname), "")
                if not is_valid_ground_truth(clean_doxygen_comment(raw_comment)):
                    valid = [c for c in doc_candidates.get((lib, fname), [])
                             if is_valid_ground_truth(clean_doxygen_comment(c))]
                    if valid:
                        raw_comment = valid[-1]
                source_code = func.get("source_code", "").strip()
                
                params_list = func.get("parameters", [])
                params_str = ", ".join([f"{p.get('type','')} {p.get('name','')}".strip() for p in params_list]) if params_list else "void"
                ret_type = func.get("return_type", "")
                signature = f"{ret_type} {fname}({params_str})".strip()

                cleaned_doc = clean_doxygen_comment(raw_comment)
                doc_origin = "own"

                # Nessun commento proprio valido: si usa il commento condiviso dal gruppo di
                # dichiarazioni, con in coda la variante ricavata dal nome della funzione
                if not is_valid_ground_truth(cleaned_doc) and (lib, fname) in group_registry:
                    g_text, g_variant = group_registry[(lib, fname)]
                    raw_comment = g_text
                    cleaned_doc = clean_doxygen_comment(g_text)
                    if g_variant:
                        cleaned_doc += f"\n{VARIANT_LABEL}: {g_variant}"
                    doc_origin = "group"
                
                # Filtro rigoroso: conserviamo SOLO funzioni dotate di codice e con documentazione originale valida (Ground Truth)
                if not source_code or not is_valid_ground_truth(cleaned_doc):
                    continue

                rec_id = f"{lib.lower()}_{filename}_{fname}".replace("::", "_").replace("*", "ptr").replace(" ", "_").replace(".", "_")
                
                record = {
                    "id": rec_id,
                    "library": lib,
                    "language": lang,
                    "filename": filename,
                    "function_name": fname,
                    "signature": signature,
                    "return_type": ret_type,
                    "parameters": params_list,
                    "source_code": source_code,
                    "raw_comment": raw_comment,
                    "cleaned_doc": cleaned_doc,
                    "time_complexity": func.get("time_complexity", "O(1)"),
                    "space_complexity": func.get("space_complexity", "O(1)"),
                    "doc_origin": doc_origin
                }
                all_records.append(record)

    # Salvataggio su JSONL
    print(f"\n[INFO] Salvataggio di {len(all_records)} record in {JSONL_PATH}...")
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Salvataggio su SQLite
    print(f"[INFO] Salvataggio nel database SQLite {DB_PATH}...")
    save_to_database(DB_PATH, all_records)
    
    print("\n[SUCCESS] Costruzione del dataset completata con successo!")
    print(f"Totale funzioni nel dataset: {len(all_records)}")
    
    from collections import Counter
    lib_counts = Counter(r["library"] for r in all_records)
    for lib_name, count in lib_counts.items():
        lang = next(r["language"] for r in all_records if r["library"] == lib_name)
        print(f"- Funzioni {lang.upper()} ({lib_name}): {count}")
    
    n_group = sum(1 for r in all_records if r["doc_origin"] == "group")
    print(f"- Funzioni con documentazione ereditata da un gruppo: {n_group}")
    documented_count = sum(1 for r in all_records if r["cleaned_doc"])
    with_source_count = sum(1 for r in all_records if r["source_code"])
    print(f"- Funzioni con documentazione originale: {documented_count}")
    print(f"- Funzioni con codice sorgente: {with_source_count}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Costruisce il dataset di benchmark (Ground Truth)")
    ap.add_argument("--output-dir", default=None,
                    help="Scrive benchmark.db e ground_truth.jsonl in questa cartella invece di dataset/ (anteprima)")
    ap.add_argument("--no-group-comments", action="store_true",
                    help="Non estende ai membri di un gruppo il commento condiviso (solo commenti propri)")
    cli = ap.parse_args()
    if cli.output_dir:
        os.makedirs(cli.output_dir, exist_ok=True)
        DB_PATH = os.path.join(cli.output_dir, "benchmark.db")
        JSONL_PATH = os.path.join(cli.output_dir, "ground_truth.jsonl")
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
    build_dataset(group_comments=not cli.no_group_comments)
