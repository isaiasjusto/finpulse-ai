import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mlflow_tracking_uri: str
    model_name: str
    model_alias: str
    database_url: str
    ollama_host: str
    ollama_model: str
    ollama_timeout_seconds: float

    @property
    def model_uri(self) -> str:
        return f"models:/{self.model_name}@{self.model_alias}"


def load_settings() -> Settings:
    return Settings(
        mlflow_tracking_uri=os.getenv(
            "MLFLOW_TRACKING_URI",
            "http://mlflow:5000",
        ),
        model_name=os.getenv(
            "MODEL_NAME",
            "finpulse-churn-catboost",
        ),
        model_alias=os.getenv(
            "MODEL_ALIAS",
            "champion",
        ),
        database_url=os.getenv(
            "DATABASE_URL",
            (
                "postgresql+psycopg2://"
                "finpulse_user:finpulse_password"
                "@postgres:5432/finpulse"
            ),
        ),
        ollama_host=os.getenv(
            "OLLAMA_HOST",
            "http://ollama:11434",
        ),
        ollama_model=os.getenv(
            "OLLAMA_MODEL",
            "llama3.1:8b",
        ),
        ollama_timeout_seconds=float(
            os.getenv(
                "OLLAMA_TIMEOUT_SECONDS",
                "120",
            )
        ),
    )


settings = load_settings()