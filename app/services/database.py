import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


LOCAL_DATABASE_URL = (
    "postgresql+psycopg2://finpulse_user:"
    "finpulse_password@localhost:5433/finpulse"
)


@st.cache_resource
def get_database_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL", LOCAL_DATABASE_URL)

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_overview() -> pd.DataFrame:
    query = text(
        """
        select *
        from marts.mart_churn_dashboard_overview
        limit 1
        """
    )

    return pd.read_sql_query(query, get_database_engine())


@st.cache_data(ttl=300, show_spinner=False)
def load_risk_distribution() -> pd.DataFrame:
    query = text(
        """
        select *
        from marts.mart_churn_risk_distribution
        order by risk_order
        """
    )

    return pd.read_sql_query(query, get_database_engine())