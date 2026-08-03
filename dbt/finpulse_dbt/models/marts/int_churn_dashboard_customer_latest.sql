{{ config(materialized='view') }}

with ranked_predictions as (

    select
        *,
        row_number() over (
            partition by customer_id
            order by scored_at desc, scoring_run_id desc
        ) as prediction_rank

    from {{ source('scoring', 'mart_customer_churn_predictions') }}

),

latest_predictions as (

    select *
    from ranked_predictions
    where prediction_rank = 1

),

customer_predictions as (

    select
        customer.*,
        prediction.churn_probability,
        prediction.risk_band,
        prediction.churn_prediction,
        prediction.model_name,
        prediction.model_version,
        prediction.model_alias,
        prediction.scored_at,
        prediction.scoring_run_id,
        prediction.snapshot_uri

    from {{ ref('mart_customer_churn_model') }} as customer

    left join latest_predictions as prediction
        on customer.customer_id = prediction.customer_id

)

select *
from customer_predictions