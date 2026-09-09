from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # AI
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.7-flash"
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"
    gcs_bucket: str | None = None

    # Runtime
    media_root: str = "./media"
    # Demo-speed FFmpeg defaults: faster encoding while keeping 720p output.
    ffmpeg_preset: str = "superfast"
    ffmpeg_crf: int = 21
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    service_name: str = "thats-a-wrap-backend"
    service_version: str = "3.1.0-grafana-mcp"

    # Grafana read/query access for the optional in-app Tempo preview.
    # This is intentionally separate from the MCP service-account credential.
    grafana_url: str | None = None
    grafana_observability_token: str | None = None
    grafana_tempo_datasource_uid: str | None = None
    grafana_tempo_datasource_name: str = "Tempo"
    grafana_live_window_minutes: int = 30
    grafana_live_limit: int = 8

    # Remote Grafana MCP service deployed on Cloud Run over Streamable HTTP.
    grafana_service_account_token: str | None = None
    grafana_mcp_server_token: str | None = None
    grafana_mcp_url: str = "https://grafana-mcp-450541203194.us-central1.run.app/mcp"
    grafana_mcp_timeout_seconds: float = 20.0
    grafana_mcp_sse_read_timeout_seconds: float = 60.0
    grafana_org_id: int | None = None
    grafana_mcp_extra_headers: str | None = None

    # OpenTelemetry -> Grafana Cloud / OTLP gateway.
    # The endpoint should normally be the Grafana Cloud OTLP gateway URL
    # ending in /otlp; the SDK appends /v1/traces and /v1/logs.
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None
    otel_service_name: str = "thats-a-wrap-backend"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
