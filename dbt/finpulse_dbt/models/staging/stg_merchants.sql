{{ config(materialized='view') }}

SELECT
    merchant_id,
    merchant_name,
    city
FROM {{ source('raw', 'merchants') }}