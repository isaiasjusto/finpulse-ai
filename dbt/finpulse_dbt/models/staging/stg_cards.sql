{{ config(materialized='view') }}

SELECT
    card_id,
    account_id,
    card_type,
    expiration_date
FROM {{ source('raw', 'cards') }}