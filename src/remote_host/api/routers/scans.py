"""
Security scan endpoints.

Provides API for running and managing security scans (nmap, gobuster, etc.).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import Settings, get_settings
from ...database import get_async_session
from ...models import Scan, ScanStatus, ScanType
from ...security import get_current_user, validate_target, validate_scan_options

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class ScanRequest(BaseModel):
    """Request model for creating a new scan."""

    scan_type: ScanType
    target: str = Field(..., description="IP address or domain to scan")
    options: Optional[dict] = Field(default_factory=dict, description="Scan-specific options")

    class Config:
        json_schema_extra = {
            "example": {
                "scan_type": "nmap",
                "target": "192.168.1.100",
                "options": {"ports": "80,443,8080", "scan_type": "syn", "timing": 4},
            }
        }


class ScanResponse(BaseModel):
    """Response model for scan information."""

    id: int
    scan_type: str
    target: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    """Response model for list of scans."""

    scans: list[ScanResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan_request: ScanRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """
    Create a new security scan.

    Validates input, creates database record, and queues scan for execution.
    """
    # Validate target
    validated_target = validate_target(scan_request.target, allow_domains=True)

    # Validate options
    validated_options = validate_scan_options(scan_request.options)

    # Create scan record
    scan = Scan(
        scan_type=scan_request.scan_type,
        target=validated_target,
        status=ScanStatus.PENDING,
        options=validated_options,
        created_by=current_user.get("username"),
    )

    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # TODO: Queue scan for execution (implement background worker)
    # For now, just return the created scan record

    return scan


@router.get("", response_model=ScanListResponse)
async def list_scans(
    page: int = 1,
    page_size: int = 50,
    scan_type: Optional[ScanType] = None,
    status_filter: Optional[ScanStatus] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    """
    List all scans with pagination and filtering.
    """
    # Build query
    query = select(Scan).order_by(Scan.created_at.desc())

    # Apply filters
    if scan_type:
        query = query.where(Scan.scan_type == scan_type)
    if status_filter:
        query = query.where(Scan.status == status_filter)

    # Get total count
    count_query = select(Scan)
    if scan_type:
        count_query = count_query.where(Scan.scan_type == scan_type)
    if status_filter:
        count_query = count_query.where(Scan.status == status_filter)

    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    scans = result.scalars().all()

    return {
        "scans": scans,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Get detailed information about a specific scan.
    """
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found",
        )

    return scan


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a scan and its results.
    """
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found",
        )

    # Don't allow deleting running scans
    if scan.status == ScanStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running scan. Cancel it first.",
        )

    await db.delete(scan)
    await db.commit()

    return None


@router.post("/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Cancel a running or pending scan.
    """
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found",
        )

    if scan.status not in [ScanStatus.PENDING, ScanStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel scan with status: {scan.status}",
        )

    # TODO: Actually cancel the running process
    scan.status = ScanStatus.CANCELLED
    scan.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(scan)

    return scan
