import os
import json
import clang.cindex
from typing import Dict, List, Any

class CCodeExtractor:
    def __init__(self, libclang_path: str = None):
        if libclang_path:
            clang.cindex.Index.set_library_path(libclang_path)
        elif os.name == 'nt':
            possible_paths = [
                r"C:\Program Files\LLVM\bin",
                r"C:\Program Files (x86)\LLVM\bin"
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    clang.cindex.Index.set_library_path(p)
                    break
        self.index = clang.cindex.Index.create()

    def parse_file(self, filepath: str, include_dirs: List[str] = None, extra_args: List[str] = None) -> clang.cindex.TranslationUnit:
        ext = os.path.splitext(filepath)[1].lower()
        is_cpp = ext in ['.cpp', '.hpp', '.cc', '.cxx', '.hxx', '.hh', '.c++']
        if not is_cpp and ext == '.h' and os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f_check:
                    content_head = f_check.read(40960)
                    if any(kw in content_head for kw in ["namespace ", "class ", "template<", "template <", "public:", "private:", "protected:"]):
                        is_cpp = True
            except Exception:
                pass
        if extra_args and ('-x' in extra_args and 'c++' in extra_args):
            is_cpp = True
        
        args = ['-x', 'c++', '-std=c++17', '-DCV_EXPORTS=', '-D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH'] if is_cpp else ['-x', 'c', '-std=c11']
        if extra_args:
            for a in extra_args:
                if a not in args and a != '-x' and a != 'c++':
                    args.append(a)
        if include_dirs:
            for inc in include_dirs:
                args.append(f'-I{inc}')
        
        # Consenti parsing anche con macro e commenti docstring (commenti Doxygen)
        tu = self.index.parse(
            filepath, 
            args=args, 
            options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD |
                    clang.cindex.TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
        )
        return tu

    def extract_metadata(self, filepath: str, include_dirs: List[str] = None, extra_args: List[str] = None) -> Dict[str, Any]:
        tu = self.parse_file(filepath, include_dirs, extra_args=extra_args)
        target_file_abs = os.path.abspath(filepath)
        
        metadata = {
            "file": target_file_abs,
            "includes": [],
            "enums": [],
            "structs": [],
            "classes": [],
            "typedefs": [],
            "macros": [],
            "functions": []
        }

        def pretty_print_type(t: clang.cindex.Type) -> str:
            """
            Restituisce il tipo C/C++ formattato per preservare typedef noti (bool, size_t, int32_t, ecc.)
            invece di esporre la canonical representation interna del compilatore.
            """
            s = t.spelling
            if s == "_Bool":
                return "bool"
            # Pulizia puntatori o costanti
            s = s.replace("_Bool", "bool")
            return s

        def process_node(cursor: clang.cindex.Cursor, parent_scope: str = ""):
            # Filtriamo solo le dichiarazioni/definizioni definite nel file target (escludiamo header di sistema)
            loc = cursor.location
            if loc.file and os.path.abspath(loc.file.name) != target_file_abs:
                return

            kind = cursor.kind

            # 1. Directives #include
            if kind == clang.cindex.CursorKind.INCLUSION_DIRECTIVE:
                metadata["includes"].append({
                    "included_file": cursor.spelling,
                    "line": loc.line
                })

            # 2. Typedefs & Type Alias C++ (using X = Y)
            elif kind in (clang.cindex.CursorKind.TYPEDEF_DECL, clang.cindex.CursorKind.TYPE_ALIAS_DECL):
                typedef_name = cursor.spelling
                underlying_type = pretty_print_type(cursor.underlying_typedef_type)
                metadata["typedefs"].append({
                    "name": typedef_name,
                    "underlying_type": underlying_type,
                    "line": loc.line
                })

            # 3. Enum dichiarate esplicitamente o tramite typedef/enum class C++
            elif kind == clang.cindex.CursorKind.TYPEDEF_DECL and cursor.underlying_typedef_type.kind == clang.cindex.TypeKind.ENUM:
                enum_name = cursor.spelling
                if enum_name and not any(e["name"] == enum_name for e in metadata["enums"]):
                    enum_values = []
                    for child in cursor.get_children():
                        if child.kind == clang.cindex.CursorKind.ENUM_DECL:
                            for enum_const in child.get_children():
                                if enum_const.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                                    enum_values.append({
                                        "name": enum_const.spelling,
                                        "value": enum_const.enum_value
                                    })
                    metadata["enums"].append({
                        "name": enum_name,
                        "values": enum_values,
                        "line": loc.line
                    })

            elif kind == clang.cindex.CursorKind.ENUM_DECL:
                enum_name = cursor.spelling
                if enum_name and not any(e["name"] == enum_name for e in metadata["enums"]):
                    enum_values = []
                    for child in cursor.get_children():
                        if child.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                            enum_values.append({
                                "name": child.spelling,
                                "value": child.enum_value
                            })
                    metadata["enums"].append({
                        "name": enum_name,
                        "values": enum_values,
                        "line": loc.line
                    })

            # 4. Structs & Classes C++
            elif kind in (clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.CLASS_DECL):
                item_name = cursor.spelling
                if item_name and cursor.is_definition():
                    fields = []
                    for child in cursor.get_children():
                        if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                            fields.append({
                                "name": child.spelling,
                                "type": pretty_print_type(child.type)
                            })
                    target_list = metadata["classes"] if kind == clang.cindex.CursorKind.CLASS_DECL else metadata["structs"]
                    target_list.append({
                        "name": item_name,
                        "fields": fields,
                        "line": loc.line,
                        "raw_comment": cursor.raw_comment
                    })

            # 5. Funzioni C e Metodi di Classe C++ (Costruttori, Distruttori, Metodi statici e d'istanza)
            elif kind in (
                clang.cindex.CursorKind.FUNCTION_DECL,
                clang.cindex.CursorKind.CXX_METHOD,
                clang.cindex.CursorKind.CONSTRUCTOR,
                clang.cindex.CursorKind.DESTRUCTOR,
                clang.cindex.CursorKind.FUNCTION_TEMPLATE
            ):
                func_name = cursor.spelling
                # Se è un metodo membro e appartiene a una classe
                if cursor.semantic_parent and cursor.semantic_parent.kind in (clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.STRUCT_DECL):
                    parent_name = cursor.semantic_parent.spelling
                    if parent_name and not func_name.startswith(f"{parent_name}::"):
                        func_name = f"{parent_name}::{func_name}"

                is_constructor = kind == clang.cindex.CursorKind.CONSTRUCTOR
                is_destructor = kind == clang.cindex.CursorKind.DESTRUCTOR

                if is_constructor or is_destructor:
                    return_type = ""
                else:
                    return_type = pretty_print_type(cursor.result_type)

                is_definition = cursor.is_definition()

                params = []
                callees = []

                for child in cursor.get_children():
                    # Parametri di input
                    if child.kind == clang.cindex.CursorKind.PARM_DECL:
                        param_type = pretty_print_type(child.type)
                        params.append({
                            "name": child.spelling,
                            "type": param_type
                        })
                    
                    # Se è una definizione di funzione, estraiamo le funzioni chiamate (Callees)
                    if is_definition:
                        def extract_calls(node):
                            if node.kind == clang.cindex.CursorKind.CALL_EXPR:
                                target_name = node.spelling
                                # Se il nodo chiama un metodo con cursore referenziato
                                if node.referenced and node.referenced.semantic_parent:
                                    parent_kind = node.referenced.semantic_parent.kind
                                    if parent_kind in (clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.STRUCT_DECL):
                                        c_name = node.referenced.semantic_parent.spelling
                                        if c_name and not target_name.startswith(f"{c_name}::"):
                                            target_name = f"{c_name}::{target_name}"
                                if target_name and target_name not in callees:
                                    callees.append(target_name)
                            for subchild in node.get_children():
                                extract_calls(subchild)
                        extract_calls(child)

                # Estrazione del codice sorgente esatto della funzione dal file C
                source_code_snippet = ""
                try:
                    if loc.file:
                        with open(loc.file.name, "r", encoding="utf-8", errors="ignore") as f:
                            file_lines = f.readlines()
                            start_line = cursor.extent.start.line - 1
                            end_line = cursor.extent.end.line
                            source_code_snippet = "".join(file_lines[start_line:end_line])
                except Exception:
                    source_code_snippet = f"/* Impossibile leggere snippet riga {loc.line} */"

                # Calcolo DETERMINISTICO della Complessità Big-O basato sul parsing AST
                max_loop_depth = 0
                has_dynamic_alloc = False
                has_linear_stl_call = False

                # Metodi/funzioni STL o algoritmi noti a complessità O(N)
                linear_ops = {
                    "max_element", "min_element", "find", "count", "erase", "remove",
                    "std::max_element", "std::min_element", "std::find", "std::count"
                }

                def analyze_complexity(node, current_depth):
                    nonlocal max_loop_depth, has_dynamic_alloc, has_linear_stl_call
                    k = node.kind

                    if k in (clang.cindex.CursorKind.FOR_STMT, clang.cindex.CursorKind.WHILE_STMT, clang.cindex.CursorKind.DO_STMT):
                        current_depth += 1
                        if current_depth > max_loop_depth:
                            max_loop_depth = current_depth

                    if k == clang.cindex.CursorKind.CALL_EXPR:
                        call_name = node.spelling
                        if call_name in ("malloc", "calloc", "realloc", "aligned_alloc"):
                            has_dynamic_alloc = True
                        if call_name in linear_ops or (call_name and ("Trova" in call_name or "Ordina" in call_name or "Suddivisione" in call_name)):
                            has_linear_stl_call = True

                    if k == clang.cindex.CursorKind.CXX_NEW_EXPR:
                        has_dynamic_alloc = True

                    for subchild in node.get_children():
                        analyze_complexity(subchild, current_depth)

                if is_definition:
                    analyze_complexity(cursor, 0)

                # Se ci sono chiamate a funzioni lineari o passaggi di container per valore
                effective_loop_depth = max_loop_depth
                if has_linear_stl_call and effective_loop_depth == 0:
                    effective_loop_depth = 1
                elif has_linear_stl_call and effective_loop_depth >= 1:
                    effective_loop_depth += 1

                # Rileva passaggio di parametri vector per valore (che duplica la memoria -> O(N) spaziale)
                has_by_value_vector = any("vector" in p.get("type", "") and "&" not in p.get("type", "") and "*" not in p.get("type", "") for p in params)
                
                # Rileva RITORNO per valore di container STL (es. vector<vector<int>> getValori()), che comporta Deep Copy O(N) o O(N^2)
                is_return_by_value_container = "vector" in return_type and "&" not in return_type and "*" not in return_type
                is_return_2d_container = "vector<vector" in return_type.replace(" ", "") or "vector<std::vector" in return_type.replace(" ", "")

                if has_by_value_vector:
                    has_dynamic_alloc = True
                    if effective_loop_depth == 0:
                        effective_loop_depth = 1

                if is_return_by_value_container:
                    has_dynamic_alloc = True
                    if is_return_2d_container:
                        if effective_loop_depth < 2:
                            effective_loop_depth = 2
                    elif effective_loop_depth == 0:
                        effective_loop_depth = 1

                if is_return_2d_container and effective_loop_depth == 2:
                    time_comp = "O(N^2) (copia profonda matrice / W x H)"
                    space_comp = "O(N^2) (allocazione memoria matrice / W x H)"
                else:
                    time_comp = "O(1)" if effective_loop_depth == 0 else f"O(N^{effective_loop_depth})" if effective_loop_depth > 1 else "O(N)"
                    space_comp = "O(N) (allocazione/copia dinamica)" if has_dynamic_alloc else "O(1) (spazio ausiliario)"

                # Costruzione firma formale corretta (senza 'void' per costruttori/distruttori)
                if params:
                    params_str = ", ".join([f"{p['type']} {p['name']}" for p in params])
                else:
                    params_str = "void" if not is_constructor and not is_destructor else ""
                
                if is_constructor or is_destructor:
                    full_signature = f"{func_name}({params_str})"
                else:
                    full_signature = f"{return_type} {func_name}({params_str})"


                metadata["functions"].append({
                    "name": func_name,
                    "return_type": return_type,
                    "parameters": params,
                    "is_definition": is_definition,
                    "callees": callees if is_definition else [],
                    "line": loc.line,
                    "raw_comment": cursor.raw_comment,
                    "source_code": source_code_snippet,
                    "time_complexity": time_comp,
                    "space_complexity": space_comp
                })

            # Estrazione delle macro #define dal Preprocessore Clang
            elif cursor.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
                macro_name = cursor.spelling
                if macro_name and not macro_name.startswith("__"):
                    metadata["macros"].append({
                        "name": macro_name,
                        "line": loc.line
                    })

            # Ricorsione su Namespace, Classi e Strutture C++ per catturare metodi annidati
            if kind in (clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.STRUCT_DECL):
                for subchild in cursor.get_children():
                    process_node(subchild)

        # Naviga ricorsivamente l'AST a livello radice
        for child in tu.cursor.get_children():
            process_node(child)

        return metadata




if __name__ == "__main__":
    extractor = CCodeExtractor()
    header_path = r"d:\python\TESI_Nicola_Flego\Test_code\Easy C\ring_buffer.h"
    c_path = r"d:\python\TESI_Nicola_Flego\Test_code\Easy C\ring_buffer.c"

    print("=== METADATI ESTRATTI DA ring_buffer.h ===")
    header_data = extractor.extract_metadata(header_path)
    print(json.dumps(header_data, indent=2))

    print("\n=== METADATI ESTRATTI DA ring_buffer.c ===")
    c_data = extractor.extract_metadata(c_path, include_dirs=[r"d:\python\TESI_Nicola_Flego\Test_code\Easy C"])
    print(json.dumps(c_data, indent=2))
