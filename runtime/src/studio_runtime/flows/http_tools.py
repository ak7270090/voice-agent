"""Calling a flow's HTTP tools: {placeholders} in the URL and body come from collected fields
(or the LLM's arguments for tools attached to a step)."""

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from studio_runtime.flows.schema import ToolData

PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")
# Tool results go back into the LLM's prompt; long pages are cut.
MAX_TEXT_RESULT_CHARS = 2000


class MissingValueError(KeyError):
    pass


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Any


def placeholders(tool: ToolData) -> list[str]:
    found = PLACEHOLDER.findall(tool.url) + [
        name for template in tool.body.values() for name in PLACEHOLDER.findall(template)
    ]
    return list(dict.fromkeys(found))


def fill(template: str, values: dict[str, Any], *, url_encode: bool = False) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in values:
            raise MissingValueError(name)
        text = str(values[name])
        return quote(text, safe="") if url_encode else text

    return PLACEHOLDER.sub(replace, template)


def fill_leniently(template: str, values: dict[str, Any]) -> str:
    """For spoken messages: an unknown placeholder becomes empty rather than failing."""
    return PLACEHOLDER.sub(lambda match: str(values.get(match.group(1), "")), template)


def build_body(tool: ToolData, values: dict[str, Any]) -> dict[str, Any]:
    """A body value that is exactly "{field}" keeps the field's type (an age stays a number)."""
    body = {}
    for key, template in tool.body.items():
        whole = PLACEHOLDER.fullmatch(template)
        if whole:
            if whole.group(1) not in values:
                raise MissingValueError(whole.group(1))
            body[key] = values[whole.group(1)]
        else:
            body[key] = fill(template, values)
    return body


async def call_tool(http: httpx.AsyncClient, tool: ToolData, values: dict[str, Any]) -> ToolResult:
    try:
        url = fill(tool.url, values, url_encode=True)
        body = build_body(tool, values) if tool.method == "POST" else None
        response = await http.request(tool.method, url, json=body)
    except MissingValueError as error:
        return ToolResult(ok=False, data={"error": f"missing value for {error.args[0]}"})
    except httpx.HTTPError as error:
        return ToolResult(ok=False, data={"error": f"{type(error).__name__}: {error}"})
    try:
        data = response.json()
    except ValueError:
        data = response.text[:MAX_TEXT_RESULT_CHARS]
    return ToolResult(ok=response.is_success, data=data)
