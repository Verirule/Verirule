from supabase import Client, create_client

from .config import Settings


def get_supabase_client(settings: Settings) -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_API_KEY)


def get_supabase_service_client(settings: Settings) -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
