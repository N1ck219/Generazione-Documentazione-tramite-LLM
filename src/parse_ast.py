import sys
import os
import clang.cindex
from typing import Dict, List, Any

def get_cursor_info(cursor: clang.cindex.Cursor) -> Dict[str, Any]:
    """
    Estrae le informazioni salienti da un nodo dell'AST di Clang.
    """
    return {
        "kind": cursor.kind.name,
        "spelling": cursor.spelling,
        "displayname": cursor.displayname,
        "location": {
            "file": cursor.location.file.name if cursor.location.file else None,
            "line": cursor.location.line,
            "column": cursor.location.column,
        },
        "type": cursor.type.spelling if cursor.type else None,
    }

def print_ast(cursor: clang.cindex.Cursor, indent: int = 0):
    """
    Stampa in modo ricorsivo l'AST partendo dal nodo dato.
    """
    # Filtriamo i nodi che provengono da file di sistema / include esterni se desiderato
    # (Per vedere solo il codice utente)
    info = get_cursor_info(cursor)
    indent_str = "  " * indent
    
    # Visualizziamo solo nodi significativi nel dump a schermo
    print(f"{indent_str}- [{info['kind']}] {info['spelling']} (linea {info['location']['line']})")

    for child in cursor.get_children():
        # Filtra header di sistema se non appartengono al file sorgente in esame
        if child.location.file and cursor.location.file and child.location.file.name != cursor.location.file.name:
            continue
        print_ast(child, indent + 1)

def parse_c_file(filepath: str, libclang_path: str = None) -> clang.cindex.TranslationUnit:
    """
    Effettua il parsing di un file C restituendo la Translation Unit di Clang.
    """
    if libclang_path:
        clang.cindex.Index.set_library_path(libclang_path)
    elif os.name == 'nt':
        # Percorsi standard comuni su Windows se libclang.dll/LLVM è installato
        possible_paths = [
            r"C:\Program Files\LLVM\bin",
            r"C:\Program Files (x86)\LLVM\bin"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                clang.cindex.Index.set_library_path(p)
                break

    index = clang.cindex.Index.create()
    
    # Argomenti aggiuntivi per il compilatore C / C++ (es. -I per include)
    ext = os.path.splitext(filepath)[1].lower()
    is_cpp = ext in ['.cpp', '.hpp', '.cc', '.cxx', '.hxx', '.hh', '.c++']
    args = ['-x', 'c++', '-std=c++17'] if is_cpp else ['-x', 'c', '-std=c11']
    
    translation_unit = index.parse(filepath, args=args)
    
    # Controllo errori di sintassi/parsing
    if translation_unit.diagnostics:
        print(f"--- Diagnostica / Avvisi di parsing per {filepath} ---")
        for diag in translation_unit.diagnostics:
            print(f"[{diag.severity}] {diag.spelling} (linea {diag.location.line}, colonna {diag.location.column})")
        print("-----------------------------------------------------")

    return translation_unit

if __name__ == "__main__":
    # Esempio di test rapido su un file di test
    sample_c_file = r"d:\python\TESI_Nicola_Flego\Test_code\Easy C\ring_buffer.h"
    
    if os.path.exists(sample_c_file):
        print(f"Parsing AST per: {sample_c_file}\n")
        tu = parse_c_file(sample_c_file)
        print_ast(tu.cursor)
    else:
        print(f"File non trovato: {sample_c_file}")
