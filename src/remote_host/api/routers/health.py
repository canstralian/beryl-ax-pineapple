"""
Health check endpoints.

Provides system health status, readiness checks, and metrics.
"""

import platform
import psutil
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import Settings, get_settings
from ...database import get_async_session

router = APIRouter()


@router.get("")
@router.get("/")
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        Health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "beryl-ax-pineapple",
    }


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
):
    """
    Readiness check - verify all dependencies are available.

    Returns:
        Readiness status and dependency checks
    """
    checks = {
        "database": "unknown",
        "storage": "unknown",
        "mcp": "unknown",
    }

    # Check database
    try:
        await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check storage directories
    try:
        settings.pcap_storage_path.exists()
        settings.log_path.exists()
        checks["storage"] = "ok"
    except Exception as e:
        checks["storage"] = f"error: {str(e)}"

    # Check MCP status
    checks["mcp"] = "enabled" if settings.mcp_enabled else "disabled"

    # Overall status
    all_ok = all(check in ["ok", "enabled", "disabled"] for check in checks.values())

    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/system")
async def system_info(settings: Settings = Depends(get_settings)):
    """
    System information and resource usage.

    Returns:
        System metrics and resource usage
    """
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()

    # Memory usage
    memory = psutil.virtual_memory()
    memory_info = {
        "total_mb": round(memory.total / 1024 / 1024, 2),
        "available_mb": round(memory.available / 1024 / 1024, 2),
        "used_mb": round(memory.used / 1024 / 1024, 2),
        "percent": memory.percent,
    }

    # Disk usage (for storage paths)
    pcap_disk = psutil.disk_usage(str(settings.pcap_storage_path))
    pcap_storage_info = {
        "total_gb": round(pcap_disk.total / 1024 / 1024 / 1024, 2),
        "used_gb": round(pcap_disk.used / 1024 / 1024 / 1024, 2),
        "free_gb": round(pcap_disk.free / 1024 / 1024 / 1024, 2),
        "percent": pcap_disk.percent,
    }

    # Network interfaces
    net_interfaces = list(psutil.net_if_addrs().keys())

    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version(),
        },
        "cpu": {
            "count": cpu_count,
            "percent": cpu_percent,
        },
        "memory": memory_info,
        "storage": {
            "pcap_storage": pcap_storage_info,
        },
        "network": {
            "interfaces": net_interfaces,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
