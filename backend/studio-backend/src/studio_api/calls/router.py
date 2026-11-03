from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, status

from studio_api.after_call.constants import CALL_ANALYSED, CALL_ENDED, DELIVER_JOB
from studio_api.after_call.service import schedule_deliveries
from studio_api.agents.service import AgentNotFoundError
from studio_api.calls import service
from studio_api.calls.constants import ANALYSIS_PENDING, ENDED_STATUS
from studio_api.calls.models import Call
from studio_api.calls.schemas import CallEnd, CallRead, CallStart, Metrics
from studio_api.config import Settings, SettingsDep
from studio_api.database import SessionDep
from studio_api.jobs import JobQueueDep
from studio_api.security import RuntimeAuthDep

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
DEFAULT_METRICS_DAYS = 14
MAX_METRICS_DAYS = 90
ANALYSE_CALL_JOB = "analyse_call_job"

router = APIRouter(tags=["calls"])
runtime_router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[RuntimeAuthDep])


def call_not_found(call_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"call {call_id} not found")


def read(call: Call, request: Request, settings: Settings) -> CallRead:
    """The call, with links to its Langfuse session (one per call, named after the room) and to
    LiveKit Cloud's recording of the room session, when those are configured."""
    result = CallRead.model_validate(call)
    project_id = settings.langfuse_project_id or getattr(
        request.app.state, "langfuse_project_id", None
    )
    if project_id:
        base = settings.langfuse_base_url.rstrip("/")
        result.langfuse_url = f"{base}/project/{project_id}/sessions/{quote(call.room_name)}"
    if settings.livekit_session_url_template and call.room_sid:
        result.recording_url = settings.livekit_session_url_template.format(
            room_sid=call.room_sid, room=call.room_name
        )
    return result


@router.get("/calls")
async def list_calls(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    agent_id: str | None = None,
    channel: str | None = None,
    direction: str | None = None,
    outcome: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> list[CallRead]:
    calls = await service.list_calls(session, limit, agent_id, channel, direction, outcome)
    return [read(call, request, settings) for call in calls]


@router.get("/calls/{call_id}")
async def read_call(
    call_id: str, request: Request, session: SessionDep, settings: SettingsDep
) -> CallRead:
    try:
        return read(await service.get_call(session, call_id), request, settings)
    except service.CallNotFoundError as error:
        raise call_not_found(call_id) from error


@router.get("/metrics")
async def read_metrics(
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=MAX_METRICS_DAYS)] = DEFAULT_METRICS_DAYS,
) -> Metrics:
    return await service.metrics(session, days)


@runtime_router.post("/calls", status_code=status.HTTP_201_CREATED)
async def start_call(
    body: CallStart, request: Request, session: SessionDep, settings: SettingsDep
) -> CallRead:
    try:
        return read(await service.start_call(session, body), request, settings)
    except AgentNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"agent {body.agent_id} not found"
        ) from error


@runtime_router.post("/calls/{call_id}/end")
async def end_call(
    call_id: str,
    body: CallEnd,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    jobs: JobQueueDep,
) -> CallRead:
    try:
        first_end = (await service.get_call(session, call_id)).status != ENDED_STATUS
        call = await service.end_call(session, call_id, body, settings)
    except service.CallNotFoundError as error:
        raise call_not_found(call_id) from error
    if call.analysis_status == ANALYSIS_PENDING:
        await jobs.enqueue(ANALYSE_CALL_JOB, call.id)
    if first_end:
        # A call with nothing to analyse is final now: its "analysed" actions go too.
        events = [CALL_ENDED] + (
            [] if call.analysis_status == ANALYSIS_PENDING else [CALL_ANALYSED]
        )
        for event in events:
            for delivery_id in await schedule_deliveries(session, call, event):
                await jobs.enqueue(DELIVER_JOB, delivery_id)
    return read(call, request, settings)
