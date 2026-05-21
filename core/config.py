from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    supabase_postgres_url: str = Field(..., description="PostgreSQL (Supabase) async URI")
    mongo_url: str = Field("mongodb://localhost:27017", description="MongoDB URI")
    mongo_db_name: str = Field("polyglot_catalog", description="MongoDB database name")
    redis_url: str = Field("redis://localhost:6379/0", description="Redis URI")

    app_env: str = Field("development")
    app_host: str = Field("0.0.0.0")
    app_port: int = Field(8000)


settings = Settings()
