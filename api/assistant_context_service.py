from dataclasses import dataclass

from api.retention_ai_service import RetentionAIService
from api.retention_catalog import (
    RETENTION_ACTION_CATALOG,
    RetentionAction,
    get_allowed_retention_actions,
)
from api.schemas import (
    AssistantSourceResponse,
    AssistantSourceType,
    IndividualExplainabilityResponse,
    PortfolioSummaryResponse,
)


@dataclass(frozen=True)
class AssistantContextBundle:
    controlled_context: dict[str, object]
    sources: list[AssistantSourceResponse]


class AssistantContextService:
    @staticmethod
    def _serialize_action(
        action: RetentionAction,
    ) -> dict[str, object]:
        return {
            "action_id": action.action_id.value,
            "name": action.name,
            "description": action.description,
            "allowed_risk_bands": list(
                action.allowed_risk_bands
            ),
            "requires_human_review": (
                action.requires_human_review
            ),
        }

    @classmethod
    def build_customer_context(
        cls,
        explainability: IndividualExplainabilityResponse,
        priority_label: str,
    ) -> AssistantContextBundle:
        normalized_priority = priority_label.strip()

        if not normalized_priority:
            raise ValueError(
                "Customer context requires priority_label."
            )

        allowed_actions = get_allowed_retention_actions(
            explainability.risk_band.value
        )

        policy_action = (
            RetentionAIService._resolve_policy_action(
                explainability=explainability,
                priority_label=normalized_priority,
                allowed_actions=allowed_actions,
            )
        )

        risk_signals, protective_factors = (
            RetentionAIService._build_evidence_lists(
                explainability
            )
        )

        controlled_context = {
            "customer_id": explainability.customer_id,
            "churn_probability": (
                explainability.churn_probability
            ),
            "risk_band": explainability.risk_band.value,
            "priority_label": normalized_priority,
            "main_risk_signals": risk_signals,
            "protective_factors": protective_factors,
            "allowed_retention_actions": [
                cls._serialize_action(action)
                for action in allowed_actions
            ],
            "mandatory_policy_action_id": (
                policy_action.action_id.value
                if policy_action is not None
                else None
            ),
            "model": {
                "name": explainability.model_name,
                "alias": explainability.model_alias,
                "version": explainability.model_version,
                "run_id": explainability.run_id,
            },
        }

        sources = [
            AssistantSourceResponse(
                source_type=(
                    AssistantSourceType.customer_explainability
                ),
                label="Explicabilidade SHAP individual",
                reference=(
                    f"customer:{explainability.customer_id}:shap"
                ),
            ),
            AssistantSourceResponse(
                source_type=(
                    AssistantSourceType.retention_catalog
                ),
                label="Catálogo governado de retenção",
                reference="retention_catalog",
            ),
        ]

        if policy_action is not None:
            sources.append(
                AssistantSourceResponse(
                    source_type=(
                        AssistantSourceType.retention_policy
                    ),
                    label=(
                        "Política High + prioridade Alta/Crítica"
                    ),
                    reference="policy:high_priority_contact",
                )
            )

        return AssistantContextBundle(
            controlled_context=controlled_context,
            sources=sources,
        )

    @staticmethod
    def build_portfolio_context(
        summary: PortfolioSummaryResponse,
    ) -> AssistantContextBundle:
        controlled_context = {
            "total_customers": summary.total_customers,
            "predicted_churn_customers": (
                summary.predicted_churn_customers
            ),
            "predicted_churn_rate": (
                summary.predicted_churn_rate
            ),
            "average_churn_probability": (
                summary.average_churn_probability
            ),
            "risk_distribution": {
                "low": summary.low_risk_customers,
                "medium": summary.medium_risk_customers,
                "high": summary.high_risk_customers,
            },
            "model": {
                "minimum_version": (
                    summary.minimum_model_version
                ),
                "maximum_version": (
                    summary.maximum_model_version
                ),
                "alias": summary.model_alias,
            },
            "latest_scoring_at": (
                summary.latest_scoring_at.isoformat()
            ),
        }

        return AssistantContextBundle(
            controlled_context=controlled_context,
            sources=[
                AssistantSourceResponse(
                    source_type=(
                        AssistantSourceType.portfolio_summary
                    ),
                    label="Resumo atual da carteira",
                    reference="portfolio:latest_scoring",
                )
            ],
        )

    @classmethod
    def build_policy_context(
        cls,
    ) -> AssistantContextBundle:
        controlled_context = {
            "retention_actions": [
                cls._serialize_action(action)
                for action
                in RETENTION_ACTION_CATALOG.values()
            ],
            "mandatory_policies": [
                {
                    "conditions": {
                        "risk_band": "High",
                        "priority_labels": [
                            "Alta",
                            "Crítica",
                        ],
                    },
                    "required_action_id": (
                        "priority_retention_contact"
                    ),
                }
            ],
            "governance": {
                "llm_cannot_create_actions": True,
                "llm_cannot_execute_actions": True,
                "human_review_required": True,
                "shap_is_not_causality": True,
            },
        }

        return AssistantContextBundle(
            controlled_context=controlled_context,
            sources=[
                AssistantSourceResponse(
                    source_type=(
                        AssistantSourceType.retention_catalog
                    ),
                    label="Catálogo governado de retenção",
                    reference="retention_catalog",
                ),
                AssistantSourceResponse(
                    source_type=(
                        AssistantSourceType.retention_policy
                    ),
                    label=(
                        "Política High + prioridade Alta/Crítica"
                    ),
                    reference="policy:high_priority_contact",
                ),
            ],
        )