import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_backend.agents.service import get_agent
from studio_backend.campaigns.constants import (
    CALLING,
    COMPLETED,
    CONSENT_YES,
    CSV_CONSENT_COLUMN,
    CSV_NAME_COLUMN,
    CSV_PHONE_COLUMN,
    DONE,
    DRAFT,
    FAILED,
    NOBODY_REACHED_OUTCOMES,
    OPT_OUT_OUTCOME,
    OPTED_OUT,
    PAUSED,
    PENDING,
    RETRY,
    RUNNING,
    SKIPPED,
)
from studio_backend.campaigns.models import Campaign, CampaignContact
from studio_backend.campaigns.schemas import (
    CampaignCreate,
    CampaignRead,
    ContactCreate,
    ContactImport,
    RejectedRow,
)
from studio_backend.database import utc_now
from studio_backend.phone_numbers.service import CannotCallOutError, get_number

# Which status a campaign may move to from which.
ALLOWED_MOVES = {RUNNING: (PAUSED, DRAFT), PAUSED: (RUNNING,)}


class CampaignNotFoundError(LookupError):
    pass


class CampaignStateError(ValueError):
    pass


async def get_campaign(session: AsyncSession, campaign_id: str) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise CampaignNotFoundError(campaign_id)
    return campaign


async def create_campaign(session: AsyncSession, body: CampaignCreate) -> Campaign:
    await get_agent(session, body.agent_id)
    number = await get_number(session, body.from_number_id)
    if not number.can_call_out:
        raise CannotCallOutError(number.number)
    campaign = Campaign(**body.model_dump())
    session.add(campaign)
    await session.commit()
    return campaign


async def contact_counts(session: AsyncSession) -> dict[str, dict[str, int]]:
    rows = await session.execute(
        select(CampaignContact.campaign_id, CampaignContact.status, func.count()).group_by(
            CampaignContact.campaign_id, CampaignContact.status
        )
    )
    counts: dict[str, dict[str, int]] = defaultdict(dict)
    for campaign_id, status, count in rows:
        counts[campaign_id][status] = count
    return counts


async def list_campaigns(session: AsyncSession) -> list[CampaignRead]:
    campaigns = await session.scalars(select(Campaign).order_by(Campaign.created_at.desc()))
    counts = await contact_counts(session)
    return [read(campaign, counts) for campaign in campaigns]


async def read_campaign(session: AsyncSession, campaign_id: str) -> CampaignRead:
    return read(await get_campaign(session, campaign_id), await contact_counts(session))


def read(campaign: Campaign, counts: dict[str, dict[str, int]]) -> CampaignRead:
    return CampaignRead.model_validate(campaign).model_copy(
        update={"counts": counts.get(campaign.id, {})}
    )


async def move(session: AsyncSession, campaign_id: str, status: str) -> CampaignRead:
    """Start (or resume) and pause; a completed campaign stays completed."""
    campaign = await get_campaign(session, campaign_id)
    if campaign.status not in ALLOWED_MOVES[status]:
        raise CampaignStateError(f"a {campaign.status} campaign cannot become {status}")
    campaign.status = status
    await session.commit()
    return await read_campaign(session, campaign_id)


async def delete_campaign(session: AsyncSession, campaign_id: str) -> None:
    await session.delete(await get_campaign(session, campaign_id))
    await session.commit()


async def add_contacts(
    session: AsyncSession,
    campaign_id: str,
    contacts: list[ContactCreate],
    rejected: list[RejectedRow] | None = None,
) -> ContactImport:
    """Contacts without consent are kept (to show why they were not called) but never dialled."""
    campaign = await get_campaign(session, campaign_id)
    if campaign.status == COMPLETED:
        raise CampaignStateError("a completed campaign takes no new contacts")
    # One microsecond apart: contacts keep their list order (and are dialled in it), even
    # where the clock gives a whole import the same time.
    added_at = utc_now()
    for position, contact in enumerate(contacts):
        session.add(
            CampaignContact(
                campaign_id=campaign_id,
                **contact.model_dump(),
                status=PENDING if contact.consent else SKIPPED,
                created_at=added_at + timedelta(microseconds=position),
            )
        )
    await session.commit()
    skipped = sum(not contact.consent for contact in contacts)
    return ContactImport(added=len(contacts), skipped=skipped, rejected=rejected or [])


def parse_contacts_csv(text: str) -> tuple[list[ContactCreate], list[RejectedRow]]:
    """Columns: phone (E.164), name, consent (yes/no); any other column becomes a variable
    for the agent, e.g. appointment_time → {appointment_time}."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    reader.fieldnames = [name.strip().lower() for name in reader.fieldnames or []]
    contacts, rejected = [], []
    # Row 1 is the header.
    for row_number, row in enumerate(reader, start=2):
        values = {key: (value or "").strip() for key, value in row.items() if key}
        try:
            contacts.append(
                ContactCreate(
                    phone=values.pop(CSV_PHONE_COLUMN, ""),
                    name=values.pop(CSV_NAME_COLUMN, ""),
                    consent=values.pop(CSV_CONSENT_COLUMN, "").lower() in CONSENT_YES,
                    variables={key: value for key, value in values.items() if value},
                )
            )
        except ValidationError as error:
            reason = "; ".join(
                f"{'.'.join(map(str, problem['loc']))}: {problem['msg']}"
                for problem in error.errors(include_url=False)
            )
            rejected.append(RejectedRow(row=row_number, reason=reason))
    return contacts, rejected


async def list_contacts(session: AsyncSession, campaign_id: str) -> list[CampaignContact]:
    await get_campaign(session, campaign_id)
    query = (
        select(CampaignContact)
        .where(CampaignContact.campaign_id == campaign_id)
        .order_by(CampaignContact.created_at, CampaignContact.id)
    )
    return list(await session.scalars(query))


def apply_outcome(
    contact: CampaignContact, campaign: Campaign, outcome: str | None, now: datetime
) -> None:
    """What a call's outcome means for its contact. Nobody reached: try again later, until the
    attempts run out. Asked not to be called: never again. Anything else: done."""
    contact.outcome = outcome
    if outcome == OPT_OUT_OUTCOME:
        contact.status = OPTED_OUT
    elif outcome in NOBODY_REACHED_OUTCOMES:
        if contact.attempts < campaign.max_attempts:
            contact.status = RETRY
            contact.next_attempt_at = now + timedelta(minutes=campaign.retry_after_minutes)
        else:
            contact.status = FAILED
    else:
        contact.status = DONE


async def record_call_outcome(
    session: AsyncSession, contact_id: str, room: str, outcome: str | None, now: datetime
) -> None:
    """Called when the runtime ends a campaign call; the caller commits. A call that reports
    back after the dialler gave up on it (and maybe dialled again) changes nothing."""
    contact = await session.get(CampaignContact, contact_id)
    if contact is None or contact.status != CALLING or contact.last_room != room:
        return
    apply_outcome(contact, await get_campaign(session, contact.campaign_id), outcome, now)
