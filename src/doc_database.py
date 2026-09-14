import sqlite3
import os
import json
from typing import Dict, List, Optional, Any

class DocDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._create_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)


    def _create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS function_docs (
                    name TEXT PRIMARY KEY,
                    file_path TEXT,
                    signature TEXT,
                    return_type TEXT,
                    brief_summary TEXT,
                    full_doxygen_doc TEXT,
                    time_complexity TEXT,
                    space_complexity TEXT,
                    category TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cursor.execute("ALTER TABLE function_docs ADD COLUMN time_complexity TEXT DEFAULT '\\mathcal{O}(1)'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE function_docs ADD COLUMN space_complexity TEXT DEFAULT '\\mathcal{O}(1)'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE function_docs ADD COLUMN category TEXT DEFAULT 'Generale'")
            except Exception:
                pass


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS module_docs (
                    file_path TEXT PRIMARY KEY,
                    summary TEXT,
                    workflow_desc TEXT,
                    code_example TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cursor.execute("ALTER TABLE module_docs ADD COLUMN workflow_desc TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE module_docs ADD COLUMN code_example TEXT DEFAULT ''")
            except Exception:
                pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_overview (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    overview_markdown TEXT,
                    domain_context TEXT,
                    key_capabilities TEXT,
                    build_instructions TEXT DEFAULT '',
                    io_specs TEXT DEFAULT '',
                    memory_model TEXT DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cursor.execute("ALTER TABLE project_overview ADD COLUMN build_instructions TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE project_overview ADD COLUMN io_specs TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE project_overview ADD COLUMN memory_model TEXT DEFAULT ''")
            except Exception:
                pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS struct_docs (
                    name TEXT PRIMARY KEY,
                    file_path TEXT,
                    brief_summary TEXT,
                    fields_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enum_docs (
                    name TEXT PRIMARY KEY,
                    file_path TEXT,
                    brief_summary TEXT,
                    values_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_project_overview(self, overview_markdown: str, domain_context: str = "", key_capabilities: str = "", build_instructions: str = "", io_specs: str = "", memory_model: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO project_overview (id, overview_markdown, domain_context, key_capabilities, build_instructions, io_specs, memory_model)
                VALUES (1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    overview_markdown = excluded.overview_markdown,
                    domain_context = excluded.domain_context,
                    key_capabilities = excluded.key_capabilities,
                    build_instructions = excluded.build_instructions,
                    io_specs = excluded.io_specs,
                    memory_model = excluded.memory_model,
                    updated_at = CURRENT_TIMESTAMP
            """, (overview_markdown, domain_context, key_capabilities, build_instructions, io_specs, memory_model))
            conn.commit()

    def get_project_overview(self) -> Optional[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT overview_markdown, domain_context, key_capabilities, build_instructions, io_specs, memory_model FROM project_overview WHERE id = 1").fetchone()
            if row:
                return {
                    "overview_markdown": row[0] or "",
                    "domain_context": row[1] or "",
                    "key_capabilities": row[2] or "",
                    "build_instructions": row[3] or "",
                    "io_specs": row[4] or "",
                    "memory_model": row[5] or ""
                }
            return None

    def save_struct_doc(self, name: str, file_path: str, brief_summary: str, fields: List[Dict[str, str]]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO struct_docs (name, file_path, brief_summary, fields_json)
                VALUES (?, ?, ?, ?)
            """, (name, file_path, brief_summary, json.dumps(fields)))
            conn.commit()



    def save_module_doc(self, file_path: str, summary: str, workflow_desc: str = "", code_example: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO module_docs (file_path, summary, workflow_desc, code_example)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    summary = excluded.summary,
                    workflow_desc = excluded.workflow_desc,
                    code_example = excluded.code_example,
                    updated_at = CURRENT_TIMESTAMP
            """, (file_path, summary, workflow_desc, code_example))
            conn.commit()

    def get_module_doc(self, file_path: str) -> Optional[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT summary, workflow_desc, code_example FROM module_docs WHERE file_path = ?", (file_path,)).fetchone()
            if row:
                return {
                    "summary": row[0] or "",
                    "workflow_desc": row[1] or "",
                    "code_example": row[2] or ""
                }
            return None

    def get_all_function_docs(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT name, file_path, signature, return_type, brief_summary, full_doxygen_doc, time_complexity, space_complexity, category FROM function_docs").fetchall()
            return [
                {
                    "name": r[0],
                    "file_path": r[1],
                    "signature": r[2],
                    "return_type": r[3],
                    "brief_summary": r[4],
                    "full_doxygen_doc": r[5],
                    "time_complexity": r[6] if len(r) > 6 and r[6] else "O(1)",
                    "space_complexity": r[7] if len(r) > 7 and r[7] else "O(1)",
                    "category": r[8] if len(r) > 8 and r[8] else "Generale"
                }
                for r in rows
            ]

    def get_existing_categories(self) -> List[str]:
        """
        Restituisce l'elenco distinto di tutte le categorie attualmente create e memorizzate in SQLite.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT DISTINCT category FROM function_docs WHERE category IS NOT NULL AND category != ''").fetchall()
            cats = [r[0] for r in rows if r[0]]
            return sorted(cats)


    def save_enum_doc(self, name: str, file_path: str, brief_summary: str, values: List[Dict[str, str]]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO enum_docs (name, file_path, brief_summary, values_json)
                VALUES (?, ?, ?, ?)
            """, (name, file_path, brief_summary, json.dumps(values)))
            conn.commit()

    def get_all_struct_docs(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT name, file_path, brief_summary, fields_json FROM struct_docs").fetchall()
            return [
                {
                    "name": r[0],
                    "file_path": r[1],
                    "brief_summary": r[2],
                    "fields": json.loads(r[3])
                }
                for r in rows
            ]

    def get_all_enum_docs(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT name, file_path, brief_summary, values_json FROM enum_docs").fetchall()
            return [
                {
                    "name": r[0],
                    "file_path": r[1],
                    "brief_summary": r[2],
                    "values": json.loads(r[3])
                }
                for r in rows
            ]


    def clear_database(self):
        """
        Svuota l'intera tabella delle documentazioni per forzare una rigenerazione da zero.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM function_docs")
            cursor.execute("DELETE FROM module_docs")
            cursor.execute("DELETE FROM struct_docs")
            cursor.execute("DELETE FROM enum_docs")
            cursor.execute("DELETE FROM project_overview")
            conn.commit()

    def clean_invalid_docs(self):
        """
        Rimuove dal DB SQLite solo le descrizioni nulle, vuote o contenenti errori/fallback.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM function_docs 
                WHERE full_doxygen_doc IS NULL 
                   OR full_doxygen_doc = '' 
                   OR full_doxygen_doc LIKE '%Impossibile generare la documentazione%'
                   OR full_doxygen_doc LIKE '%Errore:%'
            """)
            conn.commit()





    def save_function_doc(
        self, 
        name: str, 
        file_path: str, 
        signature: str, 
        return_type: str, 
        brief_summary: str, 
        full_doxygen_doc: str,
        time_complexity: str = "O(1)",
        space_complexity: str = "O(1)",
        category: str = "Generale"
    ):
        """
        Inserisce o aggiorna la documentazione per una funzione includendo la categoria assegnata.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO function_docs (name, file_path, signature, return_type, brief_summary, full_doxygen_doc, time_complexity, space_complexity, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    file_path=excluded.file_path,
                    signature=excluded.signature,
                    return_type=excluded.return_type,
                    brief_summary=excluded.brief_summary,
                    full_doxygen_doc=excluded.full_doxygen_doc,
                    time_complexity=excluded.time_complexity,
                    space_complexity=excluded.space_complexity,
                    category=excluded.category
            """, (name, file_path, signature, return_type, brief_summary, full_doxygen_doc, time_complexity, space_complexity, category))
            conn.commit()

    def update_function_category(self, name: str, category: str):
        """
        Aggiorna la categoria funzionale di una specifica funzione nel DB.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE function_docs SET category = ? WHERE name = ?", (category, name))
            conn.commit()


    def get_function_summary(self, name: str) -> Optional[Dict[str, str]]:
        """
        Recupera il sommario breve ed la firma di una funzione già documentata.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, signature, return_type, brief_summary
                FROM function_docs
                WHERE name = ?
            """, (name,))
            row = cursor.fetchone()
            if row:
                return {
                    "name": row[0],
                    "signature": row[1],
                    "return_type": row[2],
                    "brief_summary": row[3]
                }
            return None

    def get_function_doc(self, name: str) -> Optional[Dict[str, str]]:
        """
        Recupera la documentazione generata per una specifica funzione se presente nel DB SQLite.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, brief_summary, full_doxygen_doc FROM function_docs WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return {
                    "name": row[0],
                    "brief_summary": row[1],
                    "full_doxygen_doc": row[2]
                }
            return None

    def get_callees_summaries(self, callees: List[str]) -> List[Dict[str, str]]:

        """
        Recupera i sommari per una lista di dipendenze (callees).
        """
        summaries = []
        for callee in callees:
            summary = self.get_function_summary(callee)
            if summary:
                summaries.append(summary)
            else:
                # Se è una funzione standard di sistema o non ancora in DB (es. malloc, free)
                summaries.append({
                    "name": callee,
                    "signature": f"{callee}(...)",
                    "return_type": "unknown",
                    "brief_summary": "Funzione esterna o di libreria standard."
                })
        return summaries

    def get_all_docs(self) -> List[Dict[str, str]]:
        """
        Restituisce la lista di tutte le documentazioni salvate.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, file_path, signature, return_type, brief_summary, full_doxygen_doc
                FROM function_docs
                ORDER BY name ASC
            """)
            rows = cursor.fetchall()
            return [
                {
                    "name": row[0],
                    "file_path": row[1],
                    "signature": row[2],
                    "return_type": row[3],
                    "brief_summary": row[4],
                    "full_doxygen_doc": row[5]
                }
                for row in rows
            ]
