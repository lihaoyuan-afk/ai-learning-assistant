from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "AgentLearn API"
    app_env: str = "development"
    upload_dir: Path = REPO_ROOT / "uploads"
    max_upload_size_mb: int = 50

    # Chat LLM — set OPENAI_BASE_URL + OPENAI_API_KEY to use DeepSeek or Ollama
    openai_api_key: str = "ollama"
    openai_base_url: str | None = None
    openai_chat_model: str = "deepseek-r1:1.5b"

    # Ollama-specific: context window in tokens (passed via extra_body options)
    ollama_num_ctx: int = 8192
    # LLM request timeout in seconds
    llm_timeout: int = 180

    # Embeddings — can point to a different provider (e.g. Jina AI in production)
    # If unset, falls back to openai_api_key / openai_base_url
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    openai_embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    # Database — SQLite for local dev, postgresql+psycopg:// for Neon/Supabase
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'agentlearn.db'}"

    # Qdrant — :memory: for tests, :local: for dev file storage, https://... for cloud
    qdrant_url: str = ":local:"
    qdrant_storage_path: str = str(REPO_ROOT / "qdrant_storage")
    qdrant_collection: str = "learning_chunks"
    qdrant_api_key: str | None = None

    # Demo auth — if set, all API routes require Authorization: Bearer <password>
    demo_password: str | None = None

    # JWT auth
    jwt_secret: str = "dev-secret-please-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    # CORS — comma-separated origins accepted in env var
    cors_origins: list[str] = ["http://localhost:3000", "http://10.140.178.184:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
