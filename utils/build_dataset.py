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

def extract_c_header_comments(header_path: str) -> Dict[str, str]:
    """
    Estrae i blocchi di commento posti prima delle dichiarazioni
    di funzione in un file header C (es. cJSON.h).
    Mantiene il blocco anche per funzioni adiacenti correlate.
    """
    comments = {}
    if not os.path.exists(header_path):
        return comments
    
    with open(header_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    current_comments = []
    inside_block_comment = False
    
    for line in lines:
        s = line.strip()
        
        # Inizio blocco o commento singola riga: resettiamo il commento precedente solo se non siamo già dentro un blocco
        if s.startswith("/*"):
            current_comments = []
            inside_block_comment = True
            current_comments.append(s)
            if s.endswith("*/") and len(s) > 4:
                inside_block_comment = False
            continue
            
        if inside_block_comment:
            current_comments.append(s)
            if s.endswith("*/"):
                inside_block_comment = False
            continue
            
        # Se incontriamo codice strutturale che non è una dichiarazione di funzione, resettiamo
        if s and not s.startswith("#") and not s.startswith("//") and not inside_block_comment:
            if any(k in s for k in ("typedef", "struct", "{", "}")):
                current_comments = []
            
        # Controllo riga con firma CJSON_PUBLIC
        if "CJSON_PUBLIC" in line:
            m = re.search(r"CJSON_PUBLIC\([^)]+\)\s*([a-zA-Z0-9_]+)", line)
            if m:
                func_name = m.group(1)
                if current_comments:
                    comments[func_name] = "\n".join(current_comments)
            
    return comments

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
            space_complexity TEXT
        )
    """)
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
                time_complexity, space_complexity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            r["space_complexity"]
        ))
    conn.commit()
    conn.close()

def build_dataset():
    ensure_directories()
    init_database(DB_PATH)
    
    extractor = CCodeExtractor()
    all_records = []
    
    # Mappa globale delle documentazioni per libreria
    doc_registry = {}

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
            if target_path.endswith((".h", ".hpp")):
                # Estrazione euristica per file C come cJSON.h
                if lib == "cJSON":
                    c_comments = extract_c_header_comments(target_path)
                    for fn, cmt in c_comments.items():
                        doc_registry[(lib, fn)] = cmt
                
                # Estrazione AST Clang per file C++ (OpenCV, TinyXML-2)
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

            for func in meta.get("functions", []):
                fname = func["name"]
                
                raw_comment = func.get("raw_comment") or doc_registry.get((lib, fname), "")
                source_code = func.get("source_code", "").strip()
                
                params_list = func.get("parameters", [])
                params_str = ", ".join([f"{p.get('type','')} {p.get('name','')}".strip() for p in params_list]) if params_list else "void"
                ret_type = func.get("return_type", "")
                signature = f"{ret_type} {fname}({params_str})".strip()

                cleaned_doc = clean_doxygen_comment(raw_comment)
                
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
                    "space_complexity": func.get("space_complexity", "O(1)")
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
    
    documented_count = sum(1 for r in all_records if r["cleaned_doc"])
    with_source_count = sum(1 for r in all_records if r["source_code"])
    print(f"- Funzioni con documentazione originale: {documented_count}")
    print(f"- Funzioni con codice sorgente: {with_source_count}")

if __name__ == "__main__":
    build_dataset()
