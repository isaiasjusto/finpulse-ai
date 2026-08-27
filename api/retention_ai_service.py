import json

import httpx
from ollama import AsyncClient


from api.config import settings
from api.retention_catalog import (
    RetentionAction,
    get_retention_action,
    is_retention_action_allowed,
)
from api.schemas import (
    IndividualExplainabilityResponse,
    RetentionRecommendationContent,
)
from api.retention_catalog import (
    RetentionAction,
    RetentionActionId,
    get_retention_action,
    is_retention_action_allowed,
)

from pydantic import ValidationError

RISK_BAND_LABELS = {
    "Low": "baixo risco",
    "Medium": "médio risco",
    "High": "alto risco",
}

FEATURE_LABELS = {
    "customer_age": "Idade do cliente",
    "gender": "Gênero",
    "dependent_count": "Número de dependentes",
    "education_level": "Escolaridade",
    "marital_status": "Estado civil",
    "income_category": "Faixa de renda",
    "card_category": "Categoria do cartão",
    "months_on_book": "Tempo como cliente",
    "total_relationship_count": "Produtos contratados",
    "months_inactive_last_12m": "Meses de inatividade",
    "contacts_count_last_12m": "Contatos nos últimos 12 meses",
    "credit_limit": "Limite de crédito",
    "total_revolving_balance": "Saldo rotativo",
    "average_open_to_buy": "Crédito disponível",
    "amount_change_q4_q1": "Variação do valor transacionado",
    "total_transaction_amount": "Valor total transacionado",
    "total_transaction_count": "Quantidade de transações",
    "transaction_count_change_q4_q1": (
        "Variação da quantidade de transações"
    ),
    "average_utilization_ratio": "Utilização média do limite",
}

CATEGORICAL_LABELS = {
    "gender": {
        "M": "Masculino",
        "F": "Feminino",
    },
    "education_level": {
        "Uneducated": "Sem escolaridade formal",
        "High School": "Ensino médio",
        "College": "Ensino superior incompleto",
        "Graduate": "Graduado",
        "Post-Graduate": "Pós-graduado",
        "Doctorate": "Doutorado",
        "Unknown": "Não informado",
    },
    "marital_status": {
        "Married": "Casado(a)",
        "Single": "Solteiro(a)",
        "Divorced": "Divorciado(a)",
        "Unknown": "Não informado",
    },
    "income_category": {
        "Less than $40K": "Menos de US$ 40 mil",
        "$40K - $60K": "De US$ 40 mil a US$ 60 mil",
        "$60K - $80K": "De US$ 60 mil a US$ 80 mil",
        "$80K - $120K": "De US$ 80 mil a US$ 120 mil",
        "$120K +": "Acima de US$ 120 mil",
        "Unknown": "Não informado",
    },
    "card_category": {
        "Blue": "Azul",
        "Silver": "Prata",
        "Gold": "Ouro",
        "Platinum": "Platina",
    },
}

CURRENCY_FEATURES = {
    "credit_limit",
    "total_revolving_balance",
    "average_open_to_buy",
    "total_transaction_amount",
}

RATIO_CHANGE_FEATURES = {
    "amount_change_q4_q1",
    "transaction_count_change_q4_q1",
}

NON_ACTIONABLE_RETENTION_FEATURES = {
    "customer_age",
    "gender",
    "dependent_count",
    "education_level",
    "marital_status",
    "income_category",
}

class RetentionAIUnavailableError(RuntimeError):
    """Raised when the local retention LLM service is unavailable."""

class RetentionAITimeoutError(RuntimeError):
    """Raised when the local retention LLM exceeds its timeout."""

class RetentionAIInvalidResponseError(RuntimeError):
    """Raised when the local retention LLM returns an invalid response."""

class RetentionAIService:
    def __init__(self) -> None:
        self._client = AsyncClient(
            host=settings.ollama_host,
            timeout=settings.ollama_timeout_seconds,
        )

    @staticmethod
    def _resolve_policy_action(
        explainability: IndividualExplainabilityResponse,
        priority_label: str,
        allowed_actions: list[RetentionAction],
    ) -> RetentionAction | None:
        normalized_priority = priority_label.strip().casefold()

        requires_priority_contact = (
            explainability.risk_band.value == "High"
            and normalized_priority
            in {
                "alta",
                "crítica",
                "critica",
            }
        )

        if not requires_priority_contact:
            return None

        return next(
            (
                action
                for action in allowed_actions
                if action.action_id
                == RetentionActionId.PRIORITY_RETENTION_CONTACT
            ),
            None,
        )

    @staticmethod
    def _format_number(value: float) -> str:
        return (
            f"{value:,.2f}"
            .replace(",", "TEMP")
            .replace(".", ",")
            .replace("TEMP", ".")
        )

    @classmethod
    def _format_factor_value(
        cls,
        feature: str,
        value: str | int | float,
    ) -> str:
        categorical_values = CATEGORICAL_LABELS.get(feature)

        if categorical_values is not None:
            return categorical_values.get(str(value), str(value))

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return str(value)

        if feature in CURRENCY_FEATURES:
            return f"R$ {cls._format_number(numeric_value)}"

        if feature in RATIO_CHANGE_FEATURES:
            percentage_change = (numeric_value - 1) * 100

            if abs(percentage_change) < 0.005:
                return "sem variação do 1º para o 4º trimestre"

            direction = (
                "aumento"
                if percentage_change > 0
                else "queda"
            )

            formatted_change = cls._format_number(
                abs(percentage_change)
            )

            return (
                f"{direction} de {formatted_change}% "
                "do 1º para o 4º trimestre"
            )

        if feature == "average_utilization_ratio":
            utilization = cls._format_number(
                numeric_value * 100
            )
            return f"{utilization}% do limite"

        integer_suffixes = {
            "customer_age": " anos",
            "dependent_count": " dependentes",
            "months_on_book": " meses",
            "total_relationship_count": " produtos",
            "months_inactive_last_12m": " meses",
            "contacts_count_last_12m": " contatos",
            "total_transaction_count": " transações",
        }

        if feature in integer_suffixes:
            return (
                f"{int(round(numeric_value))}"
                f"{integer_suffixes[feature]}"
            )

        return cls._format_number(numeric_value)

    @classmethod
    def _describe_factor(
        cls,
        feature: str,
        value: str | int | float,
    ) -> str:
        feature_label = FEATURE_LABELS.get(
            feature,
            feature.replace("_", " ").capitalize(),
        )

        formatted_value = cls._format_factor_value(
            feature,
            value,
        )

        return f"{feature_label}: {formatted_value}."

    @classmethod
    def _build_system_content(
        cls,
        explainability: IndividualExplainabilityResponse,
    ) -> dict[str, object]:
        probability = (
            f"{explainability.churn_probability:.2%}"
            .replace(".", ",")
        )

        risk_band = RISK_BAND_LABELS.get(
            explainability.risk_band.value,
            explainability.risk_band.value,
        )

        risk_signals, _ = cls._build_evidence_lists(
            explainability
        )

        case_summary = (
            f"Cliente classificado em {risk_band}, "
            f"com probabilidade de churn de {probability}."
        )

        if risk_signals:
            case_summary += (
                " Principal sinal identificado — "
                f"{risk_signals[0]}"
            )

        return {
            "case_summary": case_summary,
            "risk_interpretation": (
                "Os sinais abaixo mostram como as características "
                "observadas influenciaram a estimativa deste cliente. "
                "Essas contribuições não estabelecem relações de "
                "causa e efeito."
            ),
            "attention_points": [
                (
                    "A recomendação deve ser revisada por uma pessoa "
                    "antes de qualquer ação."
                ),
                (
                    "As contribuições do modelo não representam "
                    "relações causais."
                ),
            ],
        }

    @classmethod
    @classmethod
    def _build_evidence_lists(
        cls,
        explainability: IndividualExplainabilityResponse,
    ) -> tuple[list[str], list[str]]:
        actionable_risk_factors = [
            factor
            for factor in explainability.risk_increasing_factors
            if factor.feature
            not in NON_ACTIONABLE_RETENTION_FEATURES
        ][:5]

        actionable_protective_factors = [
            factor
            for factor in explainability.risk_reducing_factors
            if factor.feature
            not in NON_ACTIONABLE_RETENTION_FEATURES
        ][:5]

        risk_signals = [
            cls._describe_factor(
                factor.feature,
                factor.value,
            )
            for factor in actionable_risk_factors
        ]

        protective_factors = [
            cls._describe_factor(
                factor.feature,
                factor.value,
            )
            for factor in actionable_protective_factors
        ]

        return risk_signals, protective_factors


    @classmethod
    def _build_messages(
        cls,
        explainability: IndividualExplainabilityResponse,
        priority_label: str,
        allowed_actions: list[RetentionAction],
    ) -> list[dict[str, str]]:
        risk_signals, protective_factors = (
            cls._build_evidence_lists(explainability)
        )

        actions = [
            {
                "action_id": action.action_id.value,
                "name": action.name,
                "description": action.description,
                "requires_human_review": (
                    action.requires_human_review
                ),
            }
            for action in allowed_actions
        ]

        controlled_context = {
            "churn_probability": explainability.churn_probability,
            "risk_band": explainability.risk_band.value,
            "priority_label": priority_label,
            "main_risk_signals": risk_signals,
            "protective_factors": protective_factors,
            "allowed_retention_actions": actions,
        }

        system_message = (
            "You are the retention analysis assistant for FinPulse AI. "
            "Respond in Brazilian Portuguese. "
            "Use exclusively the controlled context provided. "
            "Do not recalculate, reinterpret, or modify the churn "
            "probability, risk band, or operational priority. "
            "Do not invent customer facts, needs, difficulties, intentions, "
            "preferences, or financial conditions. "
            "Treat the supplied risk and protective factors only as model "
            "contribution signals, never as causal evidence. "
            "The items in main_risk_signals and protective_factors are "
            "controlled evidence already translated and formatted. "
            "Do not add new factors or infer qualitative descriptions such "
            "as high, low, elevated, reduced, strong, weak, good, or bad. "
            "Do not infer that the number of supplied factors represents "
            "the complete set of factors for the customer. "
            "Treat allowed_retention_actions exclusively as policy options. "
            "Their names and descriptions are not evidence about the "
            "customer and must not be used to infer customer conditions. "
            "Choose exactly one recommended_action_id from the supplied "
            "allowed_retention_actions. "
            "The approach_guidance field must guide the human analyst in "
            "performing the selected action in a consultative manner. "
            "Do not grant or promise credit, discounts, benefits, special "
            "conditions, or automatic decisions. "
            "The suggested_message must be written directly to the customer "
            "in natural, polite, and consultative Brazilian Portuguese. "
            "It must invite dialogue without asserting that the customer "
            "has a problem or intends to leave. "
            "Never mention churn, risk scores, risk bands, SHAP, model "
            "predictions, internal priority, or retention policies in the "
            "suggested_message. "
            "Never mention age, gender, dependents, education, marital "
            "status, or income category in the suggested_message, even when "
            "those attributes appear in the controlled evidence. "
            "The attention_points field is exclusively for internal "
            "human-review considerations. "
            "Every recommendation requires human review before any action."
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
        policy_action = self._resolve_policy_action(
            explainability=explainability,
            priority_label=priority_label,
            allowed_actions=allowed_actions,
        )

        actions_for_generation = (
            [policy_action]
            if policy_action is not None
            else allowed_actions
        )

        messages = self._build_messages(
            explainability=explainability,
            priority_label=priority_label,
            allowed_actions=actions_for_generation,
        )
        try:
            response = await self._client.chat(
                model=settings.ollama_model,
                messages=messages,
                format=RetentionRecommendationContent.model_json_schema(),
                options={
                    "temperature": 0,
                },
            )
        except httpx.TimeoutException as exc:
            raise RetentionAITimeoutError(
                "Local retention AI service timed out."
            ) from exc
        except ConnectionError as exc:
            raise RetentionAIUnavailableError(
                "Local retention AI service is unavailable."
            ) from exc

        try:
            recommendation = RetentionRecommendationContent.model_validate_json(
                response.message.content
            )
        except ValidationError as exc:
            errors = exc.errors()

            is_only_invalid_action = all(
                error.get("loc") == ("recommended_action_id",)
                and error.get("type") == "enum"
                for error in errors
            )

            if is_only_invalid_action:
                raise

            raise RetentionAIInvalidResponseError(
                "Local retention AI returned an invalid structured response."
            ) from exc

        if (
            policy_action is None
            and not is_retention_action_allowed(
                recommendation.recommended_action_id,
                explainability.risk_band.value,
            )
        ):
            raise ValueError(
                (
                    f"Retention action "
                    f"'{recommendation.recommended_action_id.value}' "
                    f"is not allowed for risk band "
                    f"'{explainability.risk_band.value}'."
                )
            )

        selected_action = (
            policy_action
            if policy_action is not None
            else get_retention_action(
                recommendation.recommended_action_id
            )
        )

        risk_signals, protective_factors = self._build_evidence_lists(
            explainability
        )

        system_content = self._build_system_content(
            explainability
        )

        return recommendation.model_copy(
            update={
                "case_summary": system_content["case_summary"],
                "risk_interpretation": system_content["risk_interpretation"],
                "main_risk_signals": risk_signals,
                "protective_factors": protective_factors,
                "attention_points": system_content["attention_points"],
                "approach_guidance": selected_action.description,
                "recommended_action_id": selected_action.action_id,
            }
        )


    async def close(self) -> None:
        await self._client.close()
