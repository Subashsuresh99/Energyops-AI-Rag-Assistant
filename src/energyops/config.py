"""Configuration from environment variables."""
import os
from pathlib import Path

def db_path() -> Path:
    return Path(os.getenv("ENERGYOPS_DB_PATH", "data/energyops.sqlite3"))

def use_ollama() -> bool:
    return os.getenv("ENERGYOPS_USE_OLLAMA", "false").lower() in ("true", "1", "yes")
