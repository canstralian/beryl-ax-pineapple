"""
Router communication endpoints.

Provides API for receiving telemetry from the router and sending commands.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import Settings, get_settings
from ...database import get_async_session
from ...models import PacketCapture, RouterTelemetry
from ...security import verify_router_api_key

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class TelemetryEvent(BaseModel):
    """Telemetry event from router."""

    event_type: str = Field(..., description="Type of event (probe, beacon, client_event, etc.)")
    router_id: Optional[str] = Field(None, description="Router identifier (MAC address)")
    data: dict = Field(..., description="Event-specific data")
    ssid: Optional[str] = None
    channel: Optional[int] = None
    signal_strength: Optional[int] = None
    client_mac: Optional[str] = None
    event_timestamp: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "probe_request",
                "router_id": "AA:BB:CC:DD:EE:FF",
                "data": {"probe_ssid": "TestNetwork", "rssi": -65},
                "client_mac": "11:22:33:44:55:66",
                "signal_strength": -65,
                "event_timestamp": "2025-10-20T12:34:56",
            }
        }


class PcapUpload(BaseModel):
    """PCAP file upload metadata."""

    filename: str
    interface: Optional[str] = None
    filter_expression: Optional[str] = None
    router_id: Optional[str] = None


class CommandRequest(BaseModel):
    """Command to send to router."""

    command: str = Field(..., description="Command to execute")
    timeout: int = Field(default=30, ge=5, le=300, description="Command timeout in seconds")


class CommandResponse(BaseModel):
    """Command execution response."""

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def receive_telemetry(
    event: TelemetryEvent,
    db: AsyncSession = Depends(get_async_session),
    _auth: bool = Depends(verify_router_api_key),
):
    """
    Receive telemetry event from router.

    This endpoint is called by the router's Lua collector to send events.
    """
    # Create telemetry record
    telemetry = RouterTelemetry(
        event_type=event.event_type,
        router_id=event.router_id,
        data=event.data,
        ssid=event.ssid,
        channel=event.channel,
        signal_strength=event.signal_strength,
        client_mac=event.client_mac,
        event_timestamp=event.event_timestamp or datetime.utcnow(),
    )

    db.add(telemetry)
    await db.commit()

    return {"status": "received", "id": telemetry.id}


@router.get("/telemetry")
async def list_telemetry(
    page: int = 1,
    page_size: int = 100,
    event_type: Optional[str] = None,
    router_id: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
):
    """
    List telemetry events with pagination and filtering.
    """
    # Build query
    query = select(RouterTelemetry).order_by(RouterTelemetry.event_timestamp.desc())

    # Apply filters
    if event_type:
        query = query.where(RouterTelemetry.event_type == event_type)
    if router_id:
        query = query.where(RouterTelemetry.router_id == router_id)

    # Get total count
    count_query = select(RouterTelemetry)
    if event_type:
        count_query = count_query.where(RouterTelemetry.event_type == event_type)
    if router_id:
        count_query = count_query.where(RouterTelemetry.router_id == router_id)

    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "router_id": e.router_id,
                "data": e.data,
                "ssid": e.ssid,
                "client_mac": e.client_mac,
                "event_timestamp": e.event_timestamp,
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/pcap/upload")
async def upload_pcap_metadata(
    pcap: PcapUpload,
    db: AsyncSession = Depends(get_async_session),
    _auth: bool = Depends(verify_router_api_key),
    settings: Settings = Depends(get_settings),
):
    """
    Register uploaded PCAP file metadata.

    The actual file should be uploaded via SCP/SFTP to the PCAP storage path.
    """
    # Verify file exists
    filepath = settings.pcap_storage_path / pcap.filename
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PCAP file not found: {pcap.filename}",
        )

    # Get file size
    file_size = filepath.stat().st_size

    # Create metadata record
    capture = PacketCapture(
        filename=pcap.filename,
        filepath=str(filepath),
        file_size_bytes=file_size,
        interface=pcap.interface,
        filter_expression=pcap.filter_expression,
        router_id=pcap.router_id,
    )

    db.add(capture)
    await db.commit()

    return {"status": "registered", "id": capture.id, "filepath": str(filepath)}


@router.get("/pcaps")
async def list_pcaps(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_async_session),
):
    """
    List uploaded PCAP files.
    """
    # Build query
    query = select(PacketCapture).order_by(PacketCapture.created_at.desc())

    # Get total count
    total_result = await db.execute(select(PacketCapture))
    total = len(total_result.scalars().all())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    pcaps = result.scalars().all()

    return {
        "pcaps": [
            {
                "id": p.id,
                "filename": p.filename,
                "file_size_mb": round(p.file_size_bytes / 1024 / 1024, 2),
                "interface": p.interface,
                "packet_count": p.packet_count,
                "analyzed": p.analyzed,
                "created_at": p.created_at,
            }
            for p in pcaps
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/status")
async def router_status(
    settings: Settings = Depends(get_settings),
):
    """
    Get router connection status.
    """
    # TODO: Implement actual router connection check via SSH
    return {
        "router_host": settings.router_host,
        "router_port": settings.router_port,
        "connection": "unknown",  # Will be "connected" or "disconnected"
        "last_seen": None,
    }
