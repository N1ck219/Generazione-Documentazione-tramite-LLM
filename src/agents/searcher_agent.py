from typing import Dict, Any, List

class SearcherAgent:
    """
    Searcher Agent: Correda i fatti estratti dal Reader Agent con il contesto
    delle dipendenze interne (callees) estratte dal DB SQLite e dalle convenzioni C.
    """
    def __init__(self, db_instance):
        self.db = db_instance

    def enrich_context(
        self, 
        reader_facts: Dict[str, Any], 
        callees: List[str]
    ) -> Dict[str, Any]:
        callees_summaries = self.db.get_callees_summaries(callees)
        
        enriched = dict(reader_facts)
        enriched["callees_summaries"] = callees_summaries
        return enriched
