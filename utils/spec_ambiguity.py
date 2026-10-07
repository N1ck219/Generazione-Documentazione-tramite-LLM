"""
Specification Ambiguity Index (SAI): quanto una documentazione lascia aperti piu' comportamenti.

Idea. La stessa documentazione viene data N volte al "Coder" (temperatura > 0): se e'
non ambigua, le N implementazioni indipendenti si comportano allo stesso modo. Si misura
il disaccordo su un insieme comune di sonde (input senza oracolo), cosi' il punteggio
non richiede il codice di riferimento. Se il reference e' disponibile, ogni sonda viene
classificata in 4 casi che separano due cause di fallimento del Round-Trip che il solo
Dual Agreement confonde:

  determined_correct    le N implementazioni concordano e coincidono col reference
  determined_divergent  concordano tra loro ma divergono dal reference
                        -> informazione non presente nel contratto (information hiding)
  ambiguous_covers_ref  discordano, ma almeno una coincide col reference
  ambiguous_divergent   discordano e nessuna coincide col reference

Metriche (sulle sonde informative):
- sai                  media del disaccordo a coppie, 1 - P(due implementazioni a caso concordano); 0 = nessuna ambiguita'
- ambiguous_probe_fraction  frazione di sonde con almeno un disaccordo
- behavioral_entropy   entropia normalizzata della distribuzione degli esiti (0-1)
- ref_agreement        frazione media di implementazioni che coincidono col reference
"""

import inspect
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

# Errori che indicano una sonda mal formata o uno scaffold incompleto, non un comportamento:
# se TUTTE le implementazioni li sollevano la sonda viene scartata (accordo banale).
HARNESS_ERRORS = {"TypeError", "NameError"}

WELL_SPECIFIED_THRESHOLD = 0.8


def canonicalize(value, _depth=0, object_mode="type"):
    """
    Riduce un valore Python a una forma JSON confrontabile tra implementazioni diverse.

    Normalizzazioni (le differenze puramente di rappresentazione non sono ambiguita'):
    bool -> int, float integrale -> int, tuple/list -> lista, bytes -> {"bytes": hex}.
    Oggetti: con object_mode="type" conta solo il nome del tipo (le implementazioni
    scelgono campi interni diversi: black-box), con "state" anche `vars()`.
    NB: funzione autonoma, il suo sorgente e' incluso nel driver eseguito in subprocess.
    """
    if _depth > 6:
        return "<deep>"
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:
            return {"float": "nan"}
        if value in (float("inf"), float("-inf")):
            return {"float": str(value)}
        return int(value) if value.is_integer() else value
    if isinstance(value, (bytes, bytearray)):
        return {"bytes": bytes(value).hex()}
    if isinstance(value, (list, tuple)):
        return [canonicalize(v, _depth + 1, object_mode) for v in value]
    if isinstance(value, dict):
        items = [[canonicalize(k, _depth + 1, object_mode), canonicalize(v, _depth + 1, object_mode)]
                 for k, v in value.items()]
        return {"dict": sorted(items, key=lambda kv: json.dumps(kv[0], sort_keys=True))}
    if isinstance(value, (set, frozenset)):
        items = [canonicalize(v, _depth + 1, object_mode) for v in value]
        return {"set": sorted(items, key=lambda v: json.dumps(v, sort_keys=True))}
    name = type(value).__name__
    if object_mode == "state" and hasattr(value, "__dict__"):
        return {"obj": name, "state": canonicalize(vars(value), _depth + 1, object_mode)}
    return {"obj": name}


_DRIVER_MAIN = '''

def _main():
    impl_path, probes_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    per_probe, object_mode = float(sys.argv[4]), sys.argv[5]
    result = {"load_error": None, "outcomes": {}}
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    except Exception:
        pass

    class _ProbeTimeout(BaseException):
        pass

    def _on_alarm(signum, frame):
        raise _ProbeTimeout()

    use_alarm = hasattr(signal, "SIGALRM")
    if use_alarm:
        signal.signal(signal.SIGALRM, _on_alarm)

    ns = {"__name__": "__impl__"}
    sys.stdout = open(os.devnull, "w")
    try:
        for path in (impl_path, probes_path):
            with open(path, encoding="utf-8") as fh:
                exec(compile(fh.read(), path, "exec"), ns)
    except BaseException as e:
        result["load_error"] = type(e).__name__ + ": " + str(e)[:200]
    else:
        names = sorted(k for k, v in ns.items() if k.startswith("probe_") and callable(v))
        for name in names:
            try:
                if use_alarm:
                    signal.setitimer(signal.ITIMER_REAL, per_probe)
                try:
                    out = {"ok": canonicalize(ns[name](), 0, object_mode)}
                finally:
                    if use_alarm:
                        signal.setitimer(signal.ITIMER_REAL, 0)
            except _ProbeTimeout:
                out = {"timeout": True}
            except (Exception, SystemExit) as e:
                out = {"exc": type(e).__name__}
            result["outcomes"][name] = out
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh)


_main()
'''

PROBE_DRIVER = ("import json, os, signal, sys\n\n" + inspect.getsource(canonicalize) + _DRIVER_MAIN)


def run_probes(impl_code: str, probes_code: str, runtime_scaffold: str = "", per_probe_timeout: float = 3.0,
               total_timeout: float = 60.0, object_mode: str = "type") -> Dict[str, Any]:
    """
    Esegue tutte le funzioni `probe_*` di `probes_code` con `impl_code` in un subprocess isolato.
    Restituisce {"ok": bool, "outcomes": {nome_sonda: esito_canonico}, "error": str|None}.
    Un esito e' uno tra {"ok": valore}, {"exc": NomeEccezione}, {"timeout": True}.
    """
    with tempfile.TemporaryDirectory() as workdir:
        paths = {n: os.path.join(workdir, n) for n in ("driver.py", "impl.py", "probes.py", "out.json")}
        with open(paths["driver.py"], "w", encoding="utf-8") as f:
            f.write(PROBE_DRIVER)
        with open(paths["impl.py"], "w", encoding="utf-8") as f:
            f.write(f"{runtime_scaffold}\n\n{impl_code}\n")
        with open(paths["probes.py"], "w", encoding="utf-8") as f:
            f.write(probes_code)
        try:
            subprocess.run([sys.executable, "-I", paths["driver.py"], paths["impl.py"], paths["probes.py"],
                            paths["out.json"], str(per_probe_timeout), object_mode],
                           capture_output=True, text=True, timeout=total_timeout, cwd=workdir)
        except subprocess.TimeoutExpired:
            return {"ok": False, "outcomes": {}, "error": "timeout"}
        if not os.path.exists(paths["out.json"]):
            return {"ok": False, "outcomes": {}, "error": "driver crashed"}
        with open(paths["out.json"], encoding="utf-8") as f:
            data = json.load(f)
    if data["load_error"]:
        return {"ok": False, "outcomes": {}, "error": data["load_error"]}
    return {"ok": bool(data["outcomes"]), "outcomes": data["outcomes"],
            "error": None if data["outcomes"] else "nessuna sonda eseguita"}


def _key(outcome: Any) -> str:
    return json.dumps(outcome, sort_keys=True)


def _is_harness_error(outcome: Any) -> bool:
    return isinstance(outcome, dict) and outcome.get("exc") in HARNESS_ERRORS


def compute_ambiguity(impl_outcomes: List[Dict[str, Any]],
                      ref_outcomes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calcola SAI e classificazione delle sonde. `impl_outcomes` contiene un dizionario
    {sonda: esito} per ciascuna implementazione valida (le non caricabili vanno escluse
    a monte); `ref_outcomes` e' lo stesso per il reference, se disponibile.
    """
    n = len(impl_outcomes)
    if n < 2:
        return {"sai": None, "reason": "servono almeno 2 implementazioni valide", "n_valid_impls": n}

    probe_names = sorted(set.intersection(*[set(o) for o in impl_outcomes]))
    used, discarded = [], 0
    for p in probe_names:
        if all(_is_harness_error(o[p]) for o in impl_outcomes):
            discarded += 1
        else:
            used.append(p)
    if not used:
        return {"sai": None, "reason": "nessuna sonda informativa", "n_valid_impls": n,
                "n_probes_used": 0, "n_probes_discarded": discarded}

    pair_disagreement, entropy, ref_match = [], [], []
    taxonomy = Counter()
    for p in used:
        counts = Counter(_key(o[p]) for o in impl_outcomes)
        agree_pairs = sum(c * (c - 1) / 2 for c in counts.values())
        pair_disagreement.append(1.0 - agree_pairs / (n * (n - 1) / 2))
        entropy.append(-sum((c / n) * math.log(c / n) for c in counts.values()) / math.log(n))

        if ref_outcomes is not None and p in ref_outcomes and not _is_harness_error(ref_outcomes[p]):
            rk = _key(ref_outcomes[p])
            ref_match.append(counts.get(rk, 0) / n)
            unanimous = len(counts) == 1
            if unanimous:
                taxonomy["determined_correct" if rk in counts else "determined_divergent"] += 1
            else:
                taxonomy["ambiguous_covers_ref" if rk in counts else "ambiguous_divergent"] += 1

    out: Dict[str, Any] = {
        "n_valid_impls": n,
        "n_probes_used": len(used),
        "n_probes_discarded": discarded,
        "sai": round(sum(pair_disagreement) / len(used), 4),
        "ambiguous_probe_fraction": round(sum(1 for d in pair_disagreement if d > 0) / len(used), 4),
        "behavioral_entropy": round(sum(entropy) / len(used), 4),
        "ref_agreement": None,
        "taxonomy": None,
        "diagnosis": None,
    }
    n_ref = sum(taxonomy.values())
    if n_ref:
        tax = {k: round(taxonomy[k] / n_ref, 4) for k in
               ("determined_correct", "determined_divergent", "ambiguous_covers_ref", "ambiguous_divergent")}
        out["ref_agreement"] = round(sum(ref_match) / len(ref_match), 4)
        out["taxonomy"] = tax
        out["n_probes_vs_ref"] = n_ref
        if tax["determined_correct"] >= WELL_SPECIFIED_THRESHOLD:
            out["diagnosis"] = "well_specified"
        else:
            ambiguous = tax["ambiguous_covers_ref"] + tax["ambiguous_divergent"]
            out["diagnosis"] = "ambiguous_spec" if ambiguous >= tax["determined_divergent"] else "hidden_information"
    return out


def build_probe_prompt(func_name: str, signature: str, docstring: str, library: str = "",
                       context_scaffold: str = "", num_probes: int = 15) -> str:
    """Prompt per generare le sonde: input senza oracolo, derivati da documentazione e firma."""
    is_method = "::" in func_name
    if is_method:
        cls, meth = func_name.split("::", 1)
        call_hint = (f"The target is the C++ method `{meth}` of class `{cls}`: build the object inside each probe "
                     f"(e.g. `obj = {cls}()`) and call `obj.{meth}(...)`.")
    else:
        call_hint = f"The target is the free function `{func_name}`: call `{func_name}(...)` directly."
    context = f"\n=== LIBRARY DEFINITIONS & CONSTANTS ({library or 'component'}) ===\n{context_scaffold}\n" if context_scaffold else ""
    return f"""You are a QA engineer preparing BEHAVIOR PROBES for several independent implementations of the same function.
A probe only EXERCISES the function and RETURNS what is observable. A probe never asserts and never contains an expected value.

Target Symbol: `{func_name}`
C/C++ Signature: `{signature}`

=== SPECIFICATION (DOCUMENTATION) ===
{docstring}
{context}
=== RULES ===
1. Write exactly {num_probes} module-level functions named `probe_01`, `probe_02`, ... taking NO parameters.
2. Cover: nominal inputs, boundary values (0, negative, empty, very large), invalid or NULL (None) inputs, and every error case mentioned in the specification.
3. Each probe returns a single value summarising everything observable: the return value AND the final content of every output parameter or mutated argument, e.g. `return (result, out[0])` or `return {{"ret": r, "buf": buf}}`.
4. {call_hint}
5. Output pointers are mutable single-element lists (`out = [0]`). Create every input inside the probe.
6. Do NOT use assert, pytest, random numbers, time, ctypes or file/network access. Do NOT import the function under test: it is injected in the global scope.
7. Respect the signature: exact parameter order and count.
Return ONLY executable Python code in a single ```python ... ``` block.
"""


def extract_probes_code(response: str) -> str:
    """Estrae e ripulisce il codice delle sonde dalla risposta del modello ('' se non valido)."""
    import ast
    match = re.search(r"```python\s*(.*?)\s*```", response or "", re.DOTALL)
    code = (match.group(1) if match else (response or "")).strip()
    code = "\n".join(l for l in code.splitlines() if not re.match(r"^\s*(from|import)\s+implementation\b", l))
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ""
    has_probe = any(isinstance(n, ast.FunctionDef) and n.name.startswith("probe_") for n in tree.body)
    return code if has_probe else ""


def evaluate_spec_ambiguity(synthesize: Callable[[int], str], probes_code: str, reference_code: str = "",
                            runtime_scaffold: str = "", n_samples: int = 5, per_probe_timeout: float = 3.0,
                            object_mode: str = "type") -> Dict[str, Any]:
    """
    Pipeline completa. `synthesize(i)` restituisce l'i-esimo codice Python sintetizzato dalla
    documentazione (con temperatura > 0). Le implementazioni non caricabili vengono contate
    ma escluse dal calcolo; il reference, se presente, gira sulle stesse sonde.
    """
    if not probes_code:
        return {"sai": None, "reason": "sonde non generate", "n_samples": n_samples}

    valid_outcomes, load_failures = [], []
    for i in range(n_samples):
        code = synthesize(i)
        res = run_probes(code, probes_code, runtime_scaffold, per_probe_timeout, object_mode=object_mode) if code else \
            {"ok": False, "outcomes": {}, "error": "sintesi vuota"}
        if res["ok"]:
            valid_outcomes.append(res["outcomes"])
        else:
            load_failures.append(res["error"])

    ref_outcomes = None
    if reference_code:
        ref_res = run_probes(reference_code, probes_code, runtime_scaffold, per_probe_timeout, object_mode=object_mode)
        ref_outcomes = ref_res["outcomes"] if ref_res["ok"] else None

    metrics = compute_ambiguity(valid_outcomes, ref_outcomes)
    metrics["n_samples"] = n_samples
    metrics["load_failures"] = load_failures
    metrics["reference_available"] = ref_outcomes is not None
    return metrics


def aggregate_ambiguity_results(per_function: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored = [r for r in per_function if r.get("sai") is not None]
    def _mean(key):
        vals = [r[key] for r in scored if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None
    tax_keys = ("determined_correct", "determined_divergent", "ambiguous_covers_ref", "ambiguous_divergent")
    with_tax = [r for r in scored if r.get("taxonomy")]
    return {
        "n_functions": len(per_function),
        "n_scored": len(scored),
        "avg_sai": _mean("sai"),
        "avg_ambiguous_probe_fraction": _mean("ambiguous_probe_fraction"),
        "avg_behavioral_entropy": _mean("behavioral_entropy"),
        "avg_ref_agreement": _mean("ref_agreement"),
        "avg_taxonomy": {k: round(sum(r["taxonomy"][k] for r in with_tax) / len(with_tax), 4) for k in tax_keys}
        if with_tax else None,
        "diagnosis_counts": dict(Counter(r["diagnosis"] for r in with_tax)),
    }
