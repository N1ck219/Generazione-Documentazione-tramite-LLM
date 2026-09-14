import os
import json
from typing import Dict, List, Set, Any, Optional
try:
    from src.extract_metadata import CCodeExtractor
except ImportError:
    from extract_metadata import CCodeExtractor


class DependencyGraph:
    def __init__(self):
        # Grafo orientato: adiacenza caller -> set(callees)
        self.adj: Dict[str, Set[str]] = {}
        # Inverso: callee -> set(callers)
        self.in_degree: Dict[str, Set[str]] = {}
        # Informazioni/metadati sui nodi
        self.nodes: Dict[str, Dict[str, Any]] = {}

    def add_node(self, name: str, node_type: str = "function", metadata: Dict[str, Any] = None):
        if name not in self.adj:
            self.adj[name] = set()
            self.in_degree[name] = set()
            self.nodes[name] = {
                "type": node_type,
                "metadata": metadata or {}
            }

    def add_edge(self, caller: str, callee: str):
        self.add_node(caller)
        self.add_node(callee)
        self.adj[caller].add(callee)
        self.in_degree[callee].add(caller)

    def get_callees(self, func_name: str) -> List[str]:
        """Restituisce l'elenco delle funzioni chiamate direttamente da func_name."""
        return sorted(list(self.adj.get(func_name, set())))

    def get_callers(self, func_name: str) -> List[str]:
        """Restituisce l'elenco delle funzioni che chiamano direttamente func_name."""
        return sorted(list(self.in_degree.get(func_name, set())))

    def get_dead_code_nodes(self, entry_points: Set[str] = None) -> List[str]:
        """
        Identifica funzioni 'Dead Code' / nodi orfani:
        funzioni definite nel progetto che hanno in-degree pari a 0 (mai chiamate da nessun'altra funzione)
        e che non sono entry point tipici (es. main, test_*).
        """
        if entry_points is None:
            entry_points = {"main", "app_main", "DllMain", "WinMain"}

        dead_nodes = []
        for node, data in self.nodes.items():
            if node in entry_points or node.startswith("test_") or node.startswith("Unity") or "::main" in node:
                continue
            # Se la funzione non ha chiamanti nel grafo
            callers = self.in_degree.get(node, set())
            if not callers:
                dead_nodes.append(node)
        return sorted(dead_nodes)

    def build_from_metadata(self, all_metadata: Dict[str, Any]):
        """
        Costruisce istantaneamente il grafo dai metadati JSON già estratti in memoria (senza ri-parsare con Clang).
        """
        for rel_path, meta in all_metadata.items():
            for func in meta.get("functions", []):
                fn_name = func["name"]
                self.add_node(fn_name, node_type="function", metadata=func)

        for rel_path, meta in all_metadata.items():
            for func in meta.get("functions", []):
                caller = func["name"]
                for callee in func.get("callees", []):
                    self.add_edge(caller, callee)

    def build_from_project(self, source_files: List[str], include_dirs: List[str] = None):
        """
        Costruisce il grafo a partire dai file C/C++ del progetto usando l'estrazione AST libclang.
        """
        extractor = CCodeExtractor()
        valid_exts = ('.c', '.cpp', '.cc', '.cxx', '.c++', '.h', '.hpp', '.hh', '.hxx', '.h++')
        
        all_metadata = []
        for file in source_files:
            if any(file.lower().endswith(ext) for ext in valid_exts):
                meta = extractor.extract_metadata(file, include_dirs)
                all_metadata.append(meta)

        # 1. Registra prima tutte le funzioni definite nel progetto
        for meta in all_metadata:
            for func in meta["functions"]:
                fn_name = func["name"]
                self.add_node(fn_name, node_type="function", metadata=func)

        # 2. Aggiungi gli archi caller -> callee
        for meta in all_metadata:
            for func in meta["functions"]:
                caller = func["name"]
                for callee in func.get("callees", []):
                    self.add_edge(caller, callee)

    def tarjan_scc(self) -> List[List[str]]:
        """
        Algoritmo di Tarjan per trovare le Componenti Fortemente Connesse (SCC).
        Permette di rilevare ed isolare cicli (funzioni mutuamente ricorsive).
        """
        index = 0
        indices: Dict[str, int] = {}
        lowlink: Dict[str, int] = {}
        stack: List[str] = []
        on_stack: Set[str] = set()
        sccs: List[List[str]] = []

        def strongconnect(node: str):
            nonlocal index
            indices[node] = index
            lowlink[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for neighbor in self.adj.get(node, []):
                if neighbor not in indices:
                    strongconnect(neighbor)
                    lowlink[node] = min(lowlink[node], lowlink[neighbor])
                elif neighbor in on_stack:
                    lowlink[node] = min(lowlink[node], indices[neighbor])

            if lowlink[node] == indices[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == node:
                        break
                sccs.append(scc)

        for node in list(self.nodes.keys()):
            if node not in indices:
                strongconnect(node)

        return sccs

    def get_topological_order_bottom_up(self) -> List[List[str]]:
        """
        Restituisce l'ordine topologico Bottom-Up dei nodi (o SCC in caso di cicli).
        Garantisce il principio 'Dependencies-First': le callees vengono analizzate prima dei caller.
        """
        sccs = self.tarjan_scc()

        # Mappiamo ogni nodo alla sua SCC index
        node_to_scc: Dict[str, int] = {}
        for scc_idx, scc in enumerate(sccs):
            for node in scc:
                node_to_scc[node] = scc_idx

        # Costruiamo il Condensed DAG delle SCC
        scc_adj: Dict[int, Set[int]] = {i: set() for i in range(len(sccs))}
        scc_in_degree: Dict[int, int] = {i: 0 for i in range(len(sccs))}

        for u in self.adj:
            for v in self.adj[u]:
                u_scc = node_to_scc[u]
                v_scc = node_to_scc[v]
                if u_scc != v_scc:
                    if v_scc not in scc_adj[u_scc]:
                        scc_adj[u_scc].add(v_scc)

        # Per il Bottom-Up dobbiamo invertire la direzione delle dipendenze per l'ordinamento:
        # Se A chiama B (u -> v), B deve venire prima di A.
        reversed_scc_adj: Dict[int, Set[int]] = {i: set() for i in range(len(sccs))}
        reversed_in_degree: Dict[int, int] = {i: 0 for i in range(len(sccs))}

        for u_scc in scc_adj:
            for v_scc in scc_adj[u_scc]:
                reversed_scc_adj[v_scc].add(u_scc)
                reversed_in_degree[u_scc] += 1

        # Kahn's Algorithm su Reversed DAG
        queue = [scc_id for scc_id, deg in reversed_in_degree.items() if deg == 0]
        topological_sccs = []

        while queue:
            curr = queue.pop(0)
            topological_sccs.append(sccs[curr])

            for neighbor in reversed_scc_adj[curr]:
                reversed_in_degree[neighbor] -= 1
                if reversed_in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return topological_sccs

    def export_mermaid(self, max_edges: int = 80, include_stdlib: bool = False, all_metadata: Dict[str, Any] = None) -> str:
        """
        Esporta il grafo delle chiamate tra funzioni in formato Mermaid.
        Se include_stdlib=False (default), le funzioni della C/C++ Standard Library vengono escluse per mantenere il grafo leggibile e leggero.
        Se viene fornito 'all_metadata', clusterizza le funzioni utente in 'subgraph' separati per ciascun File/Modulo sorgente.
        I simboli C++ (operatori, namespace, template) vengono sanitizzati con ID alfanumerici univoci e label quotate.
        """
        import re
        edges_count = 0
        nodes_used = set()
        edge_tuples = []
        
        stdlib_funcs = {
            "malloc", "free", "calloc", "realloc", "aligned_alloc",
            "printf", "fprintf", "sprintf", "snprintf", "puts", "putchar", "perror",
            "memcpy", "memmove", "memset", "memcmp", "strlen", "strcpy", "strncpy", "strcmp", "strncmp",
            "exit", "abort", "assert", "atoi", "atol", "strtol", "strtod",
            "fopen", "fclose", "fread", "fwrite", "fseek", "ftell", "fflush",
            "std::cout", "std::cin", "std::endl", "std::string", "std::vector", "std::map"
        }

        def sanitize_mermaid_id(name: str) -> str:
            # Sostituisce operatori C++ con nomi parlanti univoci
            s = name.replace("operator<<", "op_lshift") \
                    .replace("operator>>", "op_rshift") \
                    .replace("operator==", "op_eq") \
                    .replace("operator!=", "op_neq") \
                    .replace("operator<=", "op_lte") \
                    .replace("operator>=", "op_gte") \
                    .replace("operator[]", "op_subscript") \
                    .replace("operator()", "op_call") \
                    .replace("operator->", "op_arrow") \
                    .replace("operator++", "op_inc") \
                    .replace("operator--", "op_dec") \
                    .replace("operator+=", "op_add_assign") \
                    .replace("operator-=", "op_sub_assign") \
                    .replace("operator*=", "op_mul_assign") \
                    .replace("operator/=", "op_div_assign") \
                    .replace("operator+", "op_add") \
                    .replace("operator-", "op_sub") \
                    .replace("operator*", "op_deref_or_mul") \
                    .replace("operator/", "op_div") \
                    .replace("operator%", "op_mod") \
                    .replace("operator=", "op_assign") \
                    .replace("operator<", "op_lt") \
                    .replace("operator>", "op_gt") \
                    .replace("operator&", "op_bit_and") \
                    .replace("operator|", "op_bit_or") \
                    .replace("operator^", "op_bit_xor") \
                    .replace("operator~", "op_bit_not") \
                    .replace("operator!", "op_log_not") \
                    .replace("operator bool", "op_cast_bool")
            clean = re.sub(r'[^a-zA-Z0-9_]', '_', s)
            if not clean or clean[0].isdigit() or clean.lower() in ("end", "subgraph", "style", "classdef", "click", "callback", "linkstyle"):
                clean = 'fn_' + clean
            return clean

        # Mappatura funzione -> file sorgente
        func_to_file = {}
        if all_metadata:
            for rel_path, meta in all_metadata.items():
                for fn in meta.get("functions", []):
                    func_to_file[fn["name"]] = rel_path
        
        for u in self.adj:
            if u.startswith("__"):
                continue
            if not include_stdlib and (u in stdlib_funcs or u.startswith("std::")):
                continue

            for v in self.adj[u]:
                if v.startswith("__"):
                    continue
                if not include_stdlib and (v in stdlib_funcs or v.startswith("std::")):
                    continue

                if edges_count >= max_edges:
                    break
                edge_tuples.append((u, v))
                nodes_used.add(u)
                nodes_used.add(v)
                edges_count += 1
            if edges_count >= max_edges:
                break

        lines = ["graph LR"]
        
        local_nodes = sorted([n for n in nodes_used if n not in stdlib_funcs and not n.startswith("std::")])
        sys_nodes = sorted([n for n in nodes_used if n in stdlib_funcs or n.startswith("std::")]) if include_stdlib else []

        if func_to_file and local_nodes:
            # Raggruppamento delle funzioni per file sorgente reale
            file_clusters: Dict[str, List[str]] = {}
            for n in local_nodes:
                f_path = func_to_file.get(n, "Altre Funzioni")
                f_key = os.path.basename(f_path)
                if f_key not in file_clusters:
                    file_clusters[f_key] = []
                file_clusters[f_key].append(n)

            for f_name, f_funcs in file_clusters.items():
                clean_cluster_id = re.sub(r'[^a-zA-Z0-9_]', '_', f_name)
                lines.append(f'  subgraph {clean_cluster_id} ["📁 Modulo: {f_name}"]')
                for fn in f_funcs:
                    node_id = sanitize_mermaid_id(fn)
                    label_escaped = fn.replace('"', "'")
                    lines.append(f'    {node_id}["{label_escaped}"]')
                lines.append('  end\n')
        elif local_nodes:
            lines.append('  subgraph User_Module ["📦 Funzioni del Progetto / Modulo"]')
            for n in local_nodes:
                node_id = sanitize_mermaid_id(n)
                label_escaped = n.replace('"', "'")
                lines.append(f'    {node_id}["{label_escaped}"]')
            lines.append('  end\n')

        if sys_nodes:
            lines.append('  subgraph Std_Lib ["⚙️ C/C++ Standard Library"]')
            for n in sys_nodes:
                node_id = sanitize_mermaid_id(n)
                label_escaped = n.replace('"', "'")
                lines.append(f'    {node_id}["{label_escaped}"]')
            lines.append('  end\n')

        for u, v in edge_tuples:
            u_id = sanitize_mermaid_id(u)
            v_id = sanitize_mermaid_id(v)
            lines.append(f'  {u_id} --> {v_id}')

        # Stile visivo
        lines.append("\n  %% Class Definitions per Gerarchia Visiva")
        lines.append("  classDef localModule fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1,font-weight:bold;")
        lines.append("  classDef sysLib fill:#f1f5f9,stroke:#94a3b8,stroke-width:1px,stroke-dasharray: 4 4,color:#64748b;")
        
        local_ids = [sanitize_mermaid_id(n) for n in local_nodes]
        sys_ids = [sanitize_mermaid_id(n) for n in sys_nodes]
        if local_ids:
            lines.append(f"  class {','.join(local_ids)} localModule;")
        if sys_ids:
            lines.append(f"  class {','.join(sys_ids)} sysLib;")

        return "\n".join(lines)

    def export_module_call_graph(self, module_functions: Set[str], max_edges: int = 50) -> str:
        """
        Esporta un sotto-grafo Mermaid focalizzato esclusivamente sulle funzioni di un singolo modulo,
        mostrando le chiamate interne e le dipendenze verso l'esterno.
        Sanitizza automaticamente tutti i simboli C++ (operatori, template, namespace).
        """
        import re
        edges = []
        nodes_in_graph = set()
        count = 0

        def sanitize_mermaid_id(name: str) -> str:
            s = name.replace("operator<<", "op_lshift") \
                    .replace("operator>>", "op_rshift") \
                    .replace("operator==", "op_eq") \
                    .replace("operator!=", "op_neq") \
                    .replace("operator<=", "op_lte") \
                    .replace("operator>=", "op_gte") \
                    .replace("operator[]", "op_subscript") \
                    .replace("operator()", "op_call") \
                    .replace("operator->", "op_arrow") \
                    .replace("operator++", "op_inc") \
                    .replace("operator--", "op_dec") \
                    .replace("operator+=", "op_add_assign") \
                    .replace("operator-=", "op_sub_assign") \
                    .replace("operator*=", "op_mul_assign") \
                    .replace("operator/=", "op_div_assign") \
                    .replace("operator+", "op_add") \
                    .replace("operator-", "op_sub") \
                    .replace("operator*", "op_deref_or_mul") \
                    .replace("operator/", "op_div") \
                    .replace("operator%", "op_mod") \
                    .replace("operator=", "op_assign") \
                    .replace("operator<", "op_lt") \
                    .replace("operator>", "op_gt") \
                    .replace("operator&", "op_bit_and") \
                    .replace("operator|", "op_bit_or") \
                    .replace("operator^", "op_bit_xor") \
                    .replace("operator~", "op_bit_not") \
                    .replace("operator!", "op_log_not") \
                    .replace("operator bool", "op_cast_bool")
            clean = re.sub(r'[^a-zA-Z0-9_]', '_', s)
            if not clean or clean[0].isdigit() or clean.lower() in ("end", "subgraph", "style", "classdef", "click", "callback", "linkstyle"):
                clean = 'fn_' + clean
            return clean

        stdlib_funcs = {
            "malloc", "free", "calloc", "realloc", "aligned_alloc",
            "printf", "fprintf", "sprintf", "snprintf", "puts", "putchar", "perror",
            "memcpy", "memmove", "memset", "memcmp", "strlen", "strcpy", "strncpy", "strcmp", "strncmp",
            "exit", "abort", "assert", "atoi", "atol", "strtol", "strtod",
            "fopen", "fclose", "fread", "fwrite", "fseek", "ftell", "fflush",
            "std::cout", "std::cin", "std::endl", "std::string", "std::vector"
        }

        # 1. Raccogli archi in cui il caller o il callee appartiene al modulo
        for u in self.adj:
            if u.startswith("__"): continue
            for v in self.adj[u]:
                if v.startswith("__"): continue
                if u in module_functions or v in module_functions:
                    if count >= max_edges: break
                    edges.append((u, v))
                    nodes_in_graph.add(u)
                    nodes_in_graph.add(v)
                    count += 1
            if count >= max_edges: break

        if not edges:
            return None

        lines = ["graph LR"]
        internal_nodes = [n for n in nodes_in_graph if n in module_functions]
        external_nodes = [n for n in nodes_in_graph if n not in module_functions and n not in stdlib_funcs and not n.startswith("std::")]
        sys_nodes = [n for n in nodes_in_graph if n in stdlib_funcs or n.startswith("std::")]

        if internal_nodes:
            lines.append('  subgraph Module_Scope ["🔷 Funzioni di Questo Modulo"]')
            for n in sorted(internal_nodes):
                n_id = sanitize_mermaid_id(n)
                lbl = n.replace('"', "'")
                lines.append(f'    {n_id}["{lbl}"]')
            lines.append('  end\n')

        if external_nodes:
            lines.append('  subgraph External_Deps ["🌐 Moduli Esterni Collegati"]')
            for n in sorted(external_nodes):
                n_id = sanitize_mermaid_id(n)
                lbl = n.replace('"', "'")
                lines.append(f'    {n_id}["{lbl}"]')
            lines.append('  end\n')

        if sys_nodes:
            lines.append('  subgraph Libc_Scope ["⚙️ C/C++ Standard Library"]')
            for n in sorted(sys_nodes):
                n_id = sanitize_mermaid_id(n)
                lbl = n.replace('"', "'")
                lines.append(f'    {n_id}["{lbl}"]')
            lines.append('  end\n')

        for u, v in edges:
            u_id = sanitize_mermaid_id(u)
            v_id = sanitize_mermaid_id(v)
            lines.append(f'  {u_id} --> {v_id}')

        lines.append("\n  classDef internal fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#1e40af,font-weight:bold;")
        lines.append("  classDef external fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#92400e;")
        lines.append("  classDef sysLib fill:#f1f5f9,stroke:#94a3b8,stroke-width:1px,stroke-dasharray: 4 4,color:#64748b;")

        if internal_nodes:
            lines.append(f"  class {','.join([sanitize_mermaid_id(n) for n in internal_nodes])} internal;")
        if external_nodes:
            lines.append(f"  class {','.join([sanitize_mermaid_id(n) for n in external_nodes])} external;")
        if sys_nodes:
            lines.append(f"  class {','.join([sanitize_mermaid_id(n) for n in sys_nodes])} sysLib;")

        return "\n".join(lines)

    def export_file_dependency_mermaid(self, all_metadata: Dict[str, Any], max_edges: int = 450) -> str:
        """
        Genera il grafo delle dipendenze tra i file del progetto (Inclusioni).
        """
        lines = ["graph TD"]
        file_edges: Set[tuple] = set()

        for rel_path, meta in all_metadata.items():
            # 1. Dipendenze da direttive #include
            for inc in meta.get("includes", []):
                inc_file = inc["included_file"]
                if not inc_file.startswith("<"): # Ignoriamo gli include di sistema come <stdio.h>
                    file_edges.add((rel_path, inc_file))

        count = 0
        for src_file, dst_file in file_edges:
            if count >= max_edges:
                break
            src_clean = os.path.basename(src_file).replace('.', '_').replace('-', '_').replace(' ', '_')
            dst_clean = os.path.basename(dst_file).replace('.', '_').replace('-', '_').replace(' ', '_')
            lines.append(f'  {src_clean}["{src_file}"] --> {dst_clean}["{dst_file}"]')
            count += 1

        return "\n".join(lines)




if __name__ == "__main__":
    test_dir = r"d:\python\TESI_Nicola_Flego\Test_code\Easy C"
    c_files = [
        os.path.join(test_dir, "ring_buffer.c"),
        os.path.join(test_dir, "main.c")
    ]

    graph = DependencyGraph()
    graph.build_from_project(c_files, include_dirs=[test_dir])

    print("=== PIPELINE: DIPENDENZE E ORDINAMENTO TOPOLOGICO ===\n")
    print(f"Nodi totali identificati nel grafo: {len(graph.nodes)}")
    
    sccs = graph.tarjan_scc()
    print(f"Componenti Fortemente Connesse (SCC / Tarjan): {sccs}")

    bottom_up_order = graph.get_topological_order_bottom_up()
    print("\n--- Sequenza di Elaborazione Bottom-Up (Dependencies-First) ---")
    for step, scc in enumerate(bottom_up_order, 1):
        print(f"  Step {step}: Processa -> {scc}")

    # Salva il grafo in formato Mermaid
    with open("dependency_graph.mmd", "w", encoding="utf-8") as f:
        f.write(graph.export_mermaid())
    print("\nGrafo delle dipendenze salvato in: dependency_graph.mmd")
