import json
import unittest


from api.assistant_context_service import (
    AssistantContextService,
)
from api.schemas import (
    AssistantSourceType,
    IndividualExplainabilityResponse,
    PortfolioSummaryResponse,
)


class AssistantContextServiceTests(unittest.TestCase):
    @staticmethod
    def _build_explainability(
        risk_band: str = "High",
    ) -> IndividualExplainabilityResponse:
        return IndividualExplainabilityResponse.model_validate(
            {
                "customer_id": 809849358,
                "churn_probability": 0.99,
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
                        "feature": "customer_age",
                        "value": 55,
                        "shap_value": 1.5,
                        "absolute_shap": 1.5,
                        "importance_share": 0.50,
                        "impact_direction": "increases_risk",
                    },
                    {
                        "feature": "total_transaction_count",
                        "value": 20,
                        "shap_value": 1.2,
                        "absolute_shap": 1.2,
                        "importance_share": 0.40,
                        "impact_direction": "increases_risk",
                    },
                ],
                "risk_reducing_factors": [
                    {
                        "feature": "gender",
                        "value": "F",
                        "shap_value": -0.8,
                        "absolute_shap": 0.8,
                        "importance_share": 0.30,
                        "impact_direction": "reduces_risk",
                    },
                    {
                        "feature": "months_on_book",
                        "value": 48,
                        "shap_value": -0.6,
                        "absolute_shap": 0.6,
                        "importance_share": 0.20,
                        "impact_direction": "reduces_risk",
                    },
                ],
            }
        )

    def test_customer_context_uses_governed_evidence(
        self,
    ) -> None:
        bundle = (
            AssistantContextService.build_customer_context(
                explainability=self._build_explainability(),
                priority_label="Alta",
            )
        )

        context = bundle.controlled_context

        self.assertEqual(
            context["main_risk_signals"],
            [
                "Quantidade de transações: 20 transações.",
            ],
        )
        self.assertEqual(
            context["protective_factors"],
            [
                "Tempo como cliente: 48 meses.",
            ],
        )
        self.assertEqual(
            context["mandatory_policy_action_id"],
            "priority_retention_contact",
        )

        serialized_context = json.dumps(
            context,
            ensure_ascii=False,
        )

        self.assertNotIn(
            "customer_age",
            serialized_context,
        )
        self.assertNotIn(
            "gender",
            serialized_context,
        )
        self.assertNotIn(
            "Idade do cliente",
            serialized_context,
        )
        self.assertNotIn(
            "Gênero",
            serialized_context,
        )

        source_types = {
            source.source_type
            for source in bundle.sources
        }

        self.assertEqual(
            source_types,
            {
                AssistantSourceType.customer_explainability,
                AssistantSourceType.retention_catalog,
                AssistantSourceType.retention_policy,
            },
        )

    def test_customer_context_does_not_force_policy_for_attention(
        self,
    ) -> None:
        bundle = (
            AssistantContextService.build_customer_context(
                explainability=self._build_explainability(),
                priority_label="Atenção",
            )
        )

        self.assertIsNone(
            bundle.controlled_context[
                "mandatory_policy_action_id"
            ]
        )

        source_types = {
            source.source_type
            for source in bundle.sources
        }

        self.assertNotIn(
            AssistantSourceType.retention_policy,
            source_types,
        )

    def test_customer_context_rejects_blank_priority(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            AssistantContextService.build_customer_context(
                explainability=self._build_explainability(),
                priority_label="   ",
            )

    def test_portfolio_context_contains_aggregated_data(
        self,
    ) -> None:
        summary = PortfolioSummaryResponse.model_validate(
            {
                "total_customers": 10127,
                "predicted_churn_customers": 1627,
                "predicted_churn_rate": 0.1607,
                "average_churn_probability": 0.22,
                "low_risk_customers": 7000,
                "medium_risk_customers": 1500,
                "high_risk_customers": 1627,
                "minimum_model_version": 3,
                "maximum_model_version": 3,
                "model_alias": "champion",
                "latest_scoring_at": (
                    "2026-08-29T12:00:00Z"
                ),
            }
        )

        bundle = (
            AssistantContextService.build_portfolio_context(
                summary
            )
        )

        self.assertEqual(
            bundle.controlled_context[
                "risk_distribution"
            ],
            {
                "low": 7000,
                "medium": 1500,
                "high": 1627,
            },
        )
        self.assertEqual(
            len(bundle.sources),
            1,
        )
        self.assertEqual(
            bundle.sources[0].source_type,
            AssistantSourceType.portfolio_summary,
        )

    def test_policy_context_uses_authorized_catalog(
        self,
    ) -> None:
        bundle = (
            AssistantContextService.build_policy_context()
        )

        context = bundle.controlled_context
        actions = context["retention_actions"]

        self.assertEqual(
            len(actions),
            5,
        )
        self.assertTrue(
            all(
                action["requires_human_review"]
                for action in actions
            )
        )
        self.assertEqual(
            context["mandatory_policies"][0][
                "required_action_id"
            ],
            "priority_retention_contact",
        )
        self.assertTrue(
            context["governance"][
                "human_review_required"
            ]
        )


if __name__ == "__main__":
    unittest.main()