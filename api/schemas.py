from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum

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

class StoredPredictionResponse(BaseModel):
    churn_probability: float
    risk_band: str
    churn_prediction: int
    model_name: str
    model_version: int
    model_alias: str
    scored_at: datetime
    scoring_run_id: str


class CustomerResponse(BaseModel):
    customer_id: int
    features: PredictionRequest
    prediction: StoredPredictionResponse | None

class CustomerPredictionResponse(BaseModel):
    customer_id: int
    churn_prediction: int
    prediction_label: str
    stored_churn_prediction: int | None
    matches_stored_prediction: bool | None
    model_name: str
    model_version: int
    model_alias: str

class PortfolioSummaryResponse(BaseModel):
    total_customers: int
    predicted_churn_customers: int
    predicted_churn_rate: float
    average_churn_probability: float
    low_risk_customers: int
    medium_risk_customers: int
    high_risk_customers: int
    minimum_model_version: int
    maximum_model_version: int
    model_alias: str
    latest_scoring_at: datetime

class RiskBand(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class CustomerListItemResponse(BaseModel):
    customer_id: int
    customer_age: int
    gender: str
    churn_probability: float
    risk_band: RiskBand
    churn_prediction: int
    model_version: int
    model_alias: str
    scored_at: datetime


class CustomerListResponse(BaseModel):
    risk_band: RiskBand | None
    total_matching: int
    returned_count: int
    limit: int
    offset: int
    customers: list[CustomerListItemResponse]