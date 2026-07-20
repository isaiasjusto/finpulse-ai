from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from api.config import settings


engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))