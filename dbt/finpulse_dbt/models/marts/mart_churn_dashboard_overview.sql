{{ config(materialized='table') }}

with customer_base as (

    select *
    from {{ ref('int_churn_dashboard_customer_latest') }}

),

portfolio_totals as (

    select
        sum(credit_limit) as portfolio_credit_limit,
        sum(total_transaction_amount) as portfolio_transaction_amount
    from customer_base

)

select
    count(distinct customer_id) as total_customers,
    sum(churn_flag) as observed_churn_customers,
    avg(churn_flag::numeric) as observed_churn_rate,

    count(*) filter (
        where risk_band = 'High'
    ) as high_risk_customers,

    avg(
        case when risk_band = 'High' then 1.0 else 0.0 end
    ) as high_risk_rate,

    avg(churn_probability) as average_churn_probability,

    sum(credit_limit) filter (
        where risk_band = 'High'
    ) as high_risk_credit_limit,

    sum(total_transaction_amount) filter (
        where risk_band = 'High'
    ) as high_risk_transaction_amount,

    (
        sum(credit_limit) filter (where risk_band = 'High')
        / nullif(max(portfolio_credit_limit), 0)
    ) as high_risk_credit_limit_share,

    (
        sum(total_transaction_amount) filter (where risk_band = 'High')
        / nullif(max(portfolio_transaction_amount), 0)
    ) as high_risk_transaction_share,

    sum(churn_flag) filter (
        where risk_band = 'High'
    ) as high_risk_observed_churn,

    avg(churn_flag::numeric) filter (
        where risk_band = 'High'
    ) as high_risk_observed_churn_rate,

    (
        sum(churn_flag) filter (where risk_band = 'High')
        / nullif(sum(churn_flag), 0)::numeric
    ) as churn_concentration_high,

    (
        avg(churn_flag::numeric) filter (where risk_band = 'High')
        / nullif(avg(churn_flag::numeric), 0)
    ) as high_risk_lift,

    max(model_version) as model_version,
    max(model_alias) as model_alias,
    max(scoring_run_id) as scoring_run_id,
    max(scored_at) as scored_at

from customer_base
cross join portfolio_totals