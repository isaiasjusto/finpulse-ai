from typing import Any

from sqlalchemy import text

from api.database import engine


PORTFOLIO_SUMMARY_QUERY = text(
    """
    SELECT
        COUNT(*)::bigint AS total_customers,
        COALESCE(
            SUM(churn_prediction),
            0
        )::bigint AS predicted_churn_customers,
        COALESCE(
            AVG(churn_prediction::double precision),
            0.0
        ) AS predicted_churn_rate,
        COALESCE(
            AVG(churn_probability),
            0.0
        ) AS average_churn_probability,
        COUNT(*) FILTER (
            WHERE risk_band = 'Low'
        )::bigint AS low_risk_customers,
        COUNT(*) FILTER (
            WHERE risk_band = 'Medium'
        )::bigint AS medium_risk_customers,
        COUNT(*) FILTER (
            WHERE risk_band = 'High'
        )::bigint AS high_risk_customers,
        MIN(model_version)::bigint AS minimum_model_version,
        MAX(model_version)::bigint AS maximum_model_version,
        MAX(model_alias) AS model_alias,
        MAX(scored_at) AS latest_scoring_at
    FROM marts.mart_customer_churn_predictions
    """
)


def get_portfolio_summary() -> dict[str, Any]:
    with engine.connect() as connection:
        row = connection.execute(
            PORTFOLIO_SUMMARY_QUERY
        ).mappings().one()

    return dict(row)