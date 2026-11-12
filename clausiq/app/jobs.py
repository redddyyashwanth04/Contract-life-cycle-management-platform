"""In-memory background-job registry with stage/progress polling."""
import asyncio
import secrets
from typing import Awaitable, Callable

JOBS: dict[str, dict] = {}


def create_job() -> str:
    job_id = secrets.token_hex(8)
    JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "stage": "Queued",
        "stage_index": 0,
        "stages": [],
        "progress": 0.0,
        "result": None,
        "error": None,
    }
    return job_id


def set_stage(job_id: str, stage: str, index: int, total: int) -> None:
    job = JOBS.get(job_id)
    if job:
        job["stage"] = stage
        job["stage_index"] = index
        job["stages"] = job["stages"] or [stage]
        if stage not in job["stages"]:
            job["stages"].append(stage)
        job["progress"] = round((index + 1) / max(total, 1), 3)


def spawn(job_id: str, factory: Callable[[], Awaitable[None]]) -> None:
    async def _run() -> None:
        job = JOBS[job_id]
        try:
            job["status"] = "running"
            await factory()
            job["status"] = "complete"
            job["progress"] = 1.0
        except Exception as exc:  # noqa: BLE001
            job["status"] = "failed"
            job["error"] = str(exc)

    asyncio.create_task(_run())
