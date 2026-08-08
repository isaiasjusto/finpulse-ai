from typing import Any

import mlflow
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.pyfunc import PyFuncModel
from sklearn.pipeline import Pipeline

from api.config import settings

from catboost import Pool

TEST_SAMPLE_SIZE = 2026

class ModelService:
    def __init__(self) -> None:
        self._model: PyFuncModel | None = None
        self._explainability_pipeline: Pipeline | None = None
        self._model_version: Any | None = None
        self._run_metrics: dict[str, float] = {}

    @property
    def is_loaded(self) -> bool:
        return (
            self._model is not None
            and self._explainability_pipeline is not None
        )

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

        prediction_model = mlflow.pyfunc.load_model(
            settings.model_uri
        )

        explainability_pipeline = mlflow.sklearn.load_model(
            settings.model_uri
        )

        if not isinstance(explainability_pipeline, Pipeline):
            raise RuntimeError(
                "Champion model is not an sklearn Pipeline."
            )

        required_steps = {
            "preprocessor",
            "classifier",
        }

        missing_steps = required_steps.difference(
            explainability_pipeline.named_steps
        )

        if missing_steps:
            raise RuntimeError(
                "Champion pipeline is missing required steps: "
                f"{sorted(missing_steps)}"
            )

        classifier = explainability_pipeline.named_steps[
            "classifier"
        ]

        if not hasattr(classifier, "get_feature_importance"):
            raise RuntimeError(
                "Champion classifier does not support native SHAP."
            )

        self._model_version = model_version
        self._model = prediction_model
        self._explainability_pipeline = explainability_pipeline
        self._run_metrics = {
            str(metric_name): float(metric_value)
            for metric_name, metric_value
            in run.data.metrics.items()
        }

    def predict(self, model_input: pd.DataFrame) -> int:
        if self._model is None:
            raise RuntimeError(
                "Champion model is not loaded."
            )

        predictions = self._model.predict(model_input)
        prediction_values = np.asarray(
            predictions
        ).reshape(-1)
        
        if prediction_values.size != 1:
            raise RuntimeError(
                "The prediction endpoint expects "
                "exactly one customer."
            )

        return int(prediction_values[0])
    @staticmethod
    def _resolve_original_feature(
        transformed_feature: str,
        original_features: list[str],
    ) -> str:
        feature_body = transformed_feature.split("__", 1)[-1]

        matches = [
            feature
            for feature in original_features
            if (
                feature_body == feature
                or feature_body.startswith(f"{feature}_")
            )
        ]

        if not matches:
            raise RuntimeError(
                "Could not map transformed feature "
                f"'{transformed_feature}' to an original feature."
            )

        return max(matches, key=len)

    def _calculate_grouped_shap(
        self,
        model_input: pd.DataFrame,
    ) -> tuple[
        pd.DataFrame,
        list[str],
        list[str],
        np.ndarray,
        np.ndarray,
    ]:
        if self._explainability_pipeline is None:
            raise RuntimeError(
                "Explainability pipeline is not loaded."
            )

        if model_input.empty:
            raise ValueError(
                "Explainability sample cannot be empty."
            )

        pipeline = self._explainability_pipeline
        preprocessor = pipeline.named_steps["preprocessor"]
        classifier = pipeline.named_steps["classifier"]

        original_features = [
            str(feature)
            for feature in preprocessor.feature_names_in_
        ]

        missing_features = [
            feature
            for feature in original_features
            if feature not in model_input.columns
        ]

        if missing_features:
            raise ValueError(
                "Explainability sample is missing features: "
                f"{missing_features}"
            )

        ordered_input = model_input.loc[:, original_features]

        transformed_input = preprocessor.transform(
            ordered_input
        )

        transformed_features = [
            str(feature)
            for feature in preprocessor.get_feature_names_out()
        ]

        if transformed_input.shape[1] != len(
            transformed_features
        ):
            raise RuntimeError(
                "Transformed matrix and feature names "
                "have different sizes."
            )

        shap_matrix = np.asarray(
            classifier.get_feature_importance(
                data=Pool(transformed_input),
                type="ShapValues",
            )
        )

        expected_columns = transformed_input.shape[1] + 1

        if (
            shap_matrix.ndim != 2
            or shap_matrix.shape[1] != expected_columns
        ):
            raise RuntimeError(
                "Unexpected SHAP matrix format: "
                f"{shap_matrix.shape}"
            )

        shap_values = shap_matrix[:, :-1]
        base_values = shap_matrix[:, -1]

        feature_positions: dict[str, list[int]] = {
            feature: []
            for feature in original_features
        }

        for position, transformed_feature in enumerate(
            transformed_features
        ):
            original_feature = self._resolve_original_feature(
                transformed_feature,
                original_features,
            )

            feature_positions[original_feature].append(
                position
            )

        grouped_shap_values = np.column_stack(
            [
                shap_values[
                    :,
                    feature_positions[feature],
                ].sum(axis=1)
                for feature in original_features
            ]
        )

        return (
            ordered_input,
            original_features,
            transformed_features,
            grouped_shap_values,
            base_values,
        )

    def get_global_explainability(
        self,
        model_input: pd.DataFrame,
    ) -> dict[str, object]:
        if self._model_version is None:
            raise RuntimeError(
                "Champion model metadata is not loaded."
            )

        (
            ordered_input,
            original_features,
            transformed_features,
            grouped_shap_values,
            base_values,
        ) = self._calculate_grouped_shap(model_input)

        mean_absolute_shap = np.mean(
            np.abs(grouped_shap_values),
            axis=0,
        )

        total_importance = float(
            mean_absolute_shap.sum()
        )

        feature_importance = []

        for feature, importance in zip(
            original_features,
            mean_absolute_shap,
        ):
            importance_value = float(importance)

            importance_share = (
                importance_value / total_importance
                if total_importance > 0
                else 0.0
            )

            feature_importance.append(
                {
                    "feature": feature,
                    "mean_absolute_shap": importance_value,
                    "importance_share": importance_share,
                }
            )

        feature_importance.sort(
            key=lambda item: item[
                "mean_absolute_shap"
            ],
            reverse=True,
        )

        return {
            "model_name": settings.model_name,
            "model_alias": settings.model_alias,
            "model_version": int(
                self._model_version.version
            ),
            "run_id": self._model_version.run_id,
            "sample_size": int(len(ordered_input)),
            "input_feature_count": len(
                original_features
            ),
            "transformed_feature_count": len(
                transformed_features
            ),
            "mean_base_value": float(
                np.mean(base_values)
            ),
            "features": feature_importance,
        }
        
    def get_individual_explainability(
        self,
        model_input: pd.DataFrame,
    ) -> dict[str, object]:
        if self._model_version is None:
            raise RuntimeError(
                "Champion model metadata is not loaded."
            )

        if self._explainability_pipeline is None:
            raise RuntimeError(
                "Explainability pipeline is not loaded."
            )

        (
            ordered_input,
            original_features,
            transformed_features,
            grouped_shap_values,
            base_values,
        ) = self._calculate_grouped_shap(model_input)

        if len(ordered_input) != 1:
            raise ValueError(
                "Individual explainability expects "
                "exactly one customer."
            )

        probability_matrix = np.asarray(
            self._explainability_pipeline.predict_proba(
                ordered_input
            )
        )

        model_classes = np.asarray(
            self._explainability_pipeline.classes_
        )

        churn_class_positions = np.flatnonzero(
            model_classes == 1
        )

        if churn_class_positions.size != 1:
            raise RuntimeError(
                "Could not identify the churn class "
                "in the champion model."
            )

        churn_class_position = int(
            churn_class_positions[0]
        )

        if (
            probability_matrix.ndim != 2
            or probability_matrix.shape[0] != 1
            or churn_class_position
            >= probability_matrix.shape[1]
        ):
            raise RuntimeError(
                "Unexpected probability matrix format: "
                f"{probability_matrix.shape}"
            )

        churn_probability = float(
            probability_matrix[0, churn_class_position]
        )

        churn_prediction = self.predict(ordered_input)

        customer_shap_values = grouped_shap_values[0]
        base_value = float(base_values[0])

        raw_prediction = float(
            base_value + customer_shap_values.sum()
        )

        if raw_prediction >= 0:
            shap_probability = float(
                1.0 / (1.0 + np.exp(-raw_prediction))
            )
        else:
            exp_raw_prediction = np.exp(raw_prediction)

            shap_probability = float(
                exp_raw_prediction
                / (1.0 + exp_raw_prediction)
            )

        if not np.isclose(
            shap_probability,
            churn_probability,
            rtol=1e-7,
            atol=1e-9,
        ):
            raise RuntimeError(
                "SHAP contributions do not reconstruct "
                "the champion probability. "
                f"SHAP probability={shap_probability}, "
                f"model probability={churn_probability}."
            )

        total_absolute_shap = float(
            np.abs(customer_shap_values).sum()
        )

        customer_values = ordered_input.iloc[0]
        feature_impacts = []

        for feature, shap_value in zip(
            original_features,
            customer_shap_values,
        ):
            shap_value = float(shap_value)
            feature_value = customer_values[feature]

            if isinstance(feature_value, np.generic):
                feature_value = feature_value.item()

            if shap_value > 1e-12:
                impact_direction = "increases_risk"
            elif shap_value < -1e-12:
                impact_direction = "reduces_risk"
            else:
                impact_direction = "neutral"

            absolute_shap = abs(shap_value)

            importance_share = (
                absolute_shap / total_absolute_shap
                if total_absolute_shap > 0
                else 0.0
            )

            feature_impacts.append(
                {
                    "feature": feature,
                    "value": feature_value,
                    "shap_value": shap_value,
                    "absolute_shap": absolute_shap,
                    "importance_share": importance_share,
                    "impact_direction": impact_direction,
                }
            )

        feature_impacts.sort(
            key=lambda item: item["absolute_shap"],
            reverse=True,
        )

        risk_increasing_factors = [
            impact
            for impact in feature_impacts
            if impact["impact_direction"] == "increases_risk"
        ]

        risk_reducing_factors = [
            impact
            for impact in feature_impacts
            if impact["impact_direction"] == "reduces_risk"
        ]

        return {
            "churn_probability": churn_probability,
            "churn_prediction": churn_prediction,
            "prediction_label": (
                "churn"
                if churn_prediction == 1
                else "no_churn"
            ),
            "model_name": settings.model_name,
            "model_alias": settings.model_alias,
            "model_version": int(
                self._model_version.version
            ),
            "run_id": self._model_version.run_id,
            "input_feature_count": len(
                original_features
            ),
            "transformed_feature_count": len(
                transformed_features
            ),
            "base_value": base_value,
            "features": feature_impacts,
            "risk_increasing_factors": (
                risk_increasing_factors
            ),
            "risk_reducing_factors": (
                risk_reducing_factors
            ),
        }
    
    def get_metrics(self) -> dict[str, float | None]:
        return {
            "roc_auc": self._run_metrics.get(
                "test_roc_auc"
            ),
            "balanced_accuracy": self._run_metrics.get(
                "test_balanced_accuracy"
            ),
            "f1": self._run_metrics.get("test_f1"),
            "precision": self._run_metrics.get(
                "test_precision"
            ),
            "recall": self._run_metrics.get(
                "test_recall"
            ),
            "ks": self._run_metrics.get("ks"),
            "psi": self._run_metrics.get("psi"),
        }
    
    def get_confusion_matrix(self) -> dict[str, int]:
        accuracy = self._run_metrics.get("test_accuracy")
        precision = self._run_metrics.get("test_precision")
        recall = self._run_metrics.get("test_recall")

        if (
            accuracy is None
            or precision is None
            or recall is None
        ):
            raise RuntimeError(
                "Test metrics required for the confusion matrix "
                "are not available."
            )

        if precision <= 0 or recall <= 0:
            raise RuntimeError(
                "Precision and recall must be greater than zero."
            )

        error_count = round(
            TEST_SAMPLE_SIZE * (1 - accuracy)
        )

        error_ratio = (
            (1 / precision - 1)
            + (1 / recall - 1)
        )

        if error_ratio <= 0:
            raise RuntimeError(
                "The confusion matrix could not be reconstructed."
            )

        true_positive = round(
            error_count / error_ratio
        )

        false_positive = round(
            true_positive * (1 / precision - 1)
        )

        false_negative = round(
            true_positive * (1 / recall - 1)
        )

        true_negative = (
            TEST_SAMPLE_SIZE
            - true_positive
            - false_positive
            - false_negative
        )

        reconstructed_accuracy = (
            true_positive + true_negative
        ) / TEST_SAMPLE_SIZE

        reconstructed_precision = (
            true_positive
            / (true_positive + false_positive)
        )

        reconstructed_recall = (
            true_positive
            / (true_positive + false_negative)
        )

        metrics_match = all(
            (
                np.isclose(
                    reconstructed_accuracy,
                    accuracy,
                    atol=1e-12,
                ),
                np.isclose(
                    reconstructed_precision,
                    precision,
                    atol=1e-12,
                ),
                np.isclose(
                    reconstructed_recall,
                    recall,
                    atol=1e-12,
                ),
            )
        )

        if not metrics_match:
            raise RuntimeError(
                "The reconstructed confusion matrix does not "
                "match the logged test metrics."
            )

        return {
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_positive": true_positive,
            "sample_size": TEST_SAMPLE_SIZE,
        }
        
    def get_info(self) -> dict[str, object]:
        if self._model_version is None:
            raise RuntimeError(
                "Champion model is not loaded."
            )

        return {
            "name": settings.model_name,
            "alias": settings.model_alias,
            "version": int(
                self._model_version.version
            ),
            "run_id": self._model_version.run_id,
            "status": self._model_version.status,
            "source": self._model_version.source,
            "model_uri": settings.model_uri,
        }
    