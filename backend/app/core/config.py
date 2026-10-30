from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "DepoSafe"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "deposafe-super-secret-key-sih-2024-grand-finale-aicte-secure")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./deposafe.db")
    
    # Upload storage
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
    
    # Bank verification
    ENABLE_BANK_SIMULATOR: bool = True
    SIMULATION_DISCLAIMER: str = "SIMULATED, not a real bank verification"
    
    class Config:
        case_sensitive = True

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

