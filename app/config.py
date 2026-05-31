import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    # Dacă python-dotenv nu este instalat, folosește doar variabilele de mediu existente.
    pass

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-env")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

HF_HOME = Path(os.getenv("HF_HOME", str(BASE_DIR / "hf_cache"))).resolve()
MODEL_ID = os.getenv("MODEL_ID", "vikhyatk/moondream2")

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", PROJECT_ROOT / "simulated_storage")).resolve()
DATABASE_FILENAME = os.getenv("DATABASE_FILENAME", "nas_database.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / DATABASE_FILENAME}")

CORS_ALLOW_ORIGIN_REGEX = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX", 
    r"http://(localhost|127\.0\.0\.1|100\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):(5173|4173)"
)

STORAGE_PATH.mkdir(parents=True, exist_ok=True)
HF_HOME.mkdir(parents=True, exist_ok=True)
