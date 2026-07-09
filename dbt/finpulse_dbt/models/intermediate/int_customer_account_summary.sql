{{ config(materialized='view') }}

WITH account_summary AS (

    SELECT
        customer_id,
        COUNT(account_id) AS total_accounts,
        SUM(balance_usd) AS total_balance_usd,
        AVG(balance_usd) AS avg_balance_usd,
        MIN(balance_usd) AS min_balance_usd,
        MAX(balance_usd) AS max_balance_usd,
        SUM(CASE WHEN account_type = 'Checking' THEN 1 ELSE 0 END) AS checking_accounts,
        SUM(CASE WHEN account_type = 'Savings' THEN 1 ELSE 0 END) AS savings_accounts,
        SUM(CASE WHEN account_type = 'Business' THEN 1 ELSE 0 END) AS business_accounts,
        MIN(open_date) AS first_account_open_date,
        MAX(open_date) AS last_account_open_date
    FROM {{ ref('stg_accounts') }}
    GROUP BY customer_id

)

SELECT
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.city,
    c.credit_score,
    c.created_at AS customer_created_at,

    COALESCE(a.total_accounts, 0) AS total_accounts,
    COALESCE(a.total_balance_usd, 0) AS total_balance_usd,
    COALESCE(a.avg_balance_usd, 0) AS avg_balance_usd,
    COALESCE(a.min_balance_usd, 0) AS min_balance_usd,
    COALESCE(a.max_balance_usd, 0) AS max_balance_usd,

    COALESCE(a.checking_accounts, 0) AS checking_accounts,
    COALESCE(a.savings_accounts, 0) AS savings_accounts,
    COALESCE(a.business_accounts, 0) AS business_accounts,

    a.first_account_open_date,
    a.last_account_open_date

FROM {{ ref('stg_customers') }} c
LEFT JOIN account_summary a
    ON c.customer_id = a.customer_id