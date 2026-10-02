"""
Dataset e runner scientifico unificato per la valutazione delle metriche NLP
attraverso 5 classi concettuali e 6 rappresentazioni/campi:
- 5 Classi:
  1. EQUIVALENT (Stessa logica / semantica, implementazione/lessico differente)
  2. ADVERSARIAL (Bug logico o inversione critica di contratto con alta somiglianza sintattica)
  3. DOMAIN_SIMILAR (Stesso dominio operativo/struttura dati, ma compiti algoritmici diversi)
  4. ORTHOGONAL (Domini concettuali totalmente scorrelati / zero baseline)
  5. FLUFF_VERBOSITY (Parafrasi con verbosita' prolissa o diluizione con token ridondanti)

- 6 Campi / Rappresentazioni:
  1. C vs C
  2. Python vs Python
  3. C vs Python (Cross-Language)
  4. Doc vs Doc (Doxygen / Docstring)
  5. Mermaid vs Mermaid (Diagrammi AST e Flowchart di controllo)
  6. Pseudocodice vs Pseudocodice (Rappresentazione Canonica Intermedia)

- 7 Metriche NLP:
  SBERT, BERTScore F1, CodeBERTScore F1, ROUGE-L, TF-IDF Cosine, METEOR, BLEURT
"""

import os
import sys
import json
from typing import Dict, List, Any
import numpy as np

# Aggiunge il path di progetto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.benchmark_metrics import (
    calculate_sbert_similarity,
    calculate_batch_bert_scores,
    calculate_rouge_l,
    calculate_tfidf_cosine,
    calculate_meteor_score,
    calculate_bleurt_score,
)

BENCHMARK_PAIRS = [
    # =========================================================================
    # 1. C vs C
    # =========================================================================
    {
        "domain": "C vs C",
        "category": "EQUIVALENT",
        "name": "Fibonacci: Iterativo vs Ricorsivo",
        "reference": """int fibonacci(int n) {
    if (n <= 0) return 0;
    if (n == 1) return 1;
    int a = 0, b = 1, c;
    for (int i = 2; i <= n; i++) {
        c = a + b;
        a = b;
        b = c;
    }
    return b;
}""",
        "candidate": """int fibonacci(int n) {
    if (n <= 0) return 0;
    if (n == 1) return 1;
    return fibonacci(n - 1) + fibonacci(n - 2);
}"""
    },
    {
        "domain": "C vs C",
        "category": "ADVERSARIAL",
        "name": "Clamp/MinMax: Minimo (<) vs Massimo (>)",
        "reference": """int find_extreme(int a, int b) {
    if (a < b) {
        return a;
    }
    return b;
}""",
        "candidate": """int find_extreme(int a, int b) {
    if (a > b) {
        return a;
    }
    return b;
}"""
    },
    {
        "domain": "C vs C",
        "category": "DOMAIN_SIMILAR",
        "name": "Array Int: Binary Search vs Somma Array",
        "reference": """int binary_search(const int arr[], int n, int target) {
    int low = 0, high = n - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}""",
        "candidate": """long sum_array(const int arr[], int len) {
    long total = 0;
    for (int i = 0; i < len; ++i) {
        total += arr[i];
    }
    return total;
}"""
    },
    {
        "domain": "C vs C",
        "category": "ORTHOGONAL",
        "name": "String Parsing vs Calcolo Matrice 3x3",
        "reference": """void parse_url(const char *url, char *proto, char *host) {
    const char *sep = strstr(url, "://");
    if (!sep) return;
    strncpy(proto, url, sep - url);
    strcpy(host, sep + 3);
}""",
        "candidate": """void matrix_mult3x3(float a[3][3], float b[3][3], float out[3][3]) {
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) {
            out[i][j] = 0.0f;
            for (int k = 0; k < 3; ++k) out[i][j] += a[i][k] * b[k][j];
        }
}"""
    },
    {
        "domain": "C vs C",
        "category": "FLUFF_VERBOSITY",
        "name": "Calcolo Minimo: Diretto vs Prolisso con Log e Variabili Ridondanti",
        "reference": """int min_val(int a, int b) {
    return (a < b) ? a : b;
}""",
        "candidate": """int min_val(int a, int b) {
    int candidate_first = a;
    int candidate_second = b;
    int evaluated_result = 0;
    if (candidate_first < candidate_second) {
        evaluated_result = candidate_first;
    } else {
        evaluated_result = candidate_second;
    }
    return evaluated_result;
}"""
    },

    # =========================================================================
    # 2. Python vs Python
    # =========================================================================
    {
        "domain": "Python vs Python",
        "category": "EQUIVALENT",
        "name": "Filtro Positivi: List Comprehension vs Loop Esplicito",
        "reference": """def filter_positive(numbers: list[int]) -> list[int]:
    result = []
    for x in numbers:
        if x > 0:
            result.append(x)
    return result""",
        "candidate": """def filter_positive(numbers: list[int]) -> list[int]:
    return [n for n in numbers if n > 0]"""
    },
    {
        "domain": "Python vs Python",
        "category": "ADVERSARIAL",
        "name": "Clamp Range: Corretto (<) vs Invertito (>)",
        "reference": """def clamp(val: float, min_val: float, max_val: float) -> float:
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val""",
        "candidate": """def clamp(val: float, min_val: float, max_val: float) -> float:
    if val > min_val:
        return min_val
    if val < max_val:
        return max_val
    return val"""
    },
    {
        "domain": "Python vs Python",
        "category": "DOMAIN_SIMILAR",
        "name": "Statistica: Media vs Varianza Campionaria",
        "reference": """def calculate_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)""",
        "candidate": """def calculate_variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return sum((x - avg) ** 2 for x in values) / (len(values) - 1)"""
    },
    {
        "domain": "Python vs Python",
        "category": "ORTHOGONAL",
        "name": "Socket Connect vs Regex Codice Fiscale",
        "reference": """def connect_socket(host: str, port: int, timeout: float = 5.0):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, port))
    return s""",
        "candidate": """def validate_tax_code(code: str) -> bool:
    import re
    pattern = r"^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$"
    return bool(re.match(pattern, code.upper()))"""
    },
    {
        "domain": "Python vs Python",
        "category": "FLUFF_VERBOSITY",
        "name": "Somma Lista: Funzione nativa sum() vs Ciclo prolisso decorato",
        "reference": """def compute_sum(items: list[int]) -> int:
    return sum(items)""",
        "candidate": """def compute_sum(items: list[int]) -> int:
    accumulator_total: int = 0
    iteration_index: int = 0
    while iteration_index < len(items):
        current_element: int = items[iteration_index]
        accumulator_total += current_element
        iteration_index += 1
    return int(accumulator_total)"""
    },

    # =========================================================================
    # 3. C vs Python (Cross-Language)
    # =========================================================================
    {
        "domain": "C vs Python",
        "category": "EQUIVALENT",
        "name": "Clamp: C if strutturato vs Python idiomatico min/max",
        "reference": """float clamp(float val, float min_val, float max_val) {
    if (val < min_val) return min_val;
    if (val > max_val) return max_val;
    return val;
}""",
        "candidate": """def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(val, max_val))"""
    },
    {
        "domain": "C vs Python",
        "category": "ADVERSARIAL",
        "name": "Ricerca Minimo: C corretto (<) vs Python errato (>)",
        "reference": """int find_min(const int arr[], int n) {
    int m = arr[0];
    for (int i = 1; i < n; i++) {
        if (arr[i] < m) m = arr[i];
    }
    return m;
}""",
        "candidate": """def find_min(arr: list[int]) -> int:
    m = arr[0]
    for x in arr[1:]:
        if x > m:
            m = x
    return m"""
    },
    {
        "domain": "C vs Python",
        "category": "DOMAIN_SIMILAR",
        "name": "Array Numerico: Bubble Sort C vs Linear Search Python",
        "reference": """void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}""",
        "candidate": """def linear_search(arr: list[int], target: int) -> int:
    for idx, val in enumerate(arr):
        if val == target:
            return idx
    return -1"""
    },
    {
        "domain": "C vs Python",
        "category": "ORTHOGONAL",
        "name": "Memoria C memcpy vs Python json.load",
        "reference": """void copy_buffer(void *dest, const void *src, size_t n) {
    char *d = (char *)dest;
    const char *s = (const char *)src;
    while (n--) *d++ = *s++;
}""",
        "candidate": """def load_config(filepath: str) -> dict:
    import json
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)"""
    },
    {
        "domain": "C vs Python",
        "category": "FLUFF_VERBOSITY",
        "name": "Inversione Stringa: C conciso vs Python sovra-ingegnerizzato",
        "reference": """void reverse_str(char *s, int len) {
    for (int i = 0, j = len - 1; i < j; ++i, --j) {
        char tmp = s[i]; s[i] = s[j]; s[j] = tmp;
    }
}""",
        "candidate": """def reverse_str(text: str) -> str:
    char_list = list(text)
    left_pointer = 0
    right_pointer = len(char_list) - 1
    while left_pointer < right_pointer:
        temporary_placeholder = char_list[left_pointer]
        char_list[left_pointer] = char_list[right_pointer]
        char_list[right_pointer] = temporary_placeholder
        left_pointer += 1
        right_pointer -= 1
    reconstructed_result = "".join(char_list)
    return str(reconstructed_result)"""
    },

    # =========================================================================
    # 4. Doc vs Doc (Doxygen / Docstring)
    # =========================================================================
    {
        "domain": "Doc vs Doc",
        "category": "EQUIVALENT",
        "name": "Parafrasi: Doxygen formale vs Descrizione naturale",
        "reference": """/**
 * @brief Computes Euclidean distance between two points in 2D space.
 * @param x1 The x-coordinate of the first point.
 * @param y1 The y-coordinate of the first point.
 * @param x2 The x-coordinate of the second point.
 * @param y2 The y-coordinate of the second point.
 * @return The straight-line distance as a floating-point number.
 */""",
        "candidate": """Calculates the distance between (x1, y1) and (x2, y2) using Pythagorean theorem.
Takes coordinates for two points in a two-dimensional Cartesian plane and returns the Euclidean distance."""
    },
    {
        "domain": "Doc vs Doc",
        "category": "ADVERSARIAL",
        "name": "Ownership e Negazione: must free vs must NOT free",
        "reference": "The caller must free the returned string buffer after usage to prevent memory leaks.",
        "candidate": "The caller must not free the returned string buffer after usage to prevent memory leaks."
    },
    {
        "domain": "Doc vs Doc",
        "category": "DOMAIN_SIMILAR",
        "name": "Documentazione Algoritmica: Quicksort vs Binary Search",
        "reference": "Sorts an array of integers in ascending order in-place using quicksort partitioning algorithm.",
        "candidate": "Searches for a specific integer target within an array using binary search algorithm."
    },
    {
        "domain": "Doc vs Doc",
        "category": "ORTHOGONAL",
        "name": "Documentazione Socket TLS vs Determinante Matrice",
        "reference": "Establishes an encrypted TLS socket connection with remote server and authenticates session.",
        "candidate": "Computes the determinant of a 3x3 square matrix using Sarrus rule and returns scalar value."
    },
    {
        "domain": "Doc vs Doc",
        "category": "FLUFF_VERBOSITY",
        "name": "Codice Ritorno: Conciso vs Prolisso con fluff LLM",
        "reference": "Returns 0 on success, or -1 on error.",
        "candidate": "This utility function serves as an operational routine that handles execution outcomes by returning an integer value of zero when the operation completes successfully without anomalies, or alternatively yields minus one when an unexpected error condition is encountered during the routine."
    },

    # =========================================================================
    # 5. Mermaid vs Mermaid
    # =========================================================================
    {
        "domain": "Mermaid vs Mermaid",
        "category": "EQUIVALENT",
        "name": "Diagramma Control Flow Clamp: Forma Standard vs Espansa",
        "reference": """graph TD
    A[Entry: clamp] --> B{val < min_val}
    B -- Yes --> C[return min_val]
    B -- No --> D{val > max_val}
    D -- Yes --> E[return max_val]
    D -- No --> F[return val]""",
        "candidate": """graph TD
    Start([Inizio clamp]) --> CheckMin{val < min_val?}
    CheckMin -- Vero --> RetMin[Restituisci min_val]
    CheckMin -- Falso --> CheckMax{val > max_val?}
    CheckMax -- Vero --> RetMax[Restituisci max_val]
    CheckMax -- Falso --> RetVal[Restituisci val]"""
    },
    {
        "domain": "Mermaid vs Mermaid",
        "category": "ADVERSARIAL",
        "name": "Diagramma Branching Invertito: Minimo (<) vs Massimo (>)",
        "reference": """graph TD
    A[Start: find_min] --> B{arr[i] < m}
    B -- Yes --> C[m = arr[i]]
    B -- No --> D[Next Step]
    C --> D
    D --> E[Return m]""",
        "candidate": """graph TD
    A[Start: find_min] --> B{arr[i] > m}
    B -- Yes --> C[m = arr[i]]
    B -- No --> D[Next Step]
    C --> D
    D --> E[Return m]"""
    },
    {
        "domain": "Mermaid vs Mermaid",
        "category": "DOMAIN_SIMILAR",
        "name": "Diagrammi Algoritmici: Loop Bubble Sort vs Loop Linear Search",
        "reference": """graph TD
    Start --> LoopI{i < n - 1}
    LoopI -- Yes --> LoopJ{j < n - i - 1}
    LoopJ -- Yes --> CondSwap{arr[j] > arr[j+1]}
    CondSwap -- Yes --> DoSwap[Swap elements]
    CondSwap -- No --> IncJ[j++]
    DoSwap --> IncJ
    IncJ --> LoopJ
    LoopJ -- No --> IncI[i++]
    IncI --> LoopI
    LoopI -- No --> End[End Sort]""",
        "candidate": """graph TD
    Start --> InitLoop[idx = 0]
    InitLoop --> CheckBounds{idx < len}
    CheckBounds -- Yes --> CheckMatch{arr[idx] == target}
    CheckMatch -- Yes --> RetIdx[Return idx]
    CheckMatch -- No --> NextIdx[idx++]
    NextIdx --> CheckBounds
    CheckBounds -- No --> RetNotFound[Return -1]
    RetIdx --> End([End])
    RetNotFound --> End"""
    },
    {
        "domain": "Mermaid vs Mermaid",
        "category": "ORTHOGONAL",
        "name": "Grafo Memcpy Buffer vs Grafo Parsing JSON",
        "reference": """graph TD
    A[Entry: copy_buffer] --> B[Init: d = dest, s = src]
    B --> C{Condition: n-- > 0}
    C -- Yes --> D[Operation: *d++ = *s++]
    D --> C
    C -- No --> E[Exit]""",
        "candidate": """graph TD
    A[Start: load_config] --> B[Open filepath]
    B --> C[Load JSON from stream]
    C --> D[Parse Key Value Pairs]
    D --> E[Return Config Map]
    E --> F[Close Stream]"""
    },
    {
        "domain": "Mermaid vs Mermaid",
        "category": "FLUFF_VERBOSITY",
        "name": "Diagramma Controllo: Minimale vs Iper-dettagliato con Nodi Log e Pass-through",
        "reference": """graph TD
    A[Start] --> B{val >= 0}
    B -- Yes --> C[Result = True]
    B -- No --> D[Result = False]
    C --> E[Return Result]
    D --> E""",
        "candidate": """graph TD
    A[Start Procedure] --> LogEntry[Log Entry Parameters]
    LogEntry --> CheckCondition{Is val greater or equal to zero?}
    CheckCondition -- Yes --> TrueBranch[Set internal status True]
    TrueBranch --> LogTrue[Audit True Event]
    LogTrue --> MergeNode[Merge Execution Path]
    CheckCondition -- No --> FalseBranch[Set internal status False]
    FalseBranch --> LogFalse[Audit False Event]
    LogFalse --> MergeNode
    MergeNode --> PreReturn[Prepare Output Envelope]
    PreReturn --> FinalReturn[Return Status Flag]"""
    },

    # =========================================================================
    # 6. Pseudocodice vs Pseudocodice (Canonical IR)
    # =========================================================================
    {
        "domain": "Pseudocodice vs Pseudocodice",
        "category": "EQUIVALENT",
        "name": "Fattoriale: Iterativo FOR vs Formula Prodotto Ricorsivo",
        "reference": """FACTORIAL(n)
    IF n < 0 THEN
        RETURN 0
    END IF
    res = 1
    FOR i FROM 2 TO n DO
        res = res * i
    END FOR
    RETURN res""",
        "candidate": """FACTORIAL_ALGO(n)
    IF n < 0 THEN
        RETURN 0
    END IF
    result = 1
    i = 1
    WHILE i <= n DO
        result = result * i
        i = i + 1
    END WHILE
    RETURN result"""
    },
    {
        "domain": "Pseudocodice vs Pseudocodice",
        "category": "ADVERSARIAL",
        "name": "Find Extreme: Minimo (<) vs Massimo (>)",
        "reference": """FIND-EXTREME(arr, n)
    m = arr[0]
    FOR i FROM 1 TO n - 1 DO
        IF arr[i] < m THEN
            m = arr[i]
        END IF
    END FOR
    RETURN m""",
        "candidate": """FIND-EXTREME(arr, n)
    m = arr[0]
    FOR i FROM 1 TO n - 1 DO
        IF arr[i] > m THEN
            m = arr[i]
        END IF
    END FOR
    RETURN m"""
    },
    {
        "domain": "Pseudocodice vs Pseudocodice",
        "category": "DOMAIN_SIMILAR",
        "name": "Array: Bubble Sort vs Linear Search",
        "reference": """BUBBLE-SORT(arr, n)
    FOR i FROM 0 TO n - 2 DO
        FOR j FROM 0 TO n - i - 2 DO
            IF arr[j] > arr[j + 1] THEN
                SWAP(arr[j], arr[j + 1])
            END IF
        END FOR
    END FOR""",
        "candidate": """LINEAR-SEARCH(arr, target)
    FOR idx FROM 0 TO LENGTH(arr) - 1 DO
        IF arr[idx] == target THEN
            RETURN idx
        END IF
    END FOR
    RETURN -1"""
    },
    {
        "domain": "Pseudocodice vs Pseudocodice",
        "category": "ORTHOGONAL",
        "name": "Copia Buffer vs Parsing Configurazione JSON",
        "reference": """COPY-BUFFER(dest, src, n)
    WHILE n > 0 DO
        n = n - 1
        *dest = *src
        dest = dest + 1
        src = src + 1
    END WHILE""",
        "candidate": """LOAD-CONFIG(filepath)
    file_handle = OPEN(filepath, "r")
    config_dict = PARSE-JSON(file_handle)
    CLOSE(file_handle)
    RETURN config_dict"""
    },
    {
        "domain": "Pseudocodice vs Pseudocodice",
        "category": "FLUFF_VERBOSITY",
        "name": "Somma Array: Pseudocodice Compatto vs Iper-verboso con Variabili Temporanee",
        "reference": """SUM-ARRAY(arr, len)
    total = 0
    FOR i FROM 0 TO len - 1 DO
        total = total + arr[i]
    END FOR
    RETURN total""",
        "candidate": """CALCULATE-AGGREGATE-SUM(elements_array, total_count)
    accumulated_sum = 0
    current_index = 0
    WHILE current_index < total_count DO
        temporary_value = elements_array[current_index]
        updated_sum = accumulated_sum + temporary_value
        accumulated_sum = updated_sum
        current_index = current_index + 1
    END WHILE
    final_output = accumulated_sum
    RETURN final_output"""
    }
]


def run_evaluation() -> List[Dict[str, Any]]:
    print("=" * 80)
    print(f"CALCOLO DI TUTTE LE 7 METRICHE NLP SU {len(BENCHMARK_PAIRS)} CASI DI TEST")
    print("=" * 80)

    refs = [case["reference"] for case in BENCHMARK_PAIRS]
    cands = [case["candidate"] for case in BENCHMARK_PAIRS]

    # 1. ROUGE-L & TF-IDF Cosine
    print("[1/6] Calcolo ROUGE-L e TF-IDF Cosine...")
    rouge_l_scores = [calculate_rouge_l(r, c) for r, c in zip(refs, cands)]
    tfidf_scores = [calculate_tfidf_cosine(r, c) for r, c in zip(refs, cands)]

    # 2. METEOR
    print("[2/6] Calcolo METEOR Score...")
    meteor_scores = [calculate_meteor_score(r, c) for r, c in zip(refs, cands)]

    # 3. SBERT
    print("[3/6] Calcolo SBERT (all-MiniLM-L6-v2)...")
    sbert_scores = [calculate_sbert_similarity(r, c) for r, c in zip(refs, cands)]

    # 4. BERTScore F1 (General)
    print("[4/6] Calcolo BERTScore F1 (bert-base-uncased)...")
    bert_results = calculate_batch_bert_scores(refs, cands, model_type="bert-base-uncased")
    bert_f1_scores = [b["f1"] for b in bert_results]

    # 5. CodeBERTScore F1 (Code-specific)
    print("[5/6] Calcolo CodeBERTScore F1 (microsoft/codebert-base)...")
    codebert_results = calculate_batch_bert_scores(refs, cands, model_type="microsoft/codebert-base")
    codebert_f1_scores = [cb["f1"] for cb in codebert_results]

    # 6. BLEURT
    print("[6/6] Calcolo BLEURT Quality Score...")
    bleurt_scores = [calculate_bleurt_score(r, c) for r, c in zip(refs, cands)]

    full_results = []
    for i, case in enumerate(BENCHMARK_PAIRS):
        res = {
            "domain": case["domain"],
            "category": case["category"],
            "name": case["name"],
            "scores": {
                "SBERT": sbert_scores[i],
                "BERTScore_F1": bert_f1_scores[i],
                "CodeBERT_F1": codebert_f1_scores[i],
                "ROUGE_L": rouge_l_scores[i],
                "TFIDF_Cosine": tfidf_scores[i],
                "METEOR": meteor_scores[i],
                "BLEURT": bleurt_scores[i]
            }
        }
        full_results.append(res)

    out_file = os.path.join(ROOT_DIR, "results", "metrics_validation", "img_finali", "nlp_benchmark_5classes_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)

    print(f"\n[OK] Calcolo completato! Risultati salvati in: {out_file}")
    return full_results


if __name__ == "__main__":
    run_evaluation()
