import os
from dotenv import load_dotenv

load_dotenv()  # Carga .env si existe (útil fuera de Docker)

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "sqlite:///fallback.db"  # valor por defecto por si no hay conexión real
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REE_API_TOKEN = os.getenv("REE_API_TOKEN", "")
    JWT_SECRET = os.getenv("JWT_SECRET", "default_key")
