"""The dialler. Every few seconds (an arq cron job) it places the campaign calls that are due:
inside the calling window, under the concurrency limit, consented contacts only, retries once
their wait is over. A contact is marked "calling" and committed before its call is dispatched,
so a dialler run that repeats (a crash, an overlap) never rings the same contact twice.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_api.campaigns.constants import (
    CALLING,
    COMPLETED,
    NOBODY_REACHED_OUTCOMES,
    OPEN,
    RUNNING,
    WAITING,
)
from studio_api.campaigns.models import Campaign, CampaignContact
from studio_api.campaigns.service import apply_outcome
from studio_api.database import assume_utc
from studio_api.numbers.constants import OUTBOUND_CALL_ROOM_PREFIX, PHONE_CHANNEL
from studio_api.numbers.service import get_number
from studio_api.numbers.telephony import Telephony, TelephonyError

# What a call that never reported back counts as.
LOST_CALL_OUTCOME = NOBODY_REACHED_OUTCOMES[0]


def in_window(campaign: Campaign, now: datetime) -> bool:
    local = now.astimezone(ZoneInfo(campaign.timezone)).time()
    return campaign.window_start <= local < campaign.window_end


def is_due(contact: CampaignContact, now: datetime) -> bool:
    return contact.next_attempt_at is None or assume_utc(contact.next_attempt_at) <= now


def room_for(contact: CampaignContact) -> str:
    """One room per attempt: the call record and the outcome are matched to it."""
    return f"{OUTBOUND_CALL_ROOM_PREFIX}{contact.id[:8]}-{contact.attempts}"


async def run_dialler(
    session: AsyncSession, telephony: Telephony, now: datetime, call_timeout: timedelta
) -> list[str]:
    """One pass over the running campaigns; returns the rooms it dispatched calls into."""
    # Stored times are UTC (SQLite drops the offset of any other zone).
    now = now.astimezone(UTC)
    campaigns = list(await session.scalars(select(Campaign).where(Campaign.status == RUNNING)))
    rooms: list[str] = []
    for campaign in campaigns:
        contacts = list(
            await session.scalars(
                select(CampaignContact)
                .where(CampaignContact.campaign_id == campaign.id)
                .order_by(CampaignContact.created_at, CampaignContact.id)
            )
        )
        for contact in contacts:
            stale = now - call_timeout
            if contact.status == CALLING and assume_utc(contact.updated_at) < stale:
                apply_outcome(contact, campaign, LOST_CALL_OUTCOME, now)
        await session.commit()
        if in_window(campaign, now):
            rooms += await _dial(session, telephony, campaign, contacts, now)
        if not any(contact.status in OPEN for contact in contacts):
            campaign.status = COMPLETED
            await session.commit()
    return rooms


async def _dial(
    session: AsyncSession,
    telephony: Telephony,
    campaign: Campaign,
    contacts: list[CampaignContact],
    now: datetime,
) -> list[str]:
    calling = sum(contact.status == CALLING for contact in contacts)
    free_lines = campaign.max_concurrent - calling
    due = [c for c in contacts if c.status in WAITING and c.consent and is_due(c, now)]
    if free_lines <= 0 or not due:
        return []
    number = await get_number(session, campaign.from_number_id)
    rooms = []
    for contact in due[:free_lines]:
        previous_status = contact.status
        contact.status, contact.attempts = CALLING, contact.attempts + 1
        contact.last_room = room_for(contact)
        await session.commit()
        try:
            await telephony.dispatch_outbound_call(
                contact.last_room,
                {
                    "agent_id": campaign.agent_id,
                    "channel": PHONE_CHANNEL,
                    "dial_to": contact.phone,
                    "outbound_trunk_id": number.outbound_trunk_id,
                    "campaign_contact_id": contact.id,
                    "variables": {"name": contact.name, **contact.variables},
                },
            )
        except TelephonyError:
            # Not placed: the attempt does not count, and the next run tries again.
            contact.status, contact.attempts = previous_status, contact.attempts - 1
            await session.commit()
            continue
        rooms.append(contact.last_room)
    return rooms
