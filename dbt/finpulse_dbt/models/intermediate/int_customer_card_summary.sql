{{ config(materialized='view') }}

WITH customer_cards AS (

    SELECT
        a.customer_id,
        c.card_id,
        c.card_type,
        c.expiration_date
    FROM {{ ref('stg_cards') }} c
    INNER JOIN {{ ref('stg_accounts') }} a
        ON c.account_id = a.account_id

),

card_summary AS (

    SELECT
        customer_id,

        COUNT(card_id) AS total_cards,

        SUM(CASE WHEN card_type = 'Credit' THEN 1 ELSE 0 END) AS credit_cards,
        SUM(CASE WHEN card_type = 'Debit' THEN 1 ELSE 0 END) AS debit_cards,

        MIN(expiration_date) AS first_card_expiration_date,
        MAX(expiration_date) AS last_card_expiration_date

    FROM customer_cards
    GROUP BY customer_id

)

SELECT
    c.customer_id,
    c.first_name,
    c.last_name,

    CASE
        WHEN COALESCE(cs.total_cards, 0) > 0 THEN 1
        ELSE 0
    END AS has_card,

    COALESCE(cs.total_cards, 0) AS total_cards,
    COALESCE(cs.credit_cards, 0) AS credit_cards,
    COALESCE(cs.debit_cards, 0) AS debit_cards,

    cs.first_card_expiration_date,
    cs.last_card_expiration_date

FROM {{ ref('stg_customers') }} c
LEFT JOIN card_summary cs
    ON c.customer_id = cs.customer_id