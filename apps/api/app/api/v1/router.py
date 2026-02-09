from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, orgs, sources

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(orgs.router)
router.include_router(sources.router)
