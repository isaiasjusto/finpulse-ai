import streamlit as st

from html import escape
from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.api_client import (
    load_customer_retention_recommendation,
)

from services.database import load_customer_priority


st.set_page_config(
    page_title="Cliente 360 | FinPulse AI",
    page_icon="👤",
    layout="wide",
)


def load_css() -> None:
    css_paths = [
        APP_DIR / "styles" / "theme.css",
        APP_DIR / "styles" / "customer_360.css",
    ]

    css_content = "\n".join(
        css_path.read_text(encoding="utf-8")
        for css_path in css_paths
    )

    st.markdown(
        f"<style>{css_content}</style>",
        unsafe_allow_html=True,
    )


def render_html(content: str) -> None:
    compact_content = " ".join(
        line.strip()
        for line in content.splitlines()
        if line.strip()
    )

    st.markdown(
        compact_content,
        unsafe_allow_html=True,
    )


def format_integer(value) -> str:
    return f"{int(value):,}".replace(",", ".")

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

def format_recommendation_factor(
    factor_text: str,
    direction: str,
) -> str:
    original_text = str(factor_text)

    matched_feature = next(
        (
            feature
            for feature in FEATURE_LABELS
            if (
                f"'{feature}'" in original_text
                or original_text.strip() == feature
            )
        ),
        None,
    )

    if matched_feature is None:
        translated_text = original_text

        for feature, label in FEATURE_LABELS.items():
            translated_text = translated_text.replace(
                feature,
                label,
            )

        return translated_text

    feature_label = FEATURE_LABELS[matched_feature]

    if direction == "risk":
        return (
            f"{feature_label} contribuiu para elevar "
            "o risco estimado pelo modelo."
        )

    return (
        f"{feature_label} contribuiu para reduzir "
        "o risco estimado pelo modelo."
    )

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


customer_search_df = customer_priority_df.copy()

customer_search_df["customer_id"] = (
    customer_search_df["customer_id"].astype(str)
)

customer_options = (
    customer_search_df["customer_id"]
    .drop_duplicates()
    .tolist()
)

customer_lookup = (
    customer_search_df
    .drop_duplicates(subset=["customer_id"])
    .set_index("customer_id")
)

remembered_customer_id = str(
    st.session_state.get("selected_customer_id", "")
)


def format_customer_option(customer_id: str) -> str:
    return f"ID {customer_id}"


def format_ratio_change(value) -> str:
    percentage_change = (float(value) - 1) * 100
    return f"{percentage_change:+.2f}%".replace(".", ",")


header_column, probability_column, risk_column, priority_column = (
    st.columns([3.5, 1, 1, 1], gap="medium")
)

with header_column:
    render_html(
        """
        <div class="customer360-header-copy">
            <div class="customer360-eyebrow">
                Análise individual
            </div>

            <h1 class="customer360-page-title">
                Cliente 360
            </h1>

            <p class="customer360-page-description">
                Selecione um cliente para consultar sua visão
                consolidada e receber apoio à retenção.
            </p>
        </div>
        """
    )

    sort_options = {
        "Maior probabilidade de churn": (
            "churn_probability",
            False,
        ),
        "Menor probabilidade de churn": (
            "churn_probability",
            True,
        ),
        "ID do cliente": (
            "customer_id",
            True,
        ),
    }

    (
        selector_column,
        risk_filter_column,
        priority_filter_column,
        sort_filter_column,
    ) = st.columns(
        [1.25, 1, 1, 1.35],
        gap="small",
    )

    available_risks = [
        risk
        for risk in ("High", "Medium", "Low")
        if risk in set(
            customer_search_df["risk_band"]
            .dropna()
            .astype(str)
        )
    ]

    with risk_filter_column:
        selected_risks = st.multiselect(
            "Faixa de risco",
            options=available_risks,
            default=[],
            format_func=lambda risk: RISK_LABELS.get(
                risk,
                risk,
            ),
            placeholder="Todas",
            key="customer360_risk_filter",
        )

    priority_order = {
        "Crítica": 0,
        "Alta": 1,
        "Média": 2,
        "Baixa": 3,
    }

    available_priorities = sorted(
        customer_search_df["priority_label"]
        .dropna()
        .astype(str)
        .unique()
        .tolist(),
        key=lambda priority: priority_order.get(
            priority,
            99,
        ),
    )

    with priority_filter_column:
        selected_priorities = st.multiselect(
            "Prioridade",
            options=available_priorities,
            default=[],
            placeholder="Todas",
            key="customer360_priority_filter",
        )

    with sort_filter_column:
        selected_sort = st.selectbox(
            "Ordenar por",
            options=list(sort_options),
            index=0,
            key="customer360_sort_filter",
        )

    filtered_customer_df = customer_search_df.copy()

    if selected_risks:
        filtered_customer_df = filtered_customer_df[
            filtered_customer_df["risk_band"]
            .astype(str)
            .isin(selected_risks)
        ]

    if selected_priorities:
        filtered_customer_df = filtered_customer_df[
            filtered_customer_df["priority_label"]
            .astype(str)
            .isin(selected_priorities)
        ]

    sort_column, sort_ascending = sort_options[
        selected_sort
    ]

    filtered_customer_df = filtered_customer_df.sort_values(
        by=sort_column,
        ascending=sort_ascending,
        kind="stable",
    )

    filtered_customer_options = (
        filtered_customer_df["customer_id"]
        .drop_duplicates()
        .tolist()
    )

    if not filtered_customer_options:
        st.warning(
            "Nenhum cliente corresponde aos filtros selecionados."
        )
        st.stop()

    current_widget_customer = str(
        st.session_state.get(
            "customer360_customer_selector",
            "",
        )
    )

    if current_widget_customer not in filtered_customer_options:
        st.session_state.pop(
            "customer360_customer_selector",
            None,
        )

    if remembered_customer_id in filtered_customer_options:
        default_customer_index = (
            filtered_customer_options.index(
                remembered_customer_id
            )
        )
    else:
        default_customer_index = 0

    with selector_column:
        selected_customer_id = st.selectbox(
            "Buscar cliente",
            options=filtered_customer_options,
            index=default_customer_index,
            format_func=format_customer_option,
            label_visibility="visible",
            key="customer360_customer_selector",
        )

st.session_state["selected_customer_id"] = (
    selected_customer_id
)

selected_customer = customer_lookup.loc[
    selected_customer_id
]

churn_probability = float(
    selected_customer["churn_probability"]
)

bounded_probability = min(
    max(churn_probability, 0.0),
    1.0,
)

probability_angle = bounded_probability * 360

risk_label = RISK_LABELS.get(
    selected_customer["risk_band"],
    selected_customer["risk_band"],
)

priority_label = str(
    selected_customer["priority_label"]
)

churn_prediction_label = (
    "Churn previsto"
    if int(selected_customer["churn_prediction"]) == 1
    else "Permanência prevista"
)

with probability_column:
    render_html(
        f"""
        <article
            class="
                customer360-card
                customer360-kpi-card
                customer360-probability-card
            "
        >
            <div
                class="customer360-mini-gauge"
                style="--probability-angle: {probability_angle:.2f}deg;"
            >
                <strong>
                    {format_percentage(churn_probability)}
                </strong>
            </div>

            <div>
                <span class="customer360-kpi-label">
                    Probabilidade
                </span>

                <div class="customer360-kpi-value">
                    {format_percentage(churn_probability)}
                </div>

                <div class="customer360-kpi-caption">
                    de churn
                </div>
            </div>
        </article>
        """
    )

with risk_column:
    render_html(
        f"""
        <article class="customer360-card customer360-kpi-card">
            <div class="customer360-kpi-top">
                <span class="customer360-kpi-label">
                    Risco
                </span>

                <span class="customer360-kpi-icon">
                    &#9888;
                </span>
            </div>

            <div
                class="
                    customer360-kpi-value
                    customer360-kpi-danger
                "
            >
                {escape(str(risk_label))}
            </div>

            <div class="customer360-kpi-caption">
                {escape(churn_prediction_label)}
            </div>
        </article>
        """
    )

with priority_column:
    render_html(
        f"""
        <article class="customer360-card customer360-kpi-card">
            <div class="customer360-kpi-top">
                <span class="customer360-kpi-label">
                    Prioridade
                </span>

                <span class="customer360-kpi-icon">
                    &#9873;
                </span>
            </div>

            <div
                class="
                    customer360-kpi-value
                    customer360-kpi-danger
                "
            >
                {escape(priority_label)}
            </div>

            <div class="customer360-kpi-caption">
                Revisão operacional
            </div>
        </article>
        """
    )


profile_age_value = format_feature_value(
    "customer_age",
    selected_customer["customer_age"],
)

profile_age = f"{profile_age_value} anos"

profile_gender = format_feature_value(
    "gender",
    selected_customer["gender"],
)

profile_marital = format_feature_value(
    "marital_status",
    selected_customer["marital_status"],
)

profile_card = format_feature_value(
    "card_category",
    selected_customer["card_category"],
)

relationship_products = format_feature_value(
    "total_relationship_count",
    selected_customer["total_relationship_count"],
)

relationship_months_value = format_feature_value(
    "months_on_book",
    selected_customer["months_on_book"],
)

relationship_months = (
    f"{relationship_months_value} meses"
)

relationship_contacts = format_feature_value(
    "contacts_count_last_12m",
    selected_customer["contacts_count_last_12m"],
)

financial_amount = format_feature_value(
    "total_transaction_amount",
    selected_customer["total_transaction_amount"],
)

financial_limit = format_feature_value(
    "credit_limit",
    selected_customer["credit_limit"],
)

financial_revolving = format_feature_value(
    "total_revolving_balance",
    selected_customer["total_revolving_balance"],
)

transaction_count = format_feature_value(
    "total_transaction_count",
    selected_customer["total_transaction_count"],
)

monthly_transaction_amount = format_feature_value(
    "total_transaction_amount",
    float(selected_customer["total_transaction_amount"]) / 12,
)

amount_change_value = float(
    selected_customer["amount_change_q4_q1"]
)

count_change_value = float(
    selected_customer["transaction_count_change_q4_q1"]
)

amount_change = format_ratio_change(amount_change_value)
count_change = format_ratio_change(count_change_value)

amount_change_class = (
    "customer360-summary-danger"
    if amount_change_value < 1
    else "customer360-summary-positive"
)

count_change_class = (
    "customer360-summary-danger"
    if count_change_value < 1
    else "customer360-summary-positive"
)

summary_columns = st.columns(
    [1.18, 1, 1, 1.25],
    gap="small",
)

with summary_columns[0]:
    render_html(
        f"""
        <article class="customer360-card customer360-summary-card">
            <header class="customer360-summary-header">
                <span class="customer360-summary-icon">&#9673;</span>
                <span class="customer360-summary-title">
                    Perfil do cliente
                </span>
            </header>

            <div class="customer360-summary-grid">
                <div class="customer360-summary-item">
                    <span>Idade</span>
                    <strong>{escape(profile_age)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Gênero</span>
                    <strong>{escape(profile_gender)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Estado civil</span>
                    <strong>{escape(profile_marital)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Cartão</span>
                    <strong>{escape(profile_card)}</strong>
                </div>
            </div>
        </article>
        """
    )

with summary_columns[1]:
    render_html(
        f"""
        <article class="customer360-card customer360-summary-card">
            <header class="customer360-summary-header">
                <span class="customer360-summary-icon">&#8644;</span>
                <span class="customer360-summary-title">
                    Relacionamento
                </span>
            </header>

            <div class="customer360-summary-grid">
                <div class="customer360-summary-item">
                    <span>Relacionamentos</span>
                    <strong>{escape(relationship_products)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Tempo de vínculo</span>
                    <strong>{escape(relationship_months)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Contatos em 12 meses</span>
                    <strong>{escape(relationship_contacts)}</strong>
                </div>
            </div>
        </article>
        """
    )

with summary_columns[2]:
    render_html(
        f"""
        <article class="customer360-card customer360-summary-card">
            <header class="customer360-summary-header">
                <span class="customer360-summary-icon">&#9635;</span>
                <span class="customer360-summary-title">
                    Financeiro
                </span>
            </header>

            <div class="customer360-summary-grid">
                <div class="customer360-summary-item">
                    <span>Valor transacionado</span>
                    <strong>{escape(financial_amount)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Limite de crédito</span>
                    <strong>{escape(financial_limit)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Saldo rotativo</span>
                    <strong>{escape(financial_revolving)}</strong>
                </div>
            </div>
        </article>
        """
    )

with summary_columns[3]:
    render_html(
        f"""
        <article class="customer360-card customer360-summary-card">
            <header class="customer360-summary-header">
                <span class="customer360-summary-icon">&#8599;</span>
                <span class="customer360-summary-title">
                    Transações
                </span>
            </header>

            <div class="customer360-summary-grid">
                <div class="customer360-summary-item">
                    <span>Total</span>
                    <strong>{escape(transaction_count)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Valor médio mensal</span>
                    <strong>{escape(monthly_transaction_amount)}</strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Variação da quantidade</span>
                    <strong class="{count_change_class}">
                        {escape(count_change)}
                    </strong>
                </div>

                <div class="customer360-summary-item">
                    <span>Variação do valor</span>
                    <strong class="{amount_change_class}">
                        {escape(amount_change)}
                    </strong>
                </div>
            </div>
        </article>
        """
    )


recommendation_key = str(selected_customer_id)

recommendation_cache = st.session_state.setdefault(
    "retention_recommendations",
    {},
)

recommendation_errors = st.session_state.setdefault(
    "retention_recommendation_errors",
    {},
)

customer_recommendation = recommendation_cache.get(
    recommendation_key
)

recommendation_error = recommendation_errors.get(
    recommendation_key
)

if recommendation_error:
    button_label = "Tentar gerar novamente"
elif customer_recommendation:
    button_label = "Gerar nova recomendação"
else:
    button_label = "Gerar recomendação"


with st.container(
    border=True,
    key="customer360-ai-panel",
):
    (
        ai_title_column,
        ai_button_column,
        ai_review_column,
    ) = st.columns(
        [2.35, 1, 1.2],
        gap="medium",
    )

    with ai_title_column:
        render_html(
            """
            <div class="customer360-ai-heading">
                <span class="customer360-ai-symbol">
                    &#10024;
                </span>

                <div>
                    <span class="customer360-ai-eyebrow">
                        FinPulse AI
                    </span>

                    <h2 class="customer360-ai-title">
                        Recomendação de retenção com IA
                    </h2>
                </div>
            </div>
            """
        )

    with ai_button_column:
        generate_recommendation = st.button(
            button_label,
            key=f"generate_recommendation_{recommendation_key}",
            type="primary",
            use_container_width=True,
        )

    with ai_review_column:
        render_html(
            """
            <div class="customer360-human-review">
                <span>&#9888;</span>
                Revisão humana obrigatória
            </div>
            """
        )

    if generate_recommendation:
        recommendation_errors.pop(
            recommendation_key,
            None,
        )

        try:
            with st.spinner(
                "A IA está analisando o cliente e preparando "
                "uma abordagem de retenção..."
            ):
                customer_recommendation = (
                    load_customer_retention_recommendation(
                        recommendation_key
                    )
                )

        except (RuntimeError, ValueError) as exc:
            recommendation_errors[recommendation_key] = (
                str(exc)
            )
            customer_recommendation = None

        else:
            recommendation_cache[recommendation_key] = (
                customer_recommendation
            )
            recommendation_errors.pop(
                recommendation_key,
                None,
            )
    recommendation_error = recommendation_errors.get(
        recommendation_key
    )

    customer_recommendation = recommendation_cache.get(
        recommendation_key
    )

    if recommendation_error:
        st.error(recommendation_error)

    elif customer_recommendation:
        recommendation = customer_recommendation["recommendation"]

        action_id = recommendation["recommended_action_id"]

        action_labels = {
            "priority_retention_contact": (
                "Contato prioritário de retenção"
            ),
            "preventive_contact": "Contato preventivo",
            "transaction_engagement": (
                "Engajamento transacional"
            ),
            "financial_profile_review": (
                "Revisão do perfil financeiro"
            ),
            "maintain_relationship": (
                "Manutenção do relacionamento"
            ),
        }

        action_descriptions = {
            "priority_retention_contact": (
                "Ação imediata e personalizada para reduzir "
                "o risco de churn."
            ),
            "preventive_contact": (
                "Contato consultivo para compreender o momento "
                "do cliente."
            ),
            "transaction_engagement": (
                "Aproximação voltada à recuperação do uso "
                "e do relacionamento."
            ),
            "financial_profile_review": (
                "Revisão consultiva das necessidades e do perfil "
                "financeiro atual."
            ),
            "maintain_relationship": (
                "Acompanhamento preventivo para preservar "
                "o vínculo atual."
            ),
        }

        action_label = action_labels.get(
            action_id,
            action_id.replace("_", " ").title(),
        )

        action_description = action_descriptions.get(
            action_id,
            "Ação consultiva selecionada pelas regras "
            "de retenção do FinPulse.",
        )

        risk_signals = (
            recommendation.get("main_risk_signals") or []
        )

        protective_factors = (
            recommendation.get("protective_factors") or []
        )

        attention_points = (
            recommendation.get("attention_points") or []
        )

        risk_signals_html = "".join(
            (
                "<li>"
                f"{escape(format_recommendation_factor(signal, 'risk'))}"
                "</li>"
            )
            for signal in risk_signals
        )

        protective_factors_html = "".join(
            (
                "<li>"
                f"{escape(format_recommendation_factor(factor, 'protective'))}"
                "</li>"
            )
            for factor in protective_factors
        )

        attention_points_html = "".join(
            (
                "<li>"
                f"{escape(format_recommendation_factor(point, 'risk'))}"
                "</li>"
            )
            for point in attention_points
        )

        action_column, analysis_column = st.columns(
            [1, 1.85],
            gap="medium",
        )

        with action_column:
            render_html(
                f"""
                <article class="customer360-ai-card customer360-action-card">
                    <div class="customer360-ai-section-label">
                        Ação recomendada
                    </div>

                    <div class="customer360-action-hero">
                        <span class="customer360-action-icon">
                            &#9742;
                        </span>

                        <div>
                            <h3>
                                {escape(action_label)}
                            </h3>

                            <p>
                                {escape(action_description)}
                            </p>
                        </div>
                    </div>

                    <div class="customer360-ai-divider"></div>

                    <div class="customer360-ai-section-label">
                        Resumo do caso
                    </div>

                    <p class="customer360-ai-body">
                        {escape(recommendation["case_summary"])}
                    </p>

                    <p class="customer360-ai-interpretation">
                        {escape(recommendation["risk_interpretation"])}
                    </p>
                </article>
                """
            )

        with analysis_column:
            render_html(
                f"""
                <article class="customer360-ai-card customer360-signals-card">
                    <div class="customer360-signals-column">
                        <div class="customer360-ai-section-label">
                            Principais sinais
                        </div>

                        <ul class="customer360-ai-list customer360-risk-list">
                            {risk_signals_html}
                        </ul>
                    </div>

                    <div class="customer360-signals-column">
                        <div class="customer360-ai-section-label">
                            Fatores protetivos
                        </div>

                        <ul class="customer360-ai-list customer360-protective-list">
                            {protective_factors_html}
                        </ul>
                    </div>
                </article>
                """
            )

            approach_column, message_column = st.columns(
                [1, 1.35],
                gap="small",
            )

            with approach_column:
                render_html(
                    f"""
                    <article class="customer360-ai-card customer360-guidance-card">
                        <div class="customer360-ai-section-label">
                            Orientação de abordagem
                        </div>

                        <p class="customer360-ai-body">
                            {escape(
                                recommendation["approach_guidance"]
                            )}
                        </p>
                    </article>
                    """
                )

            with message_column:
                render_html(
                    f"""
                    <article class="customer360-ai-card customer360-message-card">
                        <div class="customer360-ai-section-label">
                            Mensagem sugerida
                        </div>

                        <blockquote>
                            {escape(
                                recommendation["suggested_message"]
                            )}
                        </blockquote>
                    </article>
                    """
                )

        if attention_points_html:
            render_html(
                f"""
                <div class="customer360-attention-strip">
                    <strong>Pontos de atenção:</strong>

                    <ul>
                        {attention_points_html}
                    </ul>
                </div>
                """
            )

        render_html(
            f"""
            <div class="customer360-generation-caption">
                Recomendação consultiva gerada por
                {escape(
                    str(
                        customer_recommendation[
                            "generation"
                        ]["provider"]
                    )
                )}
                ·
                {escape(
                    str(
                        customer_recommendation[
                            "generation"
                        ]["model"]
                    )
                )}
                · decisão final sob revisão humana.
            </div>
            """
        )

    else:
        render_html(
            """
            <p class="customer360-ai-empty">
                A recomendação será gerada somente quando
                solicitada. Nenhuma ação será executada
                automaticamente. porque não está funcionando
                
            </p>
            """
        )