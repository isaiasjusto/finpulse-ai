from dataclasses import dataclass
from enum import Enum


class RetentionActionId(str, Enum):
    MAINTAIN_RELATIONSHIP = "maintain_relationship"
    PREVENTIVE_CONTACT = "preventive_contact"
    TRANSACTION_ENGAGEMENT = "transaction_engagement"
    FINANCIAL_PROFILE_REVIEW = "financial_profile_review"
    PRIORITY_RETENTION_CONTACT = "priority_retention_contact"


@dataclass(frozen=True)
class RetentionAction:
    action_id: RetentionActionId
    name: str
    description: str
    allowed_risk_bands: tuple[str, ...]
    requires_human_review: bool = True


RETENTION_ACTION_CATALOG = {
    RetentionActionId.MAINTAIN_RELATIONSHIP: RetentionAction(
        action_id=RetentionActionId.MAINTAIN_RELATIONSHIP,
        name="Manutenção do relacionamento",
        description=(
            "Manter o acompanhamento do cliente e reforçar ações "
            "regulares de relacionamento e fidelização."
        ),
        allowed_risk_bands=("Low", "Medium"),
    ),
    RetentionActionId.PREVENTIVE_CONTACT: RetentionAction(
        action_id=RetentionActionId.PREVENTIVE_CONTACT,
        name="Contato preventivo",
        description=(
            "Realizar contato consultivo para compreender possíveis "
            "dificuldades antes de uma decisão de saída."
        ),
        allowed_risk_bands=("Medium", "High"),
    ),
    RetentionActionId.TRANSACTION_ENGAGEMENT: RetentionAction(
        action_id=RetentionActionId.TRANSACTION_ENGAGEMENT,
        name="Engajamento transacional",
        description=(
            "Avaliar ações de relacionamento voltadas à recuperação "
            "da atividade transacional do cliente."
        ),
        allowed_risk_bands=("Medium", "High"),
    ),
    RetentionActionId.FINANCIAL_PROFILE_REVIEW: RetentionAction(
        action_id=RetentionActionId.FINANCIAL_PROFILE_REVIEW,
        name="Revisão do perfil financeiro",
        description=(
            "Encaminhar o caso para avaliação humana do limite, "
            "utilização de crédito e condições atuais do cliente."
        ),
        allowed_risk_bands=("Medium", "High"),
    ),
    RetentionActionId.PRIORITY_RETENTION_CONTACT: RetentionAction(
        action_id=RetentionActionId.PRIORITY_RETENTION_CONTACT,
        name="Contato prioritário de retenção",
        description=(
            "Priorizar contato humano para compreender o cenário e "
            "avaliar alternativas de retenção autorizadas."
        ),
        allowed_risk_bands=("High",),
    ),
}


def get_allowed_retention_actions(
    risk_band: str,
) -> list[RetentionAction]:
    return [
        action
        for action in RETENTION_ACTION_CATALOG.values()
        if risk_band in action.allowed_risk_bands
    ]

def is_retention_action_allowed(
    action_id: RetentionActionId,
    risk_band: str,
) -> bool:
    allowed_action_ids = {
        action.action_id
        for action in get_allowed_retention_actions(risk_band)
    }

    return action_id in allowed_action_ids

def get_retention_action(
            action_id: RetentionActionId,
        ) -> RetentionAction:
            return RETENTION_ACTION_CATALOG[action_id]
