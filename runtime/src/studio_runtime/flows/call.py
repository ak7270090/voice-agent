"""Setting up a flow for one call: the runner, the LLM in front of it, and what the console sees."""

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from langchain.chat_models import init_chat_model
from langchain_core.tools import BaseTool
from livekit import rtc
from livekit.plugins.langchain import LLMAdapter

from studio_runtime.config import Settings
from studio_runtime.control_plane import AgentConfig
from studio_runtime.flows.graph import FlowGraph
from studio_runtime.flows.runner import FlowRunner
from studio_runtime.parsers import parsers_for

# Participant attributes the console reads to highlight the live node and show the fields.
FLOW_NODE_ATTRIBUTE = "studio.flow_node"
FLOW_FIELDS_ATTRIBUTE = "studio.fields"


def publish_progress(room: rtc.Room, runner: FlowRunner) -> None:
    attributes = {
        FLOW_NODE_ATTRIBUTE: runner.path[-1] if runner.path else "",
        FLOW_FIELDS_ATTRIBUTE: json.dumps(runner.fields, default=str),
    }
    asyncio.get_running_loop().create_task(room.local_participant.set_attributes(attributes))


def create_flow_runner(
    config: AgentConfig,
    language: str,
    settings: Settings,
    room: rtc.Room,
    knowledge_tool: BaseTool | None,
    knowledge_rule: str,
) -> FlowRunner:
    return FlowRunner(
        config.flow,
        httpx.AsyncClient(timeout=settings.tool_timeout_seconds),
        parsers_for(language),
        datetime.now(ZoneInfo(settings.timezone)).date(),
        knowledge_tool=knowledge_tool,
        knowledge_rule=knowledge_rule,
        on_change=lambda runner: publish_progress(room, runner),
    )


def create_flow_llm(
    runner: FlowRunner, config: AgentConfig, base_instructions: str, settings: Settings
) -> LLMAdapter:
    model = init_chat_model(config.llm_model)
    return LLMAdapter(FlowGraph(runner, model, base_instructions, settings.llm_max_retries))
