"""Configuration for subtribe-ai package.

This module provides configuration management that allows the calling
application (e.g., subtribe-backend) to inject configuration values.
The package does NOT load from environment variables directly.
"""

from pydantic import BaseModel


class Settings(BaseModel):
    """AI service configuration.

    Configuration is injected by the calling application, not loaded
    from environment variables. The calling application is responsible
    for loading and providing these values.

    Example usage from backend:
        from subtribe_ai import configure
        configure(
            google_api_key="your-key",
            default_model="gemini-2.0-flash",
        )
    """

    # LLM API Keys
    google_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Default LLM settings
    default_model: str = "gemini-2.0-flash"
    default_temperature: float = 0.0
    default_max_tokens: int = 5000

    # Langfuse tracing (optional)
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Processing settings
    pdf_link_padding: float = 2.5
    max_resume_pages: int = 10


# Global settings instance - must be configured before use
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the current settings instance.

    Raises:
        RuntimeError: If configure() has not been called.
    """
    if _settings is None:
        raise RuntimeError(
            "subtribe-ai has not been configured. "
            "Call subtribe_ai.configure() before using the package."
        )
    return _settings


def configure(**kwargs) -> Settings:
    """Configure the subtribe-ai package.

    Must be called before using any subtribe-ai functionality.
    This is typically done during application startup.

    Also sets environment variables for BAML to pick up API keys.

    Args:
        **kwargs: Configuration values matching Settings fields.

    Returns:
        The configured Settings instance.

    Example:
        from subtribe_ai import configure

        configure(
            google_api_key="your-google-api-key",
            openai_api_key="your-openai-api-key",
            default_model="gemini-2.0-flash",
            langfuse_enabled=True,
            langfuse_public_key="pk-xxx",
            langfuse_secret_key="sk-xxx",
        )
    """
    import os

    global _settings
    _settings = Settings(**kwargs)

    # Set environment variables for BAML to read
    # BAML clients read API keys from env.SUBTRIBE_AI_* variables
    if _settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = _settings.google_api_key
    if _settings.openai_api_key:
        os.environ["SUBTRIBE_AI_OPENAI_API_KEY"] = _settings.openai_api_key
    if _settings.anthropic_api_key:
        os.environ["SUBTRIBE_AI_ANTHROPIC_API_KEY"] = _settings.anthropic_api_key

    return _settings


# For backward compatibility - but will raise if not configured
def settings() -> Settings:
    """Access settings (deprecated, use get_settings())."""
    return get_settings()
