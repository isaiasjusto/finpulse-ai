# Data Lake Structure

FinPulse AI uses MinIO as a local S3-compatible data lake.

The goal is to simulate a cloud data lake architecture while keeping the project fully reproducible in a local Docker environment.

## Buckets

| Bucket | Purpose |
|---|---|
| raw | Original source files |
| processed | Intermediate transformed files |
| curated | Final analytical datasets |
| models | Trained machine learning artifacts |
| reports | Reports, exports and analysis outputs |

## Raw Layer

The `raw` bucket stores the original SQL files used to create and populate the PostgreSQL database.

Current structure:

```text
raw/sql/
├── 001_create_tables.sql
├── 001_data_quality_checks.sql
├── accounts_inserts.sql
├── bank.sql
├── branches_inserts.sql
├── cards_inserts.sql
├── customers_inserts.sql
├── loans_inserts.sql
├── merchants_inserts.sql
└── transactions_inserts.sql