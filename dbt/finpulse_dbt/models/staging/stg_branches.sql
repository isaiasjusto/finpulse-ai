{{ config(materialized='view') }}

SELECT
    branch_id,
    branch_name,
    manager_name,
    city,
    country
FROM {{ source('raw', 'branches') }}