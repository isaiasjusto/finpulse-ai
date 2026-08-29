import unittest

from pydantic import ValidationError

from api.schemas import (
    AssistantGeneratedContent,
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantScope,
    AssistantSourceType,
)


class AssistantSchemaTests(unittest.TestCase):
    @staticmethod
    def _valid_response_data() -> dict[str, object]:
        return {
            "scope": "customer",
            "answer": (
                "O cliente apresenta sinais transacionais "
                "que justificam análise prioritária."
            ),
            "customer_id": 809849358,
            "sources": [
                {
                    "source_type": "customer_explainability",
                    "label": "SHAP individual",
                    "reference": "customer:809849358",
                }
            ],
            "requires_human_review": True,
            "generation": {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "generated_at": "2026-08-29T12:00:00Z",
            },
        }

    def test_customer_query_accepts_customer_id(self) -> None:
        request = AssistantQueryRequest(
            question=(
                "Por que este cliente precisa de atenção?"
            ),
            scope=AssistantScope.customer,
            customer_id=809849358,
        )

        self.assertEqual(
            request.scope,
            AssistantScope.customer,
        )
        self.assertEqual(
            request.customer_id,
            809849358,
        )

    def test_customer_query_requires_customer_id(self) -> None:
        with self.assertRaises(ValidationError):
            AssistantQueryRequest(
                question="Analise este cliente.",
                scope=AssistantScope.customer,
            )

    def test_portfolio_query_rejects_customer_id(self) -> None:
        with self.assertRaises(ValidationError):
            AssistantQueryRequest(
                question="Resuma a carteira.",
                scope=AssistantScope.portfolio,
                customer_id=809849358,
            )

    def test_blank_question_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AssistantQueryRequest(
                question="   ",
                scope=AssistantScope.portfolio,
            )

    def test_extra_request_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AssistantQueryRequest.model_validate(
                {
                    "question": "Resuma a carteira.",
                    "scope": "portfolio",
                    "uncontrolled_field": "not allowed",
                }
            )

    def test_valid_response_preserves_sources(self) -> None:
        response = AssistantQueryResponse.model_validate(
            self._valid_response_data()
        )

        self.assertTrue(
            response.requires_human_review
        )
        self.assertEqual(
            response.sources[0].source_type,
            AssistantSourceType.customer_explainability,
        )

    def test_response_requires_at_least_one_source(
        self,
    ) -> None:
        response_data = self._valid_response_data()
        response_data["sources"] = []

        with self.assertRaises(ValidationError):
            AssistantQueryResponse.model_validate(
                response_data
            )

    def test_human_review_cannot_be_disabled(self) -> None:
        response_data = self._valid_response_data()
        response_data["requires_human_review"] = False

        with self.assertRaises(ValidationError):
            AssistantQueryResponse.model_validate(
                response_data
            )

    def test_customer_response_requires_customer_id(
        self,
    ) -> None:
        response_data = self._valid_response_data()
        response_data["customer_id"] = None

        with self.assertRaises(ValidationError):
            AssistantQueryResponse.model_validate(
                response_data
            )

    def test_generated_content_accepts_answer(self) -> None:
        content = AssistantGeneratedContent(
            answer="Resposta produzida dentro do contexto controlado."
        )

        self.assertEqual(
            content.answer,
            "Resposta produzida dentro do contexto controlado.",
        )

    def test_generated_content_rejects_blank_answer(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            AssistantGeneratedContent(
                answer="   "
            )

    def test_generated_content_rejects_governed_fields(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            AssistantGeneratedContent.model_validate(
                {
                    "answer": "Resposta válida.",
                    "sources": [],
                    "requires_human_review": False,
                }
            )

if __name__ == "__main__":
    unittest.main()
