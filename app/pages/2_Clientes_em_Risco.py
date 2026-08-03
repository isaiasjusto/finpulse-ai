from pathlib import Path
import sys
from textwrap import dedent

import streamlit as st


APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.database import load_customer_priority


st.set_page_config(
    page_title="Clientes em Risco | FinPulse AI",
    page_icon="🎯",
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


load_css()


try:
    customer_priority_df = load_customer_priority()

except Exception:
    st.error(
        "Não foi possível carregar os clientes priorizados."
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


high_risk_df = customer_priority_df[
    customer_priority_df["risk_band"] == "High"
].copy()

critical_df = customer_priority_df[
    customer_priority_df["priority_label"] == "Crítica"
].copy()

high_risk_customers = len(high_risk_df)
critical_customers = len(critical_df)

high_risk_transaction_amount = (
    high_risk_df["total_transaction_amount"].sum()
)

average_high_risk_probability = (
    high_risk_df["churn_probability"].mean()
)


hero_html = dedent(
    """
    <section class="finpulse-hero">
        <div class="finpulse-eyebrow">
            Inteligência de retenção
        </div>

        <h1 class="finpulse-title">
            Clientes em risco
        </h1>

        <p class="finpulse-description">
            Identifique os clientes com maior probabilidade de churn,
            priorize ações de retenção e analise cada relacionamento
            em detalhes.
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


column_1, column_2, column_3, column_4 = st.columns(4)

with column_1:
    st.metric(
        label="Clientes em alto risco",
        value=format_integer(high_risk_customers),
        delta="Atuação prioritária",
        delta_color="inverse",
    )

with column_2:
    st.metric(
        label="Prioridade crítica",
        value=format_integer(critical_customers),
        delta="Alto risco e alto valor",
        delta_color="inverse",
    )

with column_3:
    st.metric(
        label="Valor em alto risco",
        value=format_brl_compact(
            high_risk_transaction_amount
        ),
        delta="Volume transacionado",
        delta_color="inverse",
    )

with column_4:
    st.metric(
        label="Probabilidade média",
        value=format_percentage(
            average_high_risk_probability
        ),
        delta="Clientes de alto risco",
        delta_color="inverse",
    )

st.markdown(
    """
    <div style="margin-top: 32px;">
        <div class="finpulse-eyebrow">
            Priorização operacional
        </div>
        <h2 style="margin: 6px 0 6px 0;">
            Ranking de clientes
        </h2>
        <p style="color: #94a3b8; margin-bottom: 20px;">
            Localize clientes e organize a fila de atuação da equipe.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


RISK_LABELS = {
    "High": "Alto risco",
    "Medium": "Médio risco",
    "Low": "Baixo risco",
}


filter_column_1, filter_column_2, filter_column_3, filter_column_4 = (
    st.columns([1.4, 1, 1, 1.3])
)


with filter_column_1:
    customer_search = st.text_input(
        "Buscar cliente",
        placeholder="Digite o ID do cliente",
    )


with filter_column_2:
    selected_risk_bands = st.multiselect(
        "Faixa de risco",
        options=["High", "Medium", "Low"],
        default=["High"],
        format_func=lambda value: RISK_LABELS[value],
    )


with filter_column_3:
    selected_priorities = st.multiselect(
        "Prioridade",
        options=["Crítica", "Alta", "Média", "Baixa"],
        placeholder="Todas",
    )


with filter_column_4:
    sort_option = st.selectbox(
        "Ordenar por",
        options=[
            "Maior probabilidade de churn",
            "Maior valor transacionado",
            "Maior prioridade",
            "ID do cliente",
        ],
    )


filtered_customer_df = customer_priority_df.copy()


if customer_search.strip():
    filtered_customer_df = filtered_customer_df[
        filtered_customer_df["customer_id"]
        .astype(str)
        .str.contains(
            customer_search.strip(),
            case=False,
            regex=False,
        )
    ]


if selected_risk_bands:
    filtered_customer_df = filtered_customer_df[
        filtered_customer_df["risk_band"].isin(
            selected_risk_bands
        )
    ]


if selected_priorities:
    filtered_customer_df = filtered_customer_df[
        filtered_customer_df["priority_label"].isin(
            selected_priorities
        )
    ]


SORT_CONFIG = {
    "Maior probabilidade de churn": (
        ["churn_probability", "total_transaction_amount"],
        [False, False],
    ),
    "Maior valor transacionado": (
        ["total_transaction_amount", "churn_probability"],
        [False, False],
    ),
    "Maior prioridade": (
        ["priority_order", "churn_probability"],
        [True, False],
    ),
    "ID do cliente": (
        ["customer_id"],
        [True],
    ),
}


sort_columns, sort_ascending = SORT_CONFIG[sort_option]

filtered_customer_df = filtered_customer_df.sort_values(
    by=sort_columns,
    ascending=sort_ascending,
)


st.caption(
    f"{format_integer(len(filtered_customer_df))} "
    "clientes encontrados"
)
PAGE_SIZE_OPTIONS = [10, 25, 50]

pagination_column_1, pagination_column_2 = st.columns(
    [1, 3]
)

with pagination_column_1:
    page_size = st.selectbox(
        "Clientes por página",
        options=PAGE_SIZE_OPTIONS,
        index=0,
    )


total_customers = len(filtered_customer_df)

total_pages = max(
    (total_customers + page_size - 1) // page_size,
    1,
)


if st.session_state.get("customer_page", 1) > total_pages:
    st.session_state["customer_page"] = 1


with pagination_column_2:
    page_number = st.number_input(
        "Página",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key="customer_page",
    )


start_index = (page_number - 1) * page_size
end_index = start_index + page_size

page_customer_df = (
    filtered_customer_df
    .iloc[start_index:end_index]
    .copy()
    .reset_index(drop=True)
)


ranking_df = page_customer_df[
    [
        "customer_id",
        "risk_band",
        "priority_label",
        "churn_probability",
        "total_transaction_amount",
        "months_inactive_last_12m",
        "contacts_count_last_12m",
        "recommended_action",
    ]
].copy()


ranking_df["customer_id"] = (
    ranking_df["customer_id"].astype(str)
)

ranking_df["risk_band"] = (
    ranking_df["risk_band"].map(RISK_LABELS)
)

ranking_df["churn_probability"] = (
    ranking_df["churn_probability"] * 100
)


ranking_df = ranking_df.rename(
    columns={
        "customer_id": "ID do cliente",
        "risk_band": "Faixa de risco",
        "priority_label": "Prioridade",
        "churn_probability": "Probabilidade de churn",
        "total_transaction_amount": "Valor transacionado",
        "months_inactive_last_12m": "Meses inativo",
        "contacts_count_last_12m": "Contatos em 12 meses",
        "recommended_action": "Ação recomendada",
    }
)


table_event = st.dataframe(
    ranking_df,
    hide_index=True,
    use_container_width=True,
    height=420,
    on_select="rerun",
    selection_mode="single-row",
    key="customer_ranking_table",
    column_config={
        "ID do cliente": st.column_config.TextColumn(
            width="medium",
        ),
        "Faixa de risco": st.column_config.TextColumn(
            width="small",
        ),
        "Prioridade": st.column_config.TextColumn(
            width="small",
        ),
        "Probabilidade de churn": (
            st.column_config.ProgressColumn(
                format="%.2f%%",
                min_value=0,
                max_value=100,
                width="medium",
            )
        ),
        "Valor transacionado": st.column_config.NumberColumn(
            format="R$ %.2f",
            width="medium",
        ),
        "Meses inativo": st.column_config.NumberColumn(
            format="%d",
            width="small",
        ),
        "Contatos em 12 meses": (
            st.column_config.NumberColumn(
                format="%d",
                width="small",
            )
        ),
        "Ação recomendada": st.column_config.TextColumn(
            width="large",
        ),
    },
)


selected_rows = table_event.selection.rows

if selected_rows:
    selected_position = selected_rows[0]

    selected_customer_id = str(
        page_customer_df.iloc[selected_position][
            "customer_id"
        ]
    )

    st.session_state["selected_customer_id"] = (
        selected_customer_id
    )

    st.success(
        f"Cliente {selected_customer_id} selecionado "
        "para análise detalhada."
    )


st.caption(
    f"Página {page_number} de {total_pages} · "
    f"exibindo {len(page_customer_df)} de "
    f"{format_integer(total_customers)} clientes"
)
selected_customer_id = st.session_state.get(
    "selected_customer_id"
)

if selected_customer_id:
    selected_customer_df = customer_priority_df[
        customer_priority_df["customer_id"]
        .astype(str)
        .eq(str(selected_customer_id))
    ]

    if not selected_customer_df.empty:
        customer = selected_customer_df.iloc[0]

        st.markdown("---")

        customer_header_html = dedent(
            f"""
            <div style="margin-top: 16px;">
                <div class="finpulse-eyebrow">
                    Análise individual
                </div>

                <h2 style="margin: 6px 0;">
                    Cliente 360
                </h2>

                <p style="color: #94a3b8;">
                    Visão detalhada do cliente
                    <strong>{selected_customer_id}</strong>.
                </p>
            </div>
            """
        )

        customer_header_html = " ".join(
            line.strip()
            for line in customer_header_html.splitlines()
            if line.strip()
        )

        st.markdown(
            customer_header_html,
            unsafe_allow_html=True,
        )

        risk_label = RISK_LABELS.get(
            customer["risk_band"],
            customer["risk_band"],
        )

        GENDER_LABELS = {
            "M": "Masculino",
            "F": "Feminino",
        }

        MARITAL_LABELS = {
            "Married": "Casado(a)",
            "Single": "Solteiro(a)",
            "Divorced": "Divorciado(a)",
            "Unknown": "Não informado",
        }

        CARD_LABELS = {
            "Blue": "Azul",
            "Silver": "Prata",
            "Gold": "Ouro",
            "Platinum": "Platina",
        }

        RISK_CLASSES = {
            "High": "customer360-risk-high",
            "Medium": "customer360-risk-medium",
            "Low": "customer360-risk-low",
        }

        risk_class = RISK_CLASSES.get(
            customer["risk_band"],
            "customer360-risk-low",
        )

        churn_probability = min(
            max(float(customer["churn_probability"]), 0),
            1,
        )

        risk_angle = churn_probability * 360

        gender_label = GENDER_LABELS.get(
            customer["gender"],
            str(customer["gender"]),
        )

        marital_label = MARITAL_LABELS.get(
            customer["marital_status"],
            str(customer["marital_status"]),
        )

        card_label = CARD_LABELS.get(
            customer["card_category"],
            str(customer["card_category"]),
        )

        customer_360_html = dedent(
            f"""
            <section class="customer360-layout">

                <div class="customer360-panel customer360-data-panel">

                    <div class="customer360-panel-header">
                        <div>
                            <span>Dados consolidados</span>
                            <h3>Perfil do cliente</h3>
                        </div>

                        <div class="customer360-id-badge">
                            ID {selected_customer_id}
                        </div>
                    </div>

                    <div class="customer360-detail-grid">
                        <div class="customer360-detail-card">
                            <span>Idade</span>
                            <strong>
                                {int(customer["customer_age"])} anos
                            </strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Tempo como cliente</span>
                            <strong>
                                {int(customer["months_on_book"])} meses
                            </strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Gênero</span>
                            <strong>{gender_label}</strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Relacionamentos</span>
                            <strong>
                                {format_integer(
                                    customer["total_relationship_count"]
                                )}
                            </strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Estado civil</span>
                            <strong>{marital_label}</strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Categoria do cartão</span>
                            <strong>{card_label}</strong>
                        </div>
                    </div>

                    <div class="customer360-section-title">
                        Comportamento e relacionamento
                    </div>

                    <div class="customer360-detail-grid customer360-grid-three">
                        <div class="customer360-detail-card">
                            <span>Meses inativo</span>
                            <strong>
                                {format_integer(
                                    customer[
                                        "months_inactive_last_12m"
                                    ]
                                )}
                            </strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Contatos em 12 meses</span>
                            <strong>
                                {format_integer(
                                    customer[
                                        "contacts_count_last_12m"
                                    ]
                                )}
                            </strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Total de transações</span>
                            <strong>
                                {format_integer(
                                    customer[
                                        "total_transaction_count"
                                    ]
                                )}
                            </strong>
                        </div>
                    </div>

                    <div class="customer360-section-title">
                        Perfil financeiro
                    </div>

                    <div class="customer360-detail-grid customer360-grid-three">
                        <div class="customer360-detail-card">
                            <span>Valor transacionado</span>
                            <strong>
                                {format_brl_compact(
                                    customer[
                                        "total_transaction_amount"
                                    ]
                                )}
                            </strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Limite de crédito</span>
                            <strong>
                                {format_brl_compact(
                                    customer["credit_limit"]
                                )}
                            </strong>
                        </div>

                        <div class="customer360-detail-card">
                            <span>Saldo rotativo</span>
                            <strong>
                                {format_brl_compact(
                                    customer[
                                        "total_revolving_balance"
                                    ]
                                )}
                            </strong>
                        </div>
                    </div>
                </div>

                <aside class="customer360-panel customer360-risk-panel
                              {risk_class}">

                    <div class="customer360-panel-header">
                        <div>
                            <span>Predição individual</span>
                            <h3>Risco de churn</h3>
                        </div>

                        <div class="customer360-status-dot"></div>
                    </div>

                    <div class="customer360-risk-summary">

                        <div
                            class="customer360-gauge"
                            style="--risk-angle: {risk_angle}deg;"
                        >
                            <div class="customer360-gauge-content">
                                <strong>
                                    {format_percentage(
                                        churn_probability
                                    )}
                                </strong>
                                <span>probabilidade</span>
                            </div>
                        </div>

                        <div class="customer360-risk-badges">
                            <div>
                                <span>Faixa de risco</span>
                                <strong>{risk_label}</strong>
                            </div>

                            <div>
                                <span>Prioridade</span>
                                <strong>
                                    {customer["priority_label"]}
                                </strong>
                            </div>
                        </div>
                    </div>

                    <div class="customer360-action-card">
                        <span>Ação recomendada</span>
                        <strong>
                            {customer["recommended_action"]}
                        </strong>
                        <p>
                            Próxima ação sugerida para a equipe de
                            relacionamento.
                        </p>
                    </div>

                    <div class="customer360-model-footer">
                        <span>Modelo em produção</span>

                        <strong>{customer["model_name"]}</strong>

                        <div>
                            Versão {customer["model_version"]}
                            <span>•</span>
                            Alias {customer["model_alias"]}
                        </div>
                    </div>
                </aside>
            </section>
            """
        )

        customer_360_html = " ".join(
            line.strip()
            for line in customer_360_html.splitlines()
            if line.strip()
        )

        st.markdown(
            customer_360_html,
            unsafe_allow_html=True,
        )