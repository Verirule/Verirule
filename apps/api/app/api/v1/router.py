from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    automation,
    billing,
    controls,
    evidence_files,
    exports,
    health,
    integrations,
    members,
    monitoring,
    notifications,
    notifications_inbox,
    orgs,
    readiness,
    sla,
    sources,
    system,
    task_files,
    tasks,
)
from app.routers import templates as templates_router

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(billing.router)
router.include_router(automation.router)
router.include_router(orgs.router)
router.include_router(sources.router)
router.include_router(templates_router.router)
router.include_router(controls.router)
router.include_router(monitoring.router)
router.include_router(tasks.router)
router.include_router(task_files.router)
router.include_router(evidence_files.router)
router.include_router(readiness.router)
router.include_router(sla.router)
router.include_router(integrations.router)
router.include_router(members.router)
router.include_router(notifications.router)
router.include_router(notifications_inbox.router)
router.include_router(exports.router)
router.include_router(system.router)
