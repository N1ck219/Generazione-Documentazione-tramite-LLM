import os
import sys
import json
from typing import List

from src.extract_metadata import CCodeExtractor
from src.dependency_graph import DependencyGraph
from src.doc_orchestrator import DocOrchestrator
from src.llm_provider import QuotaDailyExceededError
from utils.generate_ast_diagram import generate_mermaid_ast


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_CODE_DIR = os.path.join(BASE_DIR, "Test_code")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

def discover_projects(base_path: str) -> List[str]:
    """
    Scansiona la cartella Test_code e restituisce la lista delle sotto-cartelle (progetti).
    """
    if not os.path.exists(base_path):
        return []
    
    projects = [
        d for d in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, d)) and not d.startswith('.')
    ]
    return projects

def find_c_source_files(project_path: str):
    """
    Trova ricorsivamente tutti i file sorgente C e C++ (.c, .cpp, .cc, .cxx, .h, .hpp, .hh, .hxx) all'interno del progetto selezionato.
    """
    c_files = []
    h_files = []
    include_dirs = set()

    c_exts = ('.c', '.cpp', '.cc', '.cxx', '.c++')
    h_exts = ('.h', '.hpp', '.hh', '.hxx', '.h++')

    for root, _, files in os.walk(project_path):
        for f in files:
            full_path = os.path.join(root, f)
            f_lower = f.lower()
            if any(f_lower.endswith(ext) for ext in c_exts):
                c_files.append(full_path)
                include_dirs.add(root)
            elif any(f_lower.endswith(ext) for ext in h_exts):
                h_files.append(full_path)
                include_dirs.add(root)

    return c_files, h_files, list(include_dirs)


def process_project(project_name: str, force_rebuild: bool = False, mode: str = "single"):
    """
    Esegue l'intera pipeline di analisi statica, ast, dipendenze ed orchestrazione agenti per un progetto C/C++.
    """
    proj_source_dir = os.path.join(TEST_CODE_DIR, project_name)
    proj_results_dir = os.path.join(RESULTS_DIR, project_name)
    os.makedirs(proj_results_dir, exist_ok=True)

    print(f"\n==================================================")
    print(f"      ANALISI PROGETTO: {project_name}")
    print(f"==================================================")
    print(f"Percorso sorgenti: {proj_source_dir}")
    print(f"Cartella risultati: {proj_results_dir}")

    c_files, h_files, include_dirs = find_c_source_files(proj_source_dir)
    if not c_files and not h_files:
        print(f"[ERRORE] Nessun file C/C++ sorgente (.c/.cpp/.h/.hpp) trovato in {proj_source_dir}")
        return

    print(f"\nTrovati {len(c_files)} file sorgente (.c/.cpp) e {len(h_files)} file header (.h/.hpp)")


    # 1. Estrazione Metadati AST da tutti i file C/C++
    print("\n[1/3] Estrazione Metadati AST da tutti i file C/C++...")
    extractor = CCodeExtractor()
    all_metadata = {}

    all_source_files = c_files + h_files
    for file_path in all_source_files:
        rel_name = os.path.relpath(file_path, proj_source_dir)
        print(f"  - Parsing: {rel_name}")
        meta = extractor.extract_metadata(file_path, include_dirs=include_dirs)
        all_metadata[rel_name] = meta

        mmd_dir = os.path.join(proj_results_dir, "mmd_diagrams")
        os.makedirs(mmd_dir, exist_ok=True)

        try:
            mermaid_ast = generate_mermaid_ast(file_path, max_depth=3)
            ast_filename = f"ast_{os.path.basename(file_path)}.mmd"
            with open(os.path.join(mmd_dir, ast_filename), "w", encoding="utf-8") as f:
                f.write(mermaid_ast)
        except Exception as e:
            print(f"    (Impossibile generare diagramma AST visuale per {rel_name}: {e})")


    # Salva il file JSON dei metadati estratti
    metadata_json_path = os.path.join(proj_results_dir, "extracted_metadata.json")
    with open(metadata_json_path, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)

    # 2. Costruzione Grafo delle Dipendenze Call-Graph
    print("\n[2/3] Costruzione Grafo delle Dipendenze Call-Graph...")
    graph = DependencyGraph()
    graph.build_from_project(c_files, include_dirs=include_dirs)

    mmd_dir = os.path.join(proj_results_dir, "mmd_diagrams")
    graph_mmd_path = os.path.join(mmd_dir, "dependency_graph.mmd")
    with open(graph_mmd_path, "w", encoding="utf-8") as f:
        f.write(graph.export_mermaid(max_edges=500, include_stdlib=False, all_metadata=all_metadata))
    print(f"-> Grafo delle chiamate tra funzioni salvato in: {graph_mmd_path}")

    file_graph_mmd_path = os.path.join(mmd_dir, "file_dependency_graph.mmd")
    with open(file_graph_mmd_path, "w", encoding="utf-8") as f:
        f.write(graph.export_file_dependency_mermaid(all_metadata, max_edges=400))
    print(f"-> Grafo delle dipendenze tra FILE salvato in: {file_graph_mmd_path}")

    # 3. Calcolo Ordinamento Topologico Bottom-Up
    print("\n[3/4] Calcolo Ordinamento Topologico Bottom-Up (Dependencies-First)...")
    bottom_up_order = graph.get_topological_order_bottom_up()

    topological_json_path = os.path.join(proj_results_dir, "topological_execution_order.json")
    with open(topological_json_path, "w", encoding="utf-8") as f:
        json.dump(bottom_up_order, f, indent=2)

    # 4. Generazione della Documentazione tramite Agenti & SQLite Memory
    print("\n[4/4] Generazione della Documentazione tramite Orchestrazione Agenti & SQLite Memory...")
    orchestrator = DocOrchestrator(proj_results_dir)
    
    # Se il flag force_rebuild è attivo, svuota il DB SQLite prima di rigenerare
    if force_rebuild:
        print("  [FORCE REBUILD] Flag di rigenerazione totale attivo: Svuotamento database SQLite...")
        orchestrator.db.clear_database()
    else:
        # Ripuliamo solo le righe con descrizioni nulle o fallimenti di fallback
        orchestrator.db.clean_invalid_docs()

    try:
        doc_path = orchestrator.run_documentation_pipeline(clear_cache=force_rebuild, mode=mode)
        print(f"\n[COMPLETATO] Analisi e Documentazione del progetto '{project_name}' completate con successo!")
        print(f"Tutti gli output ed il file DOCUMENTATION.md sono disponibili in: {proj_results_dir}\n")
    except QuotaDailyExceededError as qe:
        print(f"\n{qe}\n")

def main():
    force_rebuild = "--force" in sys.argv or "-f" in sys.argv or "f" in [arg.lower() for arg in sys.argv]
    is_multiagent = "--multiagent" in sys.argv or "-m" in sys.argv or "m" in [arg.lower() for arg in sys.argv]
    export_only = "--export" in sys.argv or "-e" in sys.argv or "e" in [arg.lower() for arg in sys.argv]
    mode = "multiagent" if is_multiagent else "single"

    print("==================================================")
    print("  ORCHESTRATORE ANALISI E DOCUMENTAZIONE CODICE C ")
    print("==================================================")

    projects = discover_projects(TEST_CODE_DIR)
    if not projects:
        print(f"\n[ERRORE] Nessun progetto trovato nella cartella '{TEST_CODE_DIR}'.")
        return

    # Gestione flag rapido di sola rigenerazione report/HTML (senza chiamate LLM)
    if export_only:
        choice_idx = 0
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            choice_idx = int(sys.argv[1]) - 1
        if 0 <= choice_idx < len(projects):
            proj_name = projects[choice_idx]
            proj_results = os.path.join(RESULTS_DIR, proj_name)
            print(f"\n[EXPORT RAPIDO] Rigenerazione istantanea DOCUMENTATION.md e Grafo Interattivo per '{proj_name}' da SQLite...")
            orchestrator = DocOrchestrator(proj_results)
            doc_path = os.path.join(proj_results, "DOCUMENTATION.md")
            orchestrator._export_markdown_documentation(doc_path)
            print(f"[COMPLETATO] File DOCUMENTATION.md e interactive_call_graph.html aggiornati in 1 secondo!\n")
            return

    # Gestione argomento da riga di comando (es. python main.py 2 f o python main.py 1 --force --multiagent)
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        choice_idx = int(sys.argv[1]) - 1
        if 0 <= choice_idx < len(projects):
            process_project(projects[choice_idx], force_rebuild=force_rebuild, mode=mode)
            return

    print("\nProgetti disponibili trovati in 'Test_code':")
    for idx, proj in enumerate(projects, 1):
        print(f"  [{idx}] {proj}")
    
    print("\nOpzioni di Esecuzione:")
    print("  Digitare il numero (es: '1') per la modalita' Ibrida Standard.")
    print("  Aggiungere 'e' (es: '1 e') per AGGIORNARE ISTANTANEAMENTE il Markdown ed il Grafo Interattivo dai dati SQLite (senza chiamate LLM).")
    print("  Aggiungere 'm' (es: '1 m') per attivare la Pipeline MULTI-AGENTE (Reader -> Searcher -> Writer -> Verifier).")
    print("  Aggiungere 'f' (es: '1 f' o '1 m f') per FORZARE la rigenerazione da zero (Clear Database).")

    user_input = input("\nSeleziona il progetto (o 'q' per uscire): ").strip()
    if user_input.lower() == 'q':
        return

    parts = user_input.split()
    if parts and parts[0].isdigit():
        choice_idx = int(parts[0]) - 1
        is_force_choice = "f" in [p.lower() for p in parts[1:]]
        is_multi_choice = "m" in [p.lower() for p in parts[1:]]
        is_export_choice = "e" in [p.lower() for p in parts[1:]]
        chosen_mode = "multiagent" if (is_multiagent or is_multi_choice) else "single"

        if 0 <= choice_idx < len(projects):
            if is_export_choice:
                proj_name = projects[choice_idx]
                proj_results = os.path.join(RESULTS_DIR, proj_name)
                print(f"\n[EXPORT RAPIDO] Rigenerazione istantanea DOCUMENTATION.md e Grafo Interattivo per '{proj_name}' da SQLite...")
                orchestrator = DocOrchestrator(proj_results)
                doc_path = os.path.join(proj_results, "DOCUMENTATION.md")
                orchestrator._export_markdown_documentation(doc_path)
                print(f"[COMPLETATO] File DOCUMENTATION.md e interactive_call_graph.html aggiornati in 1 secondo!\n")
            else:
                process_project(projects[choice_idx], force_rebuild=(force_rebuild or is_force_choice), mode=chosen_mode)
    else:
        if user_input in projects:
            process_project(user_input, force_rebuild=force_rebuild, mode=mode)
        else:
            print("[ERRORE] Input non valido.")

if __name__ == "__main__":
    main()

