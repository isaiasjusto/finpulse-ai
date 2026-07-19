from pydantic import BaseModel, ConfigDict


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_age: int
    gender: str
    dependent_count: int
    education_level: str
    marital_status: str
    income_category: str
    card_category: str
    months_on_book: int
    total_relationship_count: int
    months_inactive_last_12m: int
    contacts_count_last_12m: int
    credit_limit: float
    total_revolving_balance: float
    average_open_to_buy: float
    amount_change_q4_q1: float
    total_transaction_amount: float
    total_transaction_count: int
    transaction_count_change_q4_q1: float
    average_utilization_ratio: float


class PredictionResponse(BaseModel):
    churn_prediction: int
    prediction_label: str
    model_name: str
    model_version: int
    model_alias: str