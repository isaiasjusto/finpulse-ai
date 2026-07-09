
CREATE DATABASE bank;
USE bank;

CREATE TABLE customers(
 customer_id VARCHAR(20) PRIMARY KEY,
 first_name VARCHAR(50),
 last_name VARCHAR(50),
 email VARCHAR(100),
 city VARCHAR(50),
 credit_score INT,
 created_at DATETIME
);

CREATE TABLE accounts(
 account_id VARCHAR(20) PRIMARY KEY,
 customer_id VARCHAR(20),
 account_type VARCHAR(20),
 balance_usd DECIMAL(12,2),
 open_date DATE,
 FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE cards(
 card_id VARCHAR(20) PRIMARY KEY,
 account_id VARCHAR(20),
 card_type VARCHAR(20),
 expiration_date DATE,
 FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE merchants(
 merchant_id VARCHAR(20) PRIMARY KEY,
 merchant_name VARCHAR(100),
 city VARCHAR(50)
);

CREATE TABLE branches(
 branch_id VARCHAR(20) PRIMARY KEY,
 branch_name VARCHAR(100),
 manager_name VARCHAR(100),
 city VARCHAR(50),
 country VARCHAR(50)      
);

CREATE TABLE loans(
 loan_id VARCHAR(20) PRIMARY KEY,
 customer_id VARCHAR(20),
 loan_amount DECIMAL(12,2),
 interest_rate DECIMAL(5,2),
 start_date DATE,
 FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE transactions(
 transaction_id VARCHAR(25) PRIMARY KEY,
 account_id VARCHAR(20),
 merchant_id VARCHAR(20),
 amount_usd DECIMAL(12,2),
 transaction_date DATETIME,  -- <- بدل DATE
 FOREIGN KEY (account_id) REFERENCES accounts(account_id),
 FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id)
);
