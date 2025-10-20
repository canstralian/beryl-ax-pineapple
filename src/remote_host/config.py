"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables with type validation
and sensible defaults.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =============================================================================
    # Server Configuration
    # =============================================================================
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", pattern="^(development|staging|production)$")

    # =============================================================================
    # Security & Authentication
    # =============================================================================
    secret_key: str = Field(
        ...,  # Required
        min_length=32,
        description="Secret key for JWT tokens (must be cryptographically secure)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=5, le=1440, description="Access token expiration"
    )

    router_api_key: str = Field(
        ...,  # Required
        min_length=32,
        description="API key for router authentication",
    )

    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # =============================================================================
    # Database Configuration
    # =============================================================================
    database_url: str = Field(
        default="sqlite:///./beryl.db",
        description="Database connection URL",
    )
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)

    # =============================================================================
    # Router Configuration
    # =============================================================================
    router_host: str = Field(default="192.168.8.1", description="Router IP address")
    router_port: int = Field(default=22, ge=1, le=65535, description="Router SSH port")
    router_user: str = Field(default="root", description="Router SSH username")
    router_ssh_key_path: Optional[Path] = Field(
        default=None, description="Path to SSH private key for router"
    )
    router_timeout: int = Field(default=30, ge=5, le=300, description="Router connection timeout")

    # =============================================================================
    # MCP Server Configuration
    # =============================================================================
    mcp_host: str = Field(default="0.0.0.0", description="MCP server bind address")
    mcp_port: int = Field(default=9000, ge=1024, le=65535, description="MCP server port")
    mcp_enabled: bool = Field(default=True, description="Enable MCP server")

    # =============================================================================
    # Storage & PCAP Configuration
    # =============================================================================
    pcap_storage_path: Path = Field(
        default=Path("/var/lib/beryl/pcaps"), description="PCAP storage directory"
    )
    max_pcap_size_mb: int = Field(default=100, ge=1, le=10000, description="Max PCAP file size")
    pcap_retention_days: int = Field(
        default=30, ge=1, le=365, description="PCAP retention period"
    )

    log_path: Path = Field(default=Path("/var/log/beryl"), description="Log directory")
    log_level: str = Field(
        default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$", description="Log level"
    )

    # =============================================================================
    # Security Tool Configuration
    # =============================================================================
    max_concurrent_scans: int = Field(
        default=3, ge=1, le=10, description="Maximum concurrent security scans"
    )

    nmap_timeout: int = Field(default=300, ge=60, le=3600, description="Nmap timeout (seconds)")
    gobuster_timeout: int = Field(
        default=600, ge=60, le=3600, description="Gobuster timeout (seconds)"
    )
    nikto_timeout: int = Field(
        default=900, ge=60, le=3600, description="Nikto timeout (seconds)"
    )

    # Optional tool paths (defaults to PATH lookup)
    nmap_path: Optional[Path] = Field(default=None, description="Path to nmap binary")
    gobuster_path: Optional[Path] = Field(default=None, description="Path to gobuster binary")

    # =============================================================================
    # AI Integration (Optional)
    # =============================================================================
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    ai_analysis_enabled: bool = Field(default=False, description="Enable AI analysis")

    # =============================================================================
    # Rate Limiting
    # =============================================================================
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(
        default=60, ge=1, le=1000, description="Requests per minute"
    )
    rate_limit_burst: int = Field(default=10, ge=1, le=100, description="Burst allowance")

    # =============================================================================
    # Monitoring & Observability
    # =============================================================================
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(
        default=9090, ge=1024, le=65535, description="Prometheus metrics port"
    )
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")

    # =============================================================================
    # Email Notifications (Optional)
    # =============================================================================
    smtp_host: Optional[str] = Field(default=None, description="SMTP server host")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP server port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_from: Optional[str] = Field(default=None, description="From email address")
    alert_recipients: List[str] = Field(
        default_factory=list, description="Alert recipient emails"
    )

    # =============================================================================
    # Feature Flags
    # =============================================================================
    enable_wireless_scanning: bool = Field(default=True)
    enable_packet_capture: bool = Field(default=True)
    enable_active_scanning: bool = Field(
        default=False, description="Enable active/intrusive scanning (requires ethics approval)"
    )
    enable_captive_portal: bool = Field(default=False)

    # =============================================================================
    # Resource Limits
    # =============================================================================
    max_memory_mb: int = Field(
        default=512, ge=128, le=16384, description="Max memory per scan process"
    )
    max_cpu_cores: int = Field(default=2, ge=1, le=16, description="Max CPU cores for scanning")
    max_upload_size_mb: int = Field(
        default=50, ge=1, le=1000, description="Max upload file size"
    )

    # =============================================================================
    # Development & Testing
    # =============================================================================
    reload: bool = Field(default=False, description="Auto-reload on code changes (dev only)")
    mock_router: bool = Field(default=False, description="Mock router connections (testing)")
    test_mode: bool = Field(
        default=False, description="Test mode (disables dangerous operations)"
    )

    @field_validator("secret_key", "router_api_key")
    @classmethod
    def validate_secrets(cls, v: str) -> str:
        """Ensure secrets are not using default/insecure values."""
        insecure_values = [
            "CHANGE_THIS",
            "changeme",
            "secret",
            "password",
            "12345",
            "test",
        ]
        if any(insecure in v.lower() for insecure in insecure_values):
            raise ValueError(
                "Insecure secret detected. Please use a cryptographically secure random value."
            )
        return v

    @field_validator("pcap_storage_path", "log_path")
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Create storage directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_database_url_for_sqlalchemy(self) -> str:
        """Get database URL compatible with SQLAlchemy."""
        # Handle async SQLite URLs
        if self.database_url.startswith("sqlite"):
            return self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once and reused
    across the application.
    """
    return Settings()  # type: ignore[call-arg]
