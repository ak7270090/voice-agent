"""Secrets are encrypted with the API's `secrets_key` (Fernet). Values leave the API only for the
runtime (the secrets an agent's flow names, at call start) and for after-call actions."""

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_api.config import Settings
from studio_api.secrets.constants import HIDDEN_PREVIEW, PREVIEW_EDGE_CHARS, PREVIEW_MIN_LENGTH
from studio_api.secrets.models import Secret


class SecretNotFoundError(LookupError):
    pass


class SecretsKeyMissingError(RuntimeError):
    """`SECRETS_KEY` is not set, so nothing can be encrypted or read back."""


def preview(value: str) -> str:
    if len(value) < PREVIEW_MIN_LENGTH:
        return HIDDEN_PREVIEW
    return f"{value[:PREVIEW_EDGE_CHARS]}…{value[-PREVIEW_EDGE_CHARS:]}"


def cipher(settings: Settings) -> Fernet:
    if not settings.secrets_key:
        raise SecretsKeyMissingError
    return Fernet(settings.secrets_key)


async def list_secrets(session: AsyncSession) -> list[Secret]:
    return list(await session.scalars(select(Secret).order_by(Secret.name)))


async def secret_names(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(Secret.name)))


async def save_secret(session: AsyncSession, settings: Settings, name: str, value: str) -> Secret:
    """Creates the secret, or replaces its value: a key is rotated under the same name, so the
    tools that use it need no change."""
    encrypted = cipher(settings).encrypt(value.encode()).decode()
    secret = await session.scalar(select(Secret).where(Secret.name == name))
    if secret is None:
        secret = Secret(name=name)
        session.add(secret)
    secret.encrypted_value = encrypted
    secret.preview = preview(value)
    await session.commit()
    await session.refresh(secret)
    return secret


async def delete_secret(session: AsyncSession, name: str) -> None:
    secret = await session.scalar(select(Secret).where(Secret.name == name))
    if secret is None:
        raise SecretNotFoundError(name)
    await session.delete(secret)
    await session.commit()


async def secret_values(
    session: AsyncSession, settings: Settings, names: set[str]
) -> dict[str, str]:
    """The values of the named secrets that exist; a missing one is left out (the tool that
    needs it then fails with a clear error instead of sending an empty key)."""
    if not names:
        return {}
    rows = await session.scalars(select(Secret).where(Secret.name.in_(names)))
    fernet = cipher(settings)
    values = {}
    for secret in rows:
        try:
            values[secret.name] = fernet.decrypt(secret.encrypted_value.encode()).decode()
        except InvalidToken:
            # Encrypted under another key (SECRETS_KEY changed): treated as missing.
            continue
    return values
