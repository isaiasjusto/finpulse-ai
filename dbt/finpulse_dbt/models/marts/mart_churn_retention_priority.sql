{{ config(materialized='table') }}

with customer_base as (

    select
        customer_id,
        risk_band,
        churn_probability,
        total_transaction_amount

    from {{ ref('int_churn_dashboard_customer_latest') }}

),

value_cutoff as (

    select
        percentile_cont(0.5) within group (
            order by total_transaction_amount
        ) as median_transaction_amount

    from customer_base

),

segmented_customers as (

    select
        customer.customer_id,
        customer.risk_band,
        customer.churn_probability,
        customer.total_transaction_amount,

        case
            when customer.total_transaction_amount
                >= cutoff.median_transaction_amount
                then 'High'
            else 'Low'
        end as value_band

    from customer_base as customer
    cross join value_cutoff as cutoff

),

portfolio_totals as (

    select
        count(distinct customer_id) as total_customers,
        sum(total_transaction_amount) as portfolio_transaction_amount

    from segmented_customers

)

select
    segmented.risk_band,

    case
        when segmented.risk_band = 'High' then 1
        when segmented.risk_band = 'Medium' then 2
        when segmented.risk_band = 'Low' then 3
        else 4
    end as risk_order,

    segmented.value_band,

    case
        when segmented.value_band = 'Low' then 1
        when segmented.value_band = 'High' then 2
        else 3
    end as value_order,

    count(distinct segmented.customer_id) as customers,

    (
        count(distinct segmented.customer_id)::numeric
        / nullif(max(totals.total_customers), 0)
    ) as customer_share,

    sum(segmented.total_transaction_amount)
        as total_transaction_amount,

    avg(segmented.total_transaction_amount)
        as average_transaction_amount,

    (
        sum(segmented.total_transaction_amount)
        / nullif(max(totals.portfolio_transaction_amount), 0)
    ) as transaction_amount_share,

    avg(segmented.churn_probability)
        as average_churn_probability

from segmented_customers as segmented
cross join portfolio_totals as totals

group by
    segmented.risk_band,
    segmented.value_band