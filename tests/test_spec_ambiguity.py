"""Test dello Specification Ambiguity Index (utils/spec_ambiguity.py)."""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest

from utils.spec_ambiguity import (
    build_probe_prompt,
    canonicalize,
    compute_ambiguity,
    evaluate_spec_ambiguity,
    extract_probes_code,
    run_probes,
)

PROBES = '''
def probe_01():
    out = [0]
    r = f(3, out)
    return (r, out[0])

def probe_02():
    return f(-1, [0])

def probe_03():
    return f(None, [0])
'''

IMPL_A = '''
def f(x, out):
    if x is None:
        return -1
    out[0] = x * 2
    return 0 if x >= 0 else -1
'''
# stesso comportamento di A, rappresentazione diversa (float al posto di int)
IMPL_A2 = '''
def f(x, out):
    if x is None:
        return -1.0
    out[0] = float(x * 2)
    return 0 if x >= 0 else -1
'''
IMPL_B = '''
def f(x, out):
    if x is None:
        raise ValueError("null")
    out[0] = x * 2
    return 0 if x >= 0 else -2
'''


def test_canonicalize_normalizes_representation_only():
    assert canonicalize(True) == canonicalize(1) == 1
    assert canonicalize(2.0) == 2 and canonicalize(2.5) == 2.5
    assert canonicalize((1, [2])) == canonicalize([1, (2,)])
    assert canonicalize({"b": 1, "a": 2}) == canonicalize({"a": 2, "b": 1})
    assert canonicalize({3, 1, 2}) == canonicalize({2, 3, 1})
    assert canonicalize(float("nan")) == {"float": "nan"}

    class A:
        def __init__(self, v):
            self.v = v

    class B(A):
        pass
    assert canonicalize(A(1)) == canonicalize(A(2)) == {"obj": "A"}
    assert canonicalize(A(1), object_mode="state") != canonicalize(A(2), object_mode="state")
    assert canonicalize(B(1)) != canonicalize(A(1))


def test_run_probes_outcomes_and_isolation():
    res = run_probes(IMPL_B, PROBES)
    assert res["ok"]
    assert res["outcomes"]["probe_01"] == {"ok": [0, 6]}
    assert res["outcomes"]["probe_02"] == {"ok": -2}
    assert res["outcomes"]["probe_03"] == {"exc": "ValueError"}


def test_run_probes_reports_load_error_and_timeout():
    assert run_probes("def f(:", PROBES)["ok"] is False
    loop = PROBES + "\ndef probe_04():\n    while True:\n        pass\n"
    res = run_probes(IMPL_A, loop, per_probe_timeout=0.5)
    assert res["outcomes"]["probe_04"] == {"timeout": True}
    assert res["outcomes"]["probe_01"] == {"ok": [0, 6]}  # le altre sonde non ne risentono


def test_identical_behaviors_have_zero_sai():
    outs = [run_probes(c, PROBES)["outcomes"] for c in (IMPL_A, IMPL_A2, IMPL_A)]
    m = compute_ambiguity(outs)
    assert m["sai"] == 0.0 and m["ambiguous_probe_fraction"] == 0.0 and m["behavioral_entropy"] == 0.0


def test_divergent_behaviors_raise_sai():
    outs = [run_probes(c, PROBES)["outcomes"] for c in (IMPL_A, IMPL_A, IMPL_B, IMPL_B)]
    m = compute_ambiguity(outs)
    assert 0 < m["sai"] < 1
    assert m["ambiguous_probe_fraction"] == pytest.approx(2 / 3, abs=1e-3)  # probe_02 e probe_03
    # a coppie: 2 vs 2 su 4 impl -> 4 coppie discordi su 6
    m_single = compute_ambiguity([{"p": {"ok": 1}}, {"p": {"ok": 1}}, {"p": {"ok": 2}}, {"p": {"ok": 2}}])
    assert m_single["sai"] == pytest.approx(4 / 6, abs=1e-3)
    assert m_single["behavioral_entropy"] == pytest.approx(0.5, abs=1e-3)  # ln2 / ln4


def test_all_distinct_outcomes_give_max_sai_and_entropy():
    m = compute_ambiguity([{"p": {"ok": i}} for i in range(4)])
    assert m["sai"] == 1.0 and m["behavioral_entropy"] == 1.0


def test_harness_errors_on_all_impls_discard_the_probe():
    te = {"exc": "TypeError"}
    m = compute_ambiguity([{"p": te, "q": {"ok": 1}}, {"p": te, "q": {"ok": 2}}])
    assert m["n_probes_discarded"] == 1 and m["n_probes_used"] == 1 and m["sai"] == 1.0
    assert compute_ambiguity([{"p": te}, {"p": te}])["sai"] is None


def test_needs_two_valid_implementations():
    assert compute_ambiguity([{"p": {"ok": 1}}])["sai"] is None


def test_taxonomy_separates_hidden_information_from_ambiguity():
    ref = {"a": {"ok": 1}, "b": {"ok": 1}, "c": {"ok": 1}, "d": {"ok": 1}}
    impls = [
        {"a": {"ok": 1}, "b": {"ok": 9}, "c": {"ok": 1}, "d": {"ok": 7}},
        {"a": {"ok": 1}, "b": {"ok": 9}, "c": {"ok": 2}, "d": {"ok": 8}},
    ]
    m = compute_ambiguity(impls, ref)
    assert m["taxonomy"] == {"determined_correct": 0.25, "determined_divergent": 0.25,
                             "ambiguous_covers_ref": 0.25, "ambiguous_divergent": 0.25}
    assert sum(m["taxonomy"].values()) == pytest.approx(1.0)
    assert m["ref_agreement"] == pytest.approx((1 + 0 + 0.5 + 0) / 4)


def test_diagnosis_values():
    ref = {"a": {"ok": 1}}
    good = compute_ambiguity([{"a": {"ok": 1}}] * 3, ref)
    hidden = compute_ambiguity([{"a": {"ok": 5}}] * 3, ref)
    amb = compute_ambiguity([{"a": {"ok": 1}}, {"a": {"ok": 2}}, {"a": {"ok": 3}}], ref)
    assert (good["diagnosis"], hidden["diagnosis"], amb["diagnosis"]) == \
        ("well_specified", "hidden_information", "ambiguous_spec")


def test_evaluate_pipeline_with_fake_synthesizer():
    impls = [IMPL_A, IMPL_A, IMPL_B, "def f(:"]
    m = evaluate_spec_ambiguity(lambda i: impls[i], PROBES, reference_code=IMPL_A, n_samples=4)
    assert m["n_valid_impls"] == 3 and len(m["load_failures"]) == 1
    assert m["reference_available"] and m["sai"] > 0
    # probe_01 concordano tutte col reference; probe_02 (-1 vs -2) e probe_03 (-1 vs eccezione) discordano
    assert m["taxonomy"]["determined_correct"] == pytest.approx(1 / 3, abs=1e-3)
    assert m["taxonomy"]["ambiguous_covers_ref"] == pytest.approx(2 / 3, abs=1e-3)


def test_probe_prompt_and_extraction():
    p = build_probe_prompt("XMLElement::Attribute", "const char* Attribute(const char* name)", "doc")
    assert "probe_01" in p and "XMLElement" in p and "NO parameters" in p
    code = extract_probes_code("```python\nfrom implementation import f\ndef probe_01():\n    return f(1)\n```")
    assert "implementation" not in code and "probe_01" in code
    assert extract_probes_code("```python\ndef helper():\n    pass\n```") == ""
    assert extract_probes_code("```python\ndef probe_01(:\n```") == ""
