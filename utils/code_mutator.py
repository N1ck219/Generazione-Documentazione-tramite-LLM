"""
Generatore deterministico di mutanti per codice Python (basato su `ast`).

Serve al Doc Mutation Score (`utils/doc_mutation_score.py`): dal reference Python
(trasposizione del sorgente C/C++) si derivano varianti con UNA sola alterazione
semantica ciascuna. Una suite di test scritta dalla sola documentazione e' "forte"
nella misura in cui distingue il reference dai suoi mutanti.

Operatori (campo `operator`):
- relational:      < <-> <=, > <-> >=, == <-> !=
- arithmetic:      + <-> -, * <-> //, / <-> *, % <-> *
- logical:         and <-> or
- negation:        if/while/ternario: condizione negata
- guard_removal:   if: condizione sostituita con False (il controllo non scatta mai)
- constant:        costante numerica n -> n+1, True <-> False
- return_value:    `return expr` -> `return None`
- stmt_deletion:   assegnamento / chiamata come istruzione -> `pass`
"""

import ast
import copy
import random
from dataclasses import dataclass, asdict
from typing import Callable, Dict, Iterable, List, Optional

_REL_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
             ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
_ARITH_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv,
               ast.FloorDiv: ast.Mult, ast.Div: ast.Mult, ast.Mod: ast.Mult}
_OP_SYMBOL = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
              ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "//", ast.Div: "/", ast.Mod: "%",
              ast.And: "and", ast.Or: "or"}

OPERATORS = ("relational", "arithmetic", "logical", "negation", "guard_removal",
             "constant", "return_value", "stmt_deletion")


@dataclass
class Mutant:
    mutant_id: str
    operator: str
    lineno: int
    description: str
    code: str

    def to_dict(self, with_code: bool = True) -> Dict:
        d = asdict(self)
        if not with_code:
            d.pop("code")
        return d


@dataclass
class _Site:
    operator: str
    lineno: int
    description: str
    apply: Callable[[], None]


def _is_docstring(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)


def _sites_in(root: ast.AST) -> List[_Site]:
    """Enumera in ordine deterministico (ast.walk) i punti mutabili sotto `root`."""
    sites: List[_Site] = []

    for node in ast.walk(root):
        line = getattr(node, "lineno", 0)

        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                new_cls = _REL_SWAP.get(type(op))
                if new_cls:
                    def _apply(n=node, i=i, c=new_cls):
                        n.ops[i] = c()
                    sites.append(_Site("relational", line,
                                       f"{_OP_SYMBOL[type(op)]} -> {_OP_SYMBOL[new_cls]}", _apply))

        elif isinstance(node, ast.BinOp):
            new_cls = _ARITH_SWAP.get(type(node.op))
            if new_cls:
                def _apply(n=node, c=new_cls):
                    n.op = c()
                sites.append(_Site("arithmetic", line,
                                   f"{_OP_SYMBOL[type(node.op)]} -> {_OP_SYMBOL[new_cls]}", _apply))

        elif isinstance(node, ast.BoolOp):
            new_cls = ast.Or if isinstance(node.op, ast.And) else ast.And

            def _apply(n=node, c=new_cls):
                n.op = c()
            sites.append(_Site("logical", line,
                               f"{_OP_SYMBOL[type(node.op)]} -> {_OP_SYMBOL[new_cls]}", _apply))

        elif isinstance(node, (ast.If, ast.While, ast.IfExp)):
            def _negate(n=node):
                n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
            sites.append(_Site("negation", line, "condizione negata", _negate))
            if isinstance(node, ast.If):
                def _remove(n=node):
                    n.test = ast.Constant(value=False)
                sites.append(_Site("guard_removal", line, "guardia sempre falsa", _remove))

        elif isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                def _apply(n=node):
                    n.value = not n.value
                sites.append(_Site("constant", line, f"{v} -> {not v}", _apply))
            elif isinstance(v, (int, float)):
                def _apply(n=node):
                    n.value = n.value + 1
                sites.append(_Site("constant", line, f"{v} -> {v + 1}", _apply))

        elif isinstance(node, ast.Return):
            if node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None):
                def _apply(n=node):
                    n.value = ast.Constant(value=None)
                sites.append(_Site("return_value", line, "return <expr> -> return None", _apply))

        # Cancellazione di istruzioni: richiede il parent (il nodo viene sostituito nella lista)
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(node, field, None)
            if not isinstance(stmts, list):
                continue
            for idx, stmt in enumerate(stmts):
                deletable = isinstance(stmt, (ast.Assign, ast.AugAssign)) or (
                    isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                )
                if deletable and not _is_docstring(stmt):
                    def _apply(lst=stmts, i=idx):
                        lst[i] = ast.Pass()
                    sites.append(_Site("stmt_deletion", getattr(stmt, "lineno", line),
                                       "istruzione rimossa", _apply))
    return sites


def _target_roots(tree: ast.Module, target_names: Optional[Iterable[str]]) -> List[ast.AST]:
    if not target_names:
        return [tree]
    wanted = set(target_names)
    return [n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in wanted]


def _enumerate(tree: ast.Module, target_names: Optional[Iterable[str]]) -> List[_Site]:
    sites: List[_Site] = []
    for root in _target_roots(tree, target_names):
        sites.extend(_sites_in(root))
    return sites


def generate_mutants(code: str, target_names: Optional[Iterable[str]] = None,
                     max_mutants: int = 20, seed: int = 0) -> List[Mutant]:
    """
    Genera fino a `max_mutants` mutanti di primo ordine di `code`.

    - `target_names`: nomi delle funzioni/metodi da mutare (il resto, es. mock e helper
      dello scaffold, resta intatto). Se nessuna funzione con quel nome esiste,
      non viene generato nulla.
    - Se i punti mutabili superano `max_mutants`, il campione e' stratificato per
      operatore (round-robin) e riproducibile grazie a `seed`.
    - Mutanti sintatticamente identici all'originale o tra loro vengono scartati.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    original = ast.unparse(tree)
    n_sites = len(_enumerate(tree, target_names))

    by_operator: Dict[str, List[int]] = {}
    for idx, site in enumerate(_enumerate(tree, target_names)):
        by_operator.setdefault(site.operator, []).append(idx)

    rng = random.Random(seed)
    for indices in by_operator.values():
        rng.shuffle(indices)

    order: List[int] = []
    queues = [by_operator[op] for op in OPERATORS if op in by_operator]
    while any(queues) and len(order) < n_sites:
        for q in queues:
            if q:
                order.append(q.pop())

    mutants: List[Mutant] = []
    seen = {original}
    for idx in order:
        if len(mutants) >= max_mutants:
            break
        mutated_tree = copy.deepcopy(tree)
        site = _enumerate(mutated_tree, target_names)[idx]
        site.apply()
        try:
            mutated_code = ast.unparse(ast.fix_missing_locations(mutated_tree))
            compile(mutated_code, "<mutant>", "exec")
        except (SyntaxError, ValueError, RecursionError):
            continue
        if mutated_code in seen:
            continue
        seen.add(mutated_code)
        mutants.append(Mutant(mutant_id=f"M{len(mutants) + 1:02d}", operator=site.operator,
                              lineno=site.lineno, description=site.description, code=mutated_code))
    return mutants
