from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from studio_backend.config import SettingsDep
from studio_backend.credentials import service
from studio_backend.credentials.constants import SECRET_NAME_MAX_LENGTH, SECRET_NAME_PATTERN
from studio_backend.credentials.schemas import SecretRead, SecretWrite
from studio_backend.database import SessionDep

router = APIRouter(prefix="/secrets", tags=["secrets"])

SecretName = Annotated[str, Path(pattern=SECRET_NAME_PATTERN, max_length=SECRET_NAME_MAX_LENGTH)]


@router.get("")
async def list_secrets(session: SessionDep) -> list[SecretRead]:
    return [SecretRead.model_validate(secret) for secret in await service.list_secrets(session)]


@router.put("/{name}")
async def save_secret(
    name: SecretName, body: SecretWrite, session: SessionDep, settings: SettingsDep
) -> SecretRead:
    try:
        secret = await service.save_secret(session, settings, name, body.value)
    except service.SecretsKeyMissingError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "SECRETS_KEY is not set on the API"
        ) from error
    return SecretRead.model_validate(secret)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(name: SecretName, session: SessionDep) -> None:
    try:
        await service.delete_secret(session, name)
    except service.SecretNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"secret {name} not found") from error
