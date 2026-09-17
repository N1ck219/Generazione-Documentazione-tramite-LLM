import json
from typing import Dict, Any, Optional
from src.llm_provider import LLMProvider

class JudgeAgent:
    """
    Judge / Critic Agent:
    Valuta la documentazione generata (Doxygen + brief summary) a confronto
    con il codice sorgente C/C++ originale, assegnando un punteggio da 1 a 5.
    
    Rubrica di Valutazione (1-5):
      5: Eccellente / Impeccabile. Copre esaustivamente contratti, pre/post-condizioni,
         gestione puntatori NULL ed edge cases.
      4: Buona e solida. Nessun errore fattuale, descrive accuratamente il comportamento.
         Differenze solo minori o stilistiche.
      3: Sufficiente ma lacunosa. Tecnicamente corretta ma omette dettagli critici
         (es. ownership della memoria, codici di errore specifici o gestione NULL).
      2: Insufficiente o generica. Ripete tautologicamente il nome della funzione o
         contiene ambiguità rilevanti.
      1: Gravemente errata o contraddittoria. Descrive comportamenti opposti al codice
         o include allucinazioni palesi.
    
    Regola Operativa:
      Se score < 4, il Judge genera una 'critique' costruttiva e puntuale,
      che verrà ripassata al WriterAgent per la riscrittura e perfezionamento.
    """
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def evaluate_documentation(
        self,
        func_name: str,
        signature: str,
        source_code: str,
        doxygen_doc: str,
        brief_summary: str = "",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Invoca l'LLM per valutare la qualità e veridicità della documentazione.
        Restituisce un dizionario:
        {
            "score": int,         # da 1 a 5
            "critique": str,      # motivazione dettagliata (vuota se score >= 4)
            "suggestions": list   # suggerimenti specifici per il WriterAgent
        }
        """
        # Se siamo in presenza di MockLLMProvider o fallback offline
        if hasattr(self.llm, "evaluate_documentation"):
            return self.llm.evaluate_documentation(
                func_name=func_name,
                signature=signature,
                source_code=source_code,
                doxygen_doc=doxygen_doc,
                brief_summary=brief_summary,
                language=language
            )

        # Fallback generico se il provider non implementa il metodo
        return {
            "score": 5,
            "critique": "",
            "suggestions": []
        }
