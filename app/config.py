from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Keys
    openai_api_key: str

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # API Configuration
    api_base_url: str = "http://localhost:8000"

    # LLM Configuration
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.3
    max_tokens: int = 1000

    # Application Settings
    app_name: str = "AI Mortgage Advisor"
    app_version: str = "0.1.0"

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # Feature Flags
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 60
    rate_limit_by_ip: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create a global settings instance
settings = Settings()
