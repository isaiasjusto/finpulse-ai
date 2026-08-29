import json

import httpx

from ollama import AsyncClient
from pydantic import ValidationError

from api.config import settings
from api.retention_ai_service import (
    NON_ACTIONABLE_RETENTION_FEATURES,
)
from api.schemas import (
    AssistantGeneratedContent,
    AssistantQueryRequest,
    AssistantSourceResponse,
)

ASSISTANT_GENERATION_FORMAT = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
        },
    },
    "required": [
        "answer",
    ],
}

class AssistantAIUnavailableError(RuntimeError):
    """Raised when the local assistant LLM is unavailable."""


class AssistantAITimeoutError(RuntimeError):
    """Raised when the local assistant LLM exceeds its timeout."""


class AssistantAIInvalidResponseError(RuntimeError):
    """Raised when the local assistant LLM returns invalid content."""


class AssistantAIService:
    def __init__(self) -> None:
        self._client = AsyncClient(
            host=settings.ollama_host,
            timeout=settings.ollama_timeout_seconds,
        )

    @classmethod
    def _sanitize_context(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, dict):
            return {
                key: cls._sanitize_context(item)
                for key, item in value.items()
                if key
                not in NON_ACTIONABLE_RETENTION_FEATURES
            }

        if isinstance(value, list):
            return [
                cls._sanitize_context(item)
                for item in value
            ]

        return value

    @classmethod
    def _build_messages(
        cls,
        query: AssistantQueryRequest,
        controlled_context: dict[str, object],
        sources: list[AssistantSourceResponse],
    ) -> list[dict[str, str]]:
        sanitized_context = cls._sanitize_context(
            controlled_context
        )

        source_labels = [
            {
                "source_type": source.source_type.value,
                "label": source.label,
                "reference": source.reference,
            }
            for source in sources
        ]

        system_message = (
            "You are the governed internal assistant of FinPulse AI. "
            "Answer in clear Brazilian Portuguese for a human retention "
            "analyst. Use only the supplied controlled_context. "
            "Never use external knowledge or invent missing facts. "
            "If the context is insufficient, state that there is not "
            "enough evidence to answer. "
            "Do not calculate or recalculate churn probability, SHAP, "
            "risk bands, priorities, or retention policies. "
            "Do not describe SHAP contributions as causal relationships. "
            "Do not invent customers, evidence, actions, policies, "
            "discounts, credit, benefits, offers, or special conditions. "
            "Age, gender, dependents, education, marital status, and "
            "income category must never be used as operational evidence. "
            "The available_sources are provenance labels, not additional "
            "evidence. "
            "Do not claim that any operational action was executed. "
            "Every response is advisory and requires human review. "
            "Return only the structured answer defined by the schema."
        )

        user_context = {
            "scope": query.scope.value,
            "question": query.question,
            "customer_id": query.customer_id,
            "controlled_context": sanitized_context,
            "available_sources": source_labels,
        }

        return [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": (
                    "Answer the question using only this controlled "
                    "request:\n"
                    + json.dumps(
                        user_context,
                        ensure_ascii=False,
                    )
                ),
            },
        ]

    async def generate_answer(
        self,
        query: AssistantQueryRequest,
        controlled_context: dict[str, object],
        sources: list[AssistantSourceResponse],
    ) -> AssistantGeneratedContent:
        messages = self._build_messages(
            query=query,
            controlled_context=controlled_context,
            sources=sources,
        )

        try:
            response = await self._client.chat(
                model=settings.ollama_model,
                messages=messages,
                format=ASSISTANT_GENERATION_FORMAT,
                options={
                    "temperature": 0,
                },
            )
        except httpx.TimeoutException as exc:
            raise AssistantAITimeoutError(
                "Local assistant AI service timed out."
            ) from exc
        except (
            httpx.ConnectError,
            ConnectionError,
        ) as exc:
            raise AssistantAIUnavailableError(
                "Local assistant AI service is unavailable."
            ) from exc

        try:
            return AssistantGeneratedContent.model_validate_json(
                response.message.content
            )
        except ValidationError as exc:
            raise AssistantAIInvalidResponseError(
                "Local assistant AI returned invalid content."
            ) from exc

    async def close(self) -> None:
        await self._client.close()