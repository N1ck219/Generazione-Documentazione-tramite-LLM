import os
import json
import sqlite3
from typing import Dict, List, Any, Set

def generate_interactive_call_graph(
    metadata_path: str,
    db_path: str,
    output_html_path: str,
    project_name: str = "Progetto C"
):
    """
    Genera una Single-Page Web App interattiva (HTML + Cytoscape.js) per navigare
    il Call Graph e le dipendenze in modo gerarchico, con filtri, ricerca,
    drill-down per modulo/file e ispezione Doxygen live.
    """
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"File metadati non trovato: {metadata_path}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        all_metadata = json.load(f)

    # 1. Recupera le informazioni di documentazione e complessità dal database SQLite
    doc_info_map = {}
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                rows = cursor.execute(
                    "SELECT name, file_path, signature, brief_summary, full_doxygen_doc, time_complexity, space_complexity, category FROM function_docs"
                ).fetchall()
                for r in rows:
                    doc_info_map[r[0]] = {
                        "name": r[0],
                        "file_path": r[1] or "",
                        "signature": r[2] or "",
                        "brief_summary": r[3] or "",
                        "full_doxygen_doc": r[4] or "",
                        "time_complexity": r[5] or "O(1)",
                        "space_complexity": r[6] or "O(1)",
                        "category": r[7] or "Generale"
                    }
        except Exception as e:
            print(f"  [HTML GRAPH WARNING] Impossibile leggere SQLite docs: {e}")

    # Standard C/C++ Library functions e STL da identificare come nodi di sistema
    stdlib_funcs = {
        "malloc", "free", "calloc", "realloc", "memcpy", "memset", "memmove",
        "printf", "sprintf", "snprintf", "fprintf", "fopen", "fclose", "fread",
        "fwrite", "fseek", "ftell", "rewind", "exit", "abort", "strcmp", "strncmp",
        "strcpy", "strncpy", "strlen", "strcat", "strncat", "strchr", "strrchr",
        "strstr", "strtod", "strtol", "atoi", "atof", "fabs", "tolower", "toupper",
        "sscanf", "_setjmp", "longjmp", "std::cout", "std::cin", "std::endl",
        "std::string", "std::vector", "std::map", "std::unordered_map", "std::set",
        "std::make_shared", "std::make_unique", "std::move", "std::forward", "std::sort"
    }

    # 2. Costruzione Nodi (Moduli e Funzioni) ed Archi
    modules: Dict[str, Dict[str, Any]] = {}
    functions: Dict[str, Dict[str, Any]] = {}
    edges_list = []
    edges_set = set()

    for rel_path, meta in all_metadata.items():
        clean_module_name = os.path.basename(rel_path)
        is_test_mod = any(t in rel_path.lower() for t in ["test", "unity", "mock", "fuzz"])
        
        mod_id = f"mod_{clean_module_name.replace('.', '_').replace('-', '_')}"
        if mod_id not in modules:
            modules[mod_id] = {
                "id": mod_id,
                "label": clean_module_name,
                "path": rel_path,
                "is_test": is_test_mod,
                "func_count": 0
            }

        for func in meta.get("functions", []):
            fn_name = func["name"]
            is_sys = fn_name in stdlib_funcs
            doc = doc_info_map.get(fn_name, {})
            
            # Assegna il modulo padre
            parent_mod_id = "mod_stdlib" if is_sys else mod_id
            if not is_sys:
                modules[mod_id]["func_count"] += 1

            functions[fn_name] = {
                "id": fn_name,
                "label": fn_name,
                "parent": parent_mod_id,
                "file": rel_path,
                "is_sys": is_sys,
                "is_test": is_test_mod,
                "signature": doc.get("signature") or f"{func.get('return_type', 'void')} {fn_name}()",
                "brief": doc.get("brief_summary") or "Funzione C estratta dall'AST.",
                "doxygen": doc.get("full_doxygen_doc") or f"/** @brief {fn_name} */",
                "time_comp": doc.get("time_complexity") or func.get("time_complexity") or "O(1)",
                "space_comp": doc.get("space_complexity") or func.get("space_complexity") or "O(1)",
                "category": doc.get("category") or "Generale"
            }

            for callee in func.get("callees", []):
                callee_sys = callee in stdlib_funcs
                if callee not in functions:
                    functions[callee] = {
                        "id": callee,
                        "label": callee,
                        "parent": "mod_stdlib" if callee_sys else "mod_external",
                        "file": "C Runtime / Library" if callee_sys else "External Symbol",
                        "is_sys": callee_sys,
                        "is_test": is_test_mod,
                        "signature": f"void {callee}()",
                        "brief": f"Funzione della libreria standard C: `{callee}`." if callee_sys else f"Simbolo esterno: `{callee}`.",
                        "doxygen": f"/** @brief {callee} */",
                        "time_comp": "O(1)",
                        "space_comp": "O(1)",
                        "category": "C Standard Library" if callee_sys else "Esterno"
                    }

                edge_key = (fn_name, callee)
                if edge_key not in edges_set:
                    edges_set.add(edge_key)
                    edges_list.append({
                        "source": fn_name,
                        "target": callee,
                        "is_sys": callee_sys
                    })

    # Contenitore per Standard Library
    modules["mod_stdlib"] = {
        "id": "mod_stdlib",
        "label": "⚙️ C Standard Library",
        "path": "system_headers",
        "is_test": False,
        "func_count": sum(1 for f in functions.values() if f["is_sys"])
    }

    elements_data = {
        "modules": list(modules.values()),
        "functions": list(functions.values()),
        "edges": edges_list,
        "project_name": project_name,
        "stats": {
            "total_functions": len(functions),
            "total_edges": len(edges_list),
            "total_modules": len(modules)
        }
    }

    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Call Graph Interattivo - {project_name}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
  <style>
    :root {{
      --bg-dark: #0f172a;
      --panel-bg: rgba(30, 41, 59, 0.9);
      --border-color: #334155;
      --accent: #38bdf8;
      --accent-hover: #0ea5e9;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      overflow: hidden;
      display: flex;
      height: 100vh;
      width: 100vw;
    }}

    #topbar {{
      position: absolute;
      top: 16px;
      left: 16px;
      right: 16px;
      z-index: 100;
      display: flex;
      gap: 12px;
      align-items: center;
      background: var(--panel-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 10px 18px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
    }}
    .title-box h1 {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--accent);
      white-space: nowrap;
    }}
    .title-box span {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}
    .search-input {{
      flex: 1;
      max-width: 320px;
      padding: 8px 14px;
      background: rgba(15, 23, 42, 0.75);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      color: var(--text-main);
      font-size: 0.85rem;
      outline: none;
      transition: all 0.2s ease;
    }}
    .search-input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
    }}
    .btn {{
      background: #1e293b;
      color: var(--text-main);
      border: 1px solid var(--border-color);
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 0.8rem;
      cursor: pointer;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }}
    .btn:hover {{
      background: var(--accent);
      color: #0f172a;
      border-color: var(--accent);
    }}
    .btn.active {{
      background: var(--accent);
      color: #0f172a;
    }}
    .badge {{
      background: rgba(56, 189, 248, 0.2);
      color: var(--accent);
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: bold;
    }}

    #cy {{
      flex: 1;
      height: 100%;
      background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
    }}

    #sidebar {{
      width: 440px;
      height: 100%;
      background: var(--panel-bg);
      backdrop-filter: blur(16px);
      border-left: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      transform: translateX(100%);
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 90;
      box-shadow: -10px 0 30px rgba(0,0,0,0.5);
    }}
    #sidebar.open {{
      transform: translateX(0);
    }}
    .sidebar-header {{
      padding: 20px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .sidebar-header h2 {{
      font-size: 1.2rem;
      color: var(--text-main);
      word-break: break-all;
    }}
    .sidebar-header .close-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 1.4rem;
      cursor: pointer;
      line-height: 1;
    }}
    .sidebar-header .close-btn:hover {{ color: #fff; }}
    .sidebar-content {{
      padding: 20px;
      overflow-y: auto;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .meta-card {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px;
      font-size: 0.85rem;
    }}
    .meta-row {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
    }}
    .meta-row:last-child {{ margin-bottom: 0; }}
    .meta-label {{ color: var(--text-muted); }}
    .meta-val {{ color: var(--text-main); font-weight: 600; }}
    pre code {{
      display: block;
      background: #090d16;
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 12px;
      color: #38bdf8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.8rem;
      white-space: pre-wrap;
      word-break: break-all;
    }}

    #legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: var(--panel-bg);
      backdrop-filter: blur(10px);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 0.75rem;
      display: flex;
      gap: 14px;
      z-index: 80;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 6px; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  </style>
</head>
<body>

  <div id="topbar">
    <div class="title-box">
      <h1>📊 {project_name}</h1>
      <span>Interactive Call Graph</span>
    </div>
    
    <input type="text" id="searchInput" class="search-input" placeholder="🔍 Cerca funzione o modulo...">
    
    <select id="moduleFilter" class="search-input" style="max-width: 220px; cursor: pointer;">
      <option value="ALL">📁 Tutti i Moduli</option>
    </select>

    <button id="btnToggleSys" class="btn" title="Mostra/Nascondi le funzioni della C Standard Library">
      ⚙️ C StdLib: <span id="sysStatus">Nascosto</span>
    </button>

    <button id="btnToggleTests" class="btn" title="Mostra/Nascondi le suite di test e mock">
      🧪 Test Suites: <span id="testStatus">Visibile</span>
    </button>

    <button id="btnResetView" class="btn" title="Centra ed adatta la vista">
      🎯 Centra Grafo
    </button>

    <div style="margin-left: auto; display: flex; gap: 8px; align-items: center;">
      <span class="badge" id="statsBadge">Nodi: {len(functions)} | Archi: {len(edges_list)}</span>
    </div>
  </div>

  <div id="cy"></div>

  <div id="legend">
    <div class="legend-item"><span class="dot" style="background:#0284c7;"></span> Funzione Core</div>
    <div class="legend-item"><span class="dot" style="background:#854d0e;"></span> Funzione Test</div>
    <div class="legend-item"><span class="dot" style="background:#334155; border:1px dashed #64748b;"></span> C Standard Library</div>
    <div class="legend-item"><span class="dot" style="background:#38bdf8;"></span> Selezionata / Vicinato</div>
  </div>

  <div id="sidebar">
    <div class="sidebar-header">
      <div>
        <h2 id="sideTitle">Dettaglio Funzione</h2>
        <span id="sideCategory" class="badge" style="margin-top: 4px; display: inline-block;">Generale</span>
      </div>
      <button class="close-btn" onclick="closeSidebar()">&times;</button>
    </div>
    <div class="sidebar-content">
      <div class="meta-card">
        <div class="meta-row"><span class="meta-label">File Sorgente:</span><span id="sideFile" class="meta-val">-</span></div>
        <div class="meta-row"><span class="meta-label">Firma C:</span><span id="sideSig" class="meta-val">-</span></div>
        <div class="meta-row"><span class="meta-label">Complessità AST:</span><span id="sideComp" class="meta-val">-</span></div>
      </div>

      <div>
        <h4 style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px;">Sommario Esecutivo:</h4>
        <p id="sideBrief" style="font-size: 0.9rem; line-height: 1.5; color: #e2e8f0;">-</p>
      </div>

      <div>
        <h4 style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px;">Documentazione Doxygen Certificata:</h4>
        <pre><code id="sideDoxygen">/* Doxygen */</code></pre>
      </div>

      <div>
        <button id="btnFocusNeighborhood" class="btn" style="width: 100%; justify-content: center;">
          🔍 Isola Flusso (Chiamanti e Chiamati)
        </button>
      </div>
    </div>
  </div>

  <script>
    const graphData = {json.dumps(elements_data)};
    let showSys = false; // Ottimizzazione: Nascosto di default per massime performance sui grandi progetti
    let showTests = true;
    let selectedModule = 'ALL';
    let selectedNodeId = null;

    // Popola il selettore dei moduli
    const modSelect = document.getElementById('moduleFilter');
    graphData.modules.forEach(m => {{
      if (m.id !== 'mod_stdlib') {{
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = '📁 ' + m.label + ' (' + m.func_count + ' fn)';
        modSelect.appendChild(opt);
      }}
    }});

    function buildElements() {{
      const elements = [];
      const allowedModuleIds = new Set();
      
      graphData.modules.forEach(m => {{
        if (!showTests && m.is_test) return;
        if (!showSys && m.id === 'mod_stdlib') return;
        if (selectedModule !== 'ALL' && m.id !== selectedModule && m.id !== 'mod_stdlib') return;
        allowedModuleIds.add(m.id);
        elements.push({{
          group: 'nodes',
          data: {{
            id: m.id,
            label: m.label,
            isModule: true
          }}
        }});
      }});

      const includedFuncNames = new Set();
      graphData.functions.forEach(f => {{
        if (!showSys && f.is_sys) return;
        if (!showTests && f.is_test) return;
        if (selectedModule !== 'ALL' && f.parent !== selectedModule && (!f.is_sys || !showSys)) return;
        includedFuncNames.add(f.id);
        elements.push({{
          group: 'nodes',
          data: {{
            id: f.id,
            label: f.label,
            parent: allowedModuleIds.has(f.parent) ? f.parent : undefined,
            is_sys: f.is_sys,
            is_test: f.is_test,
            meta: f
          }}
        }});
      }});

      const validNodeIds = new Set(elements.map(e => e.data.id));
      graphData.edges.forEach((e, idx) => {{
        if (validNodeIds.has(e.source) && validNodeIds.has(e.target)) {{
          elements.push({{
            group: 'edges',
            data: {{
              id: 'e_' + idx,
              source: e.source,
              target: e.target,
              is_sys: e.is_sys
            }}
          }});
        }}
      }});

      // Aggiorna badge statistiche
      const statBadge = document.getElementById('statsBadge');
      if (statBadge) {{
        statBadge.innerText = 'Nodi visibili: ' + includedFuncNames.size + ' | Archi: ' + elements.filter(x => x.group === 'edges').length;
      }}

      return elements;
    }}

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: buildElements(),
      // Opzioni di Rendering High-Performance per Grafi Grandi
      hideEdgesOnViewport: true,
      textureOnViewport: true,
      pixelRatio: 'auto',
      boxSelectionEnabled: false,
      layout: {{
        name: 'dagre',
        rankDir: 'LR',
        nodeSep: 40,
        rankSep: 75,
        animate: false
      }},
      style: [
        {{
          selector: 'node[!isModule]',
          style: {{
            'background-color': '#0284c7',
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-size': '11px',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 'label',
            'height': 28,
            'padding': '8px',
            'shape': 'round-rectangle',
            'border-width': 1,
            'border-color': '#38bdf8',
            'text-max-width': '180px',
            'text-wrap': 'ellipsis'
          }}
        }},
        {{
          selector: 'node[?is_sys]',
          style: {{
            'background-color': '#334155',
            'border-color': '#64748b',
            'border-style': 'dashed',
            'color': '#cbd5e1'
          }}
        }},
        {{
          selector: 'node[?is_test]',
          style: {{
            'background-color': '#854d0e',
            'border-color': '#eab308'
          }}
        }},
        {{
          selector: 'node[?isModule]',
          style: {{
            'background-color': 'rgba(15, 23, 42, 0.4)',
            'border-color': '#475569',
            'border-width': 2,
            'border-style': 'solid',
            'label': 'data(label)',
            'color': '#94a3b8',
            'font-size': '13px',
            'font-weight': 'bold',
            'text-valign': 'top',
            'text-halign': 'center',
            'padding': '20px'
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'width': 1.5,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
            'opacity': 0.7
          }}
        }},
        {{
          selector: 'edge[?is_sys]',
          style: {{
            'line-color': '#334155',
            'target-arrow-color': '#334155',
            'line-style': 'dotted'
          }}
        }},
        {{
          selector: '.highlighted',
          style: {{
            'background-color': '#38bdf8 !important',
            'border-color': '#fff !important',
            'border-width': 2,
            'color': '#0f172a',
            'font-weight': 'bold',
            'z-index': 999
          }}
        }},
        {{
          selector: '.edge-highlighted',
          style: {{
            'line-color': '#38bdf8 !important',
            'target-arrow-color': '#38bdf8 !important',
            'width': 3,
            'opacity': 1,
            'z-index': 999
          }}
        }},
        {{
          selector: '.faded',
          style: {{
            'opacity': 0.12
          }}
        }}
      ]
    }});

    function runLayout() {{
      cy.json({{ elements: buildElements() }});
      cy.layout({{ name: 'dagre', rankDir: 'LR', nodeSep: 40, rankSep: 75, animate: false }}).run();
      cy.fit(null, 40);
    }}

    cy.on('tap', 'node[!isModule]', function(evt){{
      const node = evt.target;
      selectedNodeId = node.id();
      const meta = node.data('meta');
      openSidebar(meta);
      highlightNeighborhood(node);
    }});

    cy.on('tap', function(evt){{
      if (evt.target === cy) {{
        clearHighlight();
        closeSidebar();
      }}
    }});

    function highlightNeighborhood(node) {{
      clearHighlight();
      const neighborhood = node.neighborhood().add(node);
      cy.elements().addClass('faded');
      neighborhood.removeClass('faded');
      node.addClass('highlighted');
      node.connectedEdges().addClass('edge-highlighted');
    }}

    function clearHighlight() {{
      cy.elements().removeClass('faded highlighted edge-highlighted');
    }}

    function openSidebar(meta) {{
      if (!meta) return;
      document.getElementById('sideTitle').innerText = meta.label;
      document.getElementById('sideCategory').innerText = meta.category || 'Generale';
      document.getElementById('sideFile').innerText = meta.file || '-';
      document.getElementById('sideSig').innerText = meta.signature || '-';
      document.getElementById('sideComp').innerText = `Tempo: ${{meta.time_comp}} | Spazio: ${{meta.space_comp}}`;
      document.getElementById('sideBrief').innerText = meta.brief || '-';
      document.getElementById('sideDoxygen').innerText = meta.doxygen || 'N/A';
      document.getElementById('sidebar').classList.add('open');
    }}

    function closeSidebar() {{
      document.getElementById('sidebar').classList.remove('open');
      clearHighlight();
    }}

    document.getElementById('btnFocusNeighborhood').addEventListener('click', () => {{
      if (!selectedNodeId) return;
      const node = cy.getElementById(selectedNodeId);
      if (node.length) {{
        const neighborhood = node.neighborhood().add(node);
        cy.fit(neighborhood, 50);
      }}
    }});

    document.getElementById('moduleFilter').addEventListener('change', function(e) {{
      selectedModule = e.target.value;
      runLayout();
    }});

    document.getElementById('btnToggleSys').addEventListener('click', function() {{
      showSys = !showSys;
      this.classList.toggle('active', showSys);
      document.getElementById('sysStatus').innerText = showSys ? 'Visibile' : 'Nascosto';
      runLayout();
    }});

    document.getElementById('btnToggleTests').addEventListener('click', function() {{
      showTests = !showTests;
      this.classList.toggle('active', !showTests);
      document.getElementById('testStatus').innerText = showTests ? 'Visibile' : 'Nascosto';
      runLayout();
    }});

    document.getElementById('btnResetView').addEventListener('click', () => {{
      clearHighlight();
      cy.fit(null, 40);
    }});

    document.getElementById('searchInput').addEventListener('input', function(e) {{
      const val = e.target.value.trim().toLowerCase();
      if (!val) {{
        clearHighlight();
        return;
      }}
      const matches = cy.nodes().filter(n => n.data('label') && n.data('label').toLowerCase().includes(val));
      if (matches.length > 0) {{
        cy.elements().addClass('faded');
        matches.removeClass('faded').addClass('highlighted');
        cy.fit(matches, 80);
      }}
    }});
  </script>
</body>
</html>
"""

    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"-> Call Graph Interattivo HTML generato in: {output_html_path}")
    return output_html_path
