from pathlib import Path
import sys

import streamlit as st

from textwrap import dedent

APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.database import (
    load_dashboard_overview,
    load_risk_distribution,
)


st.set_page_config(
    page_title="Visão Executiva | FinPulse AI",
    page_icon="⚡",
    layout="wide",
)


def format_integer(value) -> str:
    return f"{int(value):,}".replace(",", ".")


def format_percentage(value) -> str:
    return f"{float(value) * 100:.2f}%".replace(".", ",")


def format_brl_compact(value) -> str:
    value = float(value)

    if abs(value) >= 1_000_000:
        formatted = f"R$ {value / 1_000_000:.2f} mi"
    elif abs(value) >= 1_000:
        formatted = f"R$ {value / 1_000:.1f} mil"
    else:
        formatted = f"R$ {value:,.2f}"

    return formatted.replace(".", ",")


st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(
                    circle at 82% 5%,
                    rgba(20, 184, 166, 0.16),
                    transparent 28%
                ),
                linear-gradient(
                    145deg,
                    #061426 0%,
                    #081d34 52%,
                    #052d35 100%
                );
        }

        [data-testid="stAppViewContainer"] > .main {
            background: transparent;
        }

        .block-container {
            max-width: 1450px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .finpulse-hero {
            position: relative;
            overflow: hidden;
            padding: 2.2rem 2.4rem;
            margin-bottom: 1.4rem;
            border: 1px solid rgba(45, 212, 191, 0.28);
            border-radius: 26px;
            background:
                radial-gradient(
                    circle at 82% 30%,
                    rgba(45, 212, 191, 0.34),
                    transparent 28%
                ),
                linear-gradient(
                    120deg,
                    rgba(8, 45, 85, 0.96),
                    rgba(9, 80, 98, 0.88)
                );
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
        }

        .finpulse-eyebrow {
            color: #5eead4;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.16rem;
            text-transform: uppercase;
        }

        .finpulse-title {
            max-width: 780px;
            margin: 0.55rem 0 0.7rem;
            color: #f8fafc;
            font-size: clamp(2rem, 4vw, 3.5rem);
            font-weight: 800;
            line-height: 1.04;
        }

        .finpulse-description {
            max-width: 760px;
            margin: 0;
            color: #cbd5e1;
            font-size: 1rem;
            line-height: 1.65;
        }

        .model-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 1.25rem;
            padding: 0.55rem 0.85rem;
            border: 1px solid rgba(94, 234, 212, 0.35);
            border-radius: 999px;
            color: #ccfbf1;
            background: rgba(6, 78, 84, 0.55);
            font-size: 0.8rem;
            font-weight: 700;
        }

        div[data-testid="stMetric"] {
            min-height: 155px;
            padding: 1.25rem 1.35rem;
            border: 1px solid rgba(96, 165, 250, 0.20);
            border-radius: 20px;
            background: linear-gradient(
                145deg,
                rgba(15, 38, 67, 0.92),
                rgba(8, 31, 51, 0.92)
            );
            box-shadow: 0 14px 35px rgba(0, 0, 0, 0.18);
        }

        div[data-testid="stMetricLabel"] {
            color: #94a3b8;
        }

        div[data-testid="stMetricValue"] {
            color: #f8fafc;
            font-size: 2rem;
        }

        div[data-testid="stMetricDelta"] {
            color: #5eead4;
        }

        .section-title {
            margin-top: 2rem;
            color: #f8fafc;
            font-size: 1.35rem;
            font-weight: 750;
        }

        .section-subtitle {
            margin-top: -0.55rem;
            margin-bottom: 1rem;
            color: #94a3b8;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


try:
    overview_df = load_dashboard_overview()
    risk_distribution_df = load_risk_distribution()

except Exception:
    st.error(
        "Não foi possível conectar ao PostgreSQL ou carregar os marts "
        "da Visão Geral."
    )
    st.info(
        "Confirme se o PostgreSQL está ativo e se os modelos dbt "
        "já foram executados."
    )
    st.stop()


if overview_df.empty:
    st.warning("O mart da Visão Geral não retornou dados.")
    st.stop()


overview = overview_df.iloc[0]

model_alias = str(overview["model_alias"])
model_version = str(overview["model_version"])

st.markdown(
    dedent(
        f"""
        <section class="finpulse-hero">
            <div class="finpulse-eyebrow">Inteligência de retenção</div>
            <h1 class="finpulse-title">Decisões mais inteligentes para proteger a carteira.</h1>
            <p class="finpulse-description">
                O FinPulse AI identifica clientes com maior risco de churn,
                dimensiona o valor exposto e transforma previsões em
                prioridades claras de atuação.
            </p>
            <div class="model-badge">
                <span class="model-status-dot"></span>
                Modelo {model_alias} · versão {model_version}
            </div>
        </section>
        """
    ),
    unsafe_allow_html=True,
)

column_1, column_2, column_3, column_4 = st.columns(4)

with column_1:
    st.metric(
        label="Clientes analisados",
        value=format_integer(overview["total_customers"]),
        delta="Carteira avaliada",
    )

with column_2:
    st.metric(
        label="Churn observado",
        value=format_integer(overview["observed_churn_customers"]),
        delta=format_percentage(overview["observed_churn_rate"]),
        delta_color="inverse",
    )

with column_3:
    st.metric(
        label="Clientes em alto risco",
        value=format_integer(overview["high_risk_customers"]),
        delta=format_percentage(overview["high_risk_rate"]),
        delta_color="inverse",
    )

with column_4:
    st.metric(
        label="Valor transacionado em alto risco",
        value=format_brl_compact(
            overview["high_risk_transaction_amount"]
        ),
        delta=format_percentage(
            overview["high_risk_transaction_share"]
        ),
        delta_color="inverse",
    )

st.markdown(
    """
    <div class="section-title">
        Distribuição da carteira por risco
    </div>
    <div class="section-subtitle">
        Quantidade de clientes e exposição financeira em cada faixa.
    </div>
    """,
    unsafe_allow_html=True,
)

st.dataframe(
    risk_distribution_df[
        [
            "risk_band",
            "customers",
            "customer_share",
            "total_transaction_amount",
            "average_churn_probability",
        ]
    ],
    width="stretch",
    hide_index=True,
)