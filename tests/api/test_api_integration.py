import os

import httpx
import pytest


API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://api:8000",
)

KNOWN_CUSTOMER_ID = 809849358
MISSING_CUSTOMER_ID = 1


@pytest.fixture(scope="session")
def api_client():
    with httpx.Client(
        base_url=API_BASE_URL,
        timeout=30.0,
    ) as client:
        yield client


def test_health_returns_all_components_healthy(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["components"]["api"]["status"] == "healthy"
    assert data["components"]["model"]["status"] == "healthy"
    assert data["components"]["model"]["loaded"] is True
    assert data["components"]["model"]["alias"] == "champion"
    assert data["components"]["database"]["status"] == "healthy"


def test_model_info_returns_champion(api_client):
    response = api_client.get("/model-info")

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "finpulse-churn-catboost"
    assert data["alias"] == "champion"
    assert data["version"] == 3
    assert data["status"] == "READY"


def test_portfolio_summary_is_consistent(api_client):
    response = api_client.get("/portfolio/summary")

    assert response.status_code == 200

    data = response.json()

    risk_total = (
        data["low_risk_customers"]
        + data["medium_risk_customers"]
        + data["high_risk_customers"]
    )

    assert data["total_customers"] == 10127
    assert data["predicted_churn_customers"] == 1599
    assert risk_total == data["total_customers"]
    assert data["minimum_model_version"] == 3
    assert data["maximum_model_version"] == 3
    assert data["model_alias"] == "champion"


def test_known_customer_returns_profile_and_prediction(api_client):
    response = api_client.get(
        f"/customers/{KNOWN_CUSTOMER_ID}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["customer_id"] == KNOWN_CUSTOMER_ID
    assert len(data["features"]) == 19
    assert data["prediction"]["risk_band"] == "High"
    assert data["prediction"]["churn_prediction"] == 1
    assert data["prediction"]["model_version"] == 3
    assert data["prediction"]["model_alias"] == "champion"


def test_missing_customer_returns_404(api_client):
    response = api_client.get(
        f"/customers/{MISSING_CUSTOMER_ID}"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": (
            f"Customer {MISSING_CUSTOMER_ID} was not found."
        )
    }


def test_customer_list_filters_high_risk(api_client):
    response = api_client.get(
        "/customers",
        params={
            "risk_band": "High",
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()
    customers = data["customers"]

    assert data["risk_band"] == "High"
    assert data["total_matching"] == 1599
    assert data["returned_count"] == 10
    assert len(customers) == 10

    assert all(
        customer["risk_band"] == "High"
        for customer in customers
    )

    probabilities = [
        customer["churn_probability"]
        for customer in customers
    ]

    assert probabilities == sorted(
        probabilities,
        reverse=True,
    )


def test_invalid_risk_band_returns_422(api_client):
    response = api_client.get(
        "/customers",
        params={
            "risk_band": "Critical",
        },
    )

    assert response.status_code == 422


def test_predict_customer_by_id_matches_stored_prediction(
    api_client,
):
    response = api_client.post(
        f"/customers/{KNOWN_CUSTOMER_ID}/predict"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["customer_id"] == KNOWN_CUSTOMER_ID
    assert data["churn_prediction"] == 1
    assert data["stored_churn_prediction"] == 1
    assert data["matches_stored_prediction"] is True
    assert data["model_version"] == 3
    assert data["model_alias"] == "champion"


def test_manual_predict_accepts_customer_features(api_client):
    customer_response = api_client.get(
        f"/customers/{KNOWN_CUSTOMER_ID}"
    )

    assert customer_response.status_code == 200

    customer = customer_response.json()
    features = customer["features"]
    stored_prediction = customer["prediction"]

    prediction_response = api_client.post(
        "/predict",
        json=features,
    )

    assert prediction_response.status_code == 200

    prediction = prediction_response.json()

    assert (
        prediction["churn_prediction"]
        == stored_prediction["churn_prediction"]
    )
    assert prediction["model_name"] == "finpulse-churn-catboost"
    assert prediction["model_version"] == 3
    assert prediction["model_alias"] == "champion"