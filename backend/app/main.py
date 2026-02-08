from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext

from .billing.limits import (
    enforce_business_limit,
    enforce_ingestion_limit,
    get_service_client,
    get_subscription,
)
from .config import Settings, get_settings
from .ingestion.pipeline import run_ingestion
from .jwt import require_admin, validate_jwt
from .schemas import AuthPayload
from .supabase_client import get_supabase_client, get_supabase_service_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Verirule API")


def configure_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.on_event("startup")
def _configure_security():
    settings = get_settings()
    configure_cors(app, settings)


@app.get("/health")
def health_check(settings: Settings = Depends(get_settings)):
    return {"status": "ok"}


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@app.post("/register")
def register(payload: AuthPayload, settings: Settings = Depends(get_settings)):
    supabase = get_supabase_client(settings)

    _ = get_password_hash(payload.password)

    response = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
    if response.user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed")

    return {"status": "ok", "message": "Confirmation email sent"}


@app.post("/login")
def login(payload: AuthPayload, settings: Settings = Depends(get_settings)):
    supabase = get_supabase_client(settings)

    response = supabase.auth.sign_in_with_password(
        {"email": payload.email, "password": payload.password}
    )
    if response.session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {"access_token": response.session.access_token, "token_type": "bearer"}


@app.post("/logout")
def logout(settings: Settings = Depends(get_settings)):
    supabase = get_supabase_client(settings)
    supabase.auth.sign_out()
    return {"status": "ok"}


@app.get("/subscription")
def get_subscription_endpoint(
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    subscription = get_subscription(client, user_id)
    if not subscription:
        return {"plan": "free", "status": "active", "started_at": None}
    return subscription


@app.post("/subscription/upgrade")
def upgrade_subscription(
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    existing = get_subscription(client, user_id)
    payload = {
        "user_id": user_id,
        "plan": "pro",
        "status": "active",
    }
    if existing:
        result = client.table("subscriptions").update(payload).eq("id", existing["id"]).execute()
    else:
        result = client.table("subscriptions").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upgrade failed")
    return result.data[0]


@app.get("/business/profile")
def get_business_profile(
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    result = (
        client.table("business_profiles")
        .select("id, business_name, industry, jurisdiction")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return {"data": result.data[0] if result.data else None}


@app.post("/business/profile")
def upsert_business_profile(
    payload: dict,
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    existing = (
        client.table("business_profiles")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not existing.data:
        try:
            enforce_business_limit(client, user_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        result = (
            client.table("business_profiles")
            .insert(
                {
                    "user_id": user_id,
                    "business_name": payload.get("business_name"),
                    "industry": payload.get("industry"),
                    "jurisdiction": payload.get("jurisdiction"),
                }
            )
            .execute()
        )
    else:
        result = (
            client.table("business_profiles")
            .update(
                {
                    "business_name": payload.get("business_name"),
                    "industry": payload.get("industry"),
                    "jurisdiction": payload.get("jurisdiction"),
                }
            )
            .eq("id", existing.data[0]["id"])
            .execute()
        )

    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Save failed")
    return {"data": result.data[0]}


@app.get("/compliance/status")
def get_compliance_status(
    business_id: str,
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    owner = (
        client.table("business_profiles")
        .select("id")
        .eq("id", business_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not owner.data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    statuses = (
        client.table("business_compliance_status")
        .select("id, regulation_id, status, last_checked_at")
        .eq("business_id", business_id)
        .execute()
        .data
    )
    regulation_ids = [s["regulation_id"] for s in statuses]
    titles_map = {}
    if regulation_ids:
        regs = (
            client.table("regulations")
            .select("id, title")
            .in_("id", regulation_ids)
            .execute()
            .data
        )
        titles_map = {r["id"]: r.get("title", "Regulation") for r in regs}

    data = [
        {
            "id": s["id"],
            "regulation_title": titles_map.get(s["regulation_id"], "Regulation"),
            "status": s.get("status"),
            "last_checked_at": s.get("last_checked_at"),
        }
        for s in statuses
    ]
    return {"data": data}


@app.get("/violations")
def list_violations(
    business_id: str,
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    owner = (
        client.table("business_profiles")
        .select("id")
        .eq("id", business_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not owner.data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = (
        client.table("violations")
        .select("id, message, severity, detected_at")
        .eq("business_id", business_id)
        .order("detected_at", desc=True)
        .execute()
    )
    return {"data": result.data}


@app.get("/regulations")
def list_regulations(
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    industry: str | None = None,
    jurisdiction: str | None = None,
):
    client = get_supabase_service_client(settings)
    query = client.table("regulations").select(
        "id, title, summary, source, source_url, jurisdiction, industry, published_at, last_updated_at, created_at"
    )
    if industry:
        query = query.eq("industry", industry)
    if jurisdiction:
        query = query.eq("jurisdiction", jurisdiction)
    result = query.order("last_updated_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"data": result.data}


@app.get("/regulations/{regulation_id}")
def get_regulation(
    regulation_id: str,
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
    include_raw_text: bool = False,
):
    client = get_supabase_service_client(settings)
    fields = (
        "*"
        if include_raw_text
        else "id, title, summary, source, source_url, jurisdiction, industry, published_at, last_updated_at, created_at"
    )
    result = client.table("regulations").select(fields).eq("id", regulation_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return result.data[0]


@app.post("/ingest/run")
def run_ingest(
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(require_admin),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    try:
        enforce_ingestion_limit(client, user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    result = run_ingestion(settings)
    return {"status": "ok", "result": result}


@app.get("/alerts")
def list_alerts(
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    result = (
        client.table("alerts")
        .select("id, business_id, violation_id, severity, title, message, acknowledged, created_at")
        .eq("user_id", user_id)
        .order("acknowledged", desc=False)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {"data": result.data}


@app.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    settings: Settings = Depends(get_settings),
    claims: dict = Depends(validate_jwt),
):
    client = get_service_client(settings)
    user_id = claims.get("user_id")
    existing = (
        client.table("alerts")
        .select("id")
        .eq("id", alert_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    result = (
        client.table("alerts")
        .update({"acknowledged": True})
        .eq("id", alert_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Acknowledge failed")
    return result.data[0]
