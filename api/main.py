import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from api.database import check_database_connection

from api.customer_repository import (
    get_customer_by_id,
    list_customers,
)

from api.customer_repository import get_customer_by_id
from api.model_service import ModelService
from api.portfolio_repository import get_portfolio_summary
from api.schemas import (
    CustomerPredictionResponse,
    CustomerResponse,
    PortfolioSummaryResponse,
    PredictionRequest,
    PredictionResponse,
    StoredPredictionResponse,
    CustomerListResponse,
    RiskBand,
)



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_FEATURE_NAMES = tuple(PredictionRequest.model_fields)


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_service = ModelService()

    app.state.model_service = model_service
    app.state.model_load_error = None

    try:
        model_service.load()
        logger.info(
            "Champion model loaded successfully: %s",
            model_service.get_info(),
        )
    except Exception as exc:
        app.state.model_load_error = str(exc)
        logger.exception("Failed to load champion model.")

    yield


app = FastAPI(
    title="FinPulse Churn API",
    description="API de serving do modelo champion de churn bancário.",
    version="0.5.0",
    lifespan=lifespan,
)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "service": "finpulse-churn-api",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health(
    request: Request,
    response: Response,
) -> dict[str, object]:
    model_service: ModelService = request.app.state.model_service
    model_loaded = model_service.is_loaded

    database_healthy = True

    try:
        check_database_connection()
    except SQLAlchemyError:
        database_healthy = False

    service_ready = model_loaded and database_healthy

    if not service_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": (
            "healthy"
            if service_ready
            else "degraded"
        ),
        "service": "finpulse-churn-api",
        "version": "0.5.0",
        "components": {
            "api": {
                "status": "healthy",
            },
            "model": {
                "status": (
                    "healthy"
                    if model_loaded
                    else "unhealthy"
                ),
                "loaded": model_loaded,
                "alias": "champion",
            },
            "database": {
                "status": (
                    "healthy"
                    if database_healthy
                    else "unhealthy"
                ),
            },
        },
    }


@app.get("/model-info", tags=["model"])
def model_info(request: Request) -> dict[str, object]:
    model_service: ModelService = request.app.state.model_service

    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Champion model is not available.",
                "error": request.app.state.model_load_error,
            },
        )

    return model_service.get_info()


@app.get(
    "/portfolio/summary",
    response_model=PortfolioSummaryResponse,
    tags=["portfolio"],
)
def portfolio_summary() -> PortfolioSummaryResponse:
    try:
        summary = get_portfolio_summary()
    except SQLAlchemyError as exc:
        logger.exception("Portfolio summary query failed.")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Portfolio database is unavailable.",
        ) from exc

    return PortfolioSummaryResponse(**summary)

@app.get(
    "/customers",
    response_model=CustomerListResponse,
    tags=["customers"],
)
def customer_list(
    risk_band: RiskBand | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CustomerListResponse:
    try:
        customers, total_matching = list_customers(
            risk_band=(
                risk_band.value
                if risk_band is not None
                else None
            ),
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as exc:
        logger.exception("Customer list query failed.")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Customer database is unavailable.",
        ) from exc

    return CustomerListResponse(
        risk_band=risk_band,
        total_matching=total_matching,
        returned_count=len(customers),
        limit=limit,
        offset=offset,
        customers=customers,
    )


@app.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    tags=["customers"],
)
def customer_details(
    customer_id: int,
) -> CustomerResponse:
    try:
        customer = get_customer_by_id(customer_id)
    except SQLAlchemyError as exc:
        logger.exception(
            "Database query failed for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Customer database is unavailable.",
        ) from exc

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} was not found.",
        )

    features_data = {
        feature_name: customer[feature_name]
        for feature_name in MODEL_FEATURE_NAMES
    }

    stored_prediction = None

    if customer["churn_prediction"] is not None:
        stored_prediction = StoredPredictionResponse(
            churn_probability=float(customer["churn_probability"]),
            risk_band=str(customer["risk_band"]),
            churn_prediction=int(customer["churn_prediction"]),
            model_name=str(customer["model_name"]),
            model_version=int(customer["model_version"]),
            model_alias=str(customer["model_alias"]),
            scored_at=customer["scored_at"],
            scoring_run_id=str(customer["scoring_run_id"]),
        )

    return CustomerResponse(
        customer_id=int(customer["customer_id"]),
        features=PredictionRequest(**features_data),
        prediction=stored_prediction,
    )


@app.post(
    "/customers/{customer_id}/predict",
    response_model=CustomerPredictionResponse,
    tags=["customers"],
)
def predict_customer_by_id(
    customer_id: int,
    request: Request,
) -> CustomerPredictionResponse:
    model_service: ModelService = request.app.state.model_service

    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Champion model is not available.",
        )

    try:
        customer = get_customer_by_id(customer_id)
    except SQLAlchemyError as exc:
        logger.exception(
            "Database query failed for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Customer database is unavailable.",
        ) from exc

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} was not found.",
        )

    features_data = {
        feature_name: customer[feature_name]
        for feature_name in MODEL_FEATURE_NAMES
    }
    validated_features = PredictionRequest(**features_data)
    model_input = pd.DataFrame([validated_features.model_dump()])

    try:
        churn_prediction = model_service.predict(model_input)
        model_info_data = model_service.get_info()
    except Exception as exc:
        logger.exception(
            "Prediction failed for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed.",
        ) from exc

    stored_prediction = customer["churn_prediction"]

    if stored_prediction is not None:
        stored_prediction = int(stored_prediction)

    matches_stored_prediction = (
        churn_prediction == stored_prediction
        if stored_prediction is not None
        else None
    )

    return CustomerPredictionResponse(
        customer_id=customer_id,
        churn_prediction=churn_prediction,
        prediction_label=(
            "churn" if churn_prediction == 1 else "no_churn"
        ),
        stored_churn_prediction=stored_prediction,
        matches_stored_prediction=matches_stored_prediction,
        model_name=str(model_info_data["name"]),
        model_version=int(model_info_data["version"]),
        model_alias=str(model_info_data["alias"]),
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["model"],
)
def predict(
    payload: PredictionRequest,
    request: Request,
) -> PredictionResponse:
    model_service: ModelService = request.app.state.model_service

    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Champion model is not available.",
        )

    model_input = pd.DataFrame([payload.model_dump()])

    try:
        churn_prediction = model_service.predict(model_input)
        model_info_data = model_service.get_info()
    except Exception as exc:
        logger.exception("Prediction failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed.",
        ) from exc

    prediction_label = (
        "churn" if churn_prediction == 1 else "no_churn"
    )

    return PredictionResponse(
        churn_prediction=churn_prediction,
        prediction_label=prediction_label,
        model_name=str(model_info_data["name"]),
        model_version=int(model_info_data["version"]),
        model_alias=str(model_info_data["alias"]),
    )