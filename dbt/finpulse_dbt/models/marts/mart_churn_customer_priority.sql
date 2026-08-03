{{ config(materialized='table') }}

with customer_base as (

    select
        customer_id,
        churn_flag,

        customer_age,
        gender,
        dependent_count,
        education_level,
        marital_status,
        income_category,
        card_category,

        months_on_book,
        total_relationship_count,
        months_inactive_last_12m,
        contacts_count_last_12m,

        credit_limit,
        total_revolving_balance,
        average_open_to_buy,
        amount_change_q4_q1,

        total_transaction_amount,
        total_transaction_count,
        transaction_count_change_q4_q1,
        average_utilization_ratio,

        churn_probability,
        risk_band,
        churn_prediction,

        model_name,
        model_version,
        model_alias,
        scored_at,
        scoring_run_id

    from {{ ref('int_churn_dashboard_customer_latest') }}

    where churn_probability is not null
      and risk_band is not null

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
        customer.*,

        case
            when customer.risk_band = 'High' then 1
            when customer.risk_band = 'Medium' then 2
            when customer.risk_band = 'Low' then 3
            else 4
        end as risk_order,

        case
            when customer.total_transaction_amount
                >= cutoff.median_transaction_amount
                then 'High'
            else 'Low'
        end as value_band

    from customer_base as customer
    cross join value_cutoff as cutoff

)

select
    segmented.*,

    case
        when risk_band = 'High' and value_band = 'High' then 1
        when risk_band = 'High' and value_band = 'Low' then 2
        when risk_band = 'Medium' and value_band = 'High' then 3
        when risk_band = 'Medium' and value_band = 'Low' then 4
        when risk_band = 'Low' and value_band = 'High' then 5
        when risk_band = 'Low' and value_band = 'Low' then 6
        else 7
    end as priority_order,

    case
        when risk_band = 'High' and value_band = 'High'
            then 'Crítica'
        when risk_band = 'High' and value_band = 'Low'
            then 'Alta'
        when risk_band = 'Medium'
            then 'Média'
        when risk_band = 'Low'
            then 'Baixa'
        else 'Não classificada'
    end as priority_label,

    case
        when risk_band = 'High' and value_band = 'High'
            then 'Contato imediato e oferta personalizada'
        when risk_band = 'High' and value_band = 'Low'
            then 'Campanha de recuperação com baixo custo'
        when risk_band = 'Medium' and value_band = 'High'
            then 'Benefício preventivo e acompanhamento'
        when risk_band = 'Medium' and value_band = 'Low'
            then 'Monitorar a evolução do risco'
        when risk_band = 'Low' and value_band = 'High'
            then 'Desenvolver o relacionamento'
        when risk_band = 'Low' and value_band = 'Low'
            then 'Manter relacionamento e fidelização'
        else 'Revisar classificação do cliente'
    end as recommended_action

from segmented_customers as segmented