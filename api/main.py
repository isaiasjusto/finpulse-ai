import logging
from contextlib import asynccontextmanager

from api.schemas import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantScope,
)

import pandas as pd

from sqlalchemy.exc import SQLAlchemyError

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from datetime import datetime, timezone

from api.config import settings

from api.retention_catalog import get_allowed_retention_actions

from api.database import check_database_connection

from api.customer_repository import (
    get_customer_by_id,
    get_explainability_sample,
    list_customers,
)

from api.model_service import ModelService
from api.portfolio_repository import get_portfolio_summary
from api.schemas import (
    ConfusionMatrixResponse,
    CustomerListResponse,
    CustomerPredictionResponse,
    CustomerResponse,
    GlobalExplainabilityResponse,
    IndividualExplainabilityResponse,
    LatestScoringResponse,
    PortfolioSummaryResponse,
    PredictionRequest,
    PredictionResponse,
    RiskBand,
    StoredPredictionResponse,
    CustomerRetentionRecommendationResponse,
    RecommendationGenerationResponse,
)

from api.retention_ai_service import (
    RetentionAIInvalidResponseError,
    RetentionAIService,
    RetentionAITimeoutError,
    RetentionAIUnavailableError,
)

from api.assistant_ai_service import (
    AssistantAIInvalidResponseError,
    AssistantAITimeoutError,
    AssistantAIUnavailableError,
)
from api.assistant_service import (
    AssistantContextUnavailableError,
    AssistantCustomerNotFoundError,
    AssistantService,
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
    "/model-explainability/global",
    response_model=GlobalExplainabilityResponse,
    tags=["explainability"],
)
def global_model_explainability(
    request: Request,
    sample_size: int = Query(default=500, ge=100, le=5000),
) -> GlobalExplainabilityResponse:
    model_service: ModelService = request.app.state.model_service

    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Champion model is not available.",
        )

    try:
        sample_rows = get_explainability_sample(sample_size)
    except SQLAlchemyError as exc:
        logger.exception(
            "Explainability sample query failed."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Explainability database is unavailable.",
        ) from exc

    if not sample_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No customers are available for explainability.",
        )

    try:
        result = model_service.get_global_explainability(
            pd.DataFrame(sample_rows)
        )
    except Exception as exc:
        logger.exception(
            "Global explainability calculation failed."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Global explainability calculation failed.",
        ) from exc

    return GlobalExplainabilityResponse(**result)

@app.get(
    "/model-evaluation/confusion-matrix",
    response_model=ConfusionMatrixResponse,
    tags=["model-evaluation"],
)
def model_confusion_matrix(
    request: Request,
) -> ConfusionMatrixResponse:
    model_service: ModelService = request.app.state.model_service

    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Champion model is not available.",
        )

    try:
        result = model_service.get_confusion_matrix()
    except RuntimeError as exc:
        logger.exception(
            "Confusion matrix reconstruction failed."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Confusion matrix reconstruction failed.",
        ) from exc

    return ConfusionMatrixResponse(**result)

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
    "/scoring/latest",
    response_model=LatestScoringResponse,
    tags=["scoring"],
)
def latest_scoring(
    request: Request,
) -> LatestScoringResponse:
    model_service: ModelService = request.app.state.model_service

    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Champion model is not available.",
        )

    try:
        portfolio_summary_data = get_portfolio_summary()
    except SQLAlchemyError as exc:
        logger.exception(
            "Latest scoring summary query failed."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scoring database is unavailable.",
        ) from exc

    model_info_data = model_service.get_info()
    metrics_data = model_service.get_metrics()

    return LatestScoringResponse(
        status="available",
        model={
            "name": str(model_info_data["name"]),
            "alias": str(model_info_data["alias"]),
            "version": int(model_info_data["version"]),
            "run_id": str(model_info_data["run_id"]),
            "status": str(model_info_data["status"]),
        },
        scoring={
            "executed_at": portfolio_summary_data[
                "latest_scoring_at"
            ],
            "population_scored": int(
                portfolio_summary_data["total_customers"]
            ),
        },
        metrics={
            "roc_auc": metrics_data["roc_auc"],
            "balanced_accuracy": metrics_data[
                "balanced_accuracy"
            ],
            "f1": metrics_data["f1"],
            "precision": metrics_data["precision"],
            "recall": metrics_data["recall"],
            "ks": metrics_data["ks"],
            "psi": metrics_data["psi"],
        },
    )

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
    "/customers/{customer_id}/explainability",
    response_model=IndividualExplainabilityResponse,
    tags=["customers"],
)
def customer_explainability(
    customer_id: int,
    request: Request,
) -> IndividualExplainabilityResponse:
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

    if (
        customer["churn_prediction"] is None
        or customer["churn_probability"] is None
        or customer["risk_band"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Customer {customer_id} does not have "
                "a stored scoring result."
            ),
        )

    features_data = {
        feature_name: customer[feature_name]
        for feature_name in MODEL_FEATURE_NAMES
    }

    validated_features = PredictionRequest(**features_data)
    model_input = pd.DataFrame(
        [validated_features.model_dump()]
    )

    try:
        explainability_data = (
            model_service.get_individual_explainability(
                model_input
            )
        )
    except Exception as exc:
        logger.exception(
            "Individual explainability failed for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Individual explainability failed.",
        ) from exc

    return IndividualExplainabilityResponse(
        customer_id=customer_id,
        risk_band=RiskBand(str(customer["risk_band"])),
        **explainability_data,
    )

@app.post(
    "/customers/{customer_id}/retention-recommendation",
    response_model=CustomerRetentionRecommendationResponse,
    tags=["customers", "retention-ai"],
)
async def customer_retention_recommendation(
    customer_id: int,
    request: Request,
) -> CustomerRetentionRecommendationResponse:
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
            "Database query failed for retention recommendation "
            "for customer %s.",
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

    if (
        customer["churn_prediction"] is None
        or customer["churn_probability"] is None
        or customer["risk_band"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Customer {customer_id} does not have "
                "a stored scoring result."
            ),
        )

    if customer["priority_label"] is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Customer {customer_id} does not have "
                "a retention priority."
            ),
        )

    features_data = {
    feature_name: customer[feature_name]
    for feature_name in MODEL_FEATURE_NAMES
    }

    validated_features = PredictionRequest(**features_data)

    model_input = pd.DataFrame(
        [validated_features.model_dump()]
    )


    features_data = {
        feature_name: customer[feature_name]
        for feature_name in MODEL_FEATURE_NAMES
    }

    validated_features = PredictionRequest(**features_data)

    model_input = pd.DataFrame(
        [validated_features.model_dump()]
    )

    try:
        explainability_data = (
            model_service.get_individual_explainability(
                model_input
            )
        )
    except Exception as exc:
        logger.exception(
            "Retention explainability failed for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Retention explainability failed.",
        ) from exc

    explainability = IndividualExplainabilityResponse(
        customer_id=customer_id,
        risk_band=RiskBand(str(customer["risk_band"])),
        **explainability_data,
    )

    allowed_actions = get_allowed_retention_actions(
        explainability.risk_band.value
    )

    retention_service = RetentionAIService()

    try:

        recommendation = (
            await retention_service.generate_recommendation(
                explainability=explainability,
                priority_label=str(customer["priority_label"]),
                allowed_actions=allowed_actions,
            )
        )



    except RetentionAITimeoutError as exc:
        logger.exception(
            "Retention AI service timed out for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Retention AI service timed out.",
        ) from exc

    except RetentionAIInvalidResponseError as exc:
        logger.exception(
            "Retention AI returned an invalid response for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Retention AI returned an invalid response.",
        ) from exc

    except RetentionAIUnavailableError as exc:
        logger.exception(
            "Retention AI service is unavailable for customer %s.",
            customer_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retention AI service is unavailable.",
        ) from exc

    finally:
        await retention_service.close()

    return CustomerRetentionRecommendationResponse(
        customer_id=customer_id,
        churn_probability=explainability.churn_probability,
        risk_band=explainability.risk_band,
        priority_label=str(customer["priority_label"]),
        recommendation=recommendation,
        generation=RecommendationGenerationResponse(
            provider="ollama",
            model=settings.ollama_model,
            generated_at=datetime.now(timezone.utc),
        ),
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

@app.post(
    "/assistant/query",
    response_model=AssistantQueryResponse,
    tags=["assistant-ai"],
)
async def assistant_query(
    query: AssistantQueryRequest,
    request: Request,
) -> AssistantQueryResponse:
    model_service: ModelService = (
        request.app.state.model_service
    )

    if (
        query.scope == AssistantScope.customer
        and not model_service.is_loaded
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Champion model is not available.",
        )

    assistant_service = AssistantService(
        model_service=model_service
    )

    try:
        return await assistant_service.generate_response(
            query
        )
    except AssistantCustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AssistantContextUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except AssistantAIInvalidResponseError as exc:
        logger.exception(
            "Assistant AI returned invalid content."
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Assistant AI returned an invalid response."
            ),
        ) from exc
    except AssistantAIUnavailableError as exc:
        logger.exception(
            "Assistant AI service is unavailable."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant AI service is unavailable.",
        ) from exc
    except AssistantAITimeoutError as exc:
        logger.exception(
            "Assistant AI service timed out."
        )

        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Assistant AI service timed out.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception(
            "Assistant database context is unavailable."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Assistant database context is unavailable."
            ),
        ) from exc
    finally:
        await assistant_service.close()