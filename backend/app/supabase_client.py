from supabase import Client, create_client

from .config import Settings


def get_supabase_client(settings: Settings) -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_API_KEY)
