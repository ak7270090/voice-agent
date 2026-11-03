"""Background jobs on Redis (arq). The API enqueues; `studio_api.worker` runs them."""

from typing import Annotated

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import Depends, Request

from studio_api.config import Settings


class JobQueue:
    def __init__(self, redis: ArqRedis) -> None:
        self._redis = redis

    async def enqueue(self, job_name: str, *args: object) -> None:
        await self._redis.enqueue_job(job_name, *args)

    async def aclose(self) -> None:
        await self._redis.aclose()


def build_redis_settings(settings: Settings) -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def create_job_queue(settings: Settings) -> JobQueue:
    return JobQueue(await create_pool(build_redis_settings(settings)))


def get_job_queue(request: Request) -> JobQueue:
    return request.app.state.job_queue


JobQueueDep = Annotated[JobQueue, Depends(get_job_queue)]
