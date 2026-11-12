import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "ClausIQ"
APP_TAGLINE = "Governed Agentic Contract Intelligence"

DATA_DIR = Path(os.getenv("CLAUSIQ_DATA_DIR", str(BASE_DIR / "data")))
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR

DB_PATH = DATA_DIR / "clausiq.db"
SAMPLE_CONTRACTS_DIR = BASE_DIR / "data" / "sample_contracts"
PLAYBOOKS_DIR = BASE_DIR / "app" / "playbooks"
STATIC_DIR = BASE_DIR / "static"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
MAX_NEGOTIATION_ROUNDS = int(os.getenv("MAX_NEGOTIATION_ROUNDS", "6"))
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(8 * 3600)))
SEED_DEMO = os.getenv("SEED_DEMO", "1") == "1"

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
