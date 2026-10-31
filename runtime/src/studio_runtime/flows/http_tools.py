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
# A lookup that gets no answer is tried once more; a booking is not (it may have gone through).
RETRIED_METHODS = ("GET",)
LOOKUP_ATTEMPTS = 2
SERVER_ERROR_STATUS = 500


class MissingValueError(KeyError):
    pass


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Any
    # The service gave no answer (timeout, network error, 5xx), as opposed to answering "no".
    unavailable: bool = False


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
    except MissingValueError as error:
        return ToolResult(ok=False, data={"error": f"missing value for {error.args[0]}"})
    attempts = LOOKUP_ATTEMPTS if tool.method in RETRIED_METHODS else 1
    for _ in range(attempts):
        result = await _send(http, tool.method, url, body)
        if not result.unavailable:
            break
    return result


async def _send(http: httpx.AsyncClient, method: str, url: str, body: Any) -> ToolResult:
    try:
        response = await http.request(method, url, json=body)
    except httpx.HTTPError as error:
        return ToolResult(ok=False, data={"error": type(error).__name__}, unavailable=True)
    try:
        data = response.json()
    except ValueError:
        data = response.text[:MAX_TEXT_RESULT_CHARS]
    unavailable = response.status_code >= SERVER_ERROR_STATUS
    return ToolResult(ok=response.is_success, data=data, unavailable=unavailable)
