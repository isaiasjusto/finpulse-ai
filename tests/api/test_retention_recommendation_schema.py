import pytest
from pydantic import ValidationError

from api.schemas import CustomerRetentionRecommendationResponse


def build_recommendation_payload(
    risk_band: str = "High",
    action_id: str = "preventive_contact",
) -> dict:
    return {
        "customer_id": 809849358,
        "churn_probability": 0.91,
        "risk_band": risk_band,
        "priority_label": "Crítica",
        "recommendation": {
            "case_summary": "Cliente com risco elevado.",
            "risk_interpretation": "Necessita acompanhamento.",
            "main_risk_signals": [
                "Queda na atividade transacional.",
            ],
            "protective_factors": [
                "Relacionamento de longa duração.",
            ],
            "recommended_action_id": action_id,
            "approach_guidance": "Realizar contato humano.",
            "suggested_message": (
                "Olá, gostaríamos de entender se podemos ajudar."
            ),
            "attention_points": [
                "A recomendação exige revisão humana.",
            ],
        },
        "generation": {
            "provider": "test",
            "model": "test-model",
            "generated_at": "2026-08-08T12:00:00",
        },
    }


@pytest.mark.parametrize(
    ("risk_band", "action_id"),
    [
        ("High", "preventive_contact"),
        ("Low", "maintain_relationship"),
    ],
)
def test_allowed_action_for_risk_band_is_accepted(
    risk_band,
    action_id,
):
    payload = build_recommendation_payload(
        risk_band=risk_band,
        action_id=action_id,
    )

    result = CustomerRetentionRecommendationResponse.model_validate(
        payload
    )

    assert result.risk_band.value == risk_band
    assert (
        result.recommendation.recommended_action_id.value
        == action_id
    )


def test_incompatible_action_for_risk_band_is_rejected():
    payload = build_recommendation_payload(
        risk_band="High",
        action_id="maintain_relationship",
    )

    with pytest.raises(
        ValidationError,
        match="not allowed for risk band 'High'",
    ):
        CustomerRetentionRecommendationResponse.model_validate(
            payload
        )


def test_unknown_action_is_rejected():
    payload = build_recommendation_payload(
        action_id="invented_retention_action",
    )

    with pytest.raises(ValidationError) as error:
        CustomerRetentionRecommendationResponse.model_validate(
            payload
        )

    error_locations = {
        tuple(item["loc"])
        for item in error.value.errors()
    }

    assert (
        "recommendation",
        "recommended_action_id",
    ) in error_locations


def test_unknown_risk_band_is_rejected():
    payload = build_recommendation_payload(
        risk_band="Critical",
    )

    with pytest.raises(ValidationError) as error:
        CustomerRetentionRecommendationResponse.model_validate(
            payload
        )

    error_locations = {
        tuple(item["loc"])
        for item in error.value.errors()
    }

    assert ("risk_band",) in error_locations


def test_missing_required_recommendation_field_is_rejected():
    payload = build_recommendation_payload()
    del payload["recommendation"]["suggested_message"]

    with pytest.raises(ValidationError) as error:
        CustomerRetentionRecommendationResponse.model_validate(
            payload
        )

    error_locations = {
        tuple(item["loc"])
        for item in error.value.errors()
    }

    assert (
        "recommendation",
        "suggested_message",
    ) in error_locations


def test_invalid_generation_date_is_rejected():
    payload = build_recommendation_payload()
    payload["generation"]["generated_at"] = "invalid-date"

    with pytest.raises(ValidationError) as error:
        CustomerRetentionRecommendationResponse.model_validate(
            payload
        )

    error_locations = {
        tuple(item["loc"])
        for item in error.value.errors()
    }

    assert (
        "generation",
        "generated_at",
    ) in error_locations