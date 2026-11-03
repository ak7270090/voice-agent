"""Calls tomorrow's patients to confirm or move their appointment."""

from studio_backend.agents.schemas import AgentTemplate, AnalysisField
from studio_backend.agents.template_parts import at, build_agent_fields, edge
from studio_backend.core.config import Settings
from studio_backend.flows.schemas import (
    EndData,
    EndNode,
    Flow,
    StartNode,
    StepData,
    StepNode,
)

REMINDER_INSTRUCTIONS = """You call patients to remind them of tomorrow's appointment.
Confirm they are coming, or offer to move the appointment. Keep the call short."""

REMINDER_ANALYSIS = (
    [
        AnalysisField(
            name="will_attend",
            type="yes_no",
            description="Will the patient come to tomorrow's appointment?",
        ),
    ],
    "The patient confirmed, asked to move the appointment, or a voicemail was left.",
)


def build_reminder_flow() -> Flow:
    nodes = [
        StartNode(id="start", type="start", position=at(1, 0)),
        StepNode(
            id="remind",
            type="step",
            position=at(1, 1),
            data=StepData(
                name="Confirm the appointment",
                instructions=(
                    "Remind the patient of tomorrow's appointment and ask if they will come."
                ),
            ),
        ),
        EndNode(
            id="confirmed",
            type="end",
            position=at(0, 2),
            data=EndData(outcome="confirmed", message="Great, see you tomorrow. Goodbye."),
        ),
        EndNode(
            id="reschedule",
            type="end",
            position=at(2, 2),
            data=EndData(
                outcome="reschedule_requested",
                message="No problem. The front desk will call you to find a new time. Goodbye.",
            ),
        ),
        EndNode(
            id="opted_out",
            type="end",
            position=at(3, 2),
            # A campaign never calls a contact again after this outcome.
            data=EndData(
                outcome="opted_out",
                message="Understood, we won't call you again. Goodbye.",
            ),
        ),
    ]
    edges = [
        edge("start", "remind", "always"),
        edge("remind", "confirmed", condition="The patient will come"),
        edge("remind", "reschedule", condition="The patient cannot come or wants another time"),
        edge("remind", "opted_out", condition="The person asks not to be called again"),
    ]
    return Flow(nodes=nodes, edges=edges)


def build_templates(settings: Settings) -> list[AgentTemplate]:
    return [
        AgentTemplate(
            id="appointment-reminder",
            name="Appointment reminder",
            summary="Calls tomorrow's patients, confirms or reschedules, leaves voicemail.",
            channel_label="Outbound campaign",
            fields=build_agent_fields(
                settings,
                "Appointment reminder",
                REMINDER_INSTRUCTIONS,
                "Hello, this is City Hospital calling about your appointment tomorrow.",
                REMINDER_ANALYSIS,
            ),
            flow=build_reminder_flow(),
        ),
    ]
