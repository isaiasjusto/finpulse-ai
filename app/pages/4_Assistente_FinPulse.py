from html import escape
from pathlib import Path
import sys
from textwrap import dedent

import streamlit as st


APP_DIR = Path(__file__).resolve().parents[1]

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.api_client import ask_finpulse_assistant
from services.database import load_customer_priority


st.set_page_config(
    page_title="Assistente FinPulse AI",
    page_icon="💬",
    layout="wide",
)


SCOPE_OPTIONS = {
    "Cliente": "customer",
    "Carteira": "portfolio",
    "Políticas": "policy",
}

SCOPE_DESCRIPTIONS = {
    "customer": (
        "Análise individual com evidências, SHAP e "
        "políticas de retenção."
    ),
    "portfolio": (
        "Visão agregada da carteira e da distribuição "
        "de risco."
    ),
    "policy": (
        "Catálogo autorizado, regras determinísticas "
        "e revisão humana."
    ),
}

QUICK_QUESTIONS = {
    "customer": [
        "Por que este cliente precisa de atenção?",
        "Quais são os principais sinais de risco?",
        "Como devo abordar este cliente?",
    ],
    "portfolio": [
        "Como está distribuído o risco da carteira?",
        "Quantos clientes estão previstos para churn?",
        "Qual grupo exige maior atenção?",
    ],
    "policy": [
        "Quais ações de retenção estão autorizadas?",
        "Quando o contato prioritário é obrigatório?",
        "Quais decisões exigem revisão humana?",
    ],
}

RISK_LABELS = {
    "Low": "Baixo",
    "Medium": "Médio",
    "High": "Alto",
}

RISK_TONES = {
    "Low": "low",
    "Medium": "medium",
    "High": "high",
}


def load_css() -> None:
    for filename in (
        "theme.css",
        "assistant.css",
    ):
        css_path = APP_DIR / "styles" / filename

        if css_path.exists():
            st.markdown(
                (
                    "<style>"
                    f"{css_path.read_text(encoding='utf-8')}"
                    "</style>"
                ),
                unsafe_allow_html=True,
            )


def initialize_state() -> None:
    if "assistant_conversations" not in st.session_state:
        st.session_state["assistant_conversations"] = {}

    if "assistant_customer_id" not in st.session_state:
        st.session_state["assistant_customer_id"] = None


def render_html(content: str) -> None:
    normalized_content = " ".join(
        line.strip()
        for line in dedent(content).splitlines()
        if line.strip()
    )

    st.markdown(
        normalized_content,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    render_html(
        """
        <section class="assistant-hero">
            <div class="assistant-title-group">
                <span class="assistant-title-line"></span>

                <div>
                    <h1>Assistente FinPulse AI</h1>
                    <p>
                        Análise governada para apoiar decisões
                        de retenção
                    </p>
                </div>
            </div>

            <div class="assistant-model-status">
                <span class="assistant-status-dot"></span>
                Ollama · llama3.1:8b · Local
            </div>
        </section>
        """
    )


def render_customer_context(
    customer_id: int,
    probability: float,
    risk_band: str,
    priority: str,
) -> None:
    safe_customer_id = escape(str(customer_id))
    safe_priority = escape(priority)

    risk_label = escape(
        RISK_LABELS.get(risk_band, risk_band)
    )

    risk_tone = RISK_TONES.get(
        risk_band,
        "neutral",
    )

    render_html(
        f"""
        <div class="assistant-selected-customer">
            <span class="assistant-context-label">
                Cliente selecionado
            </span>

            <div class="assistant-customer-id">
                <span class="assistant-customer-icon">
                    ◎
                </span>

                <strong>{safe_customer_id}</strong>
            </div>
        </div>

        <div class="assistant-metric-grid">
            <div class="assistant-metric-card">
                <span>Probabilidade de churn</span>
                <strong>{probability:.2%}</strong>
            </div>

            <div class="
                assistant-metric-card
                assistant-risk-{risk_tone}
            ">
                <span>Faixa de risco</span>
                <strong>{risk_label}</strong>
            </div>

            <div class="
                assistant-metric-card
                assistant-priority-card
            ">
                <span>Prioridade operacional</span>
                <strong>{safe_priority}</strong>
            </div>
        </div>

        <div class="assistant-context-available">
            <h4>Contexto disponível</h4>

            <div>
                <span>✓</span>
                Perfil operacional
            </div>

            <div>
                <span>✓</span>
                Comportamento transacional
            </div>

            <div>
                <span>✓</span>
                SHAP individual
            </div>

            <div>
                <span>✓</span>
                Política de retenção
            </div>
        </div>
        """
    )


def render_portfolio_context() -> None:
    render_html(
        """
        <div class="assistant-scope-context">
            <span class="assistant-scope-icon">
                ▥
            </span>

            <div>
                <span class="assistant-context-label">
                    Contexto selecionado
                </span>

                <strong>Carteira de clientes</strong>

                <p>
                    Indicadores agregados, distribuição de
                    risco e rastreabilidade do scoring.
                </p>
            </div>
        </div>

        <div class="assistant-context-available">
            <h4>Contexto disponível</h4>

            <div>
                <span>✓</span>
                Total de clientes
            </div>

            <div>
                <span>✓</span>
                Churn previsto
            </div>

            <div>
                <span>✓</span>
                Distribuição por risco
            </div>

            <div>
                <span>✓</span>
                Versão do modelo
            </div>
        </div>
        """
    )


def render_policy_context() -> None:
    render_html(
        """
        <div class="assistant-scope-context">
            <span class="assistant-scope-icon">
                ◇
            </span>

            <div>
                <span class="assistant-context-label">
                    Contexto selecionado
                </span>

                <strong>Governança de retenção</strong>

                <p>
                    Ações autorizadas, políticas obrigatórias
                    e limites de atuação da IA.
                </p>
            </div>
        </div>

        <div class="assistant-context-available">
            <h4>Contexto disponível</h4>

            <div>
                <span>✓</span>
                Catálogo de retenção
            </div>

            <div>
                <span>✓</span>
                Ações autorizadas
            </div>

            <div>
                <span>✓</span>
                Políticas determinísticas
            </div>

            <div>
                <span>✓</span>
                Revisão humana obrigatória
            </div>
        </div>
        """
    )


def render_governance_note() -> None:
    render_html(
        """
        <div class="assistant-governance-note">
            <span>ⓘ</span>

            <p>
                A IA não executa ações automaticamente.
                A decisão final exige revisão humana.
            </p>
        </div>
        """
    )


def render_empty_state() -> None:
    render_html(
        """
        <div class="assistant-empty-state">
            <span class="assistant-bot-icon">
                ▣
            </span>

            <h3>
                Como posso apoiar sua análise?
            </h3>

            <p>
                Escolha uma pergunta orientada ou escreva
                uma pergunta usando o contexto disponível.
            </p>
        </div>
        """
    )


def render_sources(
    sources: object,
) -> None:
    if not isinstance(sources, list) or not sources:
        return

    render_html(
        """
        <p class="assistant-sources-title">
            Fontes e evidências
        </p>
        """
    )

    source_html = []

    for source in sources:
        if not isinstance(source, dict):
            continue

        label = escape(
            str(
                source.get(
                    "label",
                    "Fonte controlada",
                )
            )
        )

        source_html.append(
            (
                '<span class="assistant-source-chip">'
                f"✓&nbsp;&nbsp;{label}"
                "</span>"
            )
        )

    render_html(
        (
            '<div class="assistant-source-list">'
            + "".join(source_html)
            + "</div>"
        )
    )


def render_message(
    message: dict[str, object],
) -> None:
    role = str(message["role"])

    avatar = "👤" if role == "user" else "🤖"

    with st.chat_message(
        role,
        avatar=avatar,
    ):
        if role == "assistant":
            render_html(
                """
                <p class="assistant-answer-label">
                    Análise governada
                </p>
                """
            )

        st.markdown(str(message["content"]))

        if role != "assistant":
            return

        render_sources(
            message.get("sources")
        )

        generation = message.get("generation")

        if isinstance(generation, dict):
            provider = escape(
                str(
                    generation.get(
                        "provider",
                        "Ollama",
                    )
                )
            )

            model = escape(
                str(
                    generation.get(
                        "model",
                        "não informado",
                    )
                )
            )

            st.caption(
                f"{provider} · {model} · "
                "Revisão humana obrigatória"
            )


load_css()
initialize_state()
render_header()

context_column, chat_column = st.columns(
    [0.36, 0.64],
    gap="large",
)

selected_customer_id: int | None = None

with context_column:
    render_html(
        """
        <p class="assistant-panel-title">
            Contexto da análise
        </p>
        """
    )

    selected_scope_label = st.radio(
        "Visão",
        options=list(SCOPE_OPTIONS),
        horizontal=True,
        label_visibility="collapsed",
    )

    selected_scope = SCOPE_OPTIONS[
        selected_scope_label
    ]

    st.caption(
        SCOPE_DESCRIPTIONS[selected_scope]
    )

    if selected_scope == "customer":
        try:
            customers = (
                load_customer_priority().copy()
            )
        except Exception as exc:
            st.error(
                "Não foi possível carregar os clientes."
            )
            st.exception(exc)
            st.stop()

        if customers.empty:
            st.warning(
                "Nenhum cliente está disponível."
            )
            st.stop()

        customers["customer_id"] = (
            customers["customer_id"].astype(str)
        )

        customers = customers.sort_values(
            by="churn_probability",
            ascending=False,
        )

        customer_ids = (
            customers["customer_id"].tolist()
        )

        current_customer = st.session_state[
            "assistant_customer_id"
        ]

        default_index = (
            customer_ids.index(str(current_customer))
            if (
                current_customer is not None
                and str(current_customer)
                in customer_ids
            )
            else 0
        )

        def format_customer(
            customer_id: str,
        ) -> str:
            row = customers.loc[
                customers["customer_id"]
                == customer_id
            ].iloc[0]

            probability = float(
                row["churn_probability"]
            )

            priority = str(
                row.get(
                    "priority_label",
                    "Não informada",
                )
            )

            return (
                f"{customer_id} · "
                f"{probability:.1%} · "
                f"{priority}"
            )

        selected_customer = st.selectbox(
            "Buscar cliente",
            options=customer_ids,
            index=default_index,
            format_func=format_customer,
        )

        st.session_state[
            "assistant_customer_id"
        ] = selected_customer

        selected_customer_id = int(
            selected_customer
        )

        selected_row = customers.loc[
            customers["customer_id"]
            == selected_customer
        ].iloc[0]

        probability = float(
            selected_row["churn_probability"]
        )

        risk_band = str(
            selected_row.get(
                "risk_band",
                "Não informado",
            )
        )

        priority = str(
            selected_row.get(
                "priority_label",
                "Não informada",
            )
        )

        render_customer_context(
            customer_id=selected_customer_id,
            probability=probability,
            risk_band=risk_band,
            priority=priority,
        )

    elif selected_scope == "portfolio":
        render_portfolio_context()

    else:
        render_policy_context()

    render_governance_note()

context_key = (
    f"{selected_scope}:"
    f"{selected_customer_id or 'all'}"
)

conversations = st.session_state[
    "assistant_conversations"
]

messages = conversations.setdefault(
    context_key,
    [],
)

with chat_column:
    conversation_header, clear_column = st.columns(
        [0.78, 0.22],
    )

    with conversation_header:
        render_html(
            """
            <p class="assistant-panel-title">
                Conversa orientada
            </p>
            """
        )

    with clear_column:
        if st.button(
            "Limpar conversa",
            key=f"clear_{context_key}",
            use_container_width=True,
        ):
            conversations[context_key] = []
            st.rerun()

    if not messages:
        render_empty_state()

    for message in messages:
        render_message(message)

    submitted_question = None

    if not messages:
        render_html(
            """
            <p class="assistant-suggestion-title">
                Perguntas sugeridas
            </p>
            """
        )

        suggestion_columns = st.columns(3)

        for index, suggestion in enumerate(
            QUICK_QUESTIONS[selected_scope]
        ):
            with suggestion_columns[index]:
                if st.button(
                    suggestion,
                    key=(
                        f"suggestion_"
                        f"{context_key}_{index}"
                    ),
                    use_container_width=True,
                ):
                    submitted_question = suggestion

    typed_question = st.chat_input(
        "Pergunte sobre o contexto selecionado..."
    )

    if typed_question:
        submitted_question = typed_question

    if submitted_question:
        messages.append(
            {
                "role": "user",
                "content": submitted_question,
            }
        )

        conversations[context_key] = messages

        with st.spinner(
            "Analisando o contexto governado..."
        ):
            try:
                response = ask_finpulse_assistant(
                    question=submitted_question,
                    scope=selected_scope,
                    customer_id=selected_customer_id,
                )
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response["sources"],
                        "generation": response[
                            "generation"
                        ],
                    }
                )

                conversations[context_key] = messages
                st.rerun()