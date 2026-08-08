import math
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

def test_latest_scoring_returns_operational_metadata(api_client):
    response = api_client.get("/scoring/latest")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "available"

    assert data["model"]["name"] == "finpulse-churn-catboost"
    assert data["model"]["alias"] == "champion"
    assert data["model"]["version"] == 3
    assert data["model"]["status"] == "READY"
    assert data["model"]["run_id"]

    assert data["scoring"]["population_scored"] == 10127
    assert data["scoring"]["executed_at"]

    assert data["metrics"]["roc_auc"] == pytest.approx(
        0.9934,
        abs=0.0001,
    )
    assert data["metrics"]["balanced_accuracy"] == pytest.approx(
    0.9417,
    abs=0.0001,
)

    assert data["metrics"]["f1"] == pytest.approx(
        0.9206,
        abs=0.0001,
    )

    assert data["metrics"]["precision"] == pytest.approx(
        0.9508,
        abs=0.0001,
    )

    assert data["metrics"]["recall"] == pytest.approx(
        0.8923,
        abs=0.0001,
    )
    assert data["metrics"]["ks"] is None
    assert data["metrics"]["psi"] is None

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
def test_customer_explainability_is_consistent(api_client):
    customer_response = api_client.get(
        f"/customers/{KNOWN_CUSTOMER_ID}"
    )

    explainability_response = api_client.get(
        f"/customers/{KNOWN_CUSTOMER_ID}/explainability"
    )

    assert customer_response.status_code == 200
    assert explainability_response.status_code == 200

    customer = customer_response.json()
    data = explainability_response.json()

    assert data["churn_prediction"] == 1
    assert data["prediction_label"] == "churn"
    assert data["model_name"] == "finpulse-churn-catboost"
    assert data["model_alias"] == "champion"
    assert data["model_version"] == 3
    assert data["run_id"]

    assert data["input_feature_count"] == 19
    assert len(data["features"]) == 19
    assert data["transformed_feature_count"] >= 19

    assert data["churn_probability"] == pytest.approx(
        customer["prediction"]["churn_probability"],
        abs=1e-9,
    )

    feature_names = {
        feature["feature"]
        for feature in data["features"]
    }

    assert feature_names == set(
        customer["features"]
    )

    for feature in data["features"]:
        feature_name = feature["feature"]

        assert (
            feature["value"]
            == customer["features"][feature_name]
        )
        assert feature["absolute_shap"] == pytest.approx(
            abs(feature["shap_value"]),
            abs=1e-12,
        )
        assert 0.0 <= feature["importance_share"] <= 1.0
        assert feature["impact_direction"] in {
            "increases_risk",
            "reduces_risk",
            "neutral",
        }

    increasing_factors = data["risk_increasing_factors"]
    reducing_factors = data["risk_reducing_factors"]

    assert increasing_factors
    assert reducing_factors

    assert all(
        factor["shap_value"] > 0
        and factor["impact_direction"] == "increases_risk"
        for factor in increasing_factors
    )

    assert all(
        factor["shap_value"] < 0
        and factor["impact_direction"] == "reduces_risk"
        for factor in reducing_factors
    )

    increasing_names = {
        factor["feature"]
        for factor in increasing_factors
    }

    reducing_names = {
        factor["feature"]
        for factor in reducing_factors
    }

    assert increasing_names.isdisjoint(reducing_names)

    total_importance_share = sum(
        feature["importance_share"]
        for feature in data["features"]
    )

    assert total_importance_share == pytest.approx(
        1.0,
        abs=1e-9,
    )

    reconstructed_raw_prediction = (
        data["base_value"]
        + sum(
            feature["shap_value"]
            for feature in data["features"]
        )
    )

    reconstructed_probability = (
        1.0
        / (1.0 + math.exp(-reconstructed_raw_prediction))
    )

    assert reconstructed_probability == pytest.approx(
        data["churn_probability"],
        abs=1e-9,
    )