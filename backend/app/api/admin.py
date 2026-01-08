"""
Admin API endpoints for manual system operations.

This module provides administrative endpoints for:
- Manual processing of detections into hazards
- System statistics and monitoring

These endpoints are intended for manual triggering during development/testing.
In production, detection processing should be automated via background workers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any
from datetime import datetime

from app.db.base import get_db
from app.db.models import Detection, Hazard, HazardType
from app.services.clustering import SpatialClusteringService
from geoalchemy2.elements import WKTElement

router = APIRouter()


@router.post("/process-detections")
async def process_detections(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Manually trigger processing of unprocessed detections into hazards.

    This endpoint performs the following operations:
    1. Fetches all unprocessed detections (processed=false) from the database
    2. Clusters them using DBSCAN spatial clustering algorithm
       - Default radius: configured in settings (typically 50-100 meters)
       - Minimum detections per cluster: configured in settings (typically 3-5)
    3. For each cluster, creates a Hazard record with:
       - Centroid location (average lat/lon of all detections)
       - Severity score (0-10 scale):
         * Calculated as: 70% average magnitude + 30% max magnitude
         * Normalized assuming max realistic magnitude of 5g
       - Confidence score (0-1 scale):
         * Based on detection count and unique user count
         * Formula: min(1.0, detection_count * 0.1 + unique_users * 0.2)
       - is_active=true (hazard is visible to users)
    4. Links all detections in the cluster to the created hazard
    5. Marks all clustered detections as processed=true
    6. Marks "noise" detections (not in any cluster) as processed=true
       - Noise detections have no hazard_id (remain NULL)

    Returns:
        Dictionary with processing statistics:
        - message: Success message
        - detections_total: Total unprocessed detections found
        - detections_processed: Detections included in clusters
        - detections_marked_noise: Detections excluded as noise
        - hazards_created: Number of new hazard records created
        - clusters_found: Number of clusters identified by DBSCAN

    Example Response:
        {
            "message": "Successfully processed 39 detections into 2 hazards",
            "detections_total": 40,
            "detections_processed": 39,
            "detections_marked_noise": 1,
            "hazards_created": 2,
            "clusters_found": 2
        }

    Note:
        - This is a manual endpoint for development/testing
        - In production, use a background worker or scheduled task
        - Running this multiple times is safe (only processes unprocessed detections)
    """
    clustering_service = SpatialClusteringService()

    # Get unprocessed detections
    unprocessed = await clustering_service.get_unprocessed_detections(
        session=db,
        limit=10000
    )

    if not unprocessed:
        return {
            "message": "No unprocessed detections found",
            "detections_processed": 0,
            "hazards_created": 0,
            "detections_marked_noise": 0,
        }

    # Cluster detections
    clusters = clustering_service.cluster_detections(unprocessed)

    hazards_created = 0
    detections_processed = 0
    detection_ids_in_clusters = set()

    # Process each cluster
    for cluster_detection_ids in clusters:
        # Fetch full detection data for this cluster
        query = select(Detection).where(Detection.id.in_(cluster_detection_ids))
        result = await db.execute(query)
        cluster_detections = result.scalars().all()

        if not cluster_detections:
            continue

        # Calculate cluster properties
        cluster_coords = [
            (d.latitude, d.longitude, d.id) for d in cluster_detections
        ]
        centroid_lat, centroid_lon = clustering_service.calculate_cluster_centroid(
            cluster_coords
        )

        magnitudes = [d.magnitude for d in cluster_detections]
        severity = clustering_service.calculate_cluster_severity(magnitudes)

        # Get unique users
        unique_users = len(set(d.user_id for d in cluster_detections))

        # Get temporal bounds
        timestamps = [d.timestamp for d in cluster_detections]
        first_detected = min(timestamps)
        last_detected = max(timestamps)

        # Calculate confidence based on detection count and unique users
        # More detections and more unique users = higher confidence
        # Formula: min(1.0, detection_count * 0.1 + unique_users * 0.2)
        # Example: 5 detections from 2 users = 0.5 + 0.4 = 0.9 confidence
        detection_count = len(cluster_detections)
        confidence = min(1.0, (detection_count * 0.1) + (unique_users * 0.2))
        confidence = round(confidence, 2)

        # Create WKT point for PostGIS
        point = f"POINT({centroid_lon} {centroid_lat})"

        # Create hazard
        hazard = Hazard(
            location=WKTElement(point, srid=4326),
            latitude=centroid_lat,
            longitude=centroid_lon,
            hazard_type="unknown",  # Use string value, not enum
            severity=severity,
            confidence=confidence,
            detection_count=detection_count,
            unique_user_count=unique_users,
            verification_count=0,
            positive_verifications=0,
            first_detected=first_detected,
            last_detected=last_detected,
            is_active=True,
            is_verified=False,
        )

        db.add(hazard)
        await db.flush()  # Get hazard ID

        # Mark detections as processed and link to hazard
        for detection in cluster_detections:
            detection.processed = True
            detection.hazard_id = hazard.id
            detection_ids_in_clusters.add(detection.id)

        hazards_created += 1
        detections_processed += len(cluster_detections)

    # Mark noise detections (not in any cluster) as processed
    all_detection_ids = {det_id for _, _, det_id in unprocessed}
    noise_detection_ids = all_detection_ids - detection_ids_in_clusters

    if noise_detection_ids:
        query = select(Detection).where(Detection.id.in_(noise_detection_ids))
        result = await db.execute(query)
        noise_detections = result.scalars().all()

        for detection in noise_detections:
            detection.processed = True
            # hazard_id remains None for noise

    await db.commit()

    return {
        "message": f"Successfully processed {detections_processed} detections into {hazards_created} hazards",
        "detections_total": len(unprocessed),
        "detections_processed": detections_processed,
        "detections_marked_noise": len(noise_detection_ids),
        "hazards_created": hazards_created,
        "clusters_found": len(clusters),
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get system statistics about detections and hazards.

    Provides an overview of the current state of the system including:
    - Detection counts (total, processed, unprocessed)
    - Hazard counts (total, active, inactive)

    Returns:
        Dictionary with two main sections:
        - detections: Detection statistics
          * total: All detections in the system
          * processed: Detections that have been clustered/analyzed
          * unprocessed: Detections waiting to be processed
        - hazards: Hazard statistics
          * total: All hazards in the system
          * active: Hazards visible to users (is_active=true)
          * inactive: Hazards that have been deactivated

    Example Response:
        {
            "detections": {
                "total": 40,
                "processed": 40,
                "unprocessed": 0
            },
            "hazards": {
                "total": 2,
                "active": 2,
                "inactive": 0
            }
        }

    Use Cases:
        - Monitor system health
        - Check if detections need processing
        - Verify processing pipeline is working
        - Dashboard metrics
    """
    # Count unprocessed detections
    unprocessed_query = select(func.count()).select_from(Detection).where(
        Detection.processed == False
    )
    unprocessed_result = await db.execute(unprocessed_query)
    unprocessed_count = unprocessed_result.scalar()

    # Count total detections
    total_detections_query = select(func.count()).select_from(Detection)
    total_detections_result = await db.execute(total_detections_query)
    total_detections = total_detections_result.scalar()

    # Count active hazards
    active_hazards_query = select(func.count()).select_from(Hazard).where(
        Hazard.is_active == True
    )
    active_hazards_result = await db.execute(active_hazards_query)
    active_hazards = active_hazards_result.scalar()

    # Count total hazards
    total_hazards_query = select(func.count()).select_from(Hazard)
    total_hazards_result = await db.execute(total_hazards_query)
    total_hazards = total_hazards_result.scalar()

    return {
        "detections": {
            "total": total_detections,
            "processed": total_detections - unprocessed_count,
            "unprocessed": unprocessed_count,
        },
        "hazards": {
            "total": total_hazards,
            "active": active_hazards,
            "inactive": total_hazards - active_hazards,
        },
    }
