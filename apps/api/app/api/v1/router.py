from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    billing,
    health,
    integrations,
    monitoring,
    orgs,
    sources,
    templates,
    task_files,
    tasks,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(billing.router)
router.include_router(orgs.router)
router.include_router(sources.router)
router.include_router(templates.router)
router.include_router(monitoring.router)
router.include_router(tasks.router)
router.include_router(task_files.router)
router.include_router(integrations.router)
