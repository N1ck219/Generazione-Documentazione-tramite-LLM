import json
from typing import Dict, Any, List
from src.llm_provider import LLMProvider

class ReaderAgent:
    """
    Reader Agent: Spetta a questo agente analizzare il codice C sorgente
    ed estrarre un Fact Sheet analitico ed oggettivo (JSON) prima della scrittura.
    """
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def analyze_function(
        self, 
        func_name: str, 
        signature: str, 
        source_code: str, 
        raw_comment: str = None
    ) -> Dict[str, Any]:
        prompt = f"""Sei il READER AGENT della pipeline di analisi codice C.
Il tuo unico compito e' analizzare la funzione C sottostante ed estrarre un Fact Sheet sintetico in formato JSON.

Funzione: `{func_name}`
Firma: `{signature}`
Commento originale: {raw_comment or "Nessuno"}

Codice Sorgente:
```c
{source_code}
```

Rispondi ESCLUSIVAMENTE con un JSON contenente queste chiavi:
{{
  "preconditions": ["Lista di controlli sui parametri, es: rb != NULL, capacity > 0"],
  "operations": ["Lista delle operazioni principali, es: malloc di capacity * sizeof(int), azzeramento head/tail"],
  "error_conditions": ["Lista esatta delle condizioni di fallimento e relativi valori restituiti"],
  "success_return": "Valore o stato restituito in caso di successo"
}}
Rispondi SOLO con il JSON senza altri blocchi di testo.
"""
        max_attempts = 2
        for _ in range(max_attempts):
            try:
                res = self.llm.generate_documentation(
                    func_name=func_name,
                    signature=signature,
                    source_code=source_code,
                    callees_summaries=[],
                    raw_comment=raw_comment
                )
                text = res.get("brief_summary", "{}")
                # Se la chiamata restituisce l'output strutturato
                return {
                    "raw_fact_sheet": text,
                    "func_name": func_name,
                    "signature": signature
                }
            except Exception:
                pass

        return {
            "raw_fact_sheet": f"Analisi sintattica della funzione {func_name}",
            "func_name": func_name,
            "signature": signature
        }
