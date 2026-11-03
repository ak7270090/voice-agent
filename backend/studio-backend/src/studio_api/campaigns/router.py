from fastapi import APIRouter, HTTPException, UploadFile, status

from studio_api.agents.service import AgentNotFoundError
from studio_api.campaigns import service
from studio_api.campaigns.constants import PAUSED, RUNNING
from studio_api.campaigns.schemas import (
    CampaignCreate,
    CampaignRead,
    ContactCreate,
    ContactImport,
    ContactRead,
)
from studio_api.database import SessionDep
from studio_api.numbers.service import CannotCallOutError, PhoneNumberNotFoundError

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def campaign_not_found(campaign_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"campaign {campaign_id} not found")


@router.get("")
async def list_campaigns(session: SessionDep) -> list[CampaignRead]:
    return await service.list_campaigns(session)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(body: CampaignCreate, session: SessionDep) -> CampaignRead:
    try:
        campaign = await service.create_campaign(session, body)
    except AgentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"agent {error} not found") from error
    except PhoneNumberNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"phone number {error} not found") from error
    except CannotCallOutError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{error} has no outbound trunk, so it cannot call out"
        ) from error
    return await service.read_campaign(session, campaign.id)


@router.get("/{campaign_id}")
async def read_campaign(campaign_id: str, session: SessionDep) -> CampaignRead:
    try:
        return await service.read_campaign(session, campaign_id)
    except service.CampaignNotFoundError as error:
        raise campaign_not_found(campaign_id) from error


async def move(session: SessionDep, campaign_id: str, to: str) -> CampaignRead:
    try:
        return await service.move(session, campaign_id, to)
    except service.CampaignNotFoundError as error:
        raise campaign_not_found(campaign_id) from error
    except service.CampaignStateError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: str, session: SessionDep) -> CampaignRead:
    return await move(session, campaign_id, RUNNING)


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, session: SessionDep) -> CampaignRead:
    return await move(session, campaign_id, PAUSED)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: str, session: SessionDep) -> None:
    try:
        await service.delete_campaign(session, campaign_id)
    except service.CampaignNotFoundError as error:
        raise campaign_not_found(campaign_id) from error


@router.get("/{campaign_id}/contacts")
async def list_contacts(campaign_id: str, session: SessionDep) -> list[ContactRead]:
    try:
        contacts = await service.list_contacts(session, campaign_id)
    except service.CampaignNotFoundError as error:
        raise campaign_not_found(campaign_id) from error
    return [ContactRead.model_validate(contact) for contact in contacts]


async def add(
    session: SessionDep, campaign_id: str, contacts: list[ContactCreate], rejected=None
) -> ContactImport:
    try:
        return await service.add_contacts(session, campaign_id, contacts, rejected)
    except service.CampaignNotFoundError as error:
        raise campaign_not_found(campaign_id) from error
    except service.CampaignStateError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.post("/{campaign_id}/contacts", status_code=status.HTTP_201_CREATED)
async def add_contacts(
    campaign_id: str, body: list[ContactCreate], session: SessionDep
) -> ContactImport:
    return await add(session, campaign_id, body)


@router.post("/{campaign_id}/contacts/csv", status_code=status.HTTP_201_CREATED)
async def import_contacts(campaign_id: str, file: UploadFile, session: SessionDep) -> ContactImport:
    """Rows that fail (a phone not in +E.164 form) are listed back; the rest are added."""
    try:
        text = (await file.read()).decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "the CSV is not UTF-8") from error
    contacts, rejected = service.parse_contacts_csv(text)
    return await add(session, campaign_id, contacts, rejected)
