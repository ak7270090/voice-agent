"""Calls people who asked about a product and qualifies them for a sales meeting."""

from studio_backend.agents.schemas import AgentTemplate
from studio_backend.agents.template_parts import at, build_agent_fields, edge
from studio_backend.config import Settings
from studio_backend.flows.schemas import (
    EndData,
    EndNode,
    FieldSpec,
    Flow,
    StartNode,
    StepData,
    StepNode,
)

LEAD_QUALIFIER_INSTRUCTIONS = """You call people who asked about our product.
Find out what they need, their budget and their timeline, and offer a meeting with sales."""


def build_lead_qualifier_flow() -> Flow:
    nodes = [
        StartNode(id="start", type="start", position=at(1, 0)),
        StepNode(
            id="qualify",
            type="step",
            position=at(1, 1),
            data=StepData(
                name="Qualify the lead",
                instructions="Find out what they need, their budget and when they want to start.",
                fields=[
                    FieldSpec(name="need", description="What they want to solve"),
                    FieldSpec(name="budget", description="Budget, with currency"),
                    FieldSpec(name="timeline", description="When they want to start"),
                ],
            ),
        ),
        StepNode(
            id="offer_meeting",
            type="step",
            position=at(1, 2),
            data=StepData(
                name="Offer a meeting",
                instructions="Offer a short call with sales and ask for a day that suits them.",
                fields=[FieldSpec(name="meeting_day", type="date", description="Meeting day")],
            ),
        ),
        EndNode(
            id="qualified",
            type="end",
            position=at(0, 3),
            data=EndData(
                outcome="meeting_requested",
                message="Thanks. Our sales team will confirm the meeting for {meeting_day}.",
            ),
        ),
        EndNode(
            id="not_interested",
            type="end",
            position=at(2, 3),
            data=EndData(outcome="not_interested", message="Thanks for your time. Goodbye."),
        ),
    ]
    edges = [
        edge("start", "qualify", "always"),
        edge("qualify", "offer_meeting", "fields_complete"),
        edge("qualify", "not_interested", condition="They are not interested"),
        edge("offer_meeting", "qualified", "fields_complete"),
        edge("offer_meeting", "not_interested", condition="They do not want a meeting"),
    ]
    return Flow(nodes=nodes, edges=edges)


def build_templates(settings: Settings) -> list[AgentTemplate]:
    return [
        AgentTemplate(
            id="lead-qualifier",
            name="Lead qualifier",
            summary="Asks about need, budget and timeline, then books a meeting.",
            channel_label="Outbound",
            fields=build_agent_fields(
                settings,
                "Lead qualifier",
                LEAD_QUALIFIER_INSTRUCTIONS,
                "Hi, thanks for your interest. Do you have two minutes to talk about it?",
            ),
            flow=build_lead_qualifier_flow(),
        ),
    ]
