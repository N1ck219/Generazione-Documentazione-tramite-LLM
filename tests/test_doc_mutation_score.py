"""Test del Doc Mutation Score (utils/doc_mutation_score.py). Esegue pytest reale in subprocess."""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.code_mutator import Mutant, generate_mutants
from utils.doc_mutation_score import (
    compute_mutation_metrics,
    evaluate_doc_mutation_score,
    kill_test_names,
    run_suite_on_mutants,
)

REF = '''
def clamp(x, lo, hi):
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
'''

WEAK_SUITE = '''
def test_semantic_nominal():
    assert clamp(5, 0, 10) == 5
'''

STRONG_SUITE = '''
def test_semantic_nominal():
    assert clamp(5, 0, 10) == 5

def test_semantic_below():
    assert clamp(-3, 0, 10) == 0

def test_semantic_above():
    assert clamp(30, 0, 10) == 10

def test_semantic_boundary_low():
    assert clamp(0, 0, 10) == 0

def test_semantic_boundary_high():
    assert clamp(10, 0, 10) == 10
'''

BROKEN_SUITE = '''
def test_semantic_wrong():
    assert clamp(5, 0, 10) == 99
'''


def test_kill_requires_test_passing_on_reference():
    assert kill_test_names({"a", "b"}, {"a"}) == {"b"}
    assert kill_test_names(set(), set()) == set()


def test_strong_suite_kills_more_than_weak_suite():
    mutants = generate_mutants(REF, {"clamp"}, max_mutants=30)
    weak = run_suite_on_mutants(WEAK_SUITE, REF, mutants)
    strong = run_suite_on_mutants(STRONG_SUITE, REF, mutants)
    assert weak["valid"] and strong["valid"]
    assert len(strong["killed"]) > len(weak["killed"])
    assert set(weak["killed"]) <= set(strong["killed"])


def test_suite_failing_on_reference_is_invalid_not_a_killer():
    mutants = generate_mutants(REF, {"clamp"}, max_mutants=30)
    res = run_suite_on_mutants(BROKEN_SUITE, REF, mutants)
    assert res["valid"] is False
    assert res["killed"] == {}


def test_metrics_doc_lift_and_adjusted_score():
    out = evaluate_doc_mutation_score(REF, {"doc": STRONG_SUITE, "signature_only": WEAK_SUITE}, ["clamp"],
                                      max_mutants=30)
    assert out["n_mutants"] > 0
    doc, base = out["suites"]["doc"], out["suites"]["signature_only"]
    assert doc["mutation_score"] > base["mutation_score"]
    assert out["doc_lift"] > 0
    assert 0 < out["adjusted_score"] <= 1
    assert len(out["surviving_mutants"]) == out["n_mutants"] - doc["killed"]
    assert sum(v["total"] for v in doc["by_operator"].values()) == out["n_mutants"]


def test_adjusted_score_needs_a_second_suite():
    out = evaluate_doc_mutation_score(REF, {"doc": STRONG_SUITE}, ["clamp"], max_mutants=30)
    assert out["mutation_score"] is not None
    assert out["adjusted_score"] is None and out["doc_lift"] is None


def test_no_mutants_when_reference_missing():
    out = evaluate_doc_mutation_score("", {"doc": STRONG_SUITE}, ["clamp"])
    assert out["n_mutants"] == 0 and out["mutation_score"] is None


def test_metrics_with_fake_runner_results():
    mutants = [Mutant("M01", "relational", 1, "", ""), Mutant("M02", "constant", 1, "", ""),
               Mutant("M03", "constant", 1, "", ""), Mutant("M04", "return_value", 1, "", "")]
    results = {
        "doc": {"valid": True, "informative_tests": 3, "killed": {"M01": ["t"], "M02": ["t"]}, "timeouts": []},
        "signature_only": {"valid": True, "informative_tests": 2, "killed": {"M01": ["t"]}, "timeouts": []},
    }
    m = compute_mutation_metrics(mutants, results)
    assert m["mutation_score"] == 0.5
    assert m["n_killable_pool"] == 2
    assert m["adjusted_score"] == 1.0
    assert m["suites"]["signature_only"]["adjusted_score"] == 0.5
    assert m["doc_lift"] == 0.5
    assert m["suites"]["doc"]["unique_kills"] == 1
    assert m["surviving_mutants"] == ["M03", "M04"]
