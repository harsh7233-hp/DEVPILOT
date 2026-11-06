import warnings

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/auth/github/callback"

    session_secret: str = "change-me-in-production"

    frontend_url: str = "http://localhost:3000"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str = ""
    embedding_api_key: str = ""


settings = Settings()

if settings.session_secret == "change-me-in-production":
    warnings.warn(
        "SESSION_SECRET is using the default value. "
        "Set a secure random secret in production: "
        "python -c \"import secrets; print(secrets.token_hex(32))\"",
        stacklevel=2,
    )
