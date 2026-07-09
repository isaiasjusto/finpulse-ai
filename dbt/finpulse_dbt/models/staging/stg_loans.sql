{{ config(materialized='view') }}

SELECT
    loan_id,
    customer_id,
    loan_amount,
    interest_rate,
    start_date
FROM {{ source('raw', 'loans') }}