import json

from ollama import AsyncClient

from api.config import settings
from api.retention_catalog import RetentionAction
from api.schemas import (
    IndividualExplainabilityResponse,
    RetentionRecommendationContent,
)


class RetentionAIService:
    def __init__(self) -> None:
        self._client = AsyncClient(
            host=settings.ollama_host,
            timeout=settings.ollama_timeout_seconds,
        )

    @staticmethod
    def _build_evidence_lists(
        explainability: IndividualExplainabilityResponse,
    ) -> tuple[list[str], list[str]]:
        risk_signals = [
            (
                f"A característica '{factor.feature}' contribuiu para aumentar "
                "a previsão de churn do modelo."
            )
            for factor in explainability.risk_increasing_factors[:5]
        ]

        protective_factors = [
            (
                f"A característica '{factor.feature}' contribuiu para reduzir "
                "a previsão de churn do modelo."
            )
            for factor in explainability.risk_reducing_factors[:5]
        ]

        return risk_signals, protective_factors


    @staticmethod
    def _build_messages(
        explainability: IndividualExplainabilityResponse,
        priority_label: str,
        allowed_actions: list[RetentionAction],
    ) -> list[dict[str, str]]:
        risk_factors = [
            {
                "feature": factor.feature,
                "observed_value": factor.value,
                "model_effect": "increases_risk",
                "evidence_statement": (
                    f"The feature '{factor.feature}' contributed to increasing "
                    "the model prediction for churn."
                ),
                "qualitative_value_interpretation": None,
            }
            for factor in explainability.risk_increasing_factors[:5]
        ]

        protective_factors = [
            {
                "feature": factor.feature,
                "observed_value": factor.value,
                "model_effect": "reduces_risk",
                "evidence_statement": (
                    f"The feature '{factor.feature}' contributed to reducing "
                    "the model prediction for churn."
                ),
                "qualitative_value_interpretation": None,
            }
            for factor in explainability.risk_reducing_factors[:5]
        ]

        actions = [
            {
                "action_id": action.action_id.value,
                "name": action.name,
                "requires_human_review": action.requires_human_review,
            }
            for action in allowed_actions
        ]

        controlled_context = {
            "churn_probability": explainability.churn_probability,
            "risk_band": explainability.risk_band.value,
            "priority_label": priority_label,
            "main_risk_factors": risk_factors,
            "protective_factors": protective_factors,
            "allowed_retention_actions": actions,
        }

        system_message = (
            "You are the retention analysis assistant for FinPulse AI. "
            "Respond in Brazilian Portuguese. "
            "Interpret only the supplied evidence. "
            "Do not recalculate or modify the churn probability. "
            "Do not invent customer facts. "
            "Treat SHAP values only as model contribution signals, not as causal evidence. "
            "Do not describe a raw feature value as high, low, elevated, reduced, "
            "good, or bad unless that interpretation is explicitly provided in the context. "
            "Do not infer qualitative labels such as high, low, long, short, "
            "elevated, reduced, strong, or weak from raw feature values unless "
            "that interpretation is explicitly provided. "
            "Do not infer that the number of supplied risk or protective factors "
            "represents the total number of factors for the customer. "
            "Treat allowed_retention_actions only as policy options. "
            "Their names and descriptions are not evidence about the customer "
            "and must not be used to infer customer conditions or characteristics. "
            "Use only the supplied risk and protective factors when describing "
            "customer-specific signals or attention points. "
            "Describe feature names in clear Brazilian Portuguese when writing "
            "main_risk_signals and protective_factors, while preserving their meaning. "
            "Choose exactly one recommended_action_id from the "
            "allowed_retention_actions provided. "
            "Do not grant or promise credit, discounts, benefits, "
            "financial conditions, or automatic decisions. "
            "The suggested_message must be written directly to the customer "
            "in a polite and consultative tone, without mentioning churn, risk scores, "
            "SHAP, internal priority, or model predictions. "
            "The attention_points field is for internal human-review considerations. "
            "All recommendations require human review."
            "Do not use the raw observed value in main_risk_signals or protective_factors "
            "unless it is necessary for factual context. Never attach a qualitative "
            "interpretation to that value unless explicitly supplied. "
        )

        user_message = (
            "Generate a retention recommendation using only this "
            "controlled context:\n"
            + json.dumps(
                controlled_context,
                ensure_ascii=False,
            )
        )

        return [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

    async def generate_recommendation(
        self,
        explainability: IndividualExplainabilityResponse,
        priority_label: str,
        allowed_actions: list[RetentionAction],
    ) -> RetentionRecommendationContent:
        messages = self._build_messages(
            explainability=explainability,
            priority_label=priority_label,
            allowed_actions=allowed_actions,
        )

        response = await self._client.chat(
            model=settings.ollama_model,
            messages=messages,
            format=RetentionRecommendationContent.model_json_schema(),
            options={
                        "temperature": 0,
                    },
        )

        return RetentionRecommendationContent.model_validate_json(
            response.message.content
        )

    async def close(self) -> None:
        await self._client.close()