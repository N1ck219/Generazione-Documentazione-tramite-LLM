"""
Doc Mutation Score (DMS): quanto una documentazione "vincola" il comportamento.

Idea. La suite di test del Round-Trip e' scritta da un LLM vedendo SOLO la documentazione.
Se la documentazione fissa davvero il comportamento (rami d'errore, boundary, valori di
ritorno), la suite distingue il reference da sue varianti alterate (mutanti); se e' vaga,
i mutanti sopravvivono. Il mutation score di quella suite e' quindi una misura indiretta
della forza del contratto documentato.

Confondente da controllare. Il punteggio dipende anche dal generatore di test. Per isolare
il contributo della documentazione la stessa pipeline di generazione viene applicata anche a
una suite "signature_only" (nessuna documentazione, solo nome e firma, eventualmente anche
alla Ground Truth), e si riporta la differenza (`doc_lift`).

Definizioni (per una suite S, un reference R e l'insieme dei mutanti M di R):
- Un test e' "informativo" se passa su R (un test che fallisce su R non puo' provare nulla).
- Un mutante m e' ucciso da S se almeno un test informativo non passa su m
  (fallimento, errore o timeout).
- mutation_score(S)  = |uccisi da S| / |M|
- pool_killable      = mutanti uccisi da almeno una suite: approssimazione dei mutanti
                       non equivalenti (l'equivalenza esatta non e' decidibile)
- adjusted_score(S)  = |uccisi da S| / |pool_killable|   (richiede >= 2 suite)
- doc_lift           = adjusted_score(doc) - adjusted_score(signature_only)
"""

from typing import Any, Callable, Dict, List, Optional

from utils.code_mutator import Mutant, generate_mutants
from utils.pytest_runner import run_pytest_suite

DOC_SUITE = "doc"
BASELINE_SUITE = "signature_only"

Runner = Callable[..., Dict[str, Any]]


def kill_test_names(ref_passed: set, mutant_passed: set) -> set:
    """Test informativi (passati sul reference) che il mutante non supera piu'."""
    return set(ref_passed) - set(mutant_passed)


def run_suite_on_mutants(test_code: str, reference_code: str, mutants: List[Mutant],
                         runtime_scaffold: str = "", timeout_sec: int = 25,
                         runner: Runner = run_pytest_suite) -> Dict[str, Any]:
    """
    Esegue una suite sul reference e su ogni mutante.

    `valid=False` se la suite non ha alcun test informativo (nessun test passa sul reference):
    in quel caso non e' possibile attribuire uccisioni.
    """
    ref_exec = runner(reference_code, test_code, runtime_scaffold=runtime_scaffold, timeout_sec=timeout_sec)
    ref_passed = set(ref_exec.get("passed_test_names", set()))
    result: Dict[str, Any] = {
        "valid": bool(ref_passed),
        "reference_total": ref_exec.get("total_tests", 0),
        "informative_tests": len(ref_passed),
        "killed": {},       # mutant_id -> lista test che lo uccidono
        "timeouts": [],     # mutant_id uccisi per timeout
    }
    if not ref_passed:
        return result

    for mutant in mutants:
        m_exec = runner(mutant.code, test_code, runtime_scaffold=runtime_scaffold, timeout_sec=timeout_sec)
        killers = kill_test_names(ref_passed, m_exec.get("passed_test_names", set()))
        if killers:
            result["killed"][mutant.mutant_id] = sorted(killers)
            if m_exec.get("timed_out"):
                result["timeouts"].append(mutant.mutant_id)
    return result


def compute_mutation_metrics(mutants: List[Mutant], suite_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Aggrega i risultati per suite in Mutation Score, Adjusted Score e Doc Lift."""
    total = len(mutants)
    operators = sorted({m.operator for m in mutants})
    op_of = {m.mutant_id: m.operator for m in mutants}

    valid = {name: r for name, r in suite_results.items() if r.get("valid")}
    pool = set()
    for r in valid.values():
        pool |= set(r["killed"])

    per_suite: Dict[str, Any] = {}
    for name, r in suite_results.items():
        if not r.get("valid") or total == 0:
            per_suite[name] = {"valid": bool(r.get("valid")), "mutation_score": None,
                               "adjusted_score": None, "killed": 0,
                               "informative_tests": r.get("informative_tests", 0)}
            continue
        killed = set(r["killed"])
        others = set().union(*[set(o["killed"]) for n, o in valid.items() if n != name]) if len(valid) > 1 else set()
        per_op = {}
        for op in operators:
            n_op = sum(1 for m in mutants if m.operator == op)
            k_op = sum(1 for mid in killed if op_of.get(mid) == op)
            per_op[op] = {"killed": k_op, "total": n_op}
        per_suite[name] = {
            "valid": True,
            "informative_tests": r["informative_tests"],
            "killed": len(killed),
            "mutation_score": round(len(killed) / total, 4),
            "adjusted_score": round(len(killed) / len(pool), 4) if len(valid) > 1 and pool else None,
            "unique_kills": len(killed - others),
            "timeout_kills": len(r.get("timeouts", [])),
            "by_operator": per_op,
        }

    doc, base = per_suite.get(DOC_SUITE), per_suite.get(BASELINE_SUITE)
    doc_lift = None
    if doc and base and doc.get("adjusted_score") is not None and base.get("adjusted_score") is not None:
        doc_lift = round(doc["adjusted_score"] - base["adjusted_score"], 4)

    survivors = [m.mutant_id for m in mutants if DOC_SUITE in valid and m.mutant_id not in valid[DOC_SUITE]["killed"]]
    return {
        "n_mutants": total,
        "n_killable_pool": len(pool),
        "mutation_score": doc.get("mutation_score") if doc else None,
        "adjusted_score": doc.get("adjusted_score") if doc else None,
        "doc_lift": doc_lift,
        "suites": per_suite,
        "surviving_mutants": survivors,
    }


def evaluate_doc_mutation_score(reference_code: str, suites: Dict[str, str], target_names: List[str],
                                runtime_scaffold: str = "", max_mutants: int = 20, seed: int = 0,
                                timeout_sec: int = 25, runner: Runner = run_pytest_suite) -> Dict[str, Any]:
    """
    Pipeline completa. `suites` mappa nome -> codice pytest; la suite derivata dalla
    documentazione deve chiamarsi `doc` e la baseline senza documentazione `signature_only`.
    """
    mutants = generate_mutants(reference_code, target_names=target_names, max_mutants=max_mutants, seed=seed)
    if not mutants:
        return {"n_mutants": 0, "mutation_score": None, "adjusted_score": None, "doc_lift": None,
                "suites": {}, "surviving_mutants": [], "mutants": [],
                "note": "nessun mutante generabile (reference assente o funzione non trovata)"}

    suite_results = {name: run_suite_on_mutants(code, reference_code, mutants, runtime_scaffold,
                                                timeout_sec, runner)
                     for name, code in suites.items() if code}
    metrics = compute_mutation_metrics(mutants, suite_results)
    metrics["mutants"] = [m.to_dict(with_code=False) for m in mutants]
    return metrics


def aggregate_mutation_results(per_function: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Media su piu' funzioni (solo quelle con punteggio definito) e profilo per operatore."""
    def _mean(key: str) -> Optional[float]:
        vals = [r[key] for r in per_function if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    op_totals: Dict[str, Dict[str, int]] = {}
    for r in per_function:
        doc = r.get("suites", {}).get(DOC_SUITE, {})
        for op, kt in doc.get("by_operator", {}).items():
            acc = op_totals.setdefault(op, {"killed": 0, "total": 0})
            acc["killed"] += kt["killed"]
            acc["total"] += kt["total"]
    return {
        "n_functions": len(per_function),
        "n_scored": sum(1 for r in per_function if r.get("mutation_score") is not None),
        "avg_mutation_score": _mean("mutation_score"),
        "avg_adjusted_score": _mean("adjusted_score"),
        "avg_doc_lift": _mean("doc_lift"),
        "doc_kill_rate_by_operator": {op: round(v["killed"] / v["total"], 4) if v["total"] else None
                                      for op, v in op_totals.items()},
    }
