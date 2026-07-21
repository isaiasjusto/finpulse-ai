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

def load_css() -> None:
    css_path = APP_DIR / "styles" / "theme.css"
    css_content = css_path.read_text(encoding="utf-8")

    st.markdown(
        f"<style>{css_content}</style>",
        unsafe_allow_html=True,
    )


load_css()

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

RISK_BAND_CONFIG = {
    "Low": {
        "label": "Baixo risco",
        "class_name": "risk-low",
    },
    "Medium": {
        "label": "Médio risco",
        "class_name": "risk-medium",
    },
    "High": {
        "label": "Alto risco",
        "class_name": "risk-high",
    },
}


def render_risk_distribution(risk_df) -> None:
    risk_cards = []

    sorted_df = risk_df.sort_values("risk_order")

    for _, row in sorted_df.iterrows():
        risk_band = str(row["risk_band"])
        config = RISK_BAND_CONFIG[risk_band]

        customers = format_integer(row["customers"])
        customer_share = format_percentage(row["customer_share"])
        transaction_amount = format_brl_compact(
            row["total_transaction_amount"]
        )
        average_probability = format_percentage(
            row["average_churn_probability"]
        )

        bar_width = max(float(row["customer_share"]) * 100, 1.5)

        card_html = dedent(
            f"""
            <article class="risk-card {config["class_name"]}">
                <div class="risk-card-header">
                    <div>
                        <div class="risk-label">
                            <span class="risk-dot"></span>
                            {config["label"]}
                        </div>
                        <div class="risk-customer-count">
                            {customers} clientes
                        </div>
                    </div>

                    <div class="risk-share">
                        {customer_share}
                    </div>
                </div>

                <div class="risk-progress-track">
                    <div
                        class="risk-progress-fill"
                        style="width: {bar_width:.2f}%"
                    ></div>
                </div>

                <div class="risk-card-details">
                    <div>
                        <span>Valor transacionado</span>
                        <strong>{transaction_amount}</strong>
                    </div>

                    <div>
                        <span>Probabilidade média</span>
                        <strong>{average_probability}</strong>
                    </div>
                </div>
            </article>
            """
        )

        risk_cards.append(
            "".join(line.strip() for line in card_html.splitlines())
        )

    st.markdown(
        '<div class="risk-distribution-grid">'
        + "".join(risk_cards)
        + "</div>",
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

render_risk_distribution(risk_distribution_df)
