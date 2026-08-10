import json
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from pydantic import ValidationError

import httpx

from api.retention_ai_service import (
    RetentionAIInvalidResponseError,
    RetentionAIService,
    RetentionAITimeoutError,
    RetentionAIUnavailableError,
)

from api.retention_catalog import get_allowed_retention_actions
from api.schemas import (
    IndividualExplainabilityResponse,
    RetentionRecommendationContent,
)


class TestRetentionAIService(IsolatedAsyncioTestCase):
    @staticmethod
    def _build_explainability(
        churn_probability: float = 0.91,
        risk_band: str = "High",
    ):
        return IndividualExplainabilityResponse.model_validate(
            {
                "customer_id": 809849358,
                "churn_probability": churn_probability,
                "churn_prediction": 1,
                "prediction_label": "churn",
                "risk_band": risk_band,
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

        self.assertEqual(
            result.case_summary,
            (
                "Cliente classificado na faixa de risco High, "
                "com probabilidade de churn de 91.00%."
            ),
        )

        self.assertEqual(
            result.main_risk_signals,
            [
                (
                    "A característica 'total_transaction_count' contribuiu "
                    "para aumentar a previsão de churn do modelo."
                )
            ],
        )

        self.assertEqual(
            result.protective_factors,
            [
                (
                    "A característica 'months_on_book' contribuiu para reduzir "
                    "a previsão de churn do modelo."
                )
            ],
        )

        self.assertEqual(
            result.attention_points,
            [
                (
                    "A recomendação deve ser revisada por uma pessoa "
                    "antes de qualquer ação."
                ),
                (
                    "As contribuições SHAP não representam relações causais."
                ),
            ],
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

    async def test_medium_rejects_high_only_action(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        )

        fake_invalid_response = {
            "case_summary": "Resumo gerado pela IA.",
            "risk_interpretation": "Interpretação gerada pela IA.",
            "main_risk_signals": [],
            "protective_factors": [],
            "recommended_action_id": "priority_retention_contact",
            "approach_guidance": "Realizar contato prioritário.",
            "suggested_message": "Olá! Gostaríamos de conversar com você.",
            "attention_points": [],
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

        with self.assertRaises(ValueError):
            await service.generate_recommendation(
                explainability=explainability,
                priority_label="Atenção",
                allowed_actions=get_allowed_retention_actions("Medium"),
            )

    async def test_medium_accepts_allowed_action(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        )

        fake_valid_response = {
            "case_summary": "Resumo gerado pela IA.",
            "risk_interpretation": "Interpretação gerada pela IA.",
            "main_risk_signals": [],
            "protective_factors": [],
            "recommended_action_id": "preventive_contact",
            "approach_guidance": (
                "Realizar uma abordagem consultiva e preventiva."
            ),
            "suggested_message": (
                "Olá! Gostaríamos de saber como tem sido "
                "sua experiência conosco."
            ),
            "attention_points": [],
        }

        fake_ollama_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    fake_valid_response,
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
            priority_label="Atenção",
            allowed_actions=get_allowed_retention_actions("Medium"),
        )

        self.assertEqual(
            result.recommended_action_id.value,
            "preventive_contact",
        )

        self.assertEqual(
            result.case_summary,
            (
                "Cliente classificado na faixa de risco Medium, "
                "com probabilidade de churn de 35.00%."
            ),
        )

        self.assertEqual(
            result.approach_guidance,
            (
                "Realizar contato consultivo para compreender possíveis "
                "dificuldades antes de uma decisão de saída."
            ),
        )

    async def test_low_accepts_maintain_relationship(self):
        explainability = self._build_explainability(
            churn_probability=0.10,
            risk_band="Low",
        )

        fake_valid_response = {
            "case_summary": "Resumo gerado pela IA.",
            "risk_interpretation": "Interpretação gerada pela IA.",
            "main_risk_signals": [],
            "protective_factors": [],
            "recommended_action_id": "maintain_relationship",
            "approach_guidance": "Texto qualquer vindo da IA.",
            "suggested_message": (
                "Olá! Esperamos que sua experiência conosco "
                "continue sendo positiva."
            ),
            "attention_points": [],
        }

        fake_ollama_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    fake_valid_response,
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
            priority_label="Baixa",
            allowed_actions=get_allowed_retention_actions("Low"),
        )

        self.assertEqual(
            result.recommended_action_id.value,
            "maintain_relationship",
        )

        self.assertEqual(
            result.case_summary,
            (
                "Cliente classificado na faixa de risco Low, "
                "com probabilidade de churn de 10.00%."
            ),
        )

        self.assertEqual(
            result.approach_guidance,
            (
                "Manter o acompanhamento do cliente e reforçar ações "
                "regulares de relacionamento e fidelização."
            ),
        )

    async def test_low_rejects_medium_high_action(self):
        explainability = self._build_explainability(
            churn_probability=0.10,
            risk_band="Low",
        )

        fake_invalid_response = {
            "case_summary": "Resumo gerado pela IA.",
            "risk_interpretation": "Interpretação gerada pela IA.",
            "main_risk_signals": [],
            "protective_factors": [],
            "recommended_action_id": "preventive_contact",
            "approach_guidance": "Realizar contato preventivo.",
            "suggested_message": (
                "Olá! Gostaríamos de conversar sobre sua experiência."
            ),
            "attention_points": [],
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

        with self.assertRaises(ValueError):
            await service.generate_recommendation(
                explainability=explainability,
                priority_label="Baixa",
                allowed_actions=get_allowed_retention_actions("Low"),
            )

        service._client.chat.assert_awaited_once()


    async def test_without_protective_factors_does_not_invent_evidence(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        ).model_copy(
            update={
                "risk_reducing_factors": [],
            }
        )

        fake_llama_response = {
            "case_summary": "Resumo inventado pela IA.",
            "risk_interpretation": "Interpretação inventada pela IA.",
            "main_risk_signals": [
                "Sinal inventado pela IA."
            ],
            "protective_factors": [
                "Cliente possui excelente relacionamento de longo prazo."
            ],
            "recommended_action_id": "preventive_contact",
            "approach_guidance": "Orientação inventada pela IA.",
            "suggested_message": (
                "Olá! Gostaríamos de saber como tem sido "
                "sua experiência conosco."
            ),
            "attention_points": [
                "Ponto inventado pela IA."
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
            priority_label="Atenção",
            allowed_actions=get_allowed_retention_actions("Medium"),
        )

        self.assertEqual(
            result.protective_factors,
            [],
        )

        self.assertEqual(
            result.main_risk_signals,
            [
                (
                    "A característica 'total_transaction_count' contribuiu "
                    "para aumentar a previsão de churn do modelo."
                )
            ],
        )
    async def test_without_risk_factors_does_not_invent_evidence(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        ).model_copy(
            update={
                "risk_increasing_factors": [],
            }
        )

        fake_llama_response = {
            "case_summary": "Resumo inventado pela IA.",
            "risk_interpretation": "Interpretação inventada pela IA.",
            "main_risk_signals": [
                "Cliente apresenta sinais críticos de risco."
            ],
            "protective_factors": [
                "Fator protetor inventado pela IA."
            ],
            "recommended_action_id": "preventive_contact",
            "approach_guidance": "Orientação inventada pela IA.",
            "suggested_message": (
                "Olá! Gostaríamos de conversar sobre "
                "sua experiência conosco."
            ),
            "attention_points": [
                "Ponto inventado pela IA."
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
            priority_label="Atenção",
            allowed_actions=get_allowed_retention_actions("Medium"),
        )

        self.assertEqual(
            result.main_risk_signals,
            [],
        )

        self.assertEqual(
            result.protective_factors,
            [
                (
                    "A característica 'months_on_book' contribuiu para reduzir "
                    "a previsão de churn do modelo."
                )
            ],
        )

    async def test_without_shap_factors_does_not_invent_evidence(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        ).model_copy(
            update={
                "risk_increasing_factors": [],
                "risk_reducing_factors": [],
            }
        )

        fake_llama_response = {
            "case_summary": "Resumo inventado pela IA.",
            "risk_interpretation": "Interpretação inventada pela IA.",
            "main_risk_signals": [
                "Cliente possui sinais críticos de risco."
            ],
            "protective_factors": [
                "Cliente possui forte relacionamento."
            ],
            "recommended_action_id": "maintain_relationship",
            "approach_guidance": "Orientação inventada pela IA.",
            "suggested_message": (
                "Olá! Gostaríamos de conversar sobre "
                "sua experiência conosco."
            ),
            "attention_points": [
                "Ponto inventado pela IA."
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
            priority_label="Atenção",
            allowed_actions=get_allowed_retention_actions("Medium"),
        )

        self.assertEqual(
            result.main_risk_signals,
            [],
        )

        self.assertEqual(
            result.protective_factors,
            [],
        )

        self.assertEqual(
            result.recommended_action_id.value,
            "maintain_relationship",
        )

    async def test_ollama_unavailable_raises_domain_error(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        )

        service = RetentionAIService()

        service._client.chat = AsyncMock(
            side_effect=ConnectionError(
                "Ollama connection refused"
            )
        )

        with self.assertRaises(RetentionAIUnavailableError):
            await service.generate_recommendation(
                explainability=explainability,
                priority_label="Atenção",
                allowed_actions=get_allowed_retention_actions("Medium"),
            )

        service._client.chat.assert_awaited_once()

    async def test_ollama_timeout_raises_domain_error(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        )

        service = RetentionAIService()

        service._client.chat = AsyncMock(
            side_effect=httpx.ReadTimeout(
                "Ollama response timed out"
            )
        )

        with self.assertRaises(RetentionAITimeoutError):
            await service.generate_recommendation(
                explainability=explainability,
                priority_label="Atenção",
                allowed_actions=get_allowed_retention_actions("Medium"),
            )

        service._client.chat.assert_awaited_once()

    async def test_invalid_llama_response_raises_domain_error(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        )

        fake_ollama_response = SimpleNamespace(
            message=SimpleNamespace(
                content="isso definitivamente não é JSON"
            )
        )

        service = RetentionAIService()

        service._client.chat = AsyncMock(
            return_value=fake_ollama_response
        )

        with self.assertRaises(RetentionAIInvalidResponseError):
            await service.generate_recommendation(
                explainability=explainability,
                priority_label="Atenção",
                allowed_actions=get_allowed_retention_actions("Medium"),
            )

        service._client.chat.assert_awaited_once()

    async def test_incomplete_llama_response_raises_domain_error(self):
        explainability = self._build_explainability(
            churn_probability=0.35,
            risk_band="Medium",
        )

        incomplete_response = {
            "case_summary": "Resposta incompleta.",
            "recommended_action_id": "preventive_contact",
        }

        fake_ollama_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    incomplete_response,
                    ensure_ascii=False,
                )
            )
        )

        service = RetentionAIService()

        service._client.chat = AsyncMock(
            return_value=fake_ollama_response
        )

        with self.assertRaises(RetentionAIInvalidResponseError):
            await service.generate_recommendation(
                explainability=explainability,
                priority_label="Atenção",
                allowed_actions=get_allowed_retention_actions("Medium"),
            )

        service._client.chat.assert_awaited_once()