from pathlib import Path
import sys
from textwrap import dedent

import streamlit as st


APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.api_client import load_customer_explainability
from services.database import load_customer_priority


st.set_page_config(
    page_title="Cliente 360 | FinPulse AI",
    page_icon="👤",
    layout="wide",
)


def load_css() -> None:
    css_path = APP_DIR / "styles" / "theme.css"
    css_content = css_path.read_text(encoding="utf-8")

    st.markdown(
        f"<style>{css_content}</style>",
        unsafe_allow_html=True,
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


def format_feature_value(feature: str, value) -> str:
    categorical_labels = {
        "gender": {
            "M": "Masculino",
            "F": "Feminino",
        },
        "education_level": {
            "Uneducated": "Sem escolaridade formal",
            "High School": "Ensino médio",
            "College": "Ensino superior incompleto",
            "Graduate": "Graduado",
            "Post-Graduate": "Pós-graduado",
            "Doctorate": "Doutorado",
            "Unknown": "Não informado",
        },
        "marital_status": {
            "Married": "Casado(a)",
            "Single": "Solteiro(a)",
            "Divorced": "Divorciado(a)",
            "Unknown": "Não informado",
        },
        "income_category": {
            "Less than $40K": "Menos de US$ 40 mil",
            "$40K - $60K": "De US$ 40 mil a US$ 60 mil",
            "$60K - $80K": "De US$ 60 mil a US$ 80 mil",
            "$80K - $120K": "De US$ 80 mil a US$ 120 mil",
            "$120K +": "Acima de US$ 120 mil",
            "Unknown": "Não informado",
        },
        "card_category": {
            "Blue": "Azul",
            "Silver": "Prata",
            "Gold": "Ouro",
            "Platinum": "Platina",
        },
    }

    if feature in categorical_labels:
        return categorical_labels[feature].get(
            str(value),
            str(value),
        )

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)

    currency_features = {
        "credit_limit",
        "total_revolving_balance",
        "average_open_to_buy",
        "total_transaction_amount",
    }

    percentage_features = {
        "amount_change_q4_q1",
        "transaction_count_change_q4_q1",
        "average_utilization_ratio",
    }

    integer_features = {
        "customer_age",
        "dependent_count",
        "months_on_book",
        "total_relationship_count",
        "months_inactive_last_12m",
        "contacts_count_last_12m",
        "total_transaction_count",
    }

    if feature in currency_features:
        formatted_value = f"{numeric_value:,.2f}"
        formatted_value = (
            formatted_value
            .replace(",", "TEMP")
            .replace(".", ",")
            .replace("TEMP", ".")
        )
        return f"R$ {formatted_value}"

    if feature in percentage_features:
        return f"{numeric_value * 100:.2f}%".replace(".", ",")

    if feature in integer_features:
        return format_integer(numeric_value)

    return f"{numeric_value:.2f}".replace(".", ",")


load_css()


RISK_LABELS = {
    "High": "Alto risco",
    "Medium": "Médio risco",
    "Low": "Baixo risco",
}


try:
    customer_priority_df = load_customer_priority()

except Exception:
    st.error(
        "Não foi possível carregar os dados do Cliente 360."
    )
    st.info(
        "Confirme se o PostgreSQL está ativo e se o mart "
        "mart_churn_customer_priority foi executado."
    )
    st.stop()


if customer_priority_df.empty:
    st.warning(
        "O mart de clientes priorizados não retornou dados."
    )
    st.stop()


hero_html = dedent(
    """
    <section class="finpulse-hero">
        <div class="finpulse-eyebrow">
            Inteligência de relacionamento
        </div>

        <h1 class="finpulse-title">
            Cliente 360
        </h1>

        <p class="finpulse-description">
            Consulte o perfil consolidado, a previsão de churn,
            a recomendação operacional e os fatores que explicam
            o risco individual de cada cliente.
        </p>
    </section>
    """
)

hero_html = " ".join(
    line.strip()
    for line in hero_html.splitlines()
    if line.strip()
)

st.markdown(
    hero_html,
    unsafe_allow_html=True,
)


customer_search_df = customer_priority_df.copy()

customer_search_df["customer_id"] = (
    customer_search_df["customer_id"].astype(str)
)

risk_options = ["Todos", "High", "Medium", "Low"]

priority_options = [
    "Todas",
    *customer_search_df["priority_label"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .tolist(),
]


with st.container(border=True):
    st.markdown("### Localizar cliente")

    st.caption(
        "Pesquise pelo identificador ou refine a carteira "
        "pela faixa de risco e prioridade operacional."
    )

    search_column, risk_column, priority_column = st.columns(
        [1.4, 1, 1]
    )

    with search_column:
        customer_search = st.text_input(
            "ID do cliente",
            placeholder="Digite o ID ou parte dele",
        )

    with risk_column:
        selected_risk = st.selectbox(
            "Faixa de risco",
            options=risk_options,
            format_func=lambda value: {
                "Todos": "Todos os riscos",
                "High": "Alto risco",
                "Medium": "Médio risco",
                "Low": "Baixo risco",
            }.get(value, value),
        )

    with priority_column:
        selected_priority = st.selectbox(
            "Prioridade",
            options=priority_options,
            format_func=lambda value: (
                "Todas as prioridades"
                if value == "Todas"
                else value
            ),
        )


filtered_customer_df = customer_search_df.copy()

if customer_search.strip():
    filtered_customer_df = filtered_customer_df[
        filtered_customer_df["customer_id"].str.contains(
            customer_search.strip(),
            case=False,
            na=False,
            regex=False,
        )
    ]

if selected_risk != "Todos":
    filtered_customer_df = filtered_customer_df[
        filtered_customer_df["risk_band"].eq(selected_risk)
    ]

if selected_priority != "Todas":
    filtered_customer_df = filtered_customer_df[
        filtered_customer_df["priority_label"].eq(
            selected_priority
        )
    ]


result_count = len(filtered_customer_df)

st.caption(
    f"{format_integer(result_count)} cliente(s) encontrado(s)"
)


if filtered_customer_df.empty:
    st.warning(
        "Nenhum cliente corresponde aos filtros selecionados."
    )
    st.stop()


customer_options = (
    filtered_customer_df["customer_id"]
    .drop_duplicates()
    .tolist()
)

customer_lookup = (
    filtered_customer_df
    .drop_duplicates(subset=["customer_id"])
    .set_index("customer_id")
)

remembered_customer_id = str(
    st.session_state.get("selected_customer_id", "")
)

if remembered_customer_id in customer_options:
    default_customer_index = customer_options.index(
        remembered_customer_id
    )
else:
    default_customer_index = 0


def format_customer_option(customer_id: str) -> str:
    customer_row = customer_lookup.loc[customer_id]

    risk_label = RISK_LABELS.get(
        customer_row["risk_band"],
        customer_row["risk_band"],
    )

    return (
        f"Cliente {customer_id} · {risk_label} · "
        f"Prioridade {customer_row['priority_label']}"
    )


selected_customer_id = st.selectbox(
    "Cliente selecionado",
    options=customer_options,
    index=default_customer_index,
    format_func=format_customer_option,
)

st.session_state["selected_customer_id"] = (
    selected_customer_id
)