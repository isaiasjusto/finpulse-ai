{{ config(materialized='view') }}

SELECT
    transaction_id,
    account_id,
    merchant_id,
    amount_usd,
    transaction_date
FROM {{ source('raw', 'transactions') }}