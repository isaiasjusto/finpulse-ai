import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import api.main as main
from api.retention_catalog import RetentionActionId
from api.schemas import RetentionRecommendationContent

from api.retention_ai_service import (
    RetentionAIInvalidResponseError,
    RetentionAITimeoutError,
    RetentionAIUnavailableError,
)

CUSTOMER_ID = 809849358


class FakeModelService:
    is_loaded = True

    def get_individual_explainability(
        self,
        model_input,
    ) -> dict[str, object]:
        return {
            "churn_probability": 0.9999282856387735,
            "churn_prediction": 1,
            "prediction_label": "churn",
            "model_name": "finpulse-churn-catboost",
            "model_alias": "champion",
            "model_version": 3,
            "run_id": "test-run-id",
            "input_feature_count": 19,
            "transformed_feature_count": 37,
            "base_value": -4.83,
            "features": [],
            "risk_increasing_factors": [],
            "risk_reducing_factors": [],
        }


def fake_customer() -> dict[str, object]:
    return {
        "customer_id": CUSTOMER_ID,
        "customer_age": 55,
        "gender": "F",
        "dependent_count": 2,
        "education_level": "Graduate",
        "marital_status": "Married",
        "income_category": "$40K - $60K",
        "card_category": "Blue",
        "months_on_book": 36,
        "total_relationship_count": 2,
        "months_inactive_last_12m": 3,
        "contacts_count_last_12m": 3,
        "credit_limit": 5000.0,
        "total_revolving_balance": 0.0,
        "average_open_to_buy": 5000.0,
        "amount_change_q4_q1": 0.7,
        "total_transaction_amount": 2719.0,
        "total_transaction_count": 36,
        "transaction_count_change_q4_q1": 0.44,
        "average_utilization_ratio": 0.0,
        "churn_prediction": 1,
        "churn_probability": 0.9999282856387735,
        "risk_band": "High",
        "priority_label": "Alta",
    }


def fake_recommendation() -> RetentionRecommendationContent:
    return RetentionRecommendationContent(
        case_summary="Resumo controlado para teste.",
        risk_interpretation="Interpretação controlada para teste.",
        main_risk_signals=[],
        protective_factors=[],
        recommended_action_id=(
            RetentionActionId.PRIORITY_RETENTION_CONTACT
        ),
        approach_guidance="Contato humano prioritário.",
        suggested_message="Olá! Podemos conversar?",
        attention_points=["Revisão humana obrigatória."],
    )


class RetentionRecommendationEndpointTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        main.app.state.model_service = FakeModelService()
        main.app.state.model_load_error = None
        self.client = TestClient(main.app)

    def test_retention_recommendation_returns_200(
        self,
    ) -> None:
        service = AsyncMock()
        service.generate_recommendation.return_value = (
            fake_recommendation()
        )

        with (
            patch.object(
                main,
                "get_customer_by_id",
                return_value=fake_customer(),
            ),
            patch.object(
                main,
                "RetentionAIService",
                return_value=service,
            ),
        ):
            response = self.client.post(
                (
                    f"/customers/{CUSTOMER_ID}"
                    "/retention-recommendation"
                )
            )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            data["customer_id"],
            CUSTOMER_ID,
        )
        self.assertEqual(
            data["risk_band"],
            "High",
        )
        self.assertEqual(
            data["priority_label"],
            "Alta",
        )
        self.assertEqual(
            data["recommendation"][
                "recommended_action_id"
            ],
            "priority_retention_contact",
        )
        self.assertEqual(
            data["generation"]["provider"],
            "ollama",
        )
        self.assertEqual(
            data["generation"]["model"],
            "llama3.1:8b",
        )

        service.close.assert_awaited_once()

    def test_retention_recommendation_returns_503_when_ai_unavailable(
        self,
        ) -> None:
        service = AsyncMock()

        service.generate_recommendation.side_effect = (
            RetentionAIUnavailableError(
                "Simulated unavailable AI service."
            )
        )

        with (
            patch.object(
                main,
                "get_customer_by_id",
                return_value=fake_customer(),
            ),
            patch.object(
                main,
                "RetentionAIService",
                return_value=service,
            ),
        ):
            response = self.client.post(
                (
                    f"/customers/{CUSTOMER_ID}"
                    "/retention-recommendation"
                )
            )

        self.assertEqual(
            response.status_code,
            503,
        )

        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "Retention AI service is unavailable."
                )
            },
        )

        service.close.assert_awaited_once()


    def test_retention_recommendation_returns_504_on_timeout(
    self,
) -> None:
        service = AsyncMock()

        service.generate_recommendation.side_effect = (
            RetentionAITimeoutError(
                "Simulated AI timeout."
            )
        )

        with (
            patch.object(
                main,
                "get_customer_by_id",
                return_value=fake_customer(),
            ),
            patch.object(
                main,
                "RetentionAIService",
                return_value=service,
            ),
        ):
            response = self.client.post(
                (
                    f"/customers/{CUSTOMER_ID}"
                    "/retention-recommendation"
                )
            )

        self.assertEqual(
            response.status_code,
            504,
        )

        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "Retention AI service timed out."
                )
            },
        )

        service.close.assert_awaited_once()

    def test_retention_recommendation_returns_502_on_invalid_ai_response(
    self,
) -> None:
        service = AsyncMock()

        service.generate_recommendation.side_effect = (
            RetentionAIInvalidResponseError(
                "Simulated invalid AI response."
            )
        )

        with (
            patch.object(
                main,
                "get_customer_by_id",
                return_value=fake_customer(),
            ),
            patch.object(
                main,
                "RetentionAIService",
                return_value=service,
            ),
        ):
            response = self.client.post(
                (
                    f"/customers/{CUSTOMER_ID}"
                    "/retention-recommendation"
                )
            )

        self.assertEqual(
            response.status_code,
            502,
        )

        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "Retention AI returned an invalid response."
                )
            },
        )

        service.close.assert_awaited_once()

if __name__ == "__main__":
    unittest.main()