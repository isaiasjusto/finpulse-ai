{{ config(materialized='view') }}

WITH loan_summary AS (

    SELECT
        customer_id,

        COUNT(loan_id) AS total_loans,

        SUM(loan_amount) AS total_loan_amount,
        AVG(loan_amount) AS avg_loan_amount,
        MIN(loan_amount) AS min_loan_amount,
        MAX(loan_amount) AS max_loan_amount,

        AVG(interest_rate) AS avg_interest_rate,
        MIN(interest_rate) AS min_interest_rate,
        MAX(interest_rate) AS max_interest_rate,

        MIN(start_date) AS first_loan_start_date,
        MAX(start_date) AS last_loan_start_date

    FROM {{ ref('stg_loans') }}
    GROUP BY customer_id

)

SELECT
    c.customer_id,
    c.first_name,
    c.last_name,

    CASE
        WHEN COALESCE(ls.total_loans, 0) > 0 THEN 1
        ELSE 0
    END AS has_loan,

    COALESCE(ls.total_loans, 0) AS total_loans,

    COALESCE(ls.total_loan_amount, 0) AS total_loan_amount,
    COALESCE(ls.avg_loan_amount, 0) AS avg_loan_amount,
    COALESCE(ls.min_loan_amount, 0) AS min_loan_amount,
    COALESCE(ls.max_loan_amount, 0) AS max_loan_amount,

    COALESCE(ls.avg_interest_rate, 0) AS avg_interest_rate,
    COALESCE(ls.min_interest_rate, 0) AS min_interest_rate,
    COALESCE(ls.max_interest_rate, 0) AS max_interest_rate,

    ls.first_loan_start_date,
    ls.last_loan_start_date

FROM {{ ref('stg_customers') }} c
LEFT JOIN loan_summary ls
    ON c.customer_id = ls.customer_id