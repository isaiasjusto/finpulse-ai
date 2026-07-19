import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response, status

from api.model_service import ModelService
from api.schemas import PredictionRequest, PredictionResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    version="0.3.0",
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

    if not model_loaded:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if model_loaded else "degraded",
        "service": "finpulse-churn-api",
        "version": "0.3.0",
        "model_loaded": model_loaded,
        "model_load_error": request.app.state.model_load_error,
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
        "churn"
        if churn_prediction == 1
        else "no_churn"
    )

    return PredictionResponse(
        churn_prediction=churn_prediction,
        prediction_label=prediction_label,
        model_name=str(model_info_data["name"]),
        model_version=int(model_info_data["version"]),
        model_alias=str(model_info_data["alias"]),
    )