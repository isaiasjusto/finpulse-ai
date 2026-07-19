WITH source_data AS (

    SELECT *
    FROM {{ source('raw', 'bank_churners') }}

),

staged AS (

    SELECT
        client_num AS customer_id,

        TRIM(attrition_flag) AS attrition_status,

        CASE
            WHEN attrition_flag = 'Attrited Customer' THEN 1
            WHEN attrition_flag = 'Existing Customer' THEN 0
        END AS churn_flag,

        customer_age,
        TRIM(gender) AS gender,
        dependent_count,
        TRIM(education_level) AS education_level,
        TRIM(marital_status) AS marital_status,
        TRIM(income_category) AS income_category,
        TRIM(card_category) AS card_category,

        months_on_book,
        total_relationship_count,
        months_inactive_12_mon AS months_inactive_last_12m,
        contacts_count_12_mon AS contacts_count_last_12m,

        credit_limit,
        total_revolving_bal AS total_revolving_balance,
        avg_open_to_buy AS average_open_to_buy,
        total_amt_chng_q4_q1 AS amount_change_q4_q1,

        total_trans_amt AS total_transaction_amount,
        total_trans_ct AS total_transaction_count,
        total_ct_chng_q4_q1 AS transaction_count_change_q4_q1,
        avg_utilization_ratio AS average_utilization_ratio

    FROM source_data

)

SELECT *
FROM staged