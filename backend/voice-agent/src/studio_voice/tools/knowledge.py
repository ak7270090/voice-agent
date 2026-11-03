"""The `search_knowledge` tool: an agent's documents, searched through the backend at call time."""

from langchain_core.tools import BaseTool, StructuredTool

from studio_voice.core.backend_client import BackendClient, KnowledgeHit
from studio_voice.languages import Locale

TOOL_NAME = "search_knowledge"
TOOL_DESCRIPTION = (
    "Search this agent's documents (policies, prices, timings, people, procedures). "
    "Use it for any factual question about the business; never answer those from memory. "
    "Pass the caller's question in their own words."
)


def format_hits(hits: list[KnowledgeHit], nothing_found: str) -> str:
    if not hits:
        return nothing_found
    return "\n\n".join(f"[{hit.document_name}]\n{hit.text}" for hit in hits)


def build_knowledge_tool(backend_client: BackendClient, agent_id: str, locale: Locale) -> BaseTool:
    async def search_knowledge(question: str) -> str:
        hits = await backend_client.search_knowledge(agent_id, question)
        return format_hits(hits, locale.messages["knowledge_nothing_found"])

    return StructuredTool.from_function(
        coroutine=search_knowledge, name=TOOL_NAME, description=TOOL_DESCRIPTION
    )
