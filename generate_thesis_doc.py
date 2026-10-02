import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_cell_borders(cell, top="CCCCCC", bottom="CCCCCC", left="CCCCCC", right="CCCCCC", sz="4"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{top}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{bottom}"/>'
        f'<w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{left}"/>'
        f'<w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{right}"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

def add_callout(doc, text, title="NOTA METODOLOGICA", border_color="005691", fill_color="F0F5FA"):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.5)
    
    cell = table.cell(0, 0)
    set_cell_background(cell, fill_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>'
        f'<w:top w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run_t = p.add_run(f"[{title}] ")
    run_t.bold = True
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(10)
    run_t.font.color.rgb = RGBColor(0x00, 0x56, 0x91)
    
    run_b = p.add_run(text)
    run_b.font.name = "Calibri"
    run_b.font.size = Pt(10)
    run_b.font.italic = True
    run_b.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    
    # spacing after table
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(4)

def format_table(table, col_widths, headers, data, header_bg="005691"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    # Header row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].width = Inches(col_widths[i])
        set_cell_background(hdr_cells[i], header_bg)
        set_cell_margins(hdr_cells[i], top=140, bottom=140, left=160, right=160)
        set_cell_borders(hdr_cells[i], top="003366", bottom="003366", left="003366", right="003366")
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(10)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            
    # Data rows
    for r_idx, row_data in enumerate(data):
        row = table.add_row()
        fill_color = "F9FBFD" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.text = str(val)
            cell.width = Inches(col_widths[c_idx])
            set_cell_background(cell, fill_color)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            set_cell_borders(cell, top="E0E0E0", bottom="E0E0E0", left="E0E0E0", right="E0E0E0")
            p = cell.paragraphs[0]
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            elif c_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

def build_thesis_report(output_path):
    doc = Document()
    
    # Page setup (A4, 2.5cm / ~1 inch margins)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        # Header and Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.text = "Tesi Magistrale - Nicola Flego | Documentazione di Avanzamento Progetto"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hp.runs[0].font.name = "Calibri"
        hp.runs[0].font.size = Pt(8.5)
        hp.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.text = "Stato dell'Arte, Tassonomia delle Metriche, Verifiche Sperimentali e Roadmap"
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fp.runs[0].font.name = "Calibri"
        fp.runs[0].font.size = Pt(8.5)
        fp.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # Styles
    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x26, 0x26, 0x26)
    
    # Title Section
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("GENERAZIONE AUTOMATICA E CERTIFICATA DI DOCUMENTAZIONE SOFTWARE PER CODEBASE C/C++")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(14)
    run_sub = sub_p.add_run("Orchestrazione Multi-Agente, Analisi Statica AST, Validazione Neurale e Round-Trip Differential Testing")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(13)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    
    # Metadata Box
    meta_table = doc.add_table(rows=2, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_widths = [3.25, 3.25]
    meta_data = [
        [("Candidato:", " Nicola Flego"), ("Data:", " Settembre 2026")],
        [("Progetto:", " Tesi di Laurea Magistrale"), ("Contesto:", " Ingegneria Informatica / AI & Software Eng.")]
    ]
    for r_idx, row in enumerate(meta_table.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.width = Inches(meta_widths[c_idx])
            set_cell_background(cell, "F2F6FA")
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            set_cell_borders(cell, top="D0DCE5", bottom="D0DCE5", left="D0DCE5", right="D0DCE5")
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            lbl, val = meta_data[r_idx][c_idx]
            r1 = p.add_run(lbl)
            r1.bold = True
            r1.font.size = Pt(10)
            r1.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
            r2 = p.add_run(val)
            r2.font.size = Pt(10)
            r2.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            
    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    
    # Abstract / Overview
    add_callout(
        doc,
        "Il presente documento fornisce una sintesi formale e organica del lavoro di ricerca svolto fino ad oggi. "
        "La trattazione è strutturata per facilitare il tracciamento accademico: i paper esaminati e i relativi concetti recepiti, "
        "l'articolazione formale delle metriche di valutazione introdotte a 4 livelli, le verifiche sperimentali e gli stress-test condotti "
        "(inclusa la dimostrazione della 'cecità logica' dei modelli neurali), i risultati del benchmark consolidato su 15 funzioni reali, "
        "e infine il piano dettagliato di cosa è stato fatto, cosa manca e come proseguire.",
        title="OBIETTIVO DEL DOCUMENTO"
    )
    
    # -------------------------------------------------------------
    # CAPITOLO 1: LETTERATURA E PAPER ANALIZZATI
    # -------------------------------------------------------------
    h1 = doc.add_heading(level=1)
    r = h1.add_run("1. Quadro Concettuale e Rassegna Sistematica della Letteratura")
    r.font.name = "Calibri"
    r.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    p = doc.add_paragraph(
        "L'attività di ricerca preliminare ha comportato l'analisi sistematica di 47 articoli scientifici (presenti nell'archivio "
        "di progetto Paper/) e delle relative note metodologiche. I contributi sono stati organizzati in 5 filoni cardine, "
        "da ciascuno dei quali sono stati estratti principi architetturali specifici poi integrati nella pipeline di tesi."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(8)
    
    # Tabella riassuntiva Paper
    doc.add_heading(level=2).add_run("1.1 Sintesi Sinottica dei Paper Fondamentali e Concetti Tratti")
    
    paper_table = doc.add_table(rows=1, cols=3)
    p_widths = [1.8, 1.3, 3.4]
    p_headers = ["Paper / Riferimento", "Anno / Provenienza", "Contributo Fondamentale Tratto nel Progetto"]
    p_data = [
        ["DocAgent: A Multi-Agent System for Automated Code Doc", "2024 (Apple, Meta, DeepMind)", 
         "Separazione funzionale dei ruoli tra agenti (Reader, Searcher, Writer, Verifier). Definizione della triade qualitativa essenziale: Completeness, Helpfulness e Truthfulness."],
        ["CodeWiki: Autonomous Repository Documentation", "2024 (arXiv)", 
         "Delega gerarchica ricorsiva (Repository Manager -> Module Agents -> Function Leaf). Sintesi bottom-up e generazione coordinata di pagine modulo, diagrammi Mermaid e README."],
        ["RepoAgent: An LLM-Based Open-Source Documentation System", "2024 (ACM / IEEE)", 
         "Paradigma di 'Continuous Documentation'. Architettura ChangeDetector con hook Git pre-commit e CI/CD per aggiornamenti incrementali mirati sui soli nodi AST modificati."],
        ["RepoSummary: Feature-Oriented Summarization", "2025 (Zhu et al., PKU)", 
         "Riconoscimento delle feature architetturali tramite clustering semantico ed analisi del flusso di dati, superando la visualizzazione a singoli file isolati."],
        ["PROCONSUL: Project Context for Code Summarization", "2024 (Lomshakov et al.)", 
         "Iniezione rigorosa del grafo di dipendenza (firme e contratti delle funzioni chiamate 'callees'). Dimostra che la conoscenza delle callees abbatte drasticamente le allucinazioni."],
        ["GraphCodeBERT & CodeBERT", "2020-2021 (Microsoft Research)", 
         "Modellazione pre-addestrata su AST e Data Flow. Utilizzo operativo di microsoft/codebert-base come metrica densa di allineamento sintattico e semantico (CodeBERTScore)."],
        ["CodePlan: Repository-Level Coding using LLMs", "2023 (Microsoft Research)", 
         "Pianificazione ad albero su grafi orientati interdipendenti e gestione ordinata delle modifiche a cascata."],
        ["Program Slicing & Method-Extraction Refactoring", "1984 (Weiser) / 2023", 
         "Segmentazione atomica dei blocchi di codice, analisi delle variabili dipendenti e isolamento di porzioni di codice orfano/dead-code (funzioni a in-degree = 0)."],
        ["Together We Go Further: LLMs and IDE Static Analysis", "2024 (ICSE / FSE)", 
         "Integrazione sinergica tra LLM (flessibilità semantica) e compilatori deterministici (Clang AST), dove l'analizzatore statico impone vincoli formali insormontabili."],
        ["G-EVAL: NLG Evaluation using GPT-4", "2023 (Liu et al.)", 
         "Campionamento Monte Carlo a più iterazioni con temperatura controllata per stabilizzare la varianza intrinseca delle valutazioni espresse da LLM."],
        ["JudgeLM: Fine-Tuned LLMs as Scalable Judges", "2023 (Zhu et al.)", 
         "Definizione di rubriche di valutazione analitiche con catalogazione tassonomica rigorosa dei difetti (DEF-1..DEF-5) ed eliminazione dei bias posizionali e di lunghezza."],
        ["AssetOpsBench: A Real-World Evaluation Benchmark", "2024 (Industry Benchmark)", 
         "Criteri di validazione su codebase industriali aperte eterogenee per stile e complessità (cJSON, OpenCV, TinyXML-2, sds, miniz, http-parser)."]
    ]
    format_table(paper_table, p_widths, p_headers, p_data)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # -------------------------------------------------------------
    # CAPITOLO 2: TASSONOMIA DELLE METRICHE IMPLEMENTATE
    # -------------------------------------------------------------
    h2 = doc.add_heading(level=1)
    r2 = h2.add_run("2. Tassonomia Dettagliata delle Metriche Implementate")
    r2.font.name = "Calibri"
    r2.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    p = doc.add_paragraph(
        "Al fine di superare i limiti storici della valutazione euristica della documentazione, il progetto ha introdotto "
        "un framework metrologico multi-livello articolato su 4 assi ortogonali e complementari: dal vincolo formale "
        "del compilatore fino all'esecuzione dinamica del codice rigenerato."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    
    # Livello 1
    doc.add_heading(level=2).add_run("Livello 1: Verifiche Formali e Contratti Sintattici AST (libclang)")
    p = doc.add_paragraph(
        "Garantisce che la documentazione rispetti la realtà fisica del codice sorgente compilato. Se una docstring "
        "viola la firma o dichiara tipi/parametri inesistenti, viene rigettata all'origine dal Verifier."
    )
    p.paragraph_format.line_spacing = 1.15
    
    doc.add_paragraph(
        "• Verifier Pass Rate (%): Tasso percentuale di funzioni documentate la cui docstring supera tutti i controlli sintattici e semantici formali definiti in src/verifier.py.\n"
        "• Parameter Slot-Filling (Precision, Recall, F1-Score): Confronto insiemistico tra i parametri formali estratti dall'AST (P_AST) e i tag @param documentati (P_Doc):\n"
        "      Precision = |P_AST ∩ P_Doc| / |P_Doc|\n"
        "      Recall = |P_AST ∩ P_Doc| / |P_AST|\n"
        "      F1 = 2 * (Precision * Recall) / (Precision + Recall)\n"
        "• Return Contract Match: Indicatore binario/probabilistico che certifica la congruenza del tipo di ritorno: se la funzione è 'void', la docstring non deve dichiarare ritorni; se restituisce un tipo concreto, la presenza di @return è obbligatoria.\n"
        "• Deterministic Complexity Enforcement: Calcolo deterministico della complessità asintotica temporale e spaziale Big-O mediante ispezione della profondità dei cicli (for/while/do), delle chiamate ricorsive e dell'uso di memoria heap/stack. Il tag @complexity viene iniettato direttamente dall'analizzatore."
    )
    
    # Livello 2
    doc.add_heading(level=2).add_run("Livello 2: Qualità Ingegneristica, Completezza ed Actionability")
    p = doc.add_paragraph(
        "Valuta se la documentazione fornisce indicazioni pragmatiche e prescrittive per lo sviluppatore che deve utilizzare o manutenere l'API."
    )
    doc.add_paragraph(
        "• Hallucination Rate Globale (%) ed Existence Ratio: Misura la percentuale di identificatori, tipi, macro o simboli menzionati nella documentazione che non hanno alcuna corrispondenza né nel Grafo delle Dipendenze del progetto né nella standard library C/C++ (soglia minima di conformità: Existence Ratio >= 0.80).\n"
        "• Actionability Score (AS) [0.0 - 1.0]: Indice pesato composto da 4 dimensioni operative:\n"
        "      AS = 0.35 * S_directionality + 0.20 * S_brief + 0.25 * S_return + 0.20 * S_memory_safety\n"
        "   dove S_directionality premia l'uso esplicito di [in], [out], [in,out]; S_memory_safety certifica clausole di ownership, divieti di free, allocazione e tag @pre/@warning.\n"
        "• Error Documentation Rate (EDR) [0% - 100%]: Rapporto tra i rami di errore presenti nell'AST del sorgente (control flow di uscita anomala, codici di errore, nullptr) e quelli esplicitamente documentati.\n"
        "• Edge Case Coverage (ECC) [0% - 100%]: Percentuale di guardie fisiche (null_guard, zero_negative_guard, boundary_check) tracciate nei prerequisiti e nei casi limite della documentazione."
    )
    
    # Livello 3
    doc.add_heading(level=2).add_run("Livello 3: Valutazione Semantica Neurale ed LLM-as-a-Judge")
    p = doc.add_paragraph(
        "Quantifica la vicinanza semantica della documentazione generata rispetto alla docstring di riferimento umana o standard, "
        "integrando un valutatore neurale avanzato basato su prompt critici."
    )
    doc.add_paragraph(
        "• Sentence-BERT (SBERT) Cosine Similarity: Similarità coseno tra gli embedding densi generati dal modello 'all-MiniLM-L6-v2' (spazio vettoriale R^384) applicata al brief generato rispetto al riferimento umano.\n"
        "• BERTScore & CodeBERTScore (P, R, F1): Allineamento token-to-token calcolato tramite Greedy Matching con pesi IDF su 'bert-base-uncased' e su 'microsoft/codebert-base'.\n"
        "• METEOR Score: Metrica basata su allineamenti lessicali esatti, stemming (Porter) e sinonimia WordNet con penalizzazione per frammentazione dei chunk di testo.\n"
        "• LLM-as-a-Judge (Monte Carlo Sampling): Valutazione a 5 iterazioni con temperatura controllata (T = 0.4) su due assi ortogonali:\n"
        "      - Faithfulness [1-5]: fedeltà assoluta al codice senza invenzioni (catalogazione difetti DEF-1..5).\n"
        "      - Alignment [1-5]: rispondenza all'intento architetturale e chiarezza espositiva.\n"
        "   Include la 'Rigenerazione Guidata': se lo score medio è inferiore a 4, la motivazione del Judge viene iniettata nel Writer Agent per una riscrittura correttiva automatica."
    )
    
    # Livello 4
    doc.add_heading(level=2).add_run("Livello 4: Downstream Utility e Round-Trip Differential Testing")
    p = doc.add_paragraph(
        "Rappresenta il test definitivo di utilità: la documentazione è sufficientemente precisa e autosufficiente "
        "da permettere a un programmatore (o a un modello) di utilizzare o re-implementare la funzione?"
    )
    doc.add_paragraph(
        "• Downstream Code Retrieval (MRR, Hit@1, Hit@5): Utilizza la documentazione generata come query in linguaggio naturale per recuperare la funzione corrispondente tra tutte le funzioni della libreria. Misura Mean Reciprocal Rank e tassi di successo.\n"
        "• Round-Trip Dual Differential Testing: Paradigma sperimentale esclusivo della tesi:\n"
        "   1. Un LLM Coder riceve unicamente la documentazione generata (docstring + scaffold di contesto) senza MAI vedere il codice C/C++ originale, e sintetizza una funzione Python equivalente (f_doc).\n"
        "   2. Una seconda funzione (f_ref) viene generata tramite traspilazione diretta del codice C/C++ originale.\n"
        "   3. Un generatore automatico produce una suite di test Pytest con casi limite e fuzzing intensivo con la libreria Hypothesis (@given, >50 input casuali).\n"
        "   4. Esecuzione differenziale speculare:\n"
        "      - Self-Consistency Pass Rate (%): percentuale di test superati da f_doc (misura la coerenza interna della docstring).\n"
        "      - Dual Agreement Rate (%): concordanza stretta f_doc(x) == f_ref(x) su tutti i vettori di input.\n"
        "• Tassonomia a 3 Categorie del Round-Trip:\n"
        "   - Categoria 1 (Stateless / Primitive): funzioni matematiche/scalari; concordanza 80%-100%.\n"
        "   - Categoria 2 (Pointer / Buffer-Driven): gestione di puntatori grezzi e offset; modellate con contenitori mutabili.\n"
        "   - Categoria 3 (Stateful / Object-Graph): metodi di classe incapsulati (TinyXML-2) o grafi ricorsivi (cJSON). Dimostra sperimentalmente il principio di Information Hiding: f_doc supera il 100% dei test sul contratto pubblico pur divergendo legittimamente dai dettagli privati di f_ref."
    )
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # -------------------------------------------------------------
    # CAPITOLO 3: VERIFICHE ALLE METRICHE E TEST SPERIMENTALI
    # -------------------------------------------------------------
    h3 = doc.add_heading(level=1)
    r3 = h3.add_run("3. Verifiche alle Metriche, Prove di Robustezza e Scoperte Empiriche")
    r3.font.name = "Calibri"
    r3.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    p = doc.add_paragraph(
        "Per convalidare scientificamente il framework prima della sua applicazione su larga scala, sono state condotte "
        "specifiche campagne di validazione empirica e stress-test (implementate negli script di verifica in utils/). "
        "I risultati hanno portato a scoperte di fondamentale importanza metodologica per la tesi."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    
    # 3.1 Suite funzionale
    doc.add_heading(level=2).add_run("3.1 Validazione della Pipeline (Pytest Unit & Integration)")
    p = doc.add_paragraph(
        "• test_extraction.py: Collaudo deterministico del parser libclang AST. Ha verificato l'estrazione senza perdita di struct complesse, enum anonimi, puntatori a funzione, macro precompilatore e la corretta costruzione del grafo caller-callee. Risultato: 100% test superati.\n"
        "• test_judge_agent.py: Validazione del flusso multi-agente e dell'agente Judge. È stato verificato il meccanismo di retry condizionale: al rilevamento di un punteggio insufficiente, il Judge rigenera la docstring incorporando la critica strutturata. Risultato: 100% test superati."
    )
    p.paragraph_format.line_spacing = 1.15
    
    # 3.2 Adversarial Inversion Paradox
    doc.add_heading(level=2).add_run("3.2 La Scoperta del 'Paradosso dell'Inversione Avversaria' (Cecità Logica)")
    p = doc.add_paragraph(
        "Nello studio di sensibilità (verify_metric_sensitivity.py), le metriche sono state confrontate su funzioni EQUIVALENT "
        "(stessa semantica ma sintassi diversa) e funzioni ADVERSARIAL (codice quasi identico ma con inversione di un operatore logico, es. '<' sostituito con '>')."
    )
    p.paragraph_format.line_spacing = 1.15
    
    # Tabella paradosso
    sens_table = doc.add_table(rows=1, cols=4)
    s_widths = [1.8, 1.4, 1.4, 1.9]
    s_headers = ["Metrica Neurale / NLP", "Score su EQUIVALENT", "Score su ADVERSARIAL", "Delta (Adversarial - Equiv)"]
    s_data = [
        ["ROUGE-L (Lessicale)", "0.552", "0.855", "+0.303 (Fallimento critico)"],
        ["TF-IDF Cosine Sim", "0.620", "0.911", "+0.291 (Fallimento critico)"],
        ["Sentence-BERT (SBERT)", "0.809", "0.956", "+0.147 (Fallimento neurale)"],
        ["BERTScore F1", "0.762", "0.938", "+0.176 (Fallimento neurale)"],
        ["CodeBERTScore F1", "0.867", "0.970", "+0.103 (Fallimento neurale)"]
    ]
    format_table(sens_table, s_widths, s_headers, s_data)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    add_callout(
        doc,
        "Tutte le metriche classiche di NLP e di embedding neurale presentano un Delta positivo: premiano un codice affetto "
        "da un bug catastrofico rispetto a una reimplementazione semanticamente corretta! La vicinanza lessicale maschera la rottura logica. "
        "Questa evidenza empirica dimostra l'assoluta necessità scientifica del Round-Trip Differential Testing: "
        "mentre CodeBERT assegna 0.970 al codice invertito, i test Pytest generati dal Round-Trip crollano a 0.0% di pass rate, "
        "identificando istantaneamente l'errore semantico.",
        title="SCOPERTA CHIAVE DELLA TESI: LA CECITÀ LOGICA DELLE METRICHE NEURALI"
    )
    
    # 3.3 Spiegazione XAI
    doc.add_heading(level=2).add_run("3.3 Spiegazione dei Meccanismi Interni (XAI: Explainable AI)")
    p = doc.add_paragraph(
        "Tramite lo script explain_metric_internals.py sono stati analizzati i motivi matematici alla base di tale fallimento:\n"
        "1. Greedy Matching di BERTScore: BERTScore calcola la similarità a coppie di token scegliendo sempre il massimo. L'inserimento di un token di negazione ('not') o l'inversione di un operatore non penalizza l'allineamento dei restanti N-1 token identici: la Recall rimane al 100% e la Precision scende solo di un fattore trascurabile 1/N.\n"
        "2. Mean Pooling di SBERT: La media aritmetica dei vettori di stato nasconde il segnale semantico dei token leggeri. I token di negazione o di confronto incidono solo per il 5-8% sull'orientamento dello spazio euclideo, venendo completamente 'dilavati' dai sostantivi dominanti.\n"
        "3. Truncation Trap (Limite Fisico dei Token): Modelli come MiniLM (256 token) e BERT/CodeBERT (512 token) troncano rigidamente le sequenze oltre la soglia massima. Funzioni lunghe che condividono la medesima intestazione ma divergono nella coda ottengono una similarità del 100%, ignorando completamente il disallineamento successivo."
    )
    p.paragraph_format.line_spacing = 1.15
    
    # 3.4 Canonical IR
    doc.add_heading(level=2).add_run("3.4 Studio sulle Rappresentazioni Canoniche Intermedie (IR)")
    p = doc.add_paragraph(
        "È stata verificata la possibilità di convertire il codice in Pseudocodice Algoritmico e Flowchart Mermaid prima del confronto. "
        "I test in verify_canonical_representation.py confermano che l'IR azzera il rumore sintattico tra C e Python (SBERT sale da 0.59 a 0.84), "
        "ma non sana la cecità logica intrinseca, confermando che il test dinamico basato su asserzioni è l'unico arbitro certo."
    )
    p.paragraph_format.line_spacing = 1.15
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # -------------------------------------------------------------
    # CAPITOLO 4: RISULTATI DEL BENCHMARK REALE
    # -------------------------------------------------------------
    h4 = doc.add_heading(level=1)
    r4 = h4.add_run("4. Risultati del Benchmark Reale di Produzione")
    r4.font.name = "Calibri"
    r4.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    p = doc.add_paragraph(
        "Il framework completo è stato testato su un benchmark consolidato di 15 funzioni eterogenee estratte casualmente "
        "da 6 importanti repository open source C/C++: cJSON, OpenCV, TinyXML-2, sds (Simple Dynamic Strings), miniz e http-parser."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    
    bench_table = doc.add_table(rows=1, cols=3)
    b_widths = [2.2, 1.3, 3.0]
    b_headers = ["Indicatore di Benchmark", "Punteggio Ottenuto", "Interpretazione e Significato Scientifico"]
    b_data = [
        ["Funzioni Valide al Verifier", "93.3% (14/15)", "Conformità formale quasi totale rispetto ai vincoli dell'AST."],
        ["Hallucination Rate Globale", "0.0%", "Assoluta assenza di parametri, tipi o simboli inventati dal modello."],
        ["Parameter F1-Score (vs AST)", "1.000", "Corrispondenza biunivoca perfetta tra parametri documentati e reali."],
        ["Return Contract Match", "0.9333", "Riconoscimento rigoroso delle clausole di ritorno (void vs tipi concreti)."],
        ["Actionability Score (AS)", "0.8133 / 1.0", "Documentazione ricca di direzionalità [in,out], brief e safety."],
        ["Error Documentation Rate (EDR)", "100.0%", "Piena copertura dei rami di errore e delle uscite anomale rilevate nel sorgente."],
        ["Edge Case Coverage (ECC)", "91.1%", "Intercettazione sistematica di guardie NULL e limiti di memoria."],
        ["LLM-Judge Faithfulness", "4.24 / 5.0", "Alta fedeltà verificata dal Giudice Monte Carlo a 5 iterazioni."],
        ["LLM-Judge Alignment", "4.63 / 5.0", "Piena comprensione dello scopo algoritmico e dell'architettura."],
        ["Judge Punteggio Combinato", "4.43 / 5.0", "Qualità globale di livello esperto secondo le rubriche DEF-1..5."],
        ["Code Retrieval MRR", "0.7861", "Capacità discriminante della documentazione come motore di ricerca codice."],
        ["Code Retrieval Hit@1 / Hit@5", "66.7% / 93.3%", "La funzione corretta è al 1° posto nel 66.7% dei casi, nella top 5 nel 93.3%."],
        ["Round-Trip Pass Rate (f_doc)", "65.1%", "Tasso di autosufficienza esecutiva del codice rigenerato solo da docstring."],
        ["Round-Trip Dual Agreement", "41.3%", "Concordanza speculare f_doc == f_ref (influenzata da Information Hiding)."],
        ["Sentence-BERT Cosine Sim", "0.5997", "Elevata similarità rispetto alle docstring originali umane."],
        ["CodeBERTScore F1", "0.7463", "Elevata coerenza lessicale e sintattica specifica per codice software."],
        ["Concept Checklist Score", "0.90 / 1.0", "Preservazione quasi integrale dei concetti critici (memoria, lock, eccezioni)."]
    ]
    format_table(bench_table, b_widths, b_headers, b_data)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    p = doc.add_paragraph(
        "Diagnostica dei Fallimenti nel Round-Trip:\n"
        "L'analisi automatizzata degli errori (roundtrip_error_report.md) ha isolato le cause del mancato passaggio dei test:\n"
        "• Behavioral / Contract Failure (40.0%): sottili discrepanze di contratto nei casi limite (es. restituzione di stringa vuota invece di None).\n"
        "• Interface / Signature Mismatch (30.0%): lievi disallineamenti nelle convenzioni posizionali degli argomenti.\n"
        "• Other Execution Error (16.7%): fallimenti determinati da asserzioni stringenti generate dal modulo Hypothesis.\n"
        "• Missing Symbol / Environment (13.3%): eccezioni di tipo NameError o AttributeError dovute a classi helper o costanti non iniettate nello scaffold di contesto."
    )
    p.paragraph_format.line_spacing = 1.15
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # -------------------------------------------------------------
    # CAPITOLO 5: COSA È FATTO, COSA MANCA E PROSSIMI PASSI (ROADMAP & TODO)
    # -------------------------------------------------------------
    h5 = doc.add_heading(level=1)
    r5 = h5.add_run("5. Stato di Avanzamento, Gap Rilevati e Roadmap dei Prossimi Passi")
    r5.font.name = "Calibri"
    r5.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    p = doc.add_paragraph(
        "In questa sezione viene formalizzato lo stato esatto del progetto, evidenziando chiaramente i traguardi già "
        "conseguiti, i punti aperti (estratti da TODO.md e RoadMap.md) e la pianificazione operativa concordata per le prossime fasi."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    
    doc.add_heading(level=2).add_run("5.1 Cosa è Stato Completato con Successo")
    doc.add_paragraph(
        "[COMPLETATO] 1. Motore di Estrazione AST C/C++: Parser basato su libclang con estrazione gerarchica di firme, struct, enum, macro, include, complessità deterministica Big-O e modelli di memoria.\n"
        "[COMPLETATO] 2. Modellazione del Grafo e Tarjan SCC: Costruzione del Call Graph orientato, risoluzione di cicli di ricorsione mutua e ordinamento topologico Bottom-Up (Dependencies-First).\n"
        "[COMPLETATO] 3. Pipeline Multi-Agente Strutturata: Agenti cooperativi specializzati (Reader, Searcher, Writer, Verifier, Judge) con gestione del retry critico condizionale.\n"
        "[COMPLETATO] 4. Framework Metrologico Integrato a 4 Livelli: Metriche formali AST, metriche di actionability/qualità, metriche neurali dense e framework di Round-Trip Differential Testing (Pytest + Hypothesis).\n"
        "[COMPLETATO] 5. Validazione Scientifica e Studio XAI: Dimostrazione del paradosso dell'inversione avversaria, analisi delle mappe di attenzione e spiegazione dei limiti di troncamento dei token.\n"
        "[COMPLETATO] 6. Sistema di Presentazione Multimodale: Esportazione di DOCUMENTATION.md standard Doxygen, portali web interattivi, grafi Cytoscape.js e dashboard diagnostiche ad alta risoluzione."
    )
    
    doc.add_heading(level=2).add_run("5.2 Cosa Manca e Piano di Lavoro per i Prossimi Passi (Roadmap)")
    
    todo_table = doc.add_table(rows=1, cols=4)
    t_widths = [1.8, 1.2, 1.2, 2.3]
    t_headers = ["Attività / Feature", "Priorità", "Origine", "Obiettivo Operativo e Metodologico"]
    t_data = [
        ["Profiling Temporale e Latenza", "Alta", "TODO.md", 
         "Misurazione empirica e comparazione dei tempi di esecuzione tra la pipeline standard (single) e quella multi-agente (multiagent), suddivisa per fase."],
        ["Grafico Voto vs LOC / Complessità", "Alta", "TODO.md", 
         "Generazione di scatter plot e curve di correlazione tra punteggi (Judge, Round-Trip) e lunghezza/complessità ciclomomatica del codice."],
        ["Context Scaffold 2.0 (Arricchimento Contesto)", "Alta", "RoadMap.md / Error Report", 
         "Fornire all'LLM Coder un contesto più esteso sulle classi helper e le funzioni esterne per azzerare i NameError/AttributeError (13.3% dei fallimenti attuali)."],
        ["Self-Refinement Loop (Doc-to-Code Feedback)", "Media-Alta", "RoadMap.md (Fase 3)", 
         "Ciclo ricorsivo in cui il Coder riceve il traceback dei test Pytest falliti e auto-corregge il codice generato per massimizzare il pass rate."],
        ["Generalizzazione Multilingua (Tree-Sitter)", "Media", "RoadMap.md (Fase 4)", 
         "Estensione del parser AST da C/C++ ad altri linguaggi industriali (Python, Java, Rust, Go) tramite la libreria universale Tree-Sitter."],
        ["CI/CD Pre-Commit Hook & Drift Detection", "Media", "RoadMap.md (Fase 5)", 
         "Integrazione del ChangeDetector con Git per bloccare pull request che introducono disallineamenti tra codice e documentazione."]
    ]
    format_table(todo_table, t_widths, t_headers, t_data, header_bg="8B0000")
    
    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    
    # Conclusion callout
    add_callout(
        doc,
        "Il framework ha raggiunto uno stadio di maturità scientifica molto solido: la combinazione di analisi statica formale "
        "e Round-Trip Testing dinamico colma in modo dimostrabile le debolezze strutturali dei modelli neurali di NLP. "
        "Le prossime attività permetteranno di quantificare il trade-off costo/tempo dell'architettura multi-agente e di elevare "
        "ulteriormente il tasso di autosufficienza della sintesi del codice.",
        title="SINTESI CONCLUSIVA",
        border_color="008000",
        fill_color="F4FBF4"
    )
    
    doc.save(output_path)
    print(f"Documento generato con successo: {output_path}")

if __name__ == "__main__":
    out_file = r"d:\python\TESI_Nicola_Flego\Stato_Avanzamento_Tesi_Nicola_Flego.docx"
    build_thesis_report(out_file)
