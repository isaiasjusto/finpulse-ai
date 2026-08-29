from datetime import datetime, timezone

import pandas as pd

from api.assistant_ai_service import AssistantAIService
from api.assistant_context_service import (
    AssistantContextBundle,
    AssistantContextService,
)
from api.config import settings
from api.customer_repository import get_customer_by_id
from api.model_service import ModelService
from api.portfolio_repository import get_portfolio_summary
from api.schemas import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantScope,
    IndividualExplainabilityResponse,
    PortfolioSummaryResponse,
    PredictionRequest,
    RecommendationGenerationResponse,
    RiskBand,
)


MODEL_FEATURE_NAMES = tuple(
    PredictionRequest.model_fields
)


class AssistantCustomerNotFoundError(RuntimeError):
    """Raised when the requested customer does not exist."""


class AssistantContextUnavailableError(RuntimeError):
    """Raised when required governed context is unavailable."""


class AssistantService:
    def __init__(
        self,
        model_service: ModelService,
        ai_service: AssistantAIService | None = None,
    ) -> None:
        self._model_service = model_service
        self._ai_service = (
            ai_service
            if ai_service is not None
            else AssistantAIService()
        )

    def _build_customer_context(
        self,
        customer_id: int,
    ) -> AssistantContextBundle:
        customer = get_customer_by_id(customer_id)

        if customer is None:
            raise AssistantCustomerNotFoundError(
                f"Customer {customer_id} was not found."
            )

        if (
            customer["churn_prediction"] is None
            or customer["churn_probability"] is None
            or customer["risk_band"] is None
        ):
            raise AssistantContextUnavailableError(
                (
                    f"Customer {customer_id} does not have "
                    "a stored scoring result."
                )
            )

        if customer["priority_label"] is None:
            raise AssistantContextUnavailableError(
                (
                    f"Customer {customer_id} does not have "
                    "a retention priority."
                )
            )

        features_data = {
            feature_name: customer[feature_name]
            for feature_name in MODEL_FEATURE_NAMES
        }

        validated_features = PredictionRequest(
            **features_data
        )

        model_input = pd.DataFrame(
            [
                validated_features.model_dump()
            ]
        )

        explainability_data = (
            self._model_service
            .get_individual_explainability(
                model_input
            )
        )

        explainability = (
            IndividualExplainabilityResponse(
                customer_id=customer_id,
                risk_band=RiskBand(
                    str(customer["risk_band"])
                ),
                **explainability_data,
            )
        )

        return (
            AssistantContextService
            .build_customer_context(
                explainability=explainability,
                priority_label=str(
                    customer["priority_label"]
                ),
            )
        )

    @staticmethod
    def _build_portfolio_context(
    ) -> AssistantContextBundle:
        summary_data = get_portfolio_summary()

        summary = PortfolioSummaryResponse(
            **summary_data
        )

        return (
            AssistantContextService
            .build_portfolio_context(
                summary
            )
        )

    @staticmethod
    def _build_policy_context(
    ) -> AssistantContextBundle:
        return (
            AssistantContextService
            .build_policy_context()
        )

    def _build_context(
        self,
        query: AssistantQueryRequest,
    ) -> AssistantContextBundle:
        if query.scope == AssistantScope.customer:
            if query.customer_id is None:
                raise AssistantContextUnavailableError(
                    "Customer scope requires customer_id."
                )

            return self._build_customer_context(
                query.customer_id
            )

        if query.scope == AssistantScope.portfolio:
            return self._build_portfolio_context()

        return self._build_policy_context()

    async def generate_response(
        self,
        query: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        context_bundle = self._build_context(
            query
        )

        generated_content = (
            await self._ai_service.generate_answer(
                query=query,
                controlled_context=(
                    context_bundle.controlled_context
                ),
                sources=context_bundle.sources,
            )
        )

        return AssistantQueryResponse(
            scope=query.scope,
            answer=generated_content.answer,
            customer_id=query.customer_id,
            sources=context_bundle.sources,
            requires_human_review=True,
            generation=RecommendationGenerationResponse(
                provider="ollama",
                model=settings.ollama_model,
                generated_at=datetime.now(
                    timezone.utc
                ),
            ),
        )

    async def close(self) -> None:
        await self._ai_service.close()