from .rss_source import RssRegulationSource
from .service import upsert_regulations
from ..config import Settings
from ..supabase_client import get_supabase_service_client


def run_ingestion_job(settings: Settings) -> dict:
    source = RssRegulationSource(settings.INGESTION_FEED_URL, "rss")
    client = get_supabase_service_client(settings)
    result = upsert_regulations(client, source.fetch())
    return result
