{{ config(materialized='view') }}

SELECT
    customer_id,
    first_name,
    last_name,
    email,
    city,
    credit_score,
    created_at
FROM {{ source('raw', 'customers') }}