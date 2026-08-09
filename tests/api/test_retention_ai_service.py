import json
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from pydantic import ValidationError

from api.retention_ai_service import RetentionAIService
from api.retention_catalog import get_allowed_retention_actions
from api.schemas import (
    IndividualExplainabilityResponse,
    RetentionRecommendationContent,
)


class TestRetentionAIService(IsolatedAsyncioTestCase):
    @staticmethod
    def _build_explainability():
        return IndividualExplainabilityResponse.model_validate(
            {
                "customer_id": 809849358,
                "churn_probability": 0.91,
                "churn_prediction": 1,
                "prediction_label": "churn",
                "risk_band": "High",
                "model_name": "finpulse-churn-catboost",
                "model_alias": "champion",
                "model_version": 3,
                "run_id": "test-run",
                "input_feature_count": 19,
                "transformed_feature_count": 30,
                "base_value": -1.0,
                "features": [],
                "risk_increasing_factors": [
                    {
                        "feature": "total_transaction_count",
                        "value": 20,
                        "shap_value": 1.2,
                        "absolute_shap": 1.2,
                        "importance_share": 0.40,
                        "impact_direction": "increases_risk",
                    }
                ],
                "risk_reducing_factors": [
                    {
                        "feature": "months_on_book",
                        "value": 48,
                        "shap_value": -0.4,
                        "absolute_shap": 0.4,
                        "importance_share": 0.13,
                        "impact_direction": "reduces_risk",
                    }
                ],
            }
        )

    async def test_generate_recommendation_returns_validated_content(self):
        explainability = self._build_explainability()

        fake_llama_response = {
            "case_summary": (
                "Cliente com alto risco de churn e prioridade crítica."
            ),
            "risk_interpretation": (
                "A baixa atividade transacional aparece como sinal "
                "relevante associado ao aumento do risco."
            ),
            "main_risk_signals": [
                "Baixa quantidade de transações."
            ],
            "protective_factors": [
                "Relacionamento de 48 meses."
            ],
            "recommended_action_id": "priority_retention_contact",
            "approach_guidance": (
                "Priorizar contato humano consultivo."
            ),
            "suggested_message": (
                "Olá! Gostaríamos de entender como tem sido "
                "sua experiência conosco."
            ),
            "attention_points": [
                "A recomendação requer revisão humana."
            ],
        }

        fake_ollama_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    fake_llama_response,
                    ensure_ascii=False,
                )
            )
        )

        service = RetentionAIService()

        service._client.chat = AsyncMock(
            return_value=fake_ollama_response
        )

        result = await service.generate_recommendation(
            explainability=explainability,
            priority_label="Crítica",
            allowed_actions=get_allowed_retention_actions("High"),
        )

        self.assertIsInstance(
            result,
            RetentionRecommendationContent,
        )

        self.assertEqual(
            result.recommended_action_id.value,
            "priority_retention_contact",
        )

        service._client.chat.assert_awaited_once()

        call_kwargs = service._client.chat.await_args.kwargs

        self.assertEqual(
            call_kwargs["options"],
            {
                "temperature": 0,
            },
        )

        self.assertIn(
            "Respond in Brazilian Portuguese.",
            call_kwargs["messages"][0]["content"],
        )

        self.assertIn(
            "priority_retention_contact",
            call_kwargs["messages"][1]["content"],
        )

    async def test_generate_recommendation_rejects_invalid_action(self):
        explainability = self._build_explainability()

        fake_invalid_response = {
            "case_summary": "Cliente com alto risco de churn.",
            "risk_interpretation": "Há sinais relevantes de risco.",
            "main_risk_signals": [],
            "protective_factors": [],
            "recommended_action_id": "give_discount",
            "approach_guidance": "Oferecer desconto.",
            "suggested_message": "Temos um desconto especial.",
            "attention_points": [
                "Revisão humana necessária."
            ],
        }

        fake_ollama_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    fake_invalid_response,
                    ensure_ascii=False,
                )
            )
        )

        service = RetentionAIService()

        service._client.chat = AsyncMock(
            return_value=fake_ollama_response
        )

        with self.assertRaises(ValidationError):
            await service.generate_recommendation(
                explainability=explainability,
                priority_label="Crítica",
                allowed_actions=get_allowed_retention_actions("High"),
            )

        service._client.chat.assert_awaited_once()