"""Post-call analysis: a summary, whether the call succeeded (by the agent's own rule), the
caller's sentiment, the agent's analysis fields and a QA score, read from the transcript.

Runs as a background job when a call ends. The result's shape is built from the agent's fields,
and every field is required (its value may be null: "not said"), so the model cannot leave one
out; Retell users report custom fields going missing when they are optional.
"""

import logging
from collections.abc import Callable
from typing import Any, Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field, create_model
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from studio_api.agents.constants import CHOICE_FIELD, NUMBER_FIELD, YES_NO_FIELD
from studio_api.agents.models import Agent
from studio_api.agents.schemas import AnalysisField
from studio_api.calls.constants import (
    ANALYSIS_DONE,
    ANALYSIS_FAILED,
    ANALYSIS_PENDING,
    SENTIMENTS,
)
from studio_api.calls.costs import ANALYSIS_COST_PART, llm_cost
from studio_api.calls.models import Call
from studio_api.config import Settings

logger = logging.getLogger(__name__)

ANALYSIS_TIMEOUT_SECONDS = 60
DEFAULT_SUCCESS_RULE = "The caller got what they called for, or the agent's goal was reached."
INSTRUCTIONS = """You review a finished phone call between an AI agent and a caller.
Judge only from the transcript and the call's record; never guess what was not said.
- summary: two short sentences: what the caller wanted, and what happened.
- successful: true only if this rule is met: {success_rule}
  Judge by what the caller actually got: saying the information is not available, promising
  someone will call back, or offering to transfer is not an answer and not a success.
- sentiment: the caller's mood by the end of the call.
- fields: answer each one from the call; null when the call does not say.
- qa_score from 1 to 5 for the agent: did it answer what was asked, confirm details before
  acting, never claim something a tool did not do, stay brief, and end the call properly.
  qa_notes says what lowered the score, or "No issues"."""


def field_type(spec: AnalysisField) -> Any:
    if spec.type == CHOICE_FIELD:
        return Literal[tuple(spec.choices)]
    if spec.type == YES_NO_FIELD:
        return bool
    if spec.type == NUMBER_FIELD:
        return float
    return str


def result_model(specs: list[AnalysisField]) -> type[BaseModel]:
    """The analysis shape for one agent. Its own fields are required but may be null."""
    fields = create_model(
        "AnalysisFields",
        **{
            spec.name: (field_type(spec) | None, Field(description=spec.description))
            for spec in specs
        },
    )
    return create_model(
        "CallAnalysis",
        summary=(str, Field(description="Two sentences: what was wanted, what happened")),
        successful=(bool, Field(description="Whether the success rule was met")),
        success_reason=(str, Field(description="One sentence: why it was or was not")),
        sentiment=(Literal[SENTIMENTS], Field(description="The caller's mood at the end")),
        fields=(fields, Field(description="The agent's own questions about the call")),
        qa_score=(int, Field(ge=1, le=5, description="The agent's handling of the call")),
        qa_notes=(str, Field(description="What lowered the score, or 'No issues'")),
    )


def call_as_text(call: Call) -> str:
    lines = [f"{turn['role']}: {turn['text']}" for turn in call.transcript]
    return (
        f"Outcome recorded by the flow: {call.outcome or 'none'}\n"
        f"Details collected: {call.fields or {}}\n"
        f"Tool calls: {[(t['name'], 'ok' if t['ok'] else 'failed') for t in call.tool_calls]}\n"
        "Transcript:\n" + "\n".join(lines)
    )


def create_analysis_model(settings: Settings, shape: type[BaseModel]) -> Runnable:
    """Answers {"parsed": the analysis, "raw": the model's message}: the raw message carries
    the token usage, so the analysis is priced like the call."""
    model = init_chat_model(settings.analysis_llm_model, timeout=ANALYSIS_TIMEOUT_SECONDS)
    return model.with_structured_output(shape, include_raw=True)


async def analyse(model: Runnable, call: Call, agent: Agent) -> tuple[dict[str, Any], dict]:
    """The analysis, and the tokens it used."""
    rule = agent.success_rule or DEFAULT_SUCCESS_RULE
    answer = await model.ainvoke(
        [
            SystemMessage(INSTRUCTIONS.format(success_rule=rule)),
            HumanMessage(call_as_text(call)),
        ]
    )
    if answer.get("parsing_error") or answer["parsed"] is None:
        raise ValueError(f"the analysis did not fit its shape: {answer.get('parsing_error')}")
    usage = getattr(answer["raw"], "usage_metadata", None) or {}
    return answer["parsed"].model_dump(mode="json"), usage


def with_analysis_cost(cost: dict, usage: dict, settings: Settings) -> dict:
    """The call's cost with the analysis's own LLM call added as its own part."""
    cached = (usage.get("input_token_details") or {}).get("cache_read", 0)
    analysis = llm_cost(
        usage.get("input_tokens", 0),
        cached,
        usage.get("output_tokens", 0),
        settings.llm_prices.get(settings.analysis_llm_model),
    )
    total = cost.get("total", 0) - cost.get(ANALYSIS_COST_PART, 0) + analysis
    return {**cost, ANALYSIS_COST_PART: round(analysis, 5), "total": round(total, 5)}


ModelFactory = Callable[[Settings, type[BaseModel]], Runnable]


async def run_analysis(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    call_id: str,
    model_factory: ModelFactory = create_analysis_model,
) -> None:
    """The background job. A failure is recorded on the call rather than retried forever."""
    async with session_factory() as session:
        call = await session.get(Call, call_id)
        if call is None or call.analysis_status != ANALYSIS_PENDING:
            return
        agent = await session.get(Agent, call.agent_id)
        specs = [AnalysisField.model_validate(spec) for spec in agent.analysis_fields]
        try:
            model = model_factory(settings, result_model(specs))
            call.analysis, usage = await analyse(model, call, agent)
            call.cost = with_analysis_cost(call.cost, usage, settings)
            call.analysis_status = ANALYSIS_DONE
        except Exception:
            logger.exception("post-call analysis failed for call %s", call_id)
            call.analysis_status = ANALYSIS_FAILED
        await session.commit()
