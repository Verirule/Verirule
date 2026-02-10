from __future__ import annotations

import asyncio
import os

import uvicorn

from app.core.settings import get_settings
from app.worker.run_processor import run_worker_loop


def main() -> None:
    settings = get_settings()
    mode = settings.VERIRULE_MODE.strip().lower()

    if mode == "worker":
        asyncio.run(run_worker_loop())
        return

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", str(settings.API_PORT)))
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
