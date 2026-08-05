from pathlib import Path
import sys
from textwrap import dedent

import streamlit as st

from time import perf_counter

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

FEATURE_LABELS = {
    "customer_age": "Idade do cliente",
    "gender": "Gênero",
    "dependent_count": "Número de dependentes",
    "education_level": "Escolaridade",
    "marital_status": "Estado civil",
    "income_category": "Faixa de renda",
    "card_category": "Categoria do cartão",
    "months_on_book": "Tempo como cliente",
    "total_relationship_count": "Produtos contratados",
    "months_inactive_last_12m": "Meses inativo",
    "contacts_count_last_12m": "Contatos nos últimos 12 meses",
    "credit_limit": "Limite de crédito",
    "total_revolving_balance": "Saldo rotativo",
    "average_open_to_buy": "Crédito médio disponível",
    "amount_change_q4_q1": "Variação do valor transacionado",
    "total_transaction_amount": "Valor total transacionado",
    "total_transaction_count": "Quantidade de transações",
    "transaction_count_change_q4_q1": (
        "Variação da quantidade de transações"
    ),
    "average_utilization_ratio": "Utilização média do limite",
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

def format_ratio_change(value) -> str:
    percentage_change = (float(value) - 1) * 100
    return f"{percentage_change:+.2f}%".replace(".", ",")


selected_customer_id = st.selectbox(
    "Cliente selecionado",
    options=customer_options,
    index=default_customer_index,
    format_func=format_customer_option,
)

st.session_state["selected_customer_id"] = (
    selected_customer_id
)

selected_customer = customer_lookup.loc[
    selected_customer_id
]

risk_label = RISK_LABELS.get(
    selected_customer["risk_band"],
    selected_customer["risk_band"],
)

churn_prediction_label = (
    "Churn previsto"
    if int(selected_customer["churn_prediction"]) == 1
    else "Permanência prevista"
)

st.markdown("## Diagnóstico operacional")

with st.container(border=True):
    customer_column, probability_column, risk_column, priority_column = (
        st.columns(4)
    )

    with customer_column:
        st.metric(
            "Cliente",
            selected_customer_id,
        )

    with probability_column:
        st.metric(
            "Probabilidade de churn",
            format_percentage(
                selected_customer["churn_probability"]
            ),
        )

    with risk_column:
        st.metric(
            "Faixa de risco",
            risk_label,
        )

    with priority_column:
        st.metric(
            "Prioridade operacional",
            selected_customer["priority_label"],
        )

    st.caption(
        f"Resultado do modelo: {churn_prediction_label}"
    )

    st.info(
        f"**Ação recomendada:** "
        f"{selected_customer['recommended_action']}"
    )
st.markdown("## Perfil do cliente")

with st.container(border=True):
    age_column, gender_column, marital_column, education_column = (
        st.columns(4)
    )

    with age_column:
        age_value = format_feature_value(
            "customer_age",
            selected_customer["customer_age"],
        )

        st.metric(
            "Idade",
            f"{age_value} anos",
        )

    with gender_column:
        st.metric(
            "Gênero",
            format_feature_value(
                "gender",
                selected_customer["gender"],
            ),
        )

    with marital_column:
        st.metric(
            "Estado civil",
            format_feature_value(
                "marital_status",
                selected_customer["marital_status"],
            ),
        )

    with education_column:
        st.metric(
            "Escolaridade",
            format_feature_value(
                "education_level",
                selected_customer["education_level"],
            ),
        )

    dependent_column, income_column, card_column, relationship_column = (
        st.columns(4)
    )

    with dependent_column:
        st.metric(
            "Dependentes",
            format_feature_value(
                "dependent_count",
                selected_customer["dependent_count"],
            ),
        )

    with income_column:
        st.metric(
            "Faixa de renda",
            format_feature_value(
                "income_category",
                selected_customer["income_category"],
            ),
        )

    with card_column:
        st.metric(
            "Categoria do cartão",
            format_feature_value(
                "card_category",
                selected_customer["card_category"],
            ),
        )

    with relationship_column:
        relationship_months = format_feature_value(
            "months_on_book",
            selected_customer["months_on_book"],
        )

        st.metric(
            "Tempo de relacionamento",
            f"{relationship_months} meses",
        )
st.markdown("## Relacionamento e comportamento")

with st.container(border=True):
    products_column, inactivity_column, contacts_column, transactions_column = (
        st.columns(4)
    )

    with products_column:
        st.metric(
            "Produtos contratados",
            format_feature_value(
                "total_relationship_count",
                selected_customer["total_relationship_count"],
            ),
        )

    with inactivity_column:
        st.metric(
            "Meses de inatividade",
            format_feature_value(
                "months_inactive_last_12m",
                selected_customer["months_inactive_last_12m"],
            ),
        )

    with contacts_column:
        st.metric(
            "Contatos nos últimos 12 meses",
            format_feature_value(
                "contacts_count_last_12m",
                selected_customer["contacts_count_last_12m"],
            ),
        )

    with transactions_column:
        st.metric(
            "Total de transações",
            format_feature_value(
                "total_transaction_count",
                selected_customer["total_transaction_count"],
            ),
        )

st.markdown("## Situação financeira")

with st.container(border=True):
    limit_column, revolving_column, available_column, utilization_column = (
        st.columns(4)
    )

    with limit_column:
        st.metric(
            "Limite de crédito",
            format_feature_value(
                "credit_limit",
                selected_customer["credit_limit"],
            ),
        )

    with revolving_column:
        st.metric(
            "Saldo rotativo",
            format_feature_value(
                "total_revolving_balance",
                selected_customer["total_revolving_balance"],
            ),
        )

    with available_column:
        st.metric(
            "Crédito disponível",
            format_feature_value(
                "average_open_to_buy",
                selected_customer["average_open_to_buy"],
            ),
        )

    with utilization_column:
        st.metric(
            "Utilização do limite",
            format_feature_value(
                "average_utilization_ratio",
                selected_customer["average_utilization_ratio"],
            ),
        )
st.markdown("## Movimentação transacional")

with st.container(border=True):
    amount_column, count_column, amount_change_column, count_change_column = (
        st.columns(4)
    )

    with amount_column:
        st.metric(
            "Valor total transacionado",
            format_feature_value(
                "total_transaction_amount",
                selected_customer["total_transaction_amount"],
            ),
        )

    with count_column:
        st.metric(
            "Quantidade de transações",
            format_feature_value(
                "total_transaction_count",
                selected_customer["total_transaction_count"],
            ),
        )

    with amount_change_column:
        st.metric(
            "Variação do valor — Q4 vs. Q1",
            format_ratio_change(
                selected_customer["amount_change_q4_q1"]
            ),
        )

    with count_change_column:
        st.metric(
            "Variação das transações — Q4 vs. Q1",
            format_ratio_change(
                selected_customer[
                    "transaction_count_change_q4_q1"
                ]
            ),
        )

    st.caption(
        "As variações comparam o quarto trimestre com o primeiro. "
        "Valores negativos indicam redução da atividade do cliente."
    )

st.markdown("## Explicabilidade individual")

st.caption(
    "Principais características que influenciaram "
    "a previsão de churn deste cliente."
)

try:
    with st.spinner(
        "Carregando a explicabilidade do cliente..."
    ):
        customer_explainability = (
            load_customer_explainability(
                str(selected_customer_id)
            )
        )

    explainability_error = None

except RuntimeError as exc:
    customer_explainability = None
    explainability_error = str(exc)


if explainability_error:
    st.warning(explainability_error)

elif customer_explainability:
    increasing_column, reducing_column = st.columns(2)

    with increasing_column:
        st.markdown("### Fatores que aumentam o risco")

        for factor in customer_explainability[
            "risk_increasing_factors"
        ]:
            importance_share = min(
                max(
                    float(factor["importance_share"]),
                    0.0,
                ),
                1.0,
            )

            feature_label = FEATURE_LABELS.get(
                factor["feature"],
                factor["feature"],
            )

            formatted_feature_value = format_feature_value(
                factor["feature"],
                factor["value"],
            )

            st.markdown(f"**{feature_label}**")

            st.caption(
                f"Valor observado: {formatted_feature_value} · "
                f"Participação: "
                f"{importance_share * 100:.2f}%"
            )

            st.progress(importance_share)

    with reducing_column:
        st.markdown("### Fatores que reduzem o risco")

        for factor in customer_explainability[
            "risk_reducing_factors"
        ]:
            importance_share = min(
                max(
                    float(factor["importance_share"]),
                    0.0,
                ),
                1.0,
            )

            feature_label = FEATURE_LABELS.get(
                factor["feature"],
                factor["feature"],
            )

            formatted_feature_value = format_feature_value(
                factor["feature"],
                factor["value"],
            )

            st.markdown(f"**{feature_label}**")

            st.caption(
                f"Valor observado: {formatted_feature_value} · "
                f"Participação: "
                f"{importance_share * 100:.2f}%"
            )

            st.progress(importance_share)