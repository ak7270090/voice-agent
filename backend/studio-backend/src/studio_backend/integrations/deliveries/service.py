"""After-call deliveries: one row per action per call, sent by a background job and retried
with growing waits (10 s, 30 s, 90 s, ...) while the receiver is down."""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from studio_backend.agents.models import Agent
from studio_backend.calls.models import Call
from studio_backend.core.config import Settings
from studio_backend.core.database import new_id
from studio_backend.integrations.credentials.service import SecretsKeyMissingError, secret_values
from studio_backend.integrations.deliveries.constants import (
    FAILED_DELIVERY,
    GOOGLE_SHEETS_ACTION,
    HUBSPOT_ACTION,
    PENDING_DELIVERY,
    SENT_DELIVERY,
    SKIPPED_DELIVERY,
    SLACK_ACTION,
)
from studio_backend.integrations.deliveries.models import Delivery
from studio_backend.integrations.deliveries.payload import call_payload
from studio_backend.integrations.deliveries.schemas import AfterCallAction
from studio_backend.integrations.deliveries.senders import (
    NothingToSendError,
    PermanentDeliveryError,
    RetryableDeliveryError,
    append_to_sheet,
    send_hubspot,
    send_slack,
    send_webhook,
)

RETRY_GROWTH = 3


class DeliveryNotFoundError(LookupError):
    pass


def actions_of(agent: Agent) -> list[AfterCallAction]:
    return [AfterCallAction.model_validate(action) for action in agent.after_call_actions]


async def schedule_deliveries(session: AsyncSession, call: Call, event: str) -> list[str]:
    """Records a delivery for each of the agent's enabled actions on this event; the caller
    enqueues them once they are committed."""
    agent = await session.get(Agent, call.agent_id)
    deliveries = [
        Delivery(id=new_id(), call_id=call.id, action_id=action.id, kind=action.kind, event=event)
        for action in actions_of(agent)
        if action.enabled and action.event == event
    ]
    session.add_all(deliveries)
    await session.commit()
    return [delivery.id for delivery in deliveries]


async def list_deliveries(session: AsyncSession, call_id: str) -> list[Delivery]:
    result = await session.scalars(
        select(Delivery).where(Delivery.call_id == call_id).order_by(Delivery.created_at)
    )
    return list(result)


async def reset_delivery(session: AsyncSession, call_id: str, delivery_id: str) -> Delivery:
    """For "send again" in the console, e.g. after fixing a webhook URL."""
    delivery = await session.get(Delivery, delivery_id)
    if delivery is None or delivery.call_id != call_id:
        raise DeliveryNotFoundError(delivery_id)
    delivery.status, delivery.attempts, delivery.last_error = PENDING_DELIVERY, 0, ""
    await session.commit()
    await session.refresh(delivery)
    return delivery


async def send(
    http: httpx.AsyncClient,
    action: AfterCallAction,
    payload: dict,
    delivery_id: str,
    secret: str | None,
) -> int:
    if action.kind == SLACK_ACTION:
        return await send_slack(http, secret, payload)
    if action.kind == HUBSPOT_ACTION:
        return await send_hubspot(http, secret, payload)
    if action.kind == GOOGLE_SHEETS_ACTION:
        return await append_to_sheet(http, action, secret, payload)
    return await send_webhook(http, action, payload, delivery_id, secret)


async def deliver(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    http: httpx.AsyncClient,
    delivery_id: str,
) -> float | None:
    """One attempt. Returns the seconds to wait before the next one, or None when done (sent,
    skipped, or given up)."""
    async with session_factory() as session:
        delivery = await session.get(Delivery, delivery_id)
        if delivery is None or delivery.status != PENDING_DELIVERY:
            return None
        call = await session.get(Call, delivery.call_id)
        agent = await session.get(Agent, call.agent_id)
        action = next((a for a in actions_of(agent) if a.id == delivery.action_id), None)
        if action is None:
            delivery.status, delivery.last_error = SKIPPED_DELIVERY, "the action was removed"
            await session.commit()
            return None
        delivery.attempts += 1
        retry_in = None
        try:
            secret = await _secret(session, settings, action)
            payload = call_payload(delivery.event, call, agent, settings)
            delivery.response_status = await send(http, action, payload, delivery.id, secret)
            delivery.status, delivery.last_error = SENT_DELIVERY, ""
        except NothingToSendError as reason:
            delivery.status, delivery.last_error = SKIPPED_DELIVERY, str(reason)
        except PermanentDeliveryError as error:
            delivery.status, delivery.last_error = FAILED_DELIVERY, str(error)
            delivery.response_status = error.status
        except (RetryableDeliveryError, httpx.HTTPError) as error:
            delivery.last_error = str(error) or type(error).__name__
            delivery.response_status = getattr(error, "status", None)
            if delivery.attempts < settings.delivery_attempts:
                growth = RETRY_GROWTH ** (delivery.attempts - 1)
                retry_in = settings.delivery_first_retry_seconds * growth
            else:
                delivery.status = FAILED_DELIVERY
        await session.commit()
        return retry_in


async def _secret(session: AsyncSession, settings: Settings, action: AfterCallAction) -> str | None:
    if not action.secret:
        return None
    try:
        values = await secret_values(session, settings, {action.secret})
    except SecretsKeyMissingError as error:
        raise PermanentDeliveryError("SECRETS_KEY is not set on the API") from error
    if action.secret not in values:
        raise PermanentDeliveryError(f"secret {action.secret} is not set")
    return values[action.secret]
