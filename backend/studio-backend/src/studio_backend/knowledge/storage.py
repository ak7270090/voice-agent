"""Object storage (S3 API): uploaded documents now, call recordings later.

Locally this is RustFS; in the cloud any S3-compatible store, changed by settings only.
boto3 is synchronous, so each call runs in a thread.
"""

import asyncio
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, Request

from studio_backend.core.config import Settings


class FileStore:
    def __init__(self, client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def ensure_bucket(self) -> None:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
        except ClientError:
            await asyncio.to_thread(self._client.create_bucket, Bucket=self._bucket)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)


def get_file_store(request: Request) -> FileStore:
    return request.app.state.file_store


FileStoreDep = Annotated[FileStore, Depends(get_file_store)]


def create_file_store(settings: Settings) -> FileStore:
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    return FileStore(client, settings.s3_bucket)
