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