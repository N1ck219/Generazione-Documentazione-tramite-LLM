import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.reader_agent import ReaderAgent
from src.agents.searcher_agent import SearcherAgent
from src.agents.writer_agent import WriterAgent
from src.agents.judge_agent import JudgeAgent
from src.llm_provider import MockLLMProvider, LLMProvider
from src.verifier import DocumentationVerifier

class CustomMockJudgeLLM(MockLLMProvider):
    """Mock LLM per testare sia scenari di approvazione che di rifiuto del Giudice."""
    def __init__(self, scores_sequence):
        super().__init__()
        self.scores_sequence = list(scores_sequence)
        self.eval_call_count = 0
        self.writer_call_count = 0
        self.received_critiques = []

    def evaluate_documentation(self, func_name, signature, source_code, doxygen_doc, brief_summary="", language="en"):
        self.eval_call_count += 1
        score, critique = self.scores_sequence.pop(0) if self.scores_sequence else (5, "")
        return {
            "score": score,
            "critique": critique,
            "suggestions": ["Migliora i dettagli dei parametri"] if score < 4 else []
        }

    def generate_documentation(self, func_name, signature, source_code, callees_summaries, raw_comment=None, validation_feedback=None, language="en"):
        self.writer_call_count += 1
        if validation_feedback:
            self.received_critiques.append(validation_feedback)
        
        # Genera una documentazione formalmente valida per superare l'AST Verifier
        return {
            "brief_summary": f"Documentazione generata per {func_name}",
            "full_doxygen_doc": f"""/**
 * @brief Test doc for {func_name}
 * @details Dettagli tecnici della funzione.
 * @param[in] capacity Capacita del buffer.
 * @return 0 in caso di successo.
 */"""
        }

class TestJudgeAgentPipeline(unittest.TestCase):
    def test_judge_agent_initialization(self):
        llm = MockLLMProvider()
        judge = JudgeAgent(llm)
        res = judge.evaluate_documentation(
            func_name="test_func",
            signature="int test_func(int x)",
            source_code="int test_func(int x) { return x * 2; }",
            doxygen_doc="/** @brief Test */"
        )
        self.assertIn("score", res)
        self.assertEqual(res["score"], 5)
        self.assertEqual(res["critique"], "")

    def test_writer_agent_accepts_critic_feedback(self):
        llm = CustomMockJudgeLLM(scores_sequence=[(5, "")])
        writer = WriterAgent(llm)
        enriched_ctx = {
            "func_name": "rb_init",
            "signature": "int rb_init(int capacity)",
            "callees_summaries": [],
            "raw_fact_sheet": "Inizializza la struttura"
        }
        writer.write_documentation(
            enriched_context=enriched_ctx,
            source_code="int rb_init(int capacity) { return 0; }",
            validation_feedback="AST error",
            critic_feedback="Punteggio 3/5: manca la specifica di allocazione"
        )
        self.assertEqual(len(llm.received_critiques), 1)
        self.assertIn("[VERIFIER AST FEEDBACK]", llm.received_critiques[0])
        self.assertIn("[JUDGE AGENT CRITIQUE & IMPROVEMENT GUIDELINES]", llm.received_critiques[0])

    def test_judge_reject_and_regeneration_loop(self):
        # Scenario: Primo tentativo rifiutato dal giudice (score 3 < 4), secondo tentativo approvato (score 5 >= 4)
        mock_llm = CustomMockJudgeLLM(scores_sequence=[
            (3, "Manca la spiegazione sulla gestione della memoria."),
            (5, "Ottima documentazione.")
        ])
        
        reader = ReaderAgent(mock_llm)
        writer = WriterAgent(mock_llm)
        judge = JudgeAgent(mock_llm)
        verifier = DocumentationVerifier({})

        func_name = "rb_init"
        signature = "int rb_init(int capacity)"
        source_code = "int rb_init(int capacity) { return 0; }"
        fn_info = {
            "name": func_name,
            "parameters": [{"name": "capacity", "type": "int"}],
            "return_type": "int"
        }

        critic_feedback = None
        validation_feedback = None
        final_score = None
        approved = False

        for attempt in range(3):
            # 1. Reader
            reader_facts = reader.analyze_function(func_name, signature, source_code)
            enriched_ctx = {
                "func_name": func_name,
                "signature": signature,
                "callees_summaries": [],
                "raw_fact_sheet": reader_facts.get("raw_fact_sheet", "")
            }

            # 2. Writer con critic_feedback
            doc_result = writer.write_documentation(
                enriched_context=enriched_ctx,
                source_code=source_code,
                validation_feedback=validation_feedback,
                critic_feedback=critic_feedback
            )

            # 3. Verifier AST
            val_res = verifier.verify_function_doc(fn_info, doc_result)
            self.assertTrue(val_res["is_valid"])

            # 4. Judge Agent
            judge_res = judge.evaluate_documentation(
                func_name=func_name,
                signature=signature,
                source_code=source_code,
                doxygen_doc=doc_result["full_doxygen_doc"],
                brief_summary=doc_result["brief_summary"]
            )
            score = judge_res["score"]
            critique = judge_res["critique"]

            if score < 4 and attempt < 2:
                critic_feedback = f"Punteggio assegnato: {score}/5. Critica: {critique}"
            else:
                approved = True
                final_score = score
                break

        self.assertTrue(approved)
        self.assertEqual(final_score, 5)
        self.assertEqual(mock_llm.eval_call_count, 2)
        self.assertEqual(len(mock_llm.received_critiques), 1)
        self.assertIn("Punteggio assegnato: 3/5", mock_llm.received_critiques[0])

if __name__ == "__main__":
    unittest.main()
