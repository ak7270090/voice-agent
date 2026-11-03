"""Calls customers to confirm a delivery. Prompt only, with no flow."""

from studio_backend.agents.schemas import AgentTemplate
from studio_backend.agents.template_parts import build_agent_fields
from studio_backend.core.config import Settings

DELIVERY_FOLLOW_UP_INSTRUCTIONS = """You call customers about a delivery.
Confirm the address and a delivery slot that suits them."""


def build_templates(settings: Settings) -> list[AgentTemplate]:
    return [
        AgentTemplate(
            id="delivery-follow-up",
            name="Delivery follow-up",
            summary="Confirms the address and a delivery slot.",
            channel_label="Outbound",
            fields=build_agent_fields(
                settings,
                "Delivery follow-up",
                DELIVERY_FOLLOW_UP_INSTRUCTIONS,
                "Hello, I'm calling about your delivery. Is now a good time?",
            ),
        ),
    ]
