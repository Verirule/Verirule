from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext

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
    result = run_ingestion(settings)
    return {"status": "ok", "result": result}
