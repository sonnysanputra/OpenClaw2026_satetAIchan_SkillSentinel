"""Environment-driven settings loaded via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenClaw Gateway connection (where the SkillsSentinel security agent runs)
    security_gateway_url: str = "wss://localhost:18789"
    security_gateway_token: str = ""
    security_agent_session: str = "agent:security:main"
    # When the gateway is loopback/same-host we can omit device signing per
    # the gateway protocol docs (client.id=gateway-client, client.mode=backend).
    security_gateway_loopback: bool = True
    # TLS pin (optional). When empty, default TLS verify applies.
    security_gateway_tls_fingerprint: str = ""

    # Frontend
    frontend_origin: str = "http://localhost:3000"

    # SkillsHub
    skillshub_readme_url: str = (
        "https://raw.githubusercontent.com/mergisi/awesome-openclaw-agents/main/README.md"
    )
    skillshub_cache_ttl: int = 300

    log_level: str = "info"


settings = Settings()  # type: ignore[call-arg]
