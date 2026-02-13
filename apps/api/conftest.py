import os
import sys
from pathlib import Path

# Default env for app settings in tests.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("API_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("VERIRULE_SECRETS_KEY", "test-secrets-key-for-encryption")
os.environ.setdefault("INTEGRATIONS_ENCRYPTION_KEY", "VkObE4xoqlrYO7a5aH8VUZj1VOVjo5ZcPDKKAmaGrWY=")

# Ensure "apps/api" is on sys.path so imports like "from app.main import app" work in CI.
API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
