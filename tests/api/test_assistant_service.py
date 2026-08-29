from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from api.assistant_service import (
    AssistantContextUnavailableError,
    AssistantCustomerNotFoundError,
    AssistantService,
)
from api.schemas import (
    AssistantGeneratedContent,
    AssistantQueryRequest,
    AssistantScope,
    AssistantSourceType,
)


class AssistantServiceTests(IsolatedAsyncioTestCase):
    @staticmethod
    def _customer() -> dict[str, object]:
        return {
            "customer_id": 809849358,
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
            "churn_probability": 0.99,
            "risk_band": "High",
            "priority_label": "Alta",
        }

    @staticmethod
    def _model_service() -> Mock:
        model_service = Mock()

        model_service.get_individual_explainability.return_value = {
            "churn_probability": 0.99,
            "churn_prediction": 1,
            "prediction_label": "churn",
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
                    "value": 36,
                    "shap_value": 1.2,
                    "absolute_shap": 1.2,
                    "importance_share": 0.40,
                    "impact_direction": "increases_risk",
                }
            ],
            "risk_reducing_factors": [],
        }

        return model_service

    @staticmethod
    def _ai_service() -> AsyncMock:
        ai_service = AsyncMock()

        ai_service.generate_answer.return_value = (
            AssistantGeneratedContent(
                answer=(
                    "O contexto disponível indica necessidade "
                    "de análise humana prioritária."
                )
            )
        )

        return ai_service

    async def test_customer_query_builds_governed_response(
        self,
    ) -> None:
        model_service = self._model_service()
        ai_service = self._ai_service()

        service = AssistantService(
            model_service=model_service,
            ai_service=ai_service,
        )

        query = AssistantQueryRequest(
            question="Por que este cliente exige atenção?",
            scope=AssistantScope.customer,
            customer_id=809849358,
        )

        with patch(
            "api.assistant_service.get_customer_by_id",
            return_value=self._customer(),
        ):
            response = await service.generate_response(
                query
            )

        self.assertEqual(
            response.customer_id,
            809849358,
        )
        self.assertTrue(
            response.requires_human_review
        )

        source_types = {
            source.source_type
            for source in response.sources
        }

        self.assertEqual(
            source_types,
            {
                AssistantSourceType.customer_explainability,
                AssistantSourceType.retention_catalog,
                AssistantSourceType.retention_policy,
            },
        )

        call_kwargs = (
            ai_service.generate_answer.await_args.kwargs
        )
        controlled_context = call_kwargs[
            "controlled_context"
        ]

        self.assertEqual(
            controlled_context[
                "mandatory_policy_action_id"
            ],
            "priority_retention_contact",
        )

    async def test_customer_query_raises_when_not_found(
        self,
    ) -> None:
        service = AssistantService(
            model_service=self._model_service(),
            ai_service=self._ai_service(),
        )

        query = AssistantQueryRequest(
            question="Analise este cliente.",
            scope=AssistantScope.customer,
            customer_id=809849358,
        )

        with (
            patch(
                "api.assistant_service.get_customer_by_id",
                return_value=None,
            ),
            self.assertRaises(
                AssistantCustomerNotFoundError
            ),
        ):
            await service.generate_response(query)

    async def test_customer_query_raises_without_scoring(
        self,
    ) -> None:
        customer = self._customer()
        customer["churn_probability"] = None

        service = AssistantService(
            model_service=self._model_service(),
            ai_service=self._ai_service(),
        )

        query = AssistantQueryRequest(
            question="Analise este cliente.",
            scope=AssistantScope.customer,
            customer_id=809849358,
        )

        with (
            patch(
                "api.assistant_service.get_customer_by_id",
                return_value=customer,
            ),
            self.assertRaises(
                AssistantContextUnavailableError
            ),
        ):
            await service.generate_response(query)

    async def test_customer_query_raises_without_priority(
        self,
    ) -> None:
        customer = self._customer()
        customer["priority_label"] = None

        service = AssistantService(
            model_service=self._model_service(),
            ai_service=self._ai_service(),
        )

        query = AssistantQueryRequest(
            question="Analise este cliente.",
            scope=AssistantScope.customer,
            customer_id=809849358,
        )

        with (
            patch(
                "api.assistant_service.get_customer_by_id",
                return_value=customer,
            ),
            self.assertRaises(
                AssistantContextUnavailableError
            ),
        ):
            await service.generate_response(query)

    async def test_portfolio_query_uses_aggregated_summary(
        self,
    ) -> None:
        model_service = self._model_service()
        ai_service = self._ai_service()

        service = AssistantService(
            model_service=model_service,
            ai_service=ai_service,
        )

        query = AssistantQueryRequest(
            question="Resuma a carteira atual.",
            scope=AssistantScope.portfolio,
        )

        summary_data = {
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

        with patch(
            "api.assistant_service.get_portfolio_summary",
            return_value=summary_data,
        ):
            response = await service.generate_response(
                query
            )

        self.assertIsNone(
            response.customer_id
        )
        self.assertEqual(
            response.sources[0].source_type,
            AssistantSourceType.portfolio_summary,
        )

        model_service.get_individual_explainability\
            .assert_not_called()

        controlled_context = (
            ai_service.generate_answer
            .await_args.kwargs[
                "controlled_context"
            ]
        )

        self.assertEqual(
            controlled_context["total_customers"],
            10127,
        )

    async def test_policy_query_uses_authorized_catalog(
        self,
    ) -> None:
        model_service = self._model_service()
        ai_service = self._ai_service()

        service = AssistantService(
            model_service=model_service,
            ai_service=ai_service,
        )

        query = AssistantQueryRequest(
            question=(
                "Qual política exige contato prioritário?"
            ),
            scope=AssistantScope.policy,
        )

        with (
            patch(
                "api.assistant_service.get_customer_by_id"
            ) as customer_repository,
            patch(
                "api.assistant_service.get_portfolio_summary"
            ) as portfolio_repository,
        ):
            response = await service.generate_response(
                query
            )

        customer_repository.assert_not_called()
        portfolio_repository.assert_not_called()
        model_service.get_individual_explainability\
            .assert_not_called()

        source_types = {
            source.source_type
            for source in response.sources
        }

        self.assertEqual(
            source_types,
            {
                AssistantSourceType.retention_catalog,
                AssistantSourceType.retention_policy,
            },
        )

        controlled_context = (
            ai_service.generate_answer
            .await_args.kwargs[
                "controlled_context"
            ]
        )

        self.assertEqual(
            len(
                controlled_context[
                    "retention_actions"
                ]
            ),
            5,
        )

    async def test_close_closes_ai_service(
        self,
    ) -> None:
        ai_service = self._ai_service()

        service = AssistantService(
            model_service=self._model_service(),
            ai_service=ai_service,
        )

        await service.close()

        ai_service.close.assert_awaited_once()