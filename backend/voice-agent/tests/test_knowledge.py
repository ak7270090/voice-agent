import json

import httpx

from studio_voice.backend_client import BackendClient
from studio_voice.languages import load_locale
from studio_voice.tools.knowledge import build_knowledge_tool

HITS = [
    {"document_name": "timings.md", "text": "Open 8 am to 8 pm.", "score": 0.9},
    {"document_name": "doctors.md", "text": "Dr. Rao sees patients daily.", "score": 0.7},
]


def tool_answering(hits: list[dict]) -> tuple:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=hits)

    http = httpx.AsyncClient(transport=httpx.MockTransport(answer), base_url="http://api")
    tool = build_knowledge_tool(BackendClient(http), "agent-1", load_locale("en"))
    return tool, requests


async def test_tool_searches_the_agents_documents_and_cites_each_hit():
    tool, requests = tool_answering(HITS)

    result = await tool.ainvoke({"question": "When are you open?"})

    assert tool.name == "search_knowledge"
    assert requests[0].url.path == "/runtime/agents/agent-1/knowledge-search"
    assert json.loads(requests[0].content) == {"query": "When are you open?"}
    assert (
        result == "[timings.md]\nOpen 8 am to 8 pm.\n\n[doctors.md]\nDr. Rao sees patients daily."
    )


async def test_tool_says_so_when_nothing_matches():
    tool, _ = tool_answering([])

    assert await tool.ainvoke({"question": "Do you sell cars?"}) == (
        "Nothing about this in the documents."
    )
