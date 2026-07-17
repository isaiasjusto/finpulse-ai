-- Database used by the MLflow Tracking Server.
CREATE DATABASE mlflow;


-- Restricted user used by dbt transformations.
CREATE ROLE dbt_user
WITH
    LOGIN
    PASSWORD 'dbt_password';


GRANT CONNECT
ON DATABASE finpulse
TO dbt_user;


\connect finpulse


-- Raw data is loaded by finpulse_user.
CREATE SCHEMA IF NOT EXISTS raw
AUTHORIZATION finpulse_user;


-- Analytical schemas are managed by dbt_user.
CREATE SCHEMA IF NOT EXISTS staging
AUTHORIZATION dbt_user;


CREATE SCHEMA IF NOT EXISTS marts
AUTHORIZATION dbt_user;


GRANT USAGE
ON SCHEMA raw
TO dbt_user;


GRANT SELECT
ON ALL TABLES IN SCHEMA raw
TO dbt_user;


-- Future raw tables automatically become readable by dbt.
ALTER DEFAULT PRIVILEGES
FOR ROLE finpulse_user
IN SCHEMA raw
GRANT SELECT ON TABLES TO dbt_user;