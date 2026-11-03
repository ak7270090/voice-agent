"""The agents shown when creating a new one: a blank start, then every example."""

from studio_backend.agent_catalog.examples import (
    appointment_reminder,
    clinic_booking,
    delivery_follow_up,
    lead_qualifier,
)
from studio_backend.agent_catalog.template_parts import build_agent_fields
from studio_backend.agents.schemas import AgentTemplate
from studio_backend.config import Settings

BLANK_INSTRUCTIONS = "You answer phone calls for the business. Be warm and brief."
# Listed in this order in the dashboard.
EXAMPLES = (clinic_booking, appointment_reminder, lead_qualifier, delivery_follow_up)


def build_templates(settings: Settings) -> list[AgentTemplate]:
    blank = AgentTemplate(
        id="blank",
        name="Start from scratch",
        summary="An empty agent: write what it says and draw its conversation yourself.",
        channel_label="Any",
        fields=build_agent_fields(
            settings,
            "New agent",
            BLANK_INSTRUCTIONS,
            "Hello, how can I help you today?",
        ),
    )
    return [
        blank,
        *(template for example in EXAMPLES for template in example.build_templates(settings)),
    ]
