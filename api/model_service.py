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
        self._run_metrics: dict[str, float] = {}

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

        run = client.get_run(model_version.run_id)

        model = mlflow.pyfunc.load_model(settings.model_uri)

        self._model_version = model_version
        self._model = model
        self._run_metrics = {
            str(metric_name): float(metric_value)
            for metric_name, metric_value in run.data.metrics.items()
        }

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
    
    def get_metrics(self) -> dict[str, float | None]:
        return {
            "roc_auc": self._run_metrics.get("test_roc_auc"),
            "balanced_accuracy": self._run_metrics.get(
                "test_balanced_accuracy"
            ),
            "f1": self._run_metrics.get("test_f1"),
            "precision": self._run_metrics.get("test_precision"),
            "recall": self._run_metrics.get("test_recall"),
            "ks": self._run_metrics.get("ks"),
            "psi": self._run_metrics.get("psi"),
        }
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