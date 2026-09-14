from typing import Dict, Any, List
from src.llm_provider import LLMProvider

class WriterAgent:
    """
    Writer Agent: Riceve il contesto analizzato dal Reader e dal Searcher
    e redige il blocco Doxygen ed il brief summary in italiano.
    """
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def write_documentation(
        self, 
        enriched_context: Dict[str, Any],
        source_code: str,
        validation_feedback: str = None
    ) -> Dict[str, str]:
        func_name = enriched_context["func_name"]
        signature = enriched_context["signature"]
        callees_summaries = enriched_context.get("callees_summaries", [])
        raw_fact = enriched_context.get("raw_fact_sheet", "")

        # Invoca il provider LLM per comporre il testo Doxygen
        return self.llm.generate_documentation(
            func_name=func_name,
            signature=signature,
            source_code=source_code,
            callees_summaries=callees_summaries,
            raw_comment=f"Fact Sheet estratto dal Reader Agent: {raw_fact}",
            validation_feedback=validation_feedback
        )
