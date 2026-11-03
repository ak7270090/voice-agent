"""Calling a flow's HTTP tools: {placeholders} in the URL, headers and body come from collected
fields (or the LLM's arguments for tools attached to a step), and {secret.NAME} from the
agent's stored secrets."""

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from studio_voice.flows.schema import ToolData

PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")
# Fields and secrets in one pattern, filled in one pass: a filled-in value (the caller's words)
# is never read again, so a caller saying "{secret.KEY}" cannot make a tool send the key.
REQUEST_PLACEHOLDER = re.compile(r"\{(?:secret\.([A-Z][A-Z0-9_]*)|([a-z][a-z0-9_]*))\}")
# Secret values found in a result (an error page echoing the key) are replaced before the
# result reaches the LLM, the trace or the call record.
SECRET_MASK = "[secret]"
MIN_MASKED_SECRET_CHARS = 4
# Tool results go back into the LLM's prompt; long pages are cut.
MAX_TEXT_RESULT_CHARS = 2000
# A request that gets no answer is tried once more if repeating it is safe: a lookup (GET), or a
# booking sent with an idempotency key (the service returns the first booking, not a second).
SAFE_TO_REPEAT_METHODS = ("GET",)
ATTEMPTS_WHEN_SAFE = 2
SERVER_ERROR_STATUS = 500
IDEMPOTENCY_HEADER = "Idempotency-Key"


class MissingValueError(KeyError):
    pass


class MissingSecretError(KeyError):
    pass


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Any
    # The service gave no answer (timeout, network error, 5xx), as opposed to answering "no".
    unavailable: bool = False


def strings_in(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in strings_in(item)]
    if isinstance(value, list):
        return [text for item in value for text in strings_in(item)]
    return []


def placeholders(tool: ToolData) -> list[str]:
    """The fields the request needs (secrets are not the LLM's to give)."""
    templates = [tool.url, *tool.headers.values(), *strings_in(tool.body)]
    found = [name for template in templates for name in PLACEHOLDER.findall(template)]
    return list(dict.fromkeys(found))


def fill(
    template: str,
    values: dict[str, Any],
    secrets: dict[str, str] | None = None,
    *,
    url_encode: bool = False,
) -> str:
    def replace(match: re.Match) -> str:
        secret, name = match.groups()
        if secret is not None:
            if not secrets or secret not in secrets:
                raise MissingSecretError(secret)
            text = secrets[secret]
        else:
            if name not in values:
                raise MissingValueError(name)
            text = str(values[name])
        return quote(text, safe="") if url_encode else text

    return REQUEST_PLACEHOLDER.sub(replace, template)


def fill_leniently(template: str, values: dict[str, Any]) -> str:
    """For spoken messages: an unknown placeholder becomes empty rather than failing. Secrets
    are never filled here, so no secret is ever spoken."""
    return PLACEHOLDER.sub(lambda match: str(values.get(match.group(1), "")), template)


def fill_json(value: Any, values: dict[str, Any], secrets: dict[str, str] | None) -> Any:
    """A string that is exactly "{field}" keeps the field's type (an age stays a number)."""
    if isinstance(value, str):
        whole = PLACEHOLDER.fullmatch(value)
        if whole:
            if whole.group(1) not in values:
                raise MissingValueError(whole.group(1))
            return values[whole.group(1)]
        return fill(value, values, secrets)
    if isinstance(value, dict):
        return {key: fill_json(item, values, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [fill_json(item, values, secrets) for item in value]
    return value


def build_body(
    tool: ToolData, values: dict[str, Any], secrets: dict[str, str] | None = None
) -> dict[str, Any]:
    return fill_json(tool.body, values, secrets)


def mask_secrets(value: Any, secrets: dict[str, str] | None) -> Any:
    hidden = [
        secret for secret in (secrets or {}).values() if len(secret) >= MIN_MASKED_SECRET_CHARS
    ]
    if not hidden:
        return value
    if isinstance(value, str):
        for secret in hidden:
            value = value.replace(secret, SECRET_MASK)
        return value
    if isinstance(value, dict):
        return {key: mask_secrets(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_secrets(item, secrets) for item in value]
    return value


async def call_tool(
    http: httpx.AsyncClient,
    tool: ToolData,
    values: dict[str, Any],
    idempotency_key: str | None = None,
    secrets: dict[str, str] | None = None,
) -> ToolResult:
    try:
        url = fill(tool.url, values, secrets, url_encode=True)
        headers = {name: fill(text, values, secrets) for name, text in tool.headers.items()}
        body = build_body(tool, values, secrets) if tool.method == "POST" else None
    except MissingValueError as error:
        return ToolResult(ok=False, data={"error": f"missing value for {error.args[0]}"})
    except MissingSecretError as error:
        return ToolResult(ok=False, data={"error": f"secret {error.args[0]} is not set"})
    keyed = bool(idempotency_key) and tool.method not in SAFE_TO_REPEAT_METHODS
    if keyed:
        headers[IDEMPOTENCY_HEADER] = idempotency_key
    safe_to_repeat = tool.method in SAFE_TO_REPEAT_METHODS or keyed
    for _ in range(ATTEMPTS_WHEN_SAFE if safe_to_repeat else 1):
        result = await _send(http, tool.method, url, body, headers)
        if not result.unavailable:
            break
    return ToolResult(result.ok, mask_secrets(result.data, secrets), result.unavailable)


async def _send(
    http: httpx.AsyncClient, method: str, url: str, body: Any, headers: dict[str, str]
) -> ToolResult:
    try:
        response = await http.request(method, url, json=body, headers=headers)
    except httpx.HTTPError as error:
        return ToolResult(ok=False, data={"error": type(error).__name__}, unavailable=True)
    try:
        data = response.json()
    except ValueError:
        data = response.text[:MAX_TEXT_RESULT_CHARS]
    unavailable = response.status_code >= SERVER_ERROR_STATUS
    return ToolResult(ok=response.is_success, data=data, unavailable=unavailable)
