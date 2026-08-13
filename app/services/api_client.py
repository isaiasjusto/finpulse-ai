import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE_URL = os.getenv(
    "FINPULSE_API_URL",
    "http://localhost:8000",
).rstrip("/")


def load_latest_scoring() -> dict[str, Any]:
    request = Request(
        url=f"{API_BASE_URL}/scoring/latest",
        headers={
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=5) as response:
            response_body = response.read().decode("utf-8")

    except HTTPError as exc:
        raise RuntimeError(
            "A API respondeu com erro ao consultar o último scoring."
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            "Não foi possível conectar à API do FinPulse."
        ) from exc

    try:
        result = json.loads(response_body)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "A API retornou uma resposta inválida."
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "A resposta do último scoring possui formato inesperado."
        )

    return result


def load_confusion_matrix() -> dict[str, int]:
    request = Request(
        url=(
            f"{API_BASE_URL}"
            "/model-evaluation/confusion-matrix"
        ),
        headers={
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")

    except HTTPError as exc:
        raise RuntimeError(
            "A API respondeu com erro ao consultar "
            "a matriz de confusão."
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            "Não foi possível conectar à API do FinPulse."
        ) from exc

    try:
        result = json.loads(response_body)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "A API retornou uma matriz de confusão inválida."
        ) from exc

    required_fields = {
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
        "sample_size",
    }

    if (
        not isinstance(result, dict)
        or not required_fields.issubset(result)
    ):
        raise RuntimeError(
            "A matriz de confusão possui formato inesperado."
        )

    return result


def load_global_explainability(
    sample_size: int = 500,
) -> dict[str, Any]:
    if not 100 <= sample_size <= 5000:
        raise ValueError(
            "O tamanho da amostra deve estar entre 100 e 5000."
        )

    request = Request(
        url=(
            f"{API_BASE_URL}/model-explainability/global"
            f"?sample_size={sample_size}"
        ),
        headers={
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")

    except HTTPError as exc:
        raise RuntimeError(
            "A API respondeu com erro ao consultar "
            "a explicabilidade global."
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            "Não foi possível conectar à API do FinPulse."
        ) from exc

    try:
        result = json.loads(response_body)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "A API retornou uma resposta SHAP inválida."
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "A resposta da explicabilidade possui formato inesperado."
        )

    return result


def load_customer_explainability(
    customer_id: str,
) -> dict[str, Any]:
    customer_id = str(customer_id).strip()

    if not customer_id:
        raise ValueError(
            "O ID do cliente não pode estar vazio."
        )

    request = Request(
        url=(
            f"{API_BASE_URL}/customers/"
            f"{customer_id}/explainability"
        ),
        headers={
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")

    except HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"O cliente {customer_id} não foi encontrado pela API."
            ) from exc

        raise RuntimeError(
            "A API respondeu com erro ao consultar "
            "a explicabilidade individual."
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            "Não foi possível conectar à API do FinPulse."
        ) from exc

    try:
        result = json.loads(response_body)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "A API retornou uma explicabilidade individual inválida."
        ) from exc

    required_fields = {
        "customer_id",
        "churn_probability",
        "churn_prediction",
        "prediction_label",
        "risk_band",
        "features",
        "risk_increasing_factors",
        "risk_reducing_factors",
    }

    if (
        not isinstance(result, dict)
        or not required_fields.issubset(result)
    ):
        raise RuntimeError(
            "A explicabilidade individual possui formato inesperado."
        )

    list_fields = {
        "features",
        "risk_increasing_factors",
        "risk_reducing_factors",
    }

    if any(
        not isinstance(result[field], list)
        for field in list_fields
    ):
        raise RuntimeError(
            "Os impactos SHAP possuem formato inesperado."
        )

    return result

def load_customer_retention_recommendation(
    customer_id: str,
) -> dict[str, Any]:
    customer_id = str(customer_id).strip()

    if not customer_id:
        raise ValueError(
            "O ID do cliente não pode estar vazio."
        )

    request = Request(
        url=(
            f"{API_BASE_URL}/customers/"
            f"{customer_id}/retention-recommendation"
        ),
        headers={
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=130) as response:
            response_body = response.read().decode("utf-8")

    except HTTPError as exc:
        error_messages = {
            404: f"O cliente {customer_id} não foi encontrado pela API.",
            502: (
                "A IA retornou uma recomendação inválida. "
                "Tente gerar novamente."
            ),
            503: (
                "O serviço de IA está indisponível no momento. "
                "Verifique o Ollama e tente novamente."
            ),
            504: (
                "A geração da recomendação ultrapassou o tempo limite. "
                "Tente novamente."
            ),
        }

        raise RuntimeError(
            error_messages.get(
                exc.code,
                "A API respondeu com erro ao gerar a recomendação.",
            )
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            "A geração da recomendação ultrapassou o tempo limite."
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            "Não foi possível conectar à API do FinPulse."
        ) from exc

    try:
        result = json.loads(response_body)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "A API retornou uma recomendação inválida."
        ) from exc

    required_fields = {
        "customer_id",
        "churn_probability",
        "risk_band",
        "priority_label",
        "recommendation",
        "generation",
    }

    if (
        not isinstance(result, dict)
        or not required_fields.issubset(result)
    ):
        raise RuntimeError(
            "A recomendação possui formato inesperado."
        )

    recommendation = result["recommendation"]
    generation = result["generation"]

    recommendation_fields = {
        "case_summary",
        "risk_interpretation",
        "main_risk_signals",
        "protective_factors",
        "recommended_action_id",
        "approach_guidance",
        "suggested_message",
        "attention_points",
    }

    generation_fields = {
        "provider",
        "model",
        "generated_at",
    }

    if (
        not isinstance(recommendation, dict)
        or not recommendation_fields.issubset(recommendation)
        or not isinstance(generation, dict)
        or not generation_fields.issubset(generation)
    ):
        raise RuntimeError(
            "O conteúdo da recomendação possui formato inesperado."
        )

    list_fields = {
        "main_risk_signals",
        "protective_factors",
        "attention_points",
    }

    if any(
        not isinstance(recommendation[field], list)
        for field in list_fields
    ):
        raise RuntimeError(
            "Os sinais da recomendação possuem formato inesperado."
        )

    return result