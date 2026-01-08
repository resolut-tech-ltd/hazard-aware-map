from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional

from app.db.base import get_db
from app.db.models import Hazard, User, HazardVerification
from app.models.schemas import HazardResponse, HazardList, VerificationCreate, AlertResponse
from app.api.auth import get_current_user
from app.services.alerts import AlertService

router = APIRouter()
alert_service = AlertService()


@router.get("/nearby", response_model=HazardList)
async def get_nearby_hazards(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: float = Query(5000, ge=100, le=50000, description="Radius in meters"),
    min_confidence: float = Query(0.0, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
):
    """
    Get hazards near a location.

    Uses PostGIS spatial queries for efficient geospatial search.
    """
    query = text("""
        SELECT
            id, latitude, longitude, hazard_type, severity, confidence,
            detection_count, unique_user_count, first_detected, last_detected,
            is_active, is_verified
        FROM hazards
        WHERE
            is_active = true
            AND confidence >= :min_confidence
            AND ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
        ORDER BY
            ST_Distance(
                location::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) ASC
        LIMIT 100
    """)

    result = await db.execute(
        query,
        {
            "lat": lat,
            "lon": lon,
            "radius": radius,
            "min_confidence": min_confidence,
        },
    )

    hazards = [
        HazardResponse(
            id=row.id,
            latitude=row.latitude,
            longitude=row.longitude,
            hazard_type=row.hazard_type,
            severity=row.severity,
            confidence=row.confidence,
            detection_count=row.detection_count,
            unique_user_count=row.unique_user_count,
            first_detected=row.first_detected,
            last_detected=row.last_detected,
            is_active=row.is_active,
            is_verified=row.is_verified,
        )
        for row in result.fetchall()
    ]

    return HazardList(hazards=hazards, count=len(hazards))


@router.get("/bounds", response_model=HazardList)
async def get_hazards_in_bounds(
    min_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    min_confidence: float = Query(0.0, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
):
    """Get all hazards within a bounding box (for map display)."""
    query = text("""
        SELECT
            id, latitude, longitude, hazard_type, severity, confidence,
            detection_count, unique_user_count, first_detected, last_detected,
            is_active, is_verified
        FROM hazards
        WHERE
            is_active = true
            AND confidence >= :min_confidence
            AND latitude BETWEEN :min_lat AND :max_lat
            AND longitude BETWEEN :min_lon AND :max_lon
        LIMIT 500
    """)

    result = await db.execute(
        query,
        {
            "min_lat": min_lat,
            "min_lon": min_lon,
            "max_lat": max_lat,
            "max_lon": max_lon,
            "min_confidence": min_confidence,
        },
    )

    hazards = [
        HazardResponse(
            id=row.id,
            latitude=row.latitude,
            longitude=row.longitude,
            hazard_type=row.hazard_type,
            severity=row.severity,
            confidence=row.confidence,
            detection_count=row.detection_count,
            unique_user_count=row.unique_user_count,
            first_detected=row.first_detected,
            last_detected=row.last_detected,
            is_active=row.is_active,
            is_verified=row.is_verified,
        )
        for row in result.fetchall()
    ]

    return HazardList(hazards=hazards, count=len(hazards))


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    speed_mps: float = Query(0, ge=0, le=50, description="Speed in meters per second"),
    heading: Optional[float] = Query(None, ge=0, le=360),
    max_alerts: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """
    Get prioritized alerts for current location and speed.

    Calculates dynamic alert distances and priority scores.
    """
    alerts = await alert_service.get_alerts_for_route(
        session=db,
        current_lat=lat,
        current_lon=lon,
        speed_mps=speed_mps,
        heading=heading,
        max_alerts=max_alerts,
    )

    return alerts


@router.get("/{hazard_id}", response_model=HazardResponse)
async def get_hazard(hazard_id: int, db: AsyncSession = Depends(get_db)):
    """Get details of a specific hazard."""
    query = select(Hazard).where(Hazard.id == hazard_id)
    result = await db.execute(query)
    hazard = result.scalar_one_or_none()

    if not hazard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hazard not found"
        )

    return hazard


@router.post("/{hazard_id}/verify", status_code=status.HTTP_201_CREATED)
async def verify_hazard(
    hazard_id: int,
    verification: VerificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit user verification for a hazard.

    Allows users to confirm or dispute detected hazards.
    """
    # Check if hazard exists
    hazard_query = select(Hazard).where(Hazard.id == hazard_id)
    result = await db.execute(hazard_query)
    hazard = result.scalar_one_or_none()

    if not hazard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hazard not found"
        )

    # Check if user already verified this hazard
    existing_query = select(HazardVerification).where(
        HazardVerification.hazard_id == hazard_id,
        HazardVerification.user_id == current_user.id,
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already verified this hazard",
        )

    # Create verification
    new_verification = HazardVerification(
        hazard_id=hazard_id,
        user_id=current_user.id,
        is_valid=verification.is_valid,
        comment=verification.comment,
    )

    db.add(new_verification)

    # Update hazard verification counts
    hazard.verification_count += 1
    if verification.is_valid:
        hazard.positive_verifications += 1

    await db.commit()

    return {"message": "Verification submitted successfully"}
