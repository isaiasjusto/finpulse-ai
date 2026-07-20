from typing import Any

import mlflow
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.pyfunc import PyFuncModel

from api.config import settings


class ModelService:
    def __init__(self) -> None:
        self._model: PyFuncModel | None = None
        self._model_version: Any | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

        client = MlflowClient(
            tracking_uri=settings.mlflow_tracking_uri,
        )

        model_version = client.get_model_version_by_alias(
            name=settings.model_name,
            alias=settings.model_alias,
        )

        model = mlflow.pyfunc.load_model(settings.model_uri)

        self._model_version = model_version
        self._model = model

    def predict(self, model_input: pd.DataFrame) -> int:
        if self._model is None:
            raise RuntimeError("Champion model is not loaded.")

        predictions = self._model.predict(model_input)
        prediction_values = np.asarray(predictions).reshape(-1)

        if prediction_values.size != 1:
            raise RuntimeError(
                "The prediction endpoint expects exactly one customer."
            )

        return int(prediction_values[0])

    def get_info(self) -> dict[str, object]:
        if self._model_version is None:
            raise RuntimeError("Champion model is not loaded.")

        return {
            "name": settings.model_name,
            "alias": settings.model_alias,
            "version": int(self._model_version.version),
            "run_id": self._model_version.run_id,
            "status": self._model_version.status,
            "source": self._model_version.source,
            "model_uri": settings.model_uri,
        }