import os
import sys
import json
import argparse
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional

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


def save_execution_config(run_dir: str, config_data: Dict[str, Any]):
    """
    Salva un file JSON contenente tutti i parametri e le impostazioni dell'esecuzione.
    """
    config_path = os.path.join(run_dir, "execution_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


def process_project(
    project_name: str, 
    force_rebuild: bool = False, 
    mode: str = "single",
    timestamp: Optional[str] = None,
    language: str = "en",
    cli_args: Optional[Dict[str, Any]] = None
):
    """
    Esegue l'intera pipeline di analisi statica, AST, dipendenze ed orchestrazione agenti per un progetto C/C++.
    Ogni esecuzione viene archiviata in una cartella con timestamp per conservare lo storico e consentire confronti.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    proj_source_dir = os.path.join(TEST_CODE_DIR, project_name)
    base_proj_results = os.path.join(RESULTS_DIR, project_name)
    
    # Cartella specifica con timestamp per questa esecuzione
    run_results_dir = os.path.join(base_proj_results, f"run_{timestamp}_{mode}")
    os.makedirs(run_results_dir, exist_ok=True)

    # Cartella per l'ultimo output (compatibilità retroattiva)
    latest_results_dir = os.path.join(base_proj_results, "latest")
    os.makedirs(latest_results_dir, exist_ok=True)

    print(f"\n==================================================")
    print(f"      ANALISI PROGETTO: {project_name}")
    print(f"==================================================")
    print(f"Percorso sorgenti:   {proj_source_dir}")
    print(f"Cartella esecuzione: {run_results_dir}")
    print(f"Modalita' pipeline:  {mode.upper()}")
    print(f"Timestamp:           {timestamp}")

    # Salva il file di configurazione con tutte le impostazioni ricevute da terminale
    config_to_save = {
        "timestamp": timestamp,
        "project_name": project_name,
        "mode": mode,
        "language": language,
        "force_rebuild": force_rebuild,
        "source_directory": proj_source_dir,
        "run_results_directory": run_results_dir,
        "cli_arguments": cli_args or {}
    }
    save_execution_config(run_results_dir, config_to_save)

    c_files, h_files, include_dirs = find_c_source_files(proj_source_dir)
    if not c_files and not h_files:
        print(f"[ERRORE] Nessun file C/C++ sorgente (.c/.cpp/.h/.hpp) trovato in {proj_source_dir}")
        return

    print(f"\nTrovati {len(c_files)} file sorgente (.c/.cpp) e {len(h_files)} file header (.h/.hpp)")

    # 1. Estrazione Metadati AST da tutti i file C/C++
    print("\n[1/4] Estrazione Metadati AST da tutti i file C/C++...")
    extractor = CCodeExtractor()
    all_metadata = {}

    all_source_files = c_files + h_files
    for file_path in all_source_files:
        rel_name = os.path.relpath(file_path, proj_source_dir)
        print(f"  - Parsing: {rel_name}")
        meta = extractor.extract_metadata(file_path, include_dirs=include_dirs)
        all_metadata[rel_name] = meta

        mmd_dir = os.path.join(run_results_dir, "mmd_diagrams")
        os.makedirs(mmd_dir, exist_ok=True)

        try:
            mermaid_ast = generate_mermaid_ast(file_path, max_depth=3)
            ast_filename = f"ast_{os.path.basename(file_path)}.mmd"
            with open(os.path.join(mmd_dir, ast_filename), "w", encoding="utf-8") as f:
                f.write(mermaid_ast)
        except Exception as e:
            print(f"    (Impossibile generare diagramma AST visuale per {rel_name}: {e})")

    # Salva il file JSON dei metadati estratti
    metadata_json_path = os.path.join(run_results_dir, "extracted_metadata.json")
    with open(metadata_json_path, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)

    # 2. Costruzione Grafo delle Dipendenze Call-Graph
    print("\n[2/4] Costruzione Grafo delle Dipendenze Call-Graph...")
    graph = DependencyGraph()
    graph.build_from_project(c_files, include_dirs=include_dirs)

    mmd_dir = os.path.join(run_results_dir, "mmd_diagrams")
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

    topological_json_path = os.path.join(run_results_dir, "topological_execution_order.json")
    with open(topological_json_path, "w", encoding="utf-8") as f:
        json.dump(bottom_up_order, f, indent=2)

    # Se non è un force_rebuild e c'è già un database nell'esecuzione precedente, possiamo sincronizzarlo
    prev_db_path = os.path.join(base_proj_results, "documentation.db")
    curr_db_path = os.path.join(run_results_dir, "documentation.db")
    if not force_rebuild and os.path.exists(prev_db_path) and not os.path.exists(curr_db_path):
        shutil.copy2(prev_db_path, curr_db_path)

    # 4. Generazione della Documentazione tramite Agenti & SQLite Memory
    print(f"\n[4/4] Generazione della Documentazione tramite Orchestrazione Agenti ({mode}) & SQLite Memory...")
    orchestrator = DocOrchestrator(run_results_dir)
    
    if force_rebuild:
        print("  [FORCE REBUILD] Flag di rigenerazione totale attivo: Svuotamento database SQLite...")
        orchestrator.db.clear_database()
    else:
        orchestrator.db.clean_invalid_docs()

    try:
        doc_path = orchestrator.run_documentation_pipeline(clear_cache=force_rebuild, mode=mode)
        
        # Aggiorna anche il database centrale del progetto per consentire riutilizzi e confronti
        shutil.copy2(curr_db_path, prev_db_path)
        # Sincronizza i file chiave anche nella cartella 'latest'
        for fname in ["DOCUMENTATION.md", "interactive_call_graph.html", "extracted_metadata.json", "topological_execution_order.json", "execution_config.json"]:
            src_f = os.path.join(run_results_dir, fname)
            if os.path.exists(src_f):
                shutil.copy2(src_f, os.path.join(latest_results_dir, fname))

        print(f"\n[COMPLETATO] Analisi e Documentazione del progetto '{project_name}' completate con successo!")
        print(f"Risultati storicizzati salvati in: {run_results_dir}")
        print(f"Copia aggiornata disponibile in:  {latest_results_dir}\n")
    except QuotaDailyExceededError as qe:
        print(f"\n{qe}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Orchestratore Analisi e Documentazione Codice C/C++ con Pipeline Specialistica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Esempi di utilizzo:
  python main.py                                      # Menu interattivo con selezione guidata
  python main.py -p "Easy C"                          # Esegue su 'Easy C' in modalita' Ibrida Standard
  python main.py -p "Easy C" -m multiagent            # Esegue con Pipeline Multi-Agente Specialistica (con Judge)
  python main.py -p "Easy C" -m multiagent --force    # Rigenerazione forzata da zero
  python main.py -p "Easy C" --export                 # Rigenera solo DOCUMENTATION.md e HTML senza chiamate LLM
"""
    )
    parser.add_argument("-p", "--project", default=None, help="Nome o indice numerico del progetto da documentare (es: 'Easy C' o '1')")
    parser.add_argument("-m", "--mode", default="single", choices=["single", "multiagent"], help="Modalita': 'single' (Ibrido Standard) o 'multiagent' (Reader->Searcher->Writer->Verifier->Judge)")
    parser.add_argument("-f", "--force", action="store_true", help="Forza la rigenerazione completa da zero (svuota cache SQLite)")
    parser.add_argument("-e", "--export", action="store_true", help="Esporta/aggiorna istantaneamente DOCUMENTATION.md e il Grafo Interattivo dai dati SQLite")
    parser.add_argument("--lang", default="en", choices=["en", "it"], help="Lingua per la documentazione LLM: 'en' (default) o 'it'")

    args = parser.parse_args()

    print("==================================================")
    print("  ORCHESTRATORE ANALISI E DOCUMENTAZIONE CODICE C ")
    print("==================================================")

    projects = discover_projects(TEST_CODE_DIR)
    if not projects:
        print(f"\n[ERRORE] Nessun progetto trovato nella cartella '{TEST_CODE_DIR}'.")
        return

    # Se il progetto e' stato passato esplicitamente da terminale via flag (-p/--project o posizionale numerico)
    target_project = None
    if args.project:
        if args.project.isdigit():
            idx = int(args.project) - 1
            if 0 <= idx < len(projects):
                target_project = projects[idx]
        elif args.project in projects:
            target_project = args.project
        else:
            # Ricerca per prefisso o case-insensitive
            match = [p for p in projects if p.lower() == args.project.lower()]
            if match:
                target_project = match[0]

    # Se specificato progetto da riga di comando
    if target_project:
        if args.export:
            proj_results = os.path.join(RESULTS_DIR, target_project)
            print(f"\n[EXPORT RAPIDO] Rigenerazione istantanea DOCUMENTATION.md e Grafo Interattivo per '{target_project}' da SQLite...")
            orchestrator = DocOrchestrator(proj_results)
            doc_path = os.path.join(proj_results, "DOCUMENTATION.md")
            orchestrator._export_markdown_documentation(doc_path)
            print(f"[COMPLETATO] File DOCUMENTATION.md e interactive_call_graph.html aggiornati!\n")
            return

        cli_dict = {
            "project": target_project,
            "mode": args.mode,
            "force": args.force,
            "export": args.export,
            "lang": args.lang
        }
        process_project(
            project_name=target_project,
            force_rebuild=args.force,
            mode=args.mode,
            language=args.lang,
            cli_args=cli_dict
        )
        return

    # Altrimenti, modalita' interattiva con menu a terminale
    print("\nProgetti disponibili trovati in 'Test_code':")
    for idx, proj in enumerate(projects, 1):
        print(f"  [{idx}] {proj}")
    
    print("\nOpzioni di Esecuzione:")
    print("  Digitare il numero (es: '1') per la modalita' Ibrida Standard.")
    print("  Aggiungere 'e' (es: '1 e') per AGGIORNARE ISTANTANEAMENTE il Markdown ed il Grafo Interattivo dai dati SQLite (senza chiamate LLM).")
    print("  Aggiungere 'm' (es: '1 m') per attivare la Pipeline MULTI-AGENTE (Reader -> Searcher -> Writer -> Verifier -> Judge).")
    print("  Aggiungere 'f' (es: '1 f' o '1 m f') per FORZARE la rigenerazione da zero (Clear Database).")

    user_input = input("\nSeleziona il progetto (o 'q' per uscire): ").strip()
    if user_input.lower() == 'q':
        return

    parts = user_input.split()
    if parts and parts[0].isdigit():
        choice_idx = int(parts[0]) - 1
        is_force_choice = "f" in [p.lower() for p in parts[1:]] or args.force
        is_multi_choice = "m" in [p.lower() for p in parts[1:]] or (args.mode == "multiagent")
        is_export_choice = "e" in [p.lower() for p in parts[1:]] or args.export
        chosen_mode = "multiagent" if is_multi_choice else "single"

        if 0 <= choice_idx < len(projects):
            chosen_proj = projects[choice_idx]
            if is_export_choice:
                proj_results = os.path.join(RESULTS_DIR, chosen_proj)
                print(f"\n[EXPORT RAPIDO] Rigenerazione istantanea DOCUMENTATION.md e Grafo Interattivo per '{chosen_proj}' da SQLite...")
                orchestrator = DocOrchestrator(proj_results)
                doc_path = os.path.join(proj_results, "DOCUMENTATION.md")
                orchestrator._export_markdown_documentation(doc_path)
                print(f"[COMPLETATO] File DOCUMENTATION.md e interactive_call_graph.html aggiornati!\n")
            else:
                cli_dict = {
                    "interactive_input": user_input,
                    "project": chosen_proj,
                    "mode": chosen_mode,
                    "force": is_force_choice,
                    "lang": args.lang
                }
                process_project(
                    project_name=chosen_proj,
                    force_rebuild=is_force_choice,
                    mode=chosen_mode,
                    language=args.lang,
                    cli_args=cli_dict
                )
    else:
        matched_proj = None
        for p in projects:
            if p.lower() == user_input.lower():
                matched_proj = p
                break
        if matched_proj:
            cli_dict = {
                "interactive_input": user_input,
                "project": matched_proj,
                "mode": args.mode,
                "force": args.force,
                "lang": args.lang
            }
            process_project(
                project_name=matched_proj,
                force_rebuild=args.force,
                mode=args.mode,
                language=args.lang,
                cli_args=cli_dict
            )
        else:
            print("[ERRORE] Input non valido.")

if __name__ == "__main__":
    main()

