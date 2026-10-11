"""
Esecuzione isolata di una suite pytest contro un frammento di codice Python.

Modulo leggero (nessuna dipendenza da LLM) condiviso da:
- `utils/roundtrip_eval.py` (Round-Trip Differential Testing),
- `utils/doc_mutation_score.py` (Doc Mutation Score).
"""

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TEST_LINE = re.compile(r"::(test_\S+)\s+(PASSED|FAILED|ERROR)")


def _pytest_command() -> list:
    venv_pytest = os.path.join(ROOT_DIR, ".venv", "Scripts", "pytest.exe")
    if os.path.exists(venv_pytest):
        return [venv_pytest]
    return [sys.executable, "-m", "pytest"]


def run_pytest_suite(code_under_test: str, test_code: str, runtime_scaffold: str = "",
                     timeout_sec: int = 25) -> Dict[str, Any]:
    """
    Esegue `test_code` con pytest davanti a `runtime_scaffold` + `code_under_test`
    (stesso file, cosi' i test vedono i simboli nel namespace globale).

    Restituisce conteggi, pass rate e gli insiemi dei nomi dei test passati / falliti,
    necessari per il confronto test-per-test tra implementazioni.
    """
    full_code = f"""# Auto-generated Round-Trip Differential Test
import pytest
try:
    from hypothesis import given, strategies as st, settings
except ImportError:
    pass

# --- External Environment & Runtime Scaffold Mocks ---
{runtime_scaffold}

# --- Code Under Test ---
{code_under_test}

# --- Test Suite ---
{test_code}
"""
    cmd = _pytest_command() + ["-v", "--tb=short", "-p", "no:cacheprovider"]
    # Seed fisso: i test property-based devono dare lo stesso esito a ogni esecuzione,
    # altrimenti un mutante potrebbe risultare "ucciso" per puro rumore.
    if importlib.util.find_spec("hypothesis") is not None:
        cmd += ["--hypothesis-seed=0"]

    with tempfile.TemporaryDirectory() as workdir:
        tmp_path = os.path.join(workdir, "test_roundtrip_target.py")
        with open(tmp_path, "w", encoding="utf-8") as tmp:
            tmp.write(full_code)
        try:
            res = subprocess.run(cmd + [tmp_path], capture_output=True, text=True,
                                 timeout=timeout_sec, cwd=workdir)
        except subprocess.TimeoutExpired:
            return {
                "total_tests": 0, "passed": 0, "failed": 0, "errors": 1, "pass_rate": 0.0,
                "passed_test_names": set(), "failed_test_names": set(),
                "is_success": False, "timed_out": True, "test_output": "Execution timed out.",
            }
        except Exception as e:
            return {
                "total_tests": 0, "passed": 0, "failed": 0, "errors": 1, "pass_rate": 0.0,
                "passed_test_names": set(), "failed_test_names": set(),
                "is_success": False, "timed_out": False, "test_output": str(e),
            }

    stdout = res.stdout
    passed_match = re.search(r"(\d+)\s+passed", stdout)
    failed_match = re.search(r"(\d+)\s+failed", stdout)
    error_match = re.search(r"(\d+)\s+error", stdout)

    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    errors = int(error_match.group(1)) if error_match else 0
    total = passed + failed + errors
    pass_rate = round((passed / total) * 100.0, 1) if total > 0 else 0.0

    outcomes = _TEST_LINE.findall(stdout)
    passed_names = {n for n, s in outcomes if s == "PASSED"}
    failed_names = {n for n, s in outcomes if s != "PASSED"}

    semantic_passed = len(re.findall(r"test_semantic[^\s]+ PASSED", stdout))
    semantic_failed = len(re.findall(r"test_semantic[^\s]+ (?:FAILED|ERROR)", stdout))
    auto_passed = len(re.findall(r"test_auto[^\s]+ PASSED", stdout))
    auto_failed = len(re.findall(r"test_auto[^\s]+ (?:FAILED|ERROR)", stdout))

    return {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": pass_rate,
        "semantic_tests": {"passed": semantic_passed, "failed": semantic_failed,
                           "total": semantic_passed + semantic_failed},
        "auto_property_tests": {"passed": auto_passed, "failed": auto_failed,
                                "total": auto_passed + auto_failed},
        "passed_test_names": passed_names,
        "failed_test_names": failed_names,
        "is_success": (res.returncode == 0 and passed > 0),
        "timed_out": False,
        "test_output": stdout[-1500:] if len(stdout) > 1500 else stdout,
    }
