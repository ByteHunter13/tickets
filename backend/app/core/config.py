from typing_extensions import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Clase que obtiene las configuraciones globales del proyecto
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str = Field(min_length=32) # Validador de la secret key para que no quede una cadena corta o predecible, para JWT
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:3000"]
    allow_credentials: bool = True
    uploads_dir: str = "uploads"
    max_upload_mb: int = 5
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "tickets@empresa.local"

    @model_validator(mode="after")
    def check_cors_wildcard_with_credentials(self) -> Self:
        if self.allow_credentials and "*" in self.cors_origins:
            raise ValueError(
                "cors_origins no puede contener '*' cuando allow_credentials es True"
            )
        return self

settings = Settings()
