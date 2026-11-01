"""Sending one call's result to a webhook, Slack, HubSpot or a Google Sheet.

Each sender raises NothingToSendError when there is nothing to do (no number to match a CRM
contact), PermanentDeliveryError for an answer that will not change on a retry (a refused token),
and lets other errors (timeouts, 5xx) through so the delivery is retried.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from studio_api.after_call.constants import (
    DELIVERY_HEADER,
    EMAIL_FIELD,
    EVENT_HEADER,
    GOOGLE_SHEETS_API_URL,
    GOOGLE_SHEETS_SCOPE,
    GOOGLE_TOKEN_SECONDS,
    HUBSPOT_API_URL,
    HUBSPOT_NOTE_TO_CONTACT,
    MAX_ERROR_CHARS,
    NAME_FIELDS,
    PHONE_FIELDS,
    RETRYABLE_STATUSES,
    SERVER_ERROR_STATUS,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
)
from studio_api.after_call.schemas import AfterCallAction


class NothingToSendError(Exception):
    pass


class PermanentDeliveryError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class RetryableDeliveryError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def check(response: httpx.Response, service: str) -> httpx.Response:
    if response.is_success:
        return response
    message = f"{service} answered {response.status_code}: {response.text[:MAX_ERROR_CHARS]}"
    if response.status_code >= SERVER_ERROR_STATUS or response.status_code in RETRYABLE_STATUSES:
        raise RetryableDeliveryError(message, response.status_code)
    raise PermanentDeliveryError(message, response.status_code)


def sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"sha256={digest.hexdigest()}"


async def send_webhook(
    http: httpx.AsyncClient,
    action: AfterCallAction,
    payload: dict[str, Any],
    delivery_id: str,
    secret: str | None,
) -> int:
    body = json.dumps(payload, default=str).encode()
    headers = {
        "Content-Type": "application/json",
        EVENT_HEADER: payload["event"],
        DELIVERY_HEADER: delivery_id,
    }
    if secret:
        timestamp = int(time.time())
        headers[TIMESTAMP_HEADER] = str(timestamp)
        headers[SIGNATURE_HEADER] = sign(secret, timestamp, body)
    response = check(await http.post(action.url, content=body, headers=headers), "the webhook")
    return response.status_code


def slack_text(payload: dict[str, Any]) -> str:
    call = payload["call"]
    who = call["remote_number"] or "browser"
    parts = [f"*{call['agent']['name']}*", f"{call['channel']} {call['direction']} ({who})"]
    parts.append(call["outcome"] or "no outcome")
    if call["duration_seconds"] is not None:
        parts.append(f"{round(call['duration_seconds'])} s")
    if call["successful"] is not None:
        parts.append("successful" if call["successful"] else "not successful")
    lines = [" · ".join(parts)]
    if call["summary"]:
        lines.append(call["summary"])
    lines.append(f"<{call['url']}|Open the call>")
    return "\n".join(lines)


async def send_slack(http: httpx.AsyncClient, webhook_url: str, payload: dict[str, Any]) -> int:
    response = await http.post(webhook_url, json={"text": slack_text(payload)})
    return check(response, "Slack").status_code


def first_field(fields: dict[str, Any], names: tuple[str, ...]) -> str | None:
    return next((str(fields[name]) for name in names if fields.get(name)), None)


def hubspot_note(payload: dict[str, Any]) -> str:
    call = payload["call"]
    lines = [f"<b>Call with {call['agent']['name']}</b>: {call['outcome'] or 'no outcome'}"]
    if call["summary"]:
        lines.append(call["summary"])
    details = ", ".join(f"{name}: {value}" for name, value in call["fields"].items())
    if details:
        lines.append(f"Details: {details}")
    lines.append(f'<a href="{call["url"]}">Open the call</a>')
    return "<br>".join(lines)


async def send_hubspot(http: httpx.AsyncClient, token: str, payload: dict[str, Any]) -> int:
    """Finds the contact by phone number (or email), creates it if there is none, and adds the
    call's summary as a note on it."""
    call = payload["call"]
    fields = call["fields"]
    phone = call["remote_number"] or first_field(fields, PHONE_FIELDS)
    email = first_field(fields, (EMAIL_FIELD,))
    if not phone and not email:
        raise NothingToSendError("no phone number or email to match a HubSpot contact")
    headers = {"Authorization": f"Bearer {token}"}
    match = ("phone", phone) if phone else ("email", email)
    search = await http.post(
        f"{HUBSPOT_API_URL}/crm/v3/objects/contacts/search",
        json={
            "filterGroups": [
                {"filters": [{"propertyName": match[0], "operator": "EQ", "value": match[1]}]}
            ],
            "limit": 1,
        },
        headers=headers,
    )
    found = check(search, "HubSpot").json().get("results", [])
    if found:
        contact_id = found[0]["id"]
    else:
        properties = {"phone": phone, "email": email}
        name = first_field(fields, NAME_FIELDS)
        if name:
            first, _, last = name.partition(" ")
            properties |= {"firstname": first, "lastname": last}
        created = await http.post(
            f"{HUBSPOT_API_URL}/crm/v3/objects/contacts",
            json={"properties": {key: value for key, value in properties.items() if value}},
            headers=headers,
        )
        contact_id = check(created, "HubSpot").json()["id"]
    note = await http.post(
        f"{HUBSPOT_API_URL}/crm/v3/objects/notes",
        json={
            "properties": {
                "hs_timestamp": call["ended_at"] or call["started_at"],
                "hs_note_body": hubspot_note(payload),
            },
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": HUBSPOT_NOTE_TO_CONTACT,
                        }
                    ],
                }
            ],
        },
        headers=headers,
    )
    return check(note, "HubSpot").status_code


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def service_account_assertion(account: dict[str, Any], now: int) -> str:
    """A JWT signed with the service account's private key (RS256), as Google's token endpoint
    expects; no Google library needed."""
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = {
        "iss": account["client_email"],
        "scope": GOOGLE_SHEETS_SCOPE,
        "aud": account["token_uri"],
        "iat": now,
        "exp": now + GOOGLE_TOKEN_SECONDS,
    }
    signing_input = f"{header}.{b64url(json.dumps(claims).encode())}"
    key = serialization.load_pem_private_key(account["private_key"].encode(), password=None)
    signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{b64url(signature)}"


def sheet_row(payload: dict[str, Any]) -> list[Any]:
    call = payload["call"]
    successful = call["successful"]
    return [
        call["ended_at"] or call["started_at"],
        call["agent"]["name"],
        call["channel"],
        call["direction"],
        call["remote_number"] or "",
        call["outcome"] or "",
        "" if successful is None else ("yes" if successful else "no"),
        call["summary"] or "",
        call["duration_seconds"] or "",
        call["cost_usd"] if call["cost_usd"] is not None else "",
        call["url"],
    ]


async def append_to_sheet(
    http: httpx.AsyncClient, action: AfterCallAction, key_json: str, payload: dict[str, Any]
) -> int:
    try:
        account = json.loads(key_json)
        assertion = service_account_assertion(account, int(time.time()))
    except (ValueError, KeyError, TypeError) as error:
        raise PermanentDeliveryError(
            "the secret is not a Google service account JSON key"
        ) from error
    token = await http.post(
        account["token_uri"],
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
    )
    access_token = check(token, "Google").json()["access_token"]
    cells = f"{action.sheet_name}!A1"
    response = await http.post(
        f"{GOOGLE_SHEETS_API_URL}/{action.spreadsheet_id}/values/{cells}:append",
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        json={"values": [sheet_row(payload)]},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return check(response, "Google Sheets").status_code
