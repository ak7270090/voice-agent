"""What every example agent is built from: its settings, and where its flow's steps sit."""

from studio_backend.agents.constants import ENGLISH
from studio_backend.agents.schemas import AgentFields, AnalysisField, VoiceSettings
from studio_backend.config import Settings
from studio_backend.flows.schemas import FlowEdge, Position

COLUMN = 300
ROW = 150


def at(column: float, row: float) -> Position:
    return Position(x=column * COLUMN, y=row * ROW)


def edge(source: str, target: str, kind: str = "condition", condition: str = "") -> FlowEdge:
    return FlowEdge(
        id=f"{source}-{target}", source=source, target=target, kind=kind, condition=condition
    )


def build_agent_fields(
    settings: Settings,
    name: str,
    instructions: str,
    greeting: str,
    analysis: tuple[list[AnalysisField], str] = ([], ""),
) -> AgentFields:
    """`analysis` is the post-call analysis: (fields, success rule)."""
    voice = VoiceSettings(
        stt_model=settings.default_stt_model,
        tts_model=settings.default_tts_model,
        voice=settings.default_voice,
    )
    return AgentFields(
        name=name,
        instructions=instructions,
        greeting=greeting,
        llm_model=settings.default_llm_model,
        languages=[ENGLISH],
        language_settings={ENGLISH: voice},
        analysis_fields=analysis[0],
        success_rule=analysis[1],
    )
