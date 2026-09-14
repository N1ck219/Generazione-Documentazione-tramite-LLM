import os
import re
import html

def export_full_documentation_html(markdown_path: str, output_html_path: str, project_name: str = "Progetto C"):
    """
    Converte il file DOCUMENTATION.md in una Web App HTML autonoma, elegante e moderna,
    con rendering nativo dei diagrammi Mermaid.js, syntax highlighting per il codice C,
    sidebar di navigazione ad albero, indice delle categorie e barra di ricerca live.
    """
    if not os.path.exists(markdown_path):
        raise FileNotFoundError(f"File Markdown non trovato: {markdown_path}")

    with open(markdown_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Pre-elaborazione e conversione Markdown -> HTML minimale per massima compatibilità e bellezza
    # Usiamo un template HTML con Mermaid.js e Prism.js / Highlight.js via CDN + Markdown-it
    escaped_md = json_escape(md_text)

    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Documentazione Tecnica - {project_name}</title>
  
  <!-- Google Fonts & Modern Icons -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  
  <!-- Markdown-it, Mermaid, Highlight.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/markdown-it@13.0.2/dist/markdown-it.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.8.0/dist/mermaid.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/c.min.js"></script>

  <style>
    :root {{
      --bg-body: #0b0f19;
      --bg-sidebar: #0f172a;
      --bg-card: #1e293b;
      --border-color: #334155;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.2);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --code-bg: #090d16;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-body);
      color: var(--text-main);
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
    }}

    /* Sidebar Navigation */
    #sidebar {{
      width: 330px;
      height: 100%;
      background-color: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      z-index: 50;
      box-shadow: 4px 0 24px rgba(0, 0, 0, 0.35);
    }}
    .sidebar-brand {{
      padding: 22px 20px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(15, 23, 42, 0.7);
    }}
    .sidebar-brand span {{
      font-size: 1.4rem;
    }}
    .sidebar-brand h1 {{
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: -0.01em;
      margin: 0;
      padding: 0;
      border: none;
    }}
    .search-box {{
      padding: 12px 18px;
      border-bottom: 1px solid var(--border-color);
      background: rgba(15, 23, 42, 0.4);
    }}
    .search-box input {{
      width: 100%;
      padding: 9px 14px;
      background: #090d16;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      color: var(--text-main);
      font-size: 0.85rem;
      outline: none;
      transition: all 0.2s ease;
    }}
    .search-box input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }}
    .toc-container {{
      flex: 1;
      overflow-y: auto;
      padding: 14px 14px 28px 14px;
      scrollbar-width: thin;
      scrollbar-color: #334155 transparent;
    }}
    .toc-container ul {{
      list-style: none;
      padding-left: 0;
      position: relative;
    }}
    .toc-container li {{
      margin-bottom: 2px;
      position: relative;
      transition: all 0.2s ease;
    }}
    
    /* Collapsible Node Row */
    .toc-item-row {{
      display: flex;
      align-items: center;
      width: 100%;
      border-radius: 6px;
      position: relative;
    }}
    
    /* Toggle Chevron Arrow */
    .toc-toggle {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      width: 20px;
      height: 20px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.65rem;
      transition: transform 0.2s ease, color 0.2s ease;
      user-select: none;
      margin-right: 2px;
      flex-shrink: 0;
    }}
    .toc-toggle:hover {{
      color: var(--accent);
    }}
    .toc-toggle.collapsed {{
      transform: rotate(-90deg);
    }}
    .toc-toggle.empty {{
      visibility: hidden;
      pointer-events: none;
    }}

    /* Base TOC Link */
    .toc-link {{
      text-decoration: none;
      display: flex;
      align-items: center;
      flex: 1;
      border-radius: 6px;
      transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
      word-break: break-word;
      line-height: 1.4;
      position: relative;
      padding: 4px 6px;
    }}
    
    /* Level 1: H2 (Capitolo Principale) */
    .toc-row-h2 {{
      margin-top: 16px;
      margin-bottom: 4px;
      background: rgba(30, 41, 59, 0.5);
      border-left: 3px solid var(--accent);
      border-radius: 0 6px 6px 0;
      padding: 4px 6px;
    }}
    .toc-row-h2 .toc-link {{
      font-weight: 700;
      font-size: 0.82rem;
      color: #f1f5f9;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .toc-row-h2:hover {{
      background: rgba(56, 189, 248, 0.15);
    }}
    .toc-row-h2 .toc-toggle {{
      color: var(--accent);
    }}

    /* Level 2: H3 (Sottocapitolo / Modulo / Struttura) */
    .toc-row-h3 {{
      margin-left: 12px;
      padding: 2px 4px;
      border-left: 1px solid rgba(51, 65, 85, 0.8);
    }}
    .toc-row-h3 .toc-link {{
      font-size: 0.84rem;
      font-weight: 600;
      color: #cbd5e1;
    }}
    .toc-row-h3:hover {{
      border-left-color: var(--accent);
      background: rgba(56, 189, 248, 0.08);
      transform: translateX(2px);
    }}
    .toc-row-h3:hover .toc-link {{
      color: var(--accent);
    }}

    /* Level 3: H4 (Funzione specifica / Item di dettaglio) */
    .toc-row-h4 {{
      margin-left: 28px;
      padding: 2px 4px 2px 8px;
      border-left: 1px dashed rgba(51, 65, 85, 0.6);
    }}
    .toc-row-h4 .toc-link {{
      font-size: 0.8rem;
      font-weight: 400;
      font-family: 'Fira Code', ui-monospace, monospace;
      color: #94a3b8;
    }}
    .toc-row-h4:hover {{
      border-left-color: var(--accent);
      background: rgba(56, 189, 248, 0.06);
      transform: translateX(3px);
    }}
    .toc-row-h4:hover .toc-link {{
      color: #38bdf8;
    }}
    
    .toc-link.active-toc {{
      background: rgba(56, 189, 248, 0.15) !important;
      color: var(--accent) !important;
      font-weight: 600;
    }}
    
    /* Collapsed child items */
    .toc-collapsed-child {{
      display: none !important;
    }}

    /* Main Content Area */
    #main-content {{
      flex: 1;
      height: 100%;
      overflow-y: auto;
      padding: 40px 60px;
      scroll-behavior: smooth;
    }}
    .doc-container {{
      max-width: 1050px;
      margin: 0 auto;
      line-height: 1.7;
    }}

    /* Typography & Markdown Styles */
    h1, h2, h3, h4, h5 {{
      color: var(--text-main);
      font-weight: 700;
      margin-top: 36px;
      margin-bottom: 16px;
      letter-spacing: -0.02em;
      border-bottom: 1px solid rgba(51, 65, 85, 0.4);
      padding-bottom: 8px;
    }}
    h1 {{ font-size: 2.2rem; border-bottom: 2px solid var(--accent); margin-top: 0; }}
    h2 {{ font-size: 1.6rem; color: var(--accent); margin-top: 48px; }}
    h3 {{ font-size: 1.25rem; color: #e2e8f0; }}
    h4 {{ font-size: 1.05rem; color: #cbd5e1; border-bottom: none; }}
    
    p {{ margin-bottom: 16px; color: #cbd5e1; }}
    blockquote {{
      border-left: 4px solid var(--accent);
      background: rgba(30, 41, 59, 0.4);
      padding: 12px 18px;
      border-radius: 0 8px 8px 0;
      margin: 18px 0;
      color: #94a3b8;
      font-style: italic;
    }}
    hr {{
      border: none;
      border-top: 1px solid var(--border-color);
      margin: 40px 0;
    }}
    
    /* Code Blocks */
    pre {{
      background-color: var(--code-bg) !important;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 16px 20px;
      overflow-x: auto;
      margin: 18px 0;
      box-shadow: 0 8px 24px -6px rgba(0,0,0,0.5);
    }}
    code {{
      font-family: 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.88rem;
    }}
    :not(pre) > code {{
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.85em;
    }}

    /* Tables */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 24px 0;
      background: var(--bg-card);
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border-color);
    }}
    th, td {{
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border-color);
      font-size: 0.9rem;
    }}
    th {{
      background: #0f172a;
      color: var(--accent);
      font-weight: 600;
    }}
    tr:hover td {{
      background: rgba(56, 189, 248, 0.03);
    }}

    /* Mermaid Diagrams */
    .mermaid {{
      background: #090d16;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 20px;
      margin: 24px 0;
      display: flex;
      justify-content: center;
    }}

    /* Floating Navigation Action */
    .btn-top {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--accent);
      color: #0f172a;
      border: none;
      border-radius: 50%;
      width: 44px;
      height: 44px;
      font-size: 1.2rem;
      font-weight: bold;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(56, 189, 248, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
    .sidebar-actions {{
      display: flex;
      gap: 6px;
      margin-top: 8px;
    }}
    .btn-toc-action {{
      flex: 1;
      padding: 5px 8px;
      font-size: 0.72rem;
      font-weight: 600;
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      color: var(--text-muted);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      transition: all 0.15s ease;
    }}
    .btn-toc-action:hover {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border-color: var(--accent);
    }}
  </style>
</head>
<body>

  <!-- Sidebar -->
  <aside id="sidebar">
    <div class="sidebar-brand">
      <span>📖</span>
      <h1>{project_name}</h1>
    </div>
    <div class="search-box">
      <input type="text" id="filterInput" placeholder="🔍 Cerca nell'indice...">
      <div class="sidebar-actions">
        <button id="btnCollapseAll" class="btn-toc-action" title="Comprimi tutti i capitoli e moduli">
          📁 Comprimi tutto
        </button>
        <button id="btnExpandAll" class="btn-toc-action" title="Espandi tutti i capitoli e moduli">
          📂 Espandi tutto
        </button>
      </div>
    </div>
    <div class="toc-container" id="tocList">
      <!-- Auto-generated TOC -->
    </div>
  </aside>

  <!-- Main Content Area -->
  <main id="main-content">
    <div class="doc-container" id="docContent">
      <!-- Rendered Markdown HTML -->
    </div>
  </main>

  <button class="btn-top" onclick="document.getElementById('main-content').scrollTo({{top: 0, behavior: 'smooth'}})" title="Torna in cima">↑</button>

  <script>
    const rawMarkdown = {escaped_md};

    // Configurazione Markdown-it con supporto syntax highlighting
    const md = window.markdownit({{
      html: true,
      linkify: true,
      typographer: true,
      highlight: function (str, lang) {{
        if (lang === 'mermaid') {{
          return '<div class="mermaid">' + str + '</div>';
        }}
        if (lang && hljs.getLanguage(lang)) {{
          try {{
            return '<pre><code class="hljs language-' + lang + '">' +
                   hljs.highlight(str, {{ language: lang, ignoreIllegals: true }}).value +
                   '</code></pre>';
          }} catch (__) {{}}
        }}
        return '<pre><code class="hljs">' + md.utils.escapeHtml(str) + '</code></pre>';
      }}
    }});

    // Rendering Markdown nel DOM
    const contentDiv = document.getElementById('docContent');
    contentDiv.innerHTML = md.render(rawMarkdown);

    // Inizializza Mermaid per i diagrammi renderizzati con fallback resiliente
    mermaid.initialize({{
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      themeVariables: {{
        primaryColor: '#0284c7',
        primaryTextColor: '#f8fafc',
        primaryBorderColor: '#38bdf8',
        lineColor: '#64748b',
        secondaryColor: '#1e293b',
        tertiaryColor: '#0f172a'
      }}
    }});

    // Esecuzione rendering asincrono non bloccante per ogni diagramma Mermaid
    document.querySelectorAll('.mermaid').forEach((el, i) => {{
      const code = el.textContent;
      const graphId = 'mermaid-svg-' + i;
      mermaid.render(graphId, code).then(res => {{
        el.innerHTML = res.svg;
      }}).catch(err => {{
        console.warn('Errore rendering Mermaid diagram ' + i + ':', err);
        el.innerHTML = '<pre style="color:#ef4444;font-size:0.75rem;">Impossibile renderizzare il diagramma Mermaid: ' + err.message + '</pre>';
      }});
    }});

    // Generazione automatica Table of Contents (TOC) Gerarchica con Collasso/Espansione
    const tocContainer = document.getElementById('tocList');
    const headers = contentDiv.querySelectorAll('h2, h3, h4');
    const ul = document.createElement('ul');

    const tocNodes = [];
    let currentH2Node = null;
    let currentH3Node = null;

    headers.forEach((h, index) => {{
      const text = h.innerText.trim();
      const prevEl = h.previousElementSibling;
      let targetId = h.id;
      if (!targetId && prevEl && prevEl.tagName.toLowerCase() === 'a' && prevEl.id) {{
        targetId = prevEl.id;
      }}
      if (!targetId) {{
        targetId = 'section-' + text.toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/-+/g, '-') + '-' + index;
        h.id = targetId;
      }}

      const tag = h.tagName.toLowerCase(); // 'h2', 'h3', 'h4'
      const li = document.createElement('li');
      li.dataset.level = tag;
      
      const row = document.createElement('div');
      row.className = 'toc-item-row toc-row-' + tag;

      const toggleBtn = document.createElement('button');
      toggleBtn.className = 'toc-toggle';
      toggleBtn.innerHTML = '▼';
      toggleBtn.title = 'Espandi / Comprimi sezione';

      const a = document.createElement('a');
      a.href = '#' + targetId;
      a.innerText = text;
      a.className = 'toc-link';

      a.addEventListener('click', (e) => {{
        e.preventDefault();
        h.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }});

      row.appendChild(toggleBtn);
      row.appendChild(a);
      li.appendChild(row);
      ul.appendChild(li);

      const nodeObj = {{
        tag: tag,
        li: li,
        toggleBtn: toggleBtn,
        children: []
      }};
      tocNodes.push(nodeObj);

      if (tag === 'h2') {{
        currentH2Node = nodeObj;
        currentH3Node = null;
      }} else if (tag === 'h3') {{
        if (currentH2Node) {{
          currentH2Node.children.push(nodeObj);
        }}
        currentH3Node = nodeObj;
      }} else if (tag === 'h4') {{
        if (currentH3Node) {{
          currentH3Node.children.push(nodeObj);
        }} else if (currentH2Node) {{
          currentH2Node.children.push(nodeObj);
        }}
      }}
    }});

    // Configura i listener di click sulle freccette e nascondi le frecce per nodi foglia (senza figli)
    tocNodes.forEach(node => {{
      if (node.children.length === 0) {{
        node.toggleBtn.classList.add('empty');
      }} else {{
        node.toggleBtn.addEventListener('click', (e) => {{
          e.stopPropagation();
          const isCollapsed = node.toggleBtn.classList.toggle('collapsed');
          toggleSubtree(node, isCollapsed);
        }});
      }}
    }});

    function toggleSubtree(parentNode, collapse) {{
      function recurse(n) {{
        n.children.forEach(child => {{
          if (collapse) {{
            child.li.classList.add('toc-collapsed-child');
          }} else {{
            child.li.classList.remove('toc-collapsed-child');
            // Se il figlio era a sua volta espanso, ripristina i suoi sotto-figli
            if (!child.toggleBtn.classList.contains('collapsed')) {{
              recurse(child);
            }}
            return;
          }}
          recurse(child);
        }});
      }}
      recurse(parentNode);
    }}

    // Pulsanti Globali "Comprimi Tutto" / "Espandi Tutto"
    document.getElementById('btnCollapseAll').addEventListener('click', () => {{
      tocNodes.forEach(node => {{
        if (node.children.length > 0) {{
          node.toggleBtn.classList.add('collapsed');
          toggleSubtree(node, true);
        }}
      }});
    }});

    document.getElementById('btnExpandAll').addEventListener('click', () => {{
      tocNodes.forEach(node => {{
        if (node.children.length > 0) {{
          node.toggleBtn.classList.remove('collapsed');
          toggleSubtree(node, false);
        }}
      }});
    }});

    tocContainer.appendChild(ul);

    // ScrollSpy: Evidenzia automaticamente la voce attiva nella Sidebar durante lo scorrimento
    const observerOptions = {{
      root: document.getElementById('main-content'),
      rootMargin: '0px 0px -70% 0px',
      threshold: 0
    }};
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach(entry => {{
        if (entry.isIntersecting) {{
          const id = entry.target.id;
          if (id) {{
            document.querySelectorAll('.toc-link').forEach(link => {{
              if (link.getAttribute('href') === '#' + id) {{
                link.classList.add('active-toc');
              }} else {{
                link.classList.remove('active-toc');
              }}
            }});
          }}
        }}
      }});
    }}, observerOptions);

    headers.forEach(h => observer.observe(h));

    // Intercetta tutti i link interni nel corpo del documento (es. dall'indice delle funzioni) per lo smooth scroll
    contentDiv.querySelectorAll('a[href^="#"]').forEach(link => {{
      link.addEventListener('click', (e) => {{
        const hash = link.getAttribute('href');
        if (hash && hash !== '#') {{
          const target = document.getElementById(hash.substring(1)) || document.querySelector('[name="' + hash.substring(1) + '"]');
          if (target) {{
            e.preventDefault();
            target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
          }}
        }}
      }});
    }});

    // Filtro Live nella Sidebar
    document.getElementById('filterInput').addEventListener('input', function(e) {{
      const val = e.target.value.toLowerCase().trim();
      const links = tocContainer.querySelectorAll('a');
      links.forEach(a => {{
        const match = a.innerText.toLowerCase().includes(val);
        a.parentElement.style.display = match ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>
"""

    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"-> Portale Completo HTML generato in: {output_html_path}")
    return output_html_path

def json_escape(text: str) -> str:
    import json
    return json.dumps(text)
