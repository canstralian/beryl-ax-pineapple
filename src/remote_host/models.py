"""
Database models for scans, results, and telemetry.

Provides SQLAlchemy ORM models for persistent storage.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class ScanStatus(str, PyEnum):
    """Scan execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(str, PyEnum):
    """Type of security scan."""

    NMAP = "nmap"
    GOBUSTER = "gobuster"
    NIKTO = "nikto"
    SQLMAP = "sqlmap"
    HYDRA = "hydra"
    WIRELESS = "wireless"
    PACKET_CAPTURE = "packet_capture"
    CUSTOM = "custom"


class Scan(Base):
    """Security scan record."""

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(Enum(ScanType), nullable=False, index=True)
    target = Column(String(255), nullable=False, index=True)
    status = Column(Enum(ScanStatus), nullable=False, default=ScanStatus.PENDING, index=True)

    # Scan configuration
    options = Column(JSON, nullable=True)  # Scan-specific options
    command = Column(Text, nullable=True)  # Actual command executed

    # Execution metadata
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Results
    output = Column(Text, nullable=True)  # Raw command output
    error_output = Column(Text, nullable=True)  # Error messages
    exit_code = Column(Integer, nullable=True)
    results_json = Column(JSON, nullable=True)  # Parsed results

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # User tracking
    created_by = Column(String(255), nullable=True)

    # Relationships
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, type={self.scan_type}, target={self.target}, status={self.status})>"


class Severity(str, PyEnum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(Base):
    """Security finding from a scan."""

    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, index=True)

    # Finding details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Enum(Severity), nullable=False, index=True)

    # Classification
    cve_id = Column(String(50), nullable=True, index=True)  # CVE identifier if applicable
    category = Column(String(100), nullable=True, index=True)  # E.g., "SQL Injection", "XSS"

    # Evidence
    evidence = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)  # Port, URL, file path, etc.

    # Remediation
    recommendation = Column(Text, nullable=True)

    # Metadata
    raw_data = Column(JSON, nullable=True)  # Original finding data
    false_positive = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    scan = relationship("Scan", back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, severity={self.severity}, title={self.title[:50]})>"


class RouterTelemetry(Base):
    """Telemetry data from the router."""

    __tablename__ = "router_telemetry"

    id = Column(Integer, primary_key=True, index=True)

    # Telemetry type
    event_type = Column(String(100), nullable=False, index=True)  # probe, beacon, client_event, etc.

    # Router identification
    router_id = Column(String(100), nullable=True, index=True)  # MAC address or identifier

    # Event data
    data = Column(JSON, nullable=False)  # Event-specific data

    # Network context
    ssid = Column(String(255), nullable=True, index=True)
    channel = Column(Integer, nullable=True)
    signal_strength = Column(Integer, nullable=True)  # RSSI in dBm

    # Client information (for probe/association events)
    client_mac = Column(String(17), nullable=True, index=True)  # MAC address
    client_vendor = Column(String(255), nullable=True)  # OUI vendor lookup

    # Timestamps
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RouterTelemetry(id={self.id}, type={self.event_type}, timestamp={self.event_timestamp})>"


class PacketCapture(Base):
    """Packet capture file metadata."""

    __tablename__ = "packet_captures"

    id = Column(Integer, primary_key=True, index=True)

    # File information
    filename = Column(String(255), nullable=False, unique=True, index=True)
    filepath = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

    # Capture details
    interface = Column(String(50), nullable=True)
    filter_expression = Column(String(500), nullable=True)  # tcpdump/BPF filter
    packet_count = Column(Integer, nullable=True)

    # Capture window
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Analysis status
    analyzed = Column(Boolean, nullable=False, default=False)
    analysis_results = Column(JSON, nullable=True)

    # Metadata
    router_id = Column(String(100), nullable=True)
    created_by = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PacketCapture(id={self.id}, filename={self.filename}, packets={self.packet_count})>"


class User(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Credentials
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Account status
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, active={self.is_active})>"
