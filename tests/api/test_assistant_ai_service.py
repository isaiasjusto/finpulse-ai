import json

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
import unittest
from unittest.mock import AsyncMock

import httpx

from api.assistant_ai_service import (
    AssistantAIInvalidResponseError,
    AssistantAIService,
    AssistantAITimeoutError,
    AssistantAIUnavailableError,
)
from api.schemas import (
    AssistantQueryRequest,
    AssistantScope,
    AssistantSourceResponse,
    AssistantSourceType,
)


class AssistantAIServiceTests(IsolatedAsyncioTestCase):
    @staticmethod
    def _query() -> AssistantQueryRequest:
        return AssistantQueryRequest(
            question=(
                "Por que este cliente precisa de atenção?"
            ),
            scope=AssistantScope.customer,
            customer_id=809849358,
        )

    @staticmethod
    def _sources() -> list[AssistantSourceResponse]:
        return [
            AssistantSourceResponse(
                source_type=(
                    AssistantSourceType.customer_explainability
                ),
                label="SHAP individual",
                reference="customer:809849358",
            )
        ]

    async def test_generate_answer_returns_validated_content(
        self,
    ) -> None:
        fake_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    {
                        "answer": (
                            "O cliente possui sinais que justificam "
                            "análise humana prioritária."
                        )
                    },
                    ensure_ascii=False,
                )
            )
        )

        service = AssistantAIService()
        service._client.chat = AsyncMock(
            return_value=fake_response
        )

        result = await service.generate_answer(
            query=self._query(),
            controlled_context={
                "risk_band": "High",
                "priority_label": "Alta",
            },
            sources=self._sources(),
        )

        self.assertEqual(
            result.answer,
            (
                "O cliente possui sinais que justificam "
                "análise humana prioritária."
            ),
        )

        call_kwargs = service._client.chat.await_args.kwargs

        self.assertEqual(
            set(call_kwargs["format"]["properties"]),
            {
                "answer",
            },
        )

    def test_personal_attributes_are_removed_recursively(
        self,
    ) -> None:
        messages = AssistantAIService._build_messages(
            query=self._query(),
            controlled_context={
                "customer_age": 55,
                "risk_band": "High",
                "nested_context": {
                    "gender": "F",
                    "signals": [
                        {
                            "income_category": "$40K - $60K",
                            "total_transaction_count": 36,
                        }
                    ],
                },
            },
            sources=self._sources(),
        )

        user_message = messages[1]["content"]
        serialized_context = user_message.split(
            "\n",
            maxsplit=1,
        )[1]
        controlled_request = json.loads(
            serialized_context
        )

        context = controlled_request[
            "controlled_context"
        ]

        self.assertNotIn(
            "customer_age",
            context,
        )
        self.assertNotIn(
            "gender",
            context["nested_context"],
        )
        self.assertNotIn(
            "income_category",
            context["nested_context"]["signals"][0],
        )
        self.assertEqual(
            context["nested_context"]["signals"][0][
                "total_transaction_count"
            ],
            36,
        )

    async def test_extra_generated_fields_are_rejected(
        self,
    ) -> None:
        fake_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    {
                        "answer": "Resposta válida.",
                        "sources": [],
                        "requires_human_review": False,
                    }
                )
            )
        )

        service = AssistantAIService()
        service._client.chat = AsyncMock(
            return_value=fake_response
        )

        with self.assertRaises(
            AssistantAIInvalidResponseError
        ):
            await service.generate_answer(
                query=self._query(),
                controlled_context={
                    "risk_band": "High",
                },
                sources=self._sources(),
            )

    async def test_blank_generated_answer_is_rejected(
        self,
    ) -> None:
        fake_response = SimpleNamespace(
            message=SimpleNamespace(
                content=json.dumps(
                    {
                        "answer": "   ",
                    }
                )
            )
        )

        service = AssistantAIService()
        service._client.chat = AsyncMock(
            return_value=fake_response
        )

        with self.assertRaises(
            AssistantAIInvalidResponseError
        ):
            await service.generate_answer(
                query=self._query(),
                controlled_context={},
                sources=self._sources(),
            )

    async def test_timeout_raises_domain_error(
        self,
    ) -> None:
        service = AssistantAIService()
        service._client.chat = AsyncMock(
            side_effect=httpx.TimeoutException(
                "Simulated timeout."
            )
        )

        with self.assertRaises(
            AssistantAITimeoutError
        ):
            await service.generate_answer(
                query=self._query(),
                controlled_context={},
                sources=self._sources(),
            )

    async def test_unavailable_raises_domain_error(
        self,
    ) -> None:
        service = AssistantAIService()
        service._client.chat = AsyncMock(
            side_effect=httpx.ConnectError(
                "Simulated connection failure."
            )
        )

        with self.assertRaises(
            AssistantAIUnavailableError
        ):
            await service.generate_answer(
                query=self._query(),
                controlled_context={},
                sources=self._sources(),
            )

    async def test_close_closes_ollama_client(
        self,
    ) -> None:
        service = AssistantAIService()
        service._client.close = AsyncMock()

        await service.close()

        service._client.close.assert_awaited_once()
if __name__ == "__main__":
    import unittest

    unittest.main()