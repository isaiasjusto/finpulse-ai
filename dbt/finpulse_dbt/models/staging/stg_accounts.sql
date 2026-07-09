{{ config(materialized='view') }}

SELECT
    account_id,
    customer_id,
    account_type,
    balance_usd,
    open_date
FROM {{ source('raw', 'accounts') }}