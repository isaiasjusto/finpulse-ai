{{ config(materialized='view') }}

WITH customer_transactions AS (

    SELECT
        a.customer_id,
        t.transaction_id,
        t.account_id,
        t.merchant_id,
        t.amount_usd,
        t.transaction_date,
        m.merchant_name,
        m.city AS merchant_city
    FROM {{ ref('stg_transactions') }} t
    INNER JOIN {{ ref('stg_accounts') }} a
        ON t.account_id = a.account_id
    LEFT JOIN {{ ref('stg_merchants') }} m
        ON t.merchant_id = m.merchant_id

),

transaction_summary AS (

    SELECT
        customer_id,

        COUNT(transaction_id) AS total_transactions,

        SUM(amount_usd) AS total_transaction_amount_usd,
        AVG(amount_usd) AS avg_transaction_amount_usd,
        MIN(amount_usd) AS min_transaction_amount_usd,
        MAX(amount_usd) AS max_transaction_amount_usd,

        MIN(transaction_date) AS first_transaction_date,
        MAX(transaction_date) AS last_transaction_date,

        COUNT(DISTINCT transaction_date::date) AS active_transaction_days,
        COUNT(DISTINCT merchant_id) AS merchant_diversity,
        COUNT(DISTINCT merchant_city) AS merchant_city_diversity

    FROM customer_transactions
    GROUP BY customer_id

)

SELECT
    c.customer_id,
    c.first_name,
    c.last_name,

    CASE
        WHEN COALESCE(ts.total_transactions, 0) > 0 THEN 1
        ELSE 0
    END AS has_transaction,

    COALESCE(ts.total_transactions, 0) AS total_transactions,

    COALESCE(ts.total_transaction_amount_usd, 0) AS total_transaction_amount_usd,
    COALESCE(ts.avg_transaction_amount_usd, 0) AS avg_transaction_amount_usd,
    COALESCE(ts.min_transaction_amount_usd, 0) AS min_transaction_amount_usd,
    COALESCE(ts.max_transaction_amount_usd, 0) AS max_transaction_amount_usd,

    ts.first_transaction_date,
    ts.last_transaction_date,

    COALESCE(ts.active_transaction_days, 0) AS active_transaction_days,
    COALESCE(ts.merchant_diversity, 0) AS merchant_diversity,
    COALESCE(ts.merchant_city_diversity, 0) AS merchant_city_diversity

FROM {{ ref('stg_customers') }} c
LEFT JOIN transaction_summary ts
    ON c.customer_id = ts.customer_id