"""Test del generatore di mutanti AST (utils/code_mutator.py)."""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.code_mutator import generate_mutants

CODE = '''
LIMIT = 10

def helper(x):
    return x + 1

def clamp(x, lo, hi, out=None):
    """Clamp x in [lo, hi]."""
    if x < lo:
        return lo
    if x > hi and hi >= lo:
        return hi
    if out is not None:
        out[0] = x * 2
    return x
'''


def test_mutants_are_valid_python_and_differ_from_original():
    mutants = generate_mutants(CODE, target_names={"clamp"}, max_mutants=50)
    assert mutants
    codes = {m.code for m in mutants}
    assert len(codes) == len(mutants)
    for m in mutants:
        compile(m.code, "<m>", "exec")


def test_only_target_function_is_mutated():
    for m in generate_mutants(CODE, target_names={"clamp"}, max_mutants=50):
        assert "LIMIT = 10" in m.code
        assert "return x + 1" in m.code  # helper intatto


def test_unknown_target_or_invalid_code_gives_no_mutants():
    assert generate_mutants(CODE, target_names={"missing"}) == []
    assert generate_mutants("def f(:", target_names={"f"}) == []


def test_covers_all_expected_operators():
    ops = {m.operator for m in generate_mutants(CODE, target_names={"clamp"}, max_mutants=100)}
    assert ops == {"relational", "arithmetic", "logical", "negation", "guard_removal",
                   "constant", "return_value", "stmt_deletion"}


def test_cap_is_stratified_and_deterministic():
    a = generate_mutants(CODE, {"clamp"}, max_mutants=5, seed=3)
    b = generate_mutants(CODE, {"clamp"}, max_mutants=5, seed=3)
    assert [m.code for m in a] == [m.code for m in b]
    assert len(a) == 5
    assert len({m.operator for m in a}) == 5  # un operatore diverso per mutante, non cinque ROR


def test_docstring_is_never_mutated_or_deleted():
    for m in generate_mutants(CODE, {"clamp"}, max_mutants=100):
        assert "Clamp x in [lo, hi]." in m.code


def test_method_target_name_matches_inside_class():
    code = "class A:\n    def get(self, k):\n        if k < 0:\n            return -1\n        return k\n"
    assert generate_mutants(code, {"get"})
