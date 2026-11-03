from fastapi import APIRouter, HTTPException, status

from studio_backend.core.database import SessionDep
from studio_backend.core.jobs import JobQueueDep
from studio_backend.integrations.deliveries import service
from studio_backend.integrations.deliveries.constants import DELIVER_JOB
from studio_backend.integrations.deliveries.schemas import DeliveryRead

router = APIRouter(prefix="/calls/{call_id}/deliveries", tags=["after call"])


@router.get("")
async def list_deliveries(call_id: str, session: SessionDep) -> list[DeliveryRead]:
    return [DeliveryRead.model_validate(d) for d in await service.list_deliveries(session, call_id)]


@router.post("/{delivery_id}/retry")
async def retry_delivery(
    call_id: str, delivery_id: str, session: SessionDep, jobs: JobQueueDep
) -> DeliveryRead:
    try:
        delivery = await service.reset_delivery(session, call_id, delivery_id)
    except service.DeliveryNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"delivery {delivery_id} not found"
        ) from error
    await jobs.enqueue(DELIVER_JOB, delivery.id)
    return DeliveryRead.model_validate(delivery)
