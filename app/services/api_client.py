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
        return json.loads(response_body)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "A API retornou uma resposta inválida."
        ) from exc
        
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