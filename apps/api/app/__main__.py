from __future__ import annotations

import asyncio
import os

import uvicorn

from app.core.settings import get_settings
from app.worker.export_processor import run_export_worker_loop
from app.worker.run_processor import run_worker_loop


async def run_all_workers() -> None:
    await asyncio.gather(run_worker_loop(), run_export_worker_loop())


def main() -> None:
    settings = get_settings()
    mode = settings.VERIRULE_MODE.strip().lower()

    if mode == "worker":
        asyncio.run(run_all_workers())
        return

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", str(settings.API_PORT)))
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
