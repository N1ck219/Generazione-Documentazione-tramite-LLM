"""Test delle correzioni su Actionability Score (direzione, return) e applicabilita' di EDR/ECC."""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.benchmark_metrics import (
    parse_doxygen_block,
    calculate_actionability_score,
    calculate_error_documentation_rate,
    calculate_edge_case_coverage,
)

PARAMS = [{"name": "buf"}, {"name": "len"}]


def _score(doc, params=PARAMS, return_type=None):
    return calculate_actionability_score(parse_doxygen_block(doc), params, return_type)


def test_param_without_direction_is_not_counted():
    doc = "/** @brief Copies bytes into a buffer.\n * @param buf Destination.\n * @param len Number of bytes.\n * @pre buf must be valid. */"
    no_dir = _score(doc, return_type="void")
    with_dir = _score(doc.replace("@param buf", "@param[out] buf").replace("@param len", "@param[in] len"),
                      return_type="void")
    assert parse_doxygen_block(doc)["params"][0]["direction"] == ""
    assert with_dir - no_dir == 0.35


def test_void_function_with_params_gets_return_credit():
    doc = "/** @brief Fills a buffer with zeros.\n * @param[out] buf Target.\n * @param[in] len Size.\n * @pre buf must be valid. */"
    assert _score(doc, return_type="void") == 1.0
    # Euristica storica (tipo non fornito): void con parametri perdeva la componente di return
    assert _score(doc, return_type=None) == 0.75


def test_void_function_documenting_return_gets_no_return_credit():
    doc = "/** @brief Fills a buffer with zeros.\n * @param[out] buf Target.\n * @param[in] len Size.\n * @return Nothing useful here.\n * @pre buf must be valid. */"
    assert _score(doc, return_type="void") == 0.75


def test_non_void_without_return_gets_no_credit():
    doc = "/** @brief Computes a checksum of the buffer.\n * @param[in] buf Input.\n * @param[in] len Size.\n * @pre buf must be valid. */"
    assert _score(doc, return_type="int") == 0.75
    with_return = doc.replace("@pre", "@return The checksum value.\n * @pre")
    assert _score(with_return, return_type="int") == 1.0


def test_edr_and_ecc_report_when_not_applicable():
    code = "int add(int a, int b) { return a + b; }"
    edr = calculate_error_documentation_rate(code, [], "Adds two integers.")
    ecc = calculate_edge_case_coverage(code, "Adds two integers.")
    assert edr["has_code_error"] is False
    assert ecc["code_guard_count"] == 0
