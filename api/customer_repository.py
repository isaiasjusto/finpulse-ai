from typing import Any

from sqlalchemy import text

from api.database import engine


CUSTOMER_BY_ID_QUERY = text(
    """
    SELECT
        model.customer_id,
        model.customer_age,
        model.gender,
        model.dependent_count,
        model.education_level,
        model.marital_status,
        model.income_category,
        model.card_category,
        model.months_on_book,
        model.total_relationship_count,
        model.months_inactive_last_12m,
        model.contacts_count_last_12m,
        model.credit_limit,
        model.total_revolving_balance,
        model.average_open_to_buy,
        model.amount_change_q4_q1,
        model.total_transaction_amount,
        model.total_transaction_count,
        model.transaction_count_change_q4_q1,
        model.average_utilization_ratio,
        prediction.churn_probability,
        prediction.risk_band,
        prediction.churn_prediction,
        prediction.model_name,
        prediction.model_version,
        prediction.model_alias,
        prediction.scored_at,
        prediction.scoring_run_id
    FROM marts.mart_customer_churn_model AS model
    LEFT JOIN marts.mart_customer_churn_predictions AS prediction
        ON prediction.customer_id = model.customer_id
    WHERE model.customer_id = :customer_id
    """
)


def get_customer_by_id(
    customer_id: int,
) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(
            CUSTOMER_BY_ID_QUERY,
            {"customer_id": customer_id},
        ).mappings().first()

    if row is None:
        return None

    return dict(row)

CUSTOMER_LIST_QUERY = text(
    """
    SELECT
        model.customer_id,
        model.customer_age,
        model.gender,
        prediction.churn_probability,
        prediction.risk_band,
        prediction.churn_prediction,
        prediction.model_version,
        prediction.model_alias,
        prediction.scored_at
    FROM marts.mart_customer_churn_predictions AS prediction
    INNER JOIN marts.mart_customer_churn_model AS model
        ON model.customer_id = prediction.customer_id
    WHERE (
        :risk_band = ''
        OR prediction.risk_band = :risk_band
    )
    ORDER BY
        prediction.churn_probability DESC,
        model.customer_id
    LIMIT :limit
    OFFSET :offset
    """
)


CUSTOMER_LIST_COUNT_QUERY = text(
    """
    SELECT COUNT(*)::bigint
    FROM marts.mart_customer_churn_predictions
    WHERE (
        :risk_band = ''
        OR risk_band = :risk_band
    )
    """
)


def list_customers(
    risk_band: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    parameters = {
        "risk_band": risk_band or "",
        "limit": limit,
        "offset": offset,
    }

    with engine.connect() as connection:
        total_matching = connection.execute(
            CUSTOMER_LIST_COUNT_QUERY,
            parameters,
        ).scalar_one()

        rows = connection.execute(
            CUSTOMER_LIST_QUERY,
            parameters,
        ).mappings().all()

    return (
        [dict(row) for row in rows],
        int(total_matching),
    )