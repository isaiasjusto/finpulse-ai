{{ config(materialized='table') }}

SELECT
    a.customer_id,
    a.first_name,
    a.last_name,

    -- Dados principais do cliente
    a.email,
    a.city,
    a.credit_score,
    a.customer_created_at,

    -- Contas
    a.total_accounts,
    a.total_balance_usd,
    a.avg_balance_usd,
    a.min_balance_usd,
    a.max_balance_usd,
    a.checking_accounts,
    a.savings_accounts,
    a.business_accounts,
    a.first_account_open_date,
    a.last_account_open_date,

    -- Cartões
    c.has_card,
    c.total_cards,
    c.credit_cards,
    c.debit_cards,
    c.first_card_expiration_date,
    c.last_card_expiration_date,

    -- Empréstimos
    l.has_loan,
    l.total_loans,
    l.total_loan_amount,
    l.avg_loan_amount,
    l.min_loan_amount,
    l.max_loan_amount,
    l.avg_interest_rate,
    l.min_interest_rate,
    l.max_interest_rate,
    l.first_loan_start_date,
    l.last_loan_start_date,

    -- Transações
    t.has_transaction,
    t.total_transactions,
    t.total_transaction_amount_usd,
    t.avg_transaction_amount_usd,
    t.min_transaction_amount_usd,
    t.max_transaction_amount_usd,
    t.first_transaction_date,
    t.last_transaction_date,
    t.active_transaction_days,
    t.merchant_diversity,
    t.merchant_city_diversity

FROM {{ ref('int_customer_account_summary') }} a

LEFT JOIN {{ ref('int_customer_card_summary') }} c
    ON a.customer_id = c.customer_id

LEFT JOIN {{ ref('int_customer_loan_summary') }} l
    ON a.customer_id = l.customer_id

LEFT JOIN {{ ref('int_customer_transaction_summary') }} t
    ON a.customer_id = t.customer_id