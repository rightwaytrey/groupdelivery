from pydantic_settings import BaseSettings
from pathlib import Path
import os
import secrets


# Get the project root directory (parent of backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Application settings and configuration"""

    # App info
    app_name: str = "Group Delivery Optimizer"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR}/delivery.db"

    # OSRM
    osrm_base_url: str = "http://router.project-osrm.org"

    # Geocoding (Nominatim)
    geocoding_user_agent: str = "groupdelivery-app/1.0"
    geocoding_rate_limit: float = 1.0  # Requests per second

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:9967",
        "https://tre.hopto.org",
        "https://tre.hopto.org:9966",
        "https://tre.hopto.org:9967",
        "http://morefood.duckdns.org",
        "https://morefood.duckdns.org",
    ]

    # Default Depot Location
    default_depot_address: str = "96 E Wheelock Pkwy, St Paul, MN 55117"
    default_depot_latitude: float = 44.9904552
    default_depot_longitude: float = -93.0978862

    # Security / Authentication
    secret_key: str = secrets.token_urlsafe(32)  # Generate a random secret key
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
