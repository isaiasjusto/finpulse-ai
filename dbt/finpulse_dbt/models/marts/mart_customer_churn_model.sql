WITH customer_features AS (

    SELECT
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
        average_utilization_ratio

    FROM {{ ref('stg_bank_churners') }}

)

SELECT *
FROM customer_features