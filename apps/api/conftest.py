import sys
from pathlib import Path

# Ensure "apps/api" is on sys.path so imports like "from app.main import app" work in CI.
API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
