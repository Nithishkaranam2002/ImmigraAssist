from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ─── App ───────────────────────────────────────────
    APP_NAME: str = "ImmigraAssist"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str

    # ─── PostgreSQL ────────────────────────────────────
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    @property
    def POSTGRES_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ─── Milvus ────────────────────────────────────────
    MILVUS_HOST: str
    MILVUS_PORT: int = 19530
    MILVUS_LAWS_COLLECTION: str = "laws"
    MILVUS_CASES_COLLECTION: str = "cases"

    # ─── Redis ─────────────────────────────────────────
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ─── OpenAI ────────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 1500
    OPENAI_TEMPERATURE: float = 0.2

    # ─── Embeddings ────────────────────────────────────
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # ─── Retrieval ─────────────────────────────────────
    TOP_K_LAWS: int = 5
    TOP_K_CASES: int = 7
    RERANKER_TOP_N: int = 5
    MILVUS_SEARCH_EF: int = 64
    COURTLISTENER_TIMEOUT: int = 8
    COURTLISTENER_MAX_RESULTS: int = 3
    USE_GLINER_PII: bool = False
    ENABLE_SECTION_RESOLVE: bool = True

    # ─── Super Admin Seed ──────────────────────────────
    ADMIN_NAME: str = "Super Admin"
    ADMIN_EMAIL: str = "admin@immigraassist.com"
    ADMIN_PASSWORD: str = "changeme123"
    ADMIN_DESIGNATION: str = "Super Administrator"

    # ─── JWT Auth ──────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # ─── Integration API (optional webhook key) ────────
    INTEGRATION_API_KEY: Optional[str] = None

    # ─── GLiNER PII ────────────────────────────────────
    GLINER_MODEL: str = "urchade/gliner_multi_pii-v1"

    # ─── LlamaGuard ────────────────────────────────────
    LLAMAGUARD_MODEL: str = "meta-llama/LlamaGuard-7b"

    # ─── File Upload ───────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"

    # ─── LangSmith ────────────────────────────────────
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_PROJECT: str = "immigraassist"

    # ─── CourtListener ─────────────────────────────────
    COURTLISTENER_API_TOKEN: str = ""

    # ─── CORS & Security ───────────────────────────────
    CORS_ORIGINS: str = "*"
    RATE_LIMIT_ENABLED: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()