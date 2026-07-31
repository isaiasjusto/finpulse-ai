from pathlib import Path
import sys
from textwrap import dedent
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.api_client import (
    load_global_explainability,
    load_latest_scoring,
)

st.set_page_config(
    page_title="Análise do Modelo | FinPulse AI",
    page_icon="🧠",
    layout="wide",
)


def load_css() -> None:
    css_path = APP_DIR / "styles" / "theme.css"
    css_content = css_path.read_text(encoding="utf-8")

    st.markdown(
        f"<style>{css_content}</style>",
        unsafe_allow_html=True,
    )


def format_metric(value) -> str:
    if value is None:
        return "N/D"

    return f"{float(value) * 100:.2f}%".replace(".", ",")


def format_integer(value) -> str:
    return f"{int(value):,}".replace(",", ".")


load_css()


try:
    scoring_data = load_latest_scoring()

except RuntimeError as exc:
    st.error(str(exc))
    st.info(
        "Verifique se a FastAPI e o MLflow estão disponíveis."
    )
    st.stop()

FEATURE_LABELS = {
    "customer_age": "Idade do cliente",
    "gender": "Gênero",
    "dependent_count": "Quantidade de dependentes",
    "education_level": "Escolaridade",
    "marital_status": "Estado civil",
    "income_category": "Faixa de renda",
    "card_category": "Categoria do cartão",
    "months_on_book": "Tempo de relacionamento",
    "total_relationship_count": "Quantidade de relacionamentos",
    "months_inactive_last_12m": "Meses inativo nos últimos 12 meses",
    "contacts_count_last_12m": "Contatos nos últimos 12 meses",
    "credit_limit": "Limite de crédito",
    "total_revolving_balance": "Saldo rotativo total",
    "average_open_to_buy": "Limite médio disponível",
    "amount_change_q4_q1": "Mudança no valor das transações",
    "total_transaction_amount": "Valor total das transações",
    "total_transaction_count": "Quantidade total de transações",
    "transaction_count_change_q4_q1": (
        "Mudança na quantidade de transações"
    ),
    "average_utilization_ratio": "Taxa média de utilização",
}


@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def load_cached_global_explainability(
    sample_size: int = 500,
) -> dict:
    return load_global_explainability(sample_size)

model_data = scoring_data["model"]
execution_data = scoring_data["scoring"]
metrics_data = scoring_data["metrics"]


hero_html = dedent(
    f"""
    <section class="finpulse-hero">
        <div class="finpulse-eyebrow">
            Governança e explicabilidade
        </div>

        <h1 class="finpulse-title">
            Análise do Modelo
        </h1>

        <p class="finpulse-description">
            Acompanhe o desempenho, a versão e a confiabilidade
            do modelo champion responsável pelas previsões de churn.
        </p>

        <div class="model-badge">
            <span class="model-status-dot"></span>
            {model_data["name"]}
            · versão {model_data["version"]}
            · alias {model_data["alias"]}
        </div>
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


st.markdown(
    """
    <div class="finpulse-eyebrow">
        Desempenho no conjunto de teste
    </div>

    <h2 style="margin: 6px 0 20px;">
        Métricas do champion
    </h2>
    """,
    unsafe_allow_html=True,
)


metric_column_1, metric_column_2, metric_column_3 = st.columns(3)



with metric_column_1:
    st.metric(
        label="ROC AUC",
        value=format_metric(metrics_data["roc_auc"]),
    )

with metric_column_2:
    st.metric(
        label="Balanced Accuracy",
        value=format_metric(
            metrics_data["balanced_accuracy"]
        ),
    )

with metric_column_3:
    st.metric(
        label="F1-Score",
        value=format_metric(metrics_data["f1"]),
    )


metric_column_4, metric_column_5, metric_column_6 = st.columns(3)

with metric_column_4:
    st.metric(
        label="Precisão",
        value=format_metric(metrics_data["precision"]),
    )

with metric_column_5:
    st.metric(
        label="Recall",
        value=format_metric(metrics_data["recall"]),
    )

with metric_column_6:
    st.metric(
        label="Carteira pontuada",
        value=format_integer(
            execution_data["population_scored"]
        ),
    )
st.markdown(
    """
    <div class="section-title">
        O que mais influencia o churn?
    </div>
    <div class="section-subtitle">
        Importância global calculada com SHAP sobre uma amostra
        determinística da carteira.
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    explainability = load_cached_global_explainability(
        sample_size=500
    )

    feature_rows = explainability.get("features", [])

    if not feature_rows:
        raise RuntimeError(
            "A API não retornou variáveis para explicabilidade."
        )

    shap_frame = pd.DataFrame(feature_rows)

    shap_frame["feature_label"] = shap_frame["feature"].map(
        FEATURE_LABELS
    ).fillna(shap_frame["feature"])

    shap_frame["importance_percentage"] = (
        shap_frame["importance_share"] * 100
    )

    top_features = (
        shap_frame
        .nlargest(10, "importance_percentage")
        .sort_values("importance_percentage")
    )

    percentage_labels = [
        f"{value:.2f}%".replace(".", ",")
        for value in top_features["importance_percentage"]
    ]

    bar_colors = [
        "#2563eb",
        "#2563eb",
        "#1d4ed8",
        "#0ea5e9",
        "#06b6d4",
        "#14b8a6",
        "#14b8a6",
        "#2dd4bf",
        "#2dd4bf",
        "#5eead4",
    ][-len(top_features):]

    figure = go.Figure(
        go.Bar(
            x=top_features["importance_percentage"],
            y=top_features["feature_label"],
            orientation="h",
            text=percentage_labels,
            textposition="outside",
            customdata=top_features[
                "mean_absolute_shap"
            ],
            marker={
                "color": bar_colors,
                "line": {
                    "color": "rgba(94, 234, 212, 0.35)",
                    "width": 1,
                },
            },
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Participação: %{x:.2f}%<br>"
                "SHAP médio absoluto: %{customdata:.4f}"
                "<extra></extra>"
            ),
        )
    )

    maximum_percentage = float(
        top_features["importance_percentage"].max()
    )

    figure.update_layout(
        height=570,
        margin={
            "l": 20,
            "r": 75,
            "t": 25,
            "b": 45,
        },
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font={
            "color": "#cbd5e1",
            "family": "Inter, sans-serif",
        },
        bargap=0.34,
        showlegend=False,
        hoverlabel={
            "bgcolor": "#0f263f",
            "bordercolor": "#2dd4bf",
            "font": {
                "color": "#f8fafc",
            },
        },
        xaxis={
            "title": "Participação na importância global",
            "range": [0, maximum_percentage * 1.22],
            "ticksuffix": "%",
            "showgrid": True,
            "gridcolor": "rgba(148, 163, 184, 0.10)",
            "zeroline": False,
            "color": "#7890aa",
        },
        yaxis={
            "title": None,
            "showgrid": False,
            "automargin": True,
            "color": "#cbd5e1",
        },
    )

    with st.container(border=True):
        st.plotly_chart(
            figure,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True,
            },
        )

        st.caption(
            "Champion "
            f"v{explainability['model_version']} · "
            f"{explainability['sample_size']} clientes · "
            f"{explainability['input_feature_count']} variáveis"
        )

    st.info(
        "Os percentuais representam a intensidade global da "
        "influência de cada variável. Eles não indicam, sozinhos, "
        "se a variável aumenta ou reduz o risco de churn."
    )

except RuntimeError as exc:
    st.error(
        "Não foi possível carregar a explicabilidade global. "
        f"Detalhes: {exc}"
    )

st.markdown(
    """
    <div style="margin-top: 32px;">
        <div class="finpulse-eyebrow">Rastreabilidade</div>
        <h2 style="margin: 6px 0 20px;">
            Execução em produção
        </h2>
    </div>
    """,
    unsafe_allow_html=True,
)

info_column_1, info_column_2 = st.columns(2)

with info_column_1:
    st.text_input(
        "Run ID do MLflow",
        value=model_data["run_id"],
        disabled=True,
    )

with info_column_2:
    st.text_input(
        "Último scoring",
        value=execution_data["executed_at"],
        disabled=True,
    )

st.info(
    "As métricas acima foram calculadas no teste reservado "
    "com 2.026 clientes. A carteira pontuada em produção "
    "contém 10.127 clientes."
)