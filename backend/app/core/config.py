from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    llm_provider: str = Field("openai", description="claude | openai")
    openai_api_key: str = Field("", description="OpenAI / 兼容代理 Key")
    openai_base_url: str = Field("https://api.openai.com/v1")
    openai_model: str = Field("gpt-4o")
    anthropic_api_key: str = Field("")
    anthropic_base_url: str = Field("https://api.anthropic.com")
    anthropic_model: str = Field("claude-sonnet-4-6")

    # --- Embedding ---
    embedding_provider: str = Field("openai", description="openai | voyage | local")
    openai_embedding_api_key: str = Field("", description="留空则复用 openai_api_key")
    openai_embedding_base_url: str = Field("", description="留空则复用 openai_base_url")
    openai_embedding_model: str = Field("text-embedding-3-small")
    voyage_api_key: str = Field("")
    voyage_embedding_model: str = Field("voyage-3")
    local_embedding_model: str = Field("paraphrase-multilingual-MiniLM-L12-v2")

    # --- Token 成本（美元/百万 token）---
    input_price_per_m: float = Field(2.5)
    output_price_per_m: float = Field(10.0)

    # --- 数据库 ---
    database_url: str = Field("sqlite:///./data/xiaosu.db")
    chroma_persist_path: str = Field("./data/chroma")

    # --- Redis ---
    redis_url: str = Field("redis://localhost:6379/0")
    redis_session_ttl: int = Field(86400, description="会话保留秒数")

    # --- IM 钉钉 ---
    dingtalk_app_key: str = Field("")
    dingtalk_app_secret: str = Field("")
    dingtalk_robot_code: str = Field("")

    # --- IM 飞书（加分项）---
    feishu_app_id: str = Field("")
    feishu_app_secret: str = Field("")
    feishu_verification_token: str = Field("")
    feishu_encrypt_key: str = Field("")

    # --- Mock API ---
    mock_api_base_url: str = Field("http://localhost:8001")
    mock_api_timeout: int = Field(10)

    # --- Langfuse ---
    langfuse_enabled: bool = Field(False)
    langfuse_secret_key: str = Field("")
    langfuse_public_key: str = Field("")
    langfuse_host: str = Field("https://cloud.langfuse.com")

    # --- 应用 ---
    log_level: str = Field("INFO")
    log_dir: str = Field("./logs")
    cors_origins: str = Field("http://localhost:3000")

    # --- 重试策略 ---
    llm_retry_max_attempts: int = Field(3)
    llm_retry_min_wait: int = Field(2)
    llm_retry_max_wait: int = Field(30)

    @property
    def effective_embedding_api_key(self) -> str:
        return self.openai_embedding_api_key or self.openai_api_key

    @property
    def effective_embedding_base_url(self) -> str:
        return self.openai_embedding_base_url or self.openai_base_url

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
