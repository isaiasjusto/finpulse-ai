from datetime import datetime
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
    load_retention_priority,
)
from services.api_client import load_latest_scoring

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
        "segment_label": "Clientes de baixo risco",
        "class_name": "risk-low",
        "color": "#34d399",
        "priority_label": "Baixa",
        "priority_class": "priority-low",
        "action": "Manter relacionamento e ações de fidelização",
    },
    "Medium": {
        "label": "Médio risco",
        "segment_label": "Clientes de médio risco",
        "class_name": "risk-medium",
        "color": "#fbbf24",
        "priority_label": "Alta",
        "priority_class": "priority-high",
        "action": "Campanha preventiva e acompanhamento",
    },
    "High": {
        "label": "Alto risco",
        "segment_label": "Clientes de alto risco",
        "class_name": "risk-high",
        "color": "#fb7185",
        "priority_label": "Crítica",
        "priority_class": "priority-critical",
        "action": "Contato imediato e oferta de retenção",
    },
}
    
def render_risk_distribution(risk_df) -> None:
    risk_cards = []

    sorted_df = risk_df.sort_values("risk_order")

    for _, row in sorted_df.iterrows():
        risk_band = str(row["risk_band"])
        config = RISK_BAND_CONFIG[risk_band]
        risk_color = config["color"]

        customers = format_integer(row["customers"])
        customer_share = format_percentage(row["customer_share"])

        transaction_amount = format_brl_compact(
            row["total_transaction_amount"]
        )

        average_probability = format_percentage(
            row["average_churn_probability"]
        )

        bar_width = min(
            max(float(row["customer_share"]) * 100, 1.5),
            100,
        )

        card_html = dedent(
            f"""
            <div
                class="risk-card {config["class_name"]}"
                style="--risk-color: {risk_color};"
            >
                <div class="risk-card-header">
                    <div>
                        <div class="risk-label">
                            <span
                                class="risk-dot"
                                style="background: {risk_color};"
                            ></span>
                            {config["label"]}
                        </div>

                        <div class="risk-customer-count">
                            {customers} clientes
                        </div>
                    </div>

                    <div
                        class="risk-share"
                        style="color: {risk_color};"
                    >
                        {customer_share}
                    </div>
                </div>

                <div
                    class="risk-progress-track"
                    style="
                        width: 100%;
                        height: 6px;
                        overflow: hidden;
                        border-radius: 999px;
                        background: rgba(148, 163, 184, 0.18);
                    "
                >
                    <div
                        class="risk-progress-fill"
                        style="
                            display: block;
                            width: {bar_width:.2f}% !important;
                            height: 100% !important;
                            min-height: 6px;
                            border-radius: 999px;
                            background-color: {risk_color} !important;
                            box-shadow: 0 0 10px {risk_color};
                        "
                    ></div>
                </div>

                <div class="risk-card-details">
                    <div>
                        <span>Valor transacionado</span>
                        <strong style="color: {risk_color} !important;">
                            {transaction_amount}
                        </strong>
                    </div>

                    <div>
                        <span>Probabilidade média</span>
                        <strong style="color: {risk_color} !important;">
                            {average_probability}
                        </strong>
                    </div>
                </div>
            </div>
            """
        )

        risk_cards.append(
            " ".join(
                line.strip()
                for line in card_html.splitlines()
                if line.strip()
            )
        )

    st.markdown(
        '<div class="risk-distribution-grid">'
        + "".join(risk_cards)
        + "</div>",
        unsafe_allow_html=True,
    )
    
def render_retention_priority_matrix(retention_df) -> None:
    segment_config = {
        ("High", "High"): {
            "title": "Retenção prioritária",
            "action": "Contato imediato e oferta personalizada",
        },
        ("High", "Low"): {
            "title": "Retenção direcionada",
            "action": "Campanha de recuperação com baixo custo",
        },
        ("Medium", "High"): {
            "title": "Fidelizar",
            "action": "Benefícios preventivos e acompanhamento",
        },
        ("Medium", "Low"): {
            "title": "Acompanhar",
            "action": "Monitorar evolução do risco",
        },
        ("Low", "High"): {
            "title": "Desenvolver relacionamento",
            "action": "Estimular recorrência e novas ofertas",
        },
        ("Low", "Low"): {
            "title": "Manter relacionamento",
            "action": "Comunicação e fidelização contínuas",
        },
    }

    segment_rows = {
        (str(row["risk_band"]), str(row["value_band"])): row
        for _, row in retention_df.iterrows()
    }

    matrix_cells = []

    for risk_band in ["High", "Medium", "Low"]:
        for value_band in ["Low", "High"]:
            segment_key = (risk_band, value_band)
            config = segment_config[segment_key]
            row = segment_rows.get(segment_key)

            if row is None:
                customers = "0"
                share_value = 0.0
                customer_share = "0,00%"
                transaction_amount = "R$ 0,00"
                churn_probability = "0,00%"
            else:
                customers = format_integer(row["customers"])
                share_value = float(row["customer_share"])

                customer_share = format_percentage(
                    share_value
                )
                transaction_amount = format_brl_compact(
                    row["total_transaction_amount"]
                )
                churn_probability = format_percentage(
                    row["average_churn_probability"]
                )

            # Mantém as bolhas menores legíveis e impede
            # que as maiores ultrapassem o quadrante.
            bubble_size = 56 + min(
                share_value ** 0.5 * 84,
                58,
            )

            empty_class = (
                " retention-bubble-empty"
                if row is None
                else ""
            )

            cell_html = (
                f'<article class="retention-matrix-cell '
                f'retention-bubble-cell '
                f'retention-risk-{risk_band.lower()}">'

                '<div class="retention-cell-header">'
                f'<strong>{config["title"]}</strong>'
                f'<span>{customers} clientes</span>'
                '</div>'

                '<div class="retention-bubble-stage">'
                f'<div class="retention-priority-bubble'
                f'{empty_class}" '
                f'style="--bubble-size: {bubble_size:.0f}px;">'
                f'<strong>{customer_share}</strong>'
                '<span>da carteira</span>'
                '</div>'
                '</div>'

                '<div class="retention-bubble-metrics">'
                '<div>'
                '<span>Valor transacionado</span>'
                f'<strong>{transaction_amount}</strong>'
                '</div>'
                '<div>'
                '<span>Churn médio</span>'
                f'<strong>{churn_probability}</strong>'
                '</div>'
                '</div>'

                f'<div class="retention-cell-action">'
                f'{config["action"]}'
                '</div>'

                '</article>'
            )

            matrix_cells.append(cell_html)

    matrix_html = (
        '<div class="retention-matrix">'
        '<div class="retention-matrix-corner">'
        '<span>Risco</span>'
        '<span>Valor</span>'
        '</div>'
        '<div class="retention-value-header">Baixo valor</div>'
        '<div class="retention-value-header">Alto valor</div>'

        '<div class="retention-risk-header retention-risk-high">'
        'Alto risco'
        '</div>'
        f'{matrix_cells[0]}'
        f'{matrix_cells[1]}'

        '<div class="retention-risk-header retention-risk-medium">'
        'Médio risco'
        '</div>'
        f'{matrix_cells[2]}'
        f'{matrix_cells[3]}'

        '<div class="retention-risk-header retention-risk-low">'
        'Baixo risco'
        '</div>'
        f'{matrix_cells[4]}'
        f'{matrix_cells[5]}'
        '</div>'
    )

    st.markdown(
        matrix_html,
        unsafe_allow_html=True,
    )
    
def render_action_priorities(risk_df) -> None:
    priority_rows = []

    sorted_df = risk_df.sort_values(
        "average_churn_probability",
        ascending=False,
    )

    for _, row in sorted_df.iterrows():
        risk_band = str(row["risk_band"])
        config = RISK_BAND_CONFIG[risk_band]

        customers = format_integer(row["customers"])

        transaction_amount = format_brl_compact(
            row["total_transaction_amount"]
        )

        average_probability_value = float(
            row["average_churn_probability"]
        )

        average_probability = format_percentage(
            average_probability_value
        )

        churn_bar_width = max(
            min(average_probability_value * 100, 100),
            4,
        )

        row_html = (
            f'<div class="priority-row {config["class_name"]}">'

            '<div class="priority-segment">'
            '<span class="priority-risk-dot"></span>'
            '<div class="priority-segment-text">'
            f'<strong>{config["segment_label"]}</strong>'
            f'<span>{config["label"]}</span>'
            '</div>'
            '</div>'

            '<div class="priority-cell">'
            '<span class="priority-mobile-label">Clientes</span>'
            f'<strong>{customers}</strong>'
            '</div>'

            '<div class="priority-cell">'
            '<span class="priority-mobile-label">Volume em risco</span>'
            f'<strong>{transaction_amount}</strong>'
            '</div>'

            '<div class="priority-cell priority-churn-cell">'
            '<span class="priority-mobile-label">Churn previsto</span>'
            '<div class="priority-churn-content">'
            f'<strong>{average_probability}</strong>'
            '<div class="priority-churn-track">'
            f'<div class="priority-churn-fill {config["class_name"]}" '
            f'style="width: {churn_bar_width:.2f}%">'
            '</div>'
            '</div>'
            '</div>'
            '</div>'

            '<div class="priority-cell priority-level-cell">'
            '<span class="priority-mobile-label">Prioridade</span>'
            f'<span class="priority-badge {config["priority_class"]}">'
            f'{config["priority_label"]}'
            '</span>'
            '</div>'

            '<div class="priority-action">'
            '<span class="priority-mobile-label">Ação recomendada</span>'
            f'<span>{config["action"]}</span>'
            '</div>'

            '</div>'
        )

        priority_rows.append(row_html)

    table_html = (
        '<div class="priority-table">'

        '<div class="priority-table-header">'
        '<div>Segmento</div>'
        '<div>Clientes</div>'
        '<div>Volume em risco</div>'
        '<div>Churn previsto</div>'
        '<div>Prioridade</div>'
        '<div>Ação recomendada</div>'
        '</div>'

        f'{"".join(priority_rows)}'

        '</div>'
    )

    st.markdown(
        table_html,
        unsafe_allow_html=True,
    )
    
def render_latest_scoring(
    scoring_data,
    scoring_error,
) -> None:
    if scoring_data is None:
        error_message = (
            scoring_error
            or "O último scoring não está disponível."
        )

        unavailable_html = (
            '<section class="latest-scoring-card">'
            '<div class="latest-scoring-header">'
            '<div class="latest-scoring-title-wrap">'
            '<span class="latest-scoring-title">'
            'Último scoring'
            '</span>'
            '</div>'
            '<span class="scoring-health-badge scoring-health-error">'
            '<span class="scoring-health-dot"></span>'
            'API indisponível'
            '</span>'
            '</div>'
            '<div class="scoring-unavailable">'
            f'{error_message}'
            '</div>'
            '</section>'
        )
        

        st.markdown(
            unavailable_html,
            unsafe_allow_html=True,
        )

        return

    model = scoring_data["model"]
    scoring = scoring_data["scoring"]
    metrics = scoring_data["metrics"]

    model_alias = str(model["alias"]).capitalize()
    model_version = int(model["version"])
    model_status = str(model["status"])

    executed_at = format_datetime_br(
        scoring["executed_at"]
    )

    population_scored = format_integer(
        scoring["population_scored"]
    )

    roc_auc = format_decimal(
        metrics.get("roc_auc"),
        decimal_places=3,
    )

    balanced_accuracy = format_decimal(
    metrics.get("balanced_accuracy"),
    decimal_places=3,
    )

    f1 = format_decimal(
        metrics.get("f1"),
        decimal_places=3,
    )

    recall = format_decimal(
        metrics.get("recall"),
        decimal_places=3,
    )
    run_id = str(model["run_id"])
    short_run_id = run_id[:10]

    scoring_html = (
        '<section class="latest-scoring-card">'

        '<div class="latest-scoring-header">'
        '<div class="latest-scoring-title-wrap">'
        '<span class="latest-scoring-title">'
        'Último scoring'
        '</span>'
        '<span class="scoring-info-icon" '
        'title="Informações operacionais do modelo champion '
        'e da execução mais recente da carteira.">'
        'i'
        '</span>'
        '</div>'

        '<span class="scoring-health-badge">'
        '<span class="scoring-health-dot"></span>'
        'API saudável'
        '</span>'
        '</div>'

        '<div class="scoring-model-panel">'
        '<div class="scoring-model-icon">ML</div>'

        '<div class="scoring-model-copy">'
        f'<strong>{model_alias} v{model_version}</strong>'
        '<span>Modelo em produção</span>'
        '</div>'

        f'<span class="scoring-model-status">{model_status}</span>'
        '</div>'

        '<div class="scoring-meta-grid">'

        '<div class="scoring-meta-item">'
        '<span>Executado em</span>'
        f'<strong>{executed_at}</strong>'
        '</div>'

        '<div class="scoring-meta-item">'
        '<span>População scoreada</span>'
        f'<strong>{population_scored}</strong>'
        '</div>'

        '</div>'

        '<div class="scoring-metrics-grid">'

        '<div class="scoring-metric-card scoring-metric-primary">'
        '<span>AUC (ROC)</span>'
        f'<strong>{roc_auc}</strong>'
        '<small>Teste</small>'
        '</div>'

        '<div class="scoring-metric-card scoring-metric-good">'
        '<span>Balanced Accuracy</span>'
        f'<strong>{balanced_accuracy}</strong>'
        '<small>Teste</small>'
        '</div>'

        '<div class="scoring-metric-card scoring-metric-good">'
        '<span>F1 Score</span>'
        f'<strong>{f1}</strong>'
        '<small>Teste</small>'
        '</div>'

        '<div class="scoring-metric-card scoring-metric-attention">'
        '<span>Recall</span>'
        f'<strong>{recall}</strong>'
        '<small>Teste</small>'
        '</div>'
        
        '</div>'

        '<div class="scoring-run-footer">'
        '<span>Run ID</span>'
        f'<code>{short_run_id}</code>'
        '</div>'

        '</section>'
    )

    st.markdown(
        scoring_html,
        unsafe_allow_html=True,
    ) 
    
    
try:
    overview_df = load_dashboard_overview()
    risk_distribution_df = load_risk_distribution()
    retention_priority_df = load_retention_priority()

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
    
try:
    latest_scoring_data = load_latest_scoring()
    latest_scoring_error = None

except RuntimeError as exc:
    latest_scoring_data = None
    latest_scoring_error = str(exc)

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
def format_datetime_br(value) -> str:
    if not value:
        return "Não disponível"

    try:
        parsed_datetime = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

        return parsed_datetime.strftime(
            "%d/%m/%Y %H:%M"
        )

    except ValueError:
        return str(value)


def format_decimal(value, decimal_places: int = 3) -> str:
    if value is None:
        return "—"

    formatted = f"{float(value):.{decimal_places}f}"

    return formatted.replace(".", ",")
retention_column, distribution_column = st.columns(
    [1.9, 1.0],
    gap="large",
)

with retention_column:
    st.markdown(
        """
        <div class="section-title">
            Matriz de prioridade de retenção
        </div>
        <div class="section-subtitle">
            Cruzamento entre risco de churn e valor transacionado.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_retention_priority_matrix(
        retention_priority_df
    )

with distribution_column:
    st.markdown(
        """
        <div class="section-title">
            Distribuição por risco
        </div>
        <div class="section-subtitle">
            Tamanho e exposição financeira da carteira.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_risk_distribution(
        risk_distribution_df
    )


priority_column, scoring_column = st.columns(
    [2.1, 1.0],
    gap="large",
)

with priority_column:
    st.markdown(
        (
            '<div class="priority-heading-card">'

            '<div class="section-title-with-info">'
            '<span>Prioridades de ação</span>'

            '<span class="info-icon" '
            'title="Os segmentos são ordenados pela probabilidade '
            'média de churn e pelo volume transacionado associado '
            'ao risco.">'
            'i'
            '</span>'

            '</div>'

            '<div class="priority-heading-subtitle">'
            'Segmentos ordenados por urgência, exposição financeira '
            'e probabilidade média de churn.'
            '</div>'

            '</div>'
        ),
        unsafe_allow_html=True,
    )

    render_action_priorities(
        risk_distribution_df
    )

    st.markdown(
        """
        <div class="priority-note">
            O churn previsto representa a probabilidade média estimada
            pelo modelo para cada faixa de risco. A classificação
            orienta a ordem de atuação da equipe de retenção.
        </div>
        """,
        unsafe_allow_html=True,
    )

with scoring_column:
    render_latest_scoring(
        latest_scoring_data,
        latest_scoring_error,
    )