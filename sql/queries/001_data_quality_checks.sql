/* ============================================================
   FinPulse AI
   Data Quality Checks - Raw PostgreSQL Layer

   Objetivo:
   Validar a carga inicial das tabelas relacionais do dataset bancário.

   Tabelas:
   - customers
   - accounts
   - cards
   - merchants
   - branches
   - loans
   - transactions
   ============================================================ */


-- ============================================================
-- 1. CONTAGEM DE REGISTROS POR TABELA
-- Esperado pela documentação:
-- customers:     50.000
-- accounts:      75.000
-- cards:        100.000
-- merchants:      5.000
-- branches:         500
-- loans:         30.000
-- transactions: 1.000.000
-- ============================================================

SELECT 'customers' AS table_name, COUNT(*) AS total_records FROM customers
UNION ALL
SELECT 'accounts' AS table_name, COUNT(*) AS total_records FROM accounts
UNION ALL
SELECT 'cards' AS table_name, COUNT(*) AS total_records FROM cards
UNION ALL
SELECT 'merchants' AS table_name, COUNT(*) AS total_records FROM merchants
UNION ALL
SELECT 'branches' AS table_name, COUNT(*) AS total_records FROM branches
UNION ALL
SELECT 'loans' AS table_name, COUNT(*) AS total_records FROM loans
UNION ALL
SELECT 'transactions' AS table_name, COUNT(*) AS total_records FROM transactions
ORDER BY table_name;


-- ============================================================
-- 2. VALIDAÇÃO DE CHAVES PRIMÁRIAS DUPLICADAS
-- O esperado é todas retornarem 0.
-- ============================================================

SELECT 'customers' AS table_name, COUNT(*) AS duplicated_ids
FROM (
    SELECT customer_id
    FROM customers
    GROUP BY customer_id
    HAVING COUNT(*) > 1
) duplicated

UNION ALL

SELECT 'accounts' AS table_name, COUNT(*) AS duplicated_ids
FROM (
    SELECT account_id
    FROM accounts
    GROUP BY account_id
    HAVING COUNT(*) > 1
) duplicated

UNION ALL

SELECT 'cards' AS table_name, COUNT(*) AS duplicated_ids
FROM (
    SELECT card_id
    FROM cards
    GROUP BY card_id
    HAVING COUNT(*) > 1
) duplicated

UNION ALL

SELECT 'merchants' AS table_name, COUNT(*) AS duplicated_ids
FROM (
    SELECT merchant_id
    FROM merchants
    GROUP BY merchant_id
    HAVING COUNT(*) > 1
) duplicated

UNION ALL

SELECT 'branches' AS table_name, COUNT(*) AS duplicated_ids
FROM (
    SELECT branch_id
    FROM branches
    GROUP BY branch_id
    HAVING COUNT(*) > 1
) duplicated

UNION ALL

SELECT 'loans' AS table_name, COUNT(*) AS duplicated_ids
FROM (
    SELECT loan_id
    FROM loans
    GROUP BY loan_id
    HAVING COUNT(*) > 1
) duplicated

UNION ALL

SELECT 'transactions' AS table_name, COUNT(*) AS duplicated_ids
FROM (
    SELECT transaction_id
    FROM transactions
    GROUP BY transaction_id
    HAVING COUNT(*) > 1
) duplicated

ORDER BY table_name;


-- ============================================================
-- 3. VALIDAÇÃO DE CAMPOS NULOS IMPORTANTES
-- O esperado idealmente é 0 nos campos críticos.
-- ============================================================

SELECT 'customers' AS table_name, 'customer_id' AS column_name, COUNT(*) AS null_records
FROM customers
WHERE customer_id IS NULL

UNION ALL

SELECT 'customers', 'credit_score', COUNT(*)
FROM customers
WHERE credit_score IS NULL

UNION ALL

SELECT 'accounts', 'account_id', COUNT(*)
FROM accounts
WHERE account_id IS NULL

UNION ALL

SELECT 'accounts', 'customer_id', COUNT(*)
FROM accounts
WHERE customer_id IS NULL

UNION ALL

SELECT 'accounts', 'balance_usd', COUNT(*)
FROM accounts
WHERE balance_usd IS NULL

UNION ALL

SELECT 'cards', 'card_id', COUNT(*)
FROM cards
WHERE card_id IS NULL

UNION ALL

SELECT 'cards', 'account_id', COUNT(*)
FROM cards
WHERE account_id IS NULL

UNION ALL

SELECT 'loans', 'loan_id', COUNT(*)
FROM loans
WHERE loan_id IS NULL

UNION ALL

SELECT 'loans', 'customer_id', COUNT(*)
FROM loans
WHERE customer_id IS NULL

UNION ALL

SELECT 'transactions', 'transaction_id', COUNT(*)
FROM transactions
WHERE transaction_id IS NULL

UNION ALL

SELECT 'transactions', 'account_id', COUNT(*)
FROM transactions
WHERE account_id IS NULL

UNION ALL

SELECT 'transactions', 'merchant_id', COUNT(*)
FROM transactions
WHERE merchant_id IS NULL

UNION ALL

SELECT 'transactions', 'amount_usd', COUNT(*)
FROM transactions
WHERE amount_usd IS NULL

UNION ALL

SELECT 'transactions', 'transaction_date', COUNT(*)
FROM transactions
WHERE transaction_date IS NULL

ORDER BY table_name, column_name;


-- ============================================================
-- 4. INTEGRIDADE REFERENCIAL
-- O esperado é todas retornarem 0.
-- ============================================================

-- Accounts sem cliente correspondente
SELECT COUNT(*) AS accounts_without_customer
FROM accounts a
LEFT JOIN customers c
    ON a.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- Cards sem conta correspondente
SELECT COUNT(*) AS cards_without_account
FROM cards ca
LEFT JOIN accounts a
    ON ca.account_id = a.account_id
WHERE a.account_id IS NULL;


-- Loans sem cliente correspondente
SELECT COUNT(*) AS loans_without_customer
FROM loans l
LEFT JOIN customers c
    ON l.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- Transactions sem conta correspondente
SELECT COUNT(*) AS transactions_without_account
FROM transactions t
LEFT JOIN accounts a
    ON t.account_id = a.account_id
WHERE a.account_id IS NULL;


-- Transactions sem merchant correspondente
SELECT COUNT(*) AS transactions_without_merchant
FROM transactions t
LEFT JOIN merchants m
    ON t.merchant_id = m.merchant_id
WHERE m.merchant_id IS NULL;


-- ============================================================
-- 5. CHECKS DE VALORES FINANCEIROS
-- Aqui não necessariamente tudo precisa ser 0.
-- Depende da regra de negócio.
-- ============================================================

-- Contas com saldo negativo
SELECT COUNT(*) AS accounts_with_negative_balance
FROM accounts
WHERE balance_usd < 0;


-- Empréstimos com valor menor ou igual a zero
SELECT COUNT(*) AS loans_with_invalid_amount
FROM loans
WHERE loan_amount <= 0;


-- Empréstimos com taxa de juros negativa
SELECT COUNT(*) AS loans_with_negative_interest_rate
FROM loans
WHERE interest_rate < 0;


-- Transações com valor igual a zero
SELECT COUNT(*) AS transactions_with_zero_amount
FROM transactions
WHERE amount_usd = 0;


-- Transações com valor negativo
SELECT COUNT(*) AS transactions_with_negative_amount
FROM transactions
WHERE amount_usd < 0;


-- ============================================================
-- 6. DISTRIBUIÇÕES BÁSICAS
-- Essas queries ajudam a entender o dataset.
-- ============================================================

-- Distribuição de tipos de conta
SELECT
    account_type,
    COUNT(*) AS total_accounts,
    ROUND(AVG(balance_usd), 2) AS avg_balance_usd,
    ROUND(MIN(balance_usd), 2) AS min_balance_usd,
    ROUND(MAX(balance_usd), 2) AS max_balance_usd
FROM accounts
GROUP BY account_type
ORDER BY total_accounts DESC;


-- Distribuição de tipos de cartão
SELECT
    card_type,
    COUNT(*) AS total_cards
FROM cards
GROUP BY card_type
ORDER BY total_cards DESC;


-- Distribuição de score de crédito
SELECT
    MIN(credit_score) AS min_credit_score,
    ROUND(AVG(credit_score), 2) AS avg_credit_score,
    MAX(credit_score) AS max_credit_score
FROM customers;


-- ============================================================
-- DISTRIBUIÇÃO DE SCORE DE CRÉDITO CONFORME DOCUMENTAÇÃO
-- ============================================================

SELECT
    CASE
        WHEN credit_score >= 750 THEN '01. Excellent (750+)'
        WHEN credit_score BETWEEN 700 AND 749 THEN '02. Good (700-749)'
        WHEN credit_score BETWEEN 650 AND 699 THEN '03. Fair (650-699)'
        WHEN credit_score BETWEEN 600 AND 649 THEN '04. Poor (600-649)'
        WHEN credit_score < 600 THEN '05. Very Poor (<600)'
    END AS credit_score_segment,
    COUNT(*) AS total_customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM customers
GROUP BY
    CASE
        WHEN credit_score >= 750 THEN '01. Excellent (750+)'
        WHEN credit_score BETWEEN 700 AND 749 THEN '02. Good (700-749)'
        WHEN credit_score BETWEEN 650 AND 699 THEN '03. Fair (650-699)'
        WHEN credit_score BETWEEN 600 AND 649 THEN '04. Poor (600-649)'
        WHEN credit_score < 600 THEN '05. Very Poor (<600)'
    END
ORDER BY credit_score_segment;


-- ============================================================
-- 7. PERÍODO DOS DADOS
-- Importante para saber a janela temporal disponível.
-- ============================================================

SELECT
    MIN(created_at) AS first_customer_created_at,
    MAX(created_at) AS last_customer_created_at
FROM customers;


SELECT
    MIN(open_date) AS first_account_open_date,
    MAX(open_date) AS last_account_open_date
FROM accounts;


SELECT
    MIN(start_date) AS first_loan_start_date,
    MAX(start_date) AS last_loan_start_date
FROM loans;


SELECT
    MIN(transaction_date) AS first_transaction_date,
    MAX(transaction_date) AS last_transaction_date
FROM transactions;


-- ============================================================
-- 8. AMOSTRA RELACIONAL
-- Confirma se o join principal para comportamento financeiro funciona.
-- ============================================================

SELECT
    t.transaction_id,
    t.transaction_date,
    t.amount_usd,
    a.account_id,
    a.account_type,
    a.balance_usd,
    c.customer_id,
    c.first_name,
    c.last_name,
    c.credit_score,
    m.merchant_id,
    m.merchant_name,
    m.city AS merchant_city
FROM transactions t
INNER JOIN accounts a
    ON t.account_id = a.account_id
INNER JOIN customers c
    ON a.customer_id = c.customer_id
INNER JOIN merchants m
    ON t.merchant_id = m.merchant_id
LIMIT 100;