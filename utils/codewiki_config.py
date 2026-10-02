"""
codewiki_config.py
------------------
Configurazione e percorsi condivisi dagli script del confronto CodeWiki vs pipeline.

Ogni libreria ha una cartella dedicata compare_CodeWiki/<Libreria>/ che contiene sia
l'input prodotto da CodeWiki (file .md, module_tree.json, overview.md, ...) sia tutti
gli output generati dal confronto (mapping, metriche, grafici, report).

Una libreria e' confrontabile quando:
  - esiste compare_CodeWiki/<Libreria>/ con la documentazione CodeWiki, e
  - il nome coincide (case-insensitive) con una libreria presente in dataset/benchmark.db.
"""

import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "dataset", "benchmark.db")
COMPARE_ROOT = os.path.join(ROOT_DIR, "compare_CodeWiki")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")

# Librerie con documentazione CodeWiki organizzata per classe ("### Classe" + bullet con i metodi).
# Per tutte le altre (C, o C++ con funzioni libere) i nomi di funzione vengono estratti
# cercando nei file Markdown gli identificatori che corrispondono al DB (vedi parse_codewiki_to_benchmark).
CLASS_STYLE_LIBRARIES = {"TinyXML-2"}

# Gerarchia di ereditarieta' (classe derivata -> classi base), usata per il matching "inherited":
# un metodo descritto da CodeWiki su una classe derivata viene associato alla dichiarazione nella base.
CLASS_BASES: Dict[str, Dict[str, List[str]]] = {
    "TinyXML-2": {
        "XMLDocument": ["XMLNode"],
        "XMLElement": ["XMLNode"],
        "XMLText": ["XMLNode"],
        "XMLComment": ["XMLNode"],
        "XMLDeclaration": ["XMLNode"],
        "XMLUnknown": ["XMLNode"],
        "XMLPrinter": ["XMLVisitor"],
    },
}

IMPL_EXTENSIONS = (".c", ".cpp", ".cc", ".cxx", ".c++")
HEADER_EXTENSIONS = (".h", ".hpp", ".hh", ".hxx", ".h++")


def is_impl_file(filename: Optional[str]) -> bool:
    return bool(filename) and filename.lower().endswith(IMPL_EXTENSIONS)


def is_header_file(filename: Optional[str]) -> bool:
    return bool(filename) and filename.lower().endswith(HEADER_EXTENSIONS)


@dataclass(frozen=True)
class LibraryPaths:
    """Tutti i percorsi di input/output del confronto per una libreria."""
    library: str
    dir: str

    def _p(self, *parts: str) -> str:
        return os.path.join(self.dir, *parts)

    @property
    def mapped_json(self) -> str:        return self._p("codewiki_mapped_functions.json")
    @property
    def results_json(self) -> str:       return self._p("codewiki_metrics_results.json")
    @property
    def summary_json(self) -> str:       return self._p("codewiki_metrics_summary.json")
    @property
    def report_md(self) -> str:          return self._p("codewiki_metrics_report.md")
    @property
    def function_list(self) -> str:      return self._p("codewiki_function_list.txt")
    @property
    def pipeline_function_list(self) -> str:
        return self._p("pipeline_function_list.txt")
    @property
    def adv_results(self) -> str:        return self._p("codewiki_advanced_results.json")
    @property
    def adv_results_mock(self) -> str:   return self._p("codewiki_advanced_results_mock.json")
    @property
    def charts_dir(self) -> str:         return self._p("charts")
    @property
    def cmp_report(self) -> str:         return self._p("codewiki_vs_pipeline_report.md")
    @property
    def cmp_json(self) -> str:           return self._p("codewiki_vs_pipeline_summary.json")


def db_libraries(db_path: str = DB_PATH) -> List[str]:
    """Librerie presenti in benchmark.db (nome canonico)."""
    conn = sqlite3.connect(db_path)
    try:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT library FROM benchmark_functions ORDER BY library")]
    finally:
        conn.close()


def codewiki_dirs(compare_root: str = COMPARE_ROOT) -> List[str]:
    """Nomi delle cartelle con documentazione CodeWiki in compare_CodeWiki/."""
    if not os.path.isdir(compare_root):
        return []
    return sorted(d for d in os.listdir(compare_root)
                  if os.path.isdir(os.path.join(compare_root, d)) and not d.startswith("."))


def resolve_library(name: str) -> Optional[str]:
    """Nome canonico (come nel DB) di una libreria, case-insensitive. None se assente dal DB."""
    for lib in db_libraries():
        if lib.lower() == name.lower():
            return lib
    return None


def discover_libraries() -> Dict[str, List[str]]:
    """
    Classifica le cartelle di compare_CodeWiki/:
      {"ready": [librerie confrontabili], "no_db": [cartelle senza righe nel DB]}
    """
    ready, no_db = [], []
    for d in codewiki_dirs():
        canon = resolve_library(d)
        (ready if canon else no_db).append(canon or d)
    return {"ready": ready, "no_db": no_db}


def lib_paths(library: str) -> LibraryPaths:
    """Percorsi per una libreria; la cartella e' trovata ignorando maiuscole/minuscole."""
    for d in codewiki_dirs():
        if d.lower() == library.lower():
            return LibraryPaths(library=library, dir=os.path.join(COMPARE_ROOT, d))
    return LibraryPaths(library=library, dir=os.path.join(COMPARE_ROOT, library))


def class_bases(library: str) -> Dict[str, List[str]]:
    return CLASS_BASES.get(library, {})


def is_class_style(library: str) -> bool:
    return library in CLASS_STYLE_LIBRARIES
