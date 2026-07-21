{{ config(materialized='table') }}

with customer_base as (

    select *
    from {{ ref('int_churn_dashboard_customer_latest') }}

),

portfolio_totals as (

    select
        count(distinct customer_id) as total_customers,
        sum(credit_limit) as portfolio_credit_limit,
        sum(total_transaction_amount) as portfolio_transaction_amount

    from customer_base

)

select
    risk_band,

    case
        when risk_band = 'Low' then 1
        when risk_band = 'Medium' then 2
        when risk_band = 'High' then 3
        else 4
    end as risk_order,

    count(distinct customer_id) as customers,

    (
        count(distinct customer_id)::numeric
        / nullif(max(total_customers), 0)
    ) as customer_share,

    sum(credit_limit) as total_credit_limit,
    avg(credit_limit) as average_credit_limit,

    sum(total_transaction_amount) as total_transaction_amount,
    avg(total_transaction_amount) as average_transaction_amount,

    avg(churn_probability) as average_churn_probability,

    (
        sum(credit_limit)
        / nullif(max(portfolio_credit_limit), 0)
    ) as credit_limit_share,

    (
        sum(total_transaction_amount)
        / nullif(max(portfolio_transaction_amount), 0)
    ) as transaction_amount_share,

    sum(churn_flag) as observed_churn_customers,

    (
        count(distinct customer_id) - sum(churn_flag)
    ) as active_customers,

    avg(churn_flag::numeric) as observed_churn_rate,

    max(model_version) as model_version,
    max(model_alias) as model_alias,
    max(scoring_run_id) as scoring_run_id,
    max(scored_at) as scored_at

from customer_base
cross join portfolio_totals

group by risk_band