import os
import clang.cindex

def generate_mermaid_ast(filepath: str, max_depth: int = 3) -> str:
    if os.name == 'nt':
        possible_paths = [r"C:\Program Files\LLVM\bin", r"C:\Program Files (x86)\LLVM\bin"]
        for p in possible_paths:
            if os.path.exists(p):
                clang.cindex.Config.set_library_path(p)
                break
    index = clang.cindex.Index.create()
    ext = os.path.splitext(filepath)[1].lower()
    is_cpp = ext in ['.cpp', '.hpp', '.cc', '.cxx', '.hxx', '.hh', '.c++']
    args = ['-x', 'c++', '-std=c++17'] if is_cpp else ['-x', 'c', '-std=c11']
    tu = index.parse(filepath, args=args)

    target_abs = os.path.abspath(filepath)
    lines = ["graph TD"]
    node_counter = [0]

    def add_node(cursor, depth=0):
        if depth > max_depth:
            return None
        loc = cursor.location
        if loc.file and os.path.abspath(loc.file.name) != target_abs:
            return None

        node_id = f"node_{node_counter[0]}"
        node_counter[0] += 1

        kind = cursor.kind.name
        label = cursor.spelling or cursor.displayname or ""
        if label:
            label_clean = label.replace('"', "'").replace('[', '(').replace(']', ')')
            node_label = f'"{kind}<br/><b>{label_clean}</b>"'
        else:
            node_label = f'"{kind}"'

        lines.append(f'  {node_id}[{node_label}]')

        for child in cursor.get_children():
            child_id = add_node(child, depth + 1)
            if child_id:
                lines.append(f'  {node_id} --> {child_id}')

        return node_id

    root_id = f"node_{node_counter[0]}"
    node_counter[0] += 1
    filename = os.path.basename(filepath)
    lines.append(f'  {root_id}["TranslationUnit<br/><b>{filename}</b>"]')

    for child in tu.cursor.get_children():
        loc = child.location
        if loc.file and os.path.abspath(loc.file.name) == target_abs:
            child_id = add_node(child, 1)
            if child_id:
                lines.append(f'  {root_id} --> {child_id}')

    return "\n".join(lines)


if __name__ == "__main__":
    h_file = r"d:\python\TESI_Nicola_Flego\Test_code\Easy C\ring_buffer.h"
    mermaid_code = generate_mermaid_ast(h_file, max_depth=3)
    
    with open("ast_diagram.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_code)
    print("Grafico Mermaid salvato in ast_diagram.mmd")
