from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from app.db.models import Hazard
from app.models.schemas import AlertResponse, HazardTypeEnum
from app.core.config import settings
from app.services.clustering import SpatialClusteringService


class AlertService:
    """Service for generating and managing hazard alerts."""

    def __init__(self):
        self.min_alert_distance = settings.MIN_ALERT_DISTANCE_METERS
        self.max_alert_distance = settings.MAX_ALERT_DISTANCE_METERS
        self.suppression_radius = settings.ALERT_SUPPRESSION_RADIUS_METERS
        self.clustering_service = SpatialClusteringService()

    def calculate_alert_distance(
        self, speed_mps: float, severity: float
    ) -> float:
        """
        Calculate optimal warning distance based on speed and severity.

        Target: 15-30 second lead time

        Args:
            speed_mps: Vehicle speed in meters per second
            severity: Hazard severity (0-10)

        Returns:
            Alert distance in meters
        """
        # Base lead time: 20 seconds
        base_lead_time = 20.0

        # Adjust lead time based on severity
        # Higher severity = more lead time
        severity_factor = 0.5 + (severity / 10) * 0.5  # 0.5 to 1.0

        lead_time = base_lead_time * severity_factor

        # Calculate distance
        distance = speed_mps * lead_time

        # Clamp to reasonable bounds
        distance = max(self.min_alert_distance, min(self.max_alert_distance, distance))

        return round(distance, 1)

    def calculate_priority_score(
        self, distance: float, severity: float, confidence: float
    ) -> float:
        """
        Calculate alert priority score.

        Formula: severity × confidence × (1 / normalized_distance)

        Args:
            distance: Distance to hazard in meters
            severity: Hazard severity (0-10)
            confidence: Confidence score (0-1)

        Returns:
            Priority score (higher = more urgent)
        """
        # Normalize distance to 0-1 scale (inverse)
        max_distance = self.max_alert_distance
        normalized_distance = 1.0 - (min(distance, max_distance) / max_distance)

        # Calculate priority
        priority = severity * confidence * normalized_distance

        return round(priority, 3)

    async def get_alerts_for_route(
        self,
        session: AsyncSession,
        current_lat: float,
        current_lon: float,
        speed_mps: float,
        heading: Optional[float] = None,
        max_alerts: int = 5,
    ) -> List[AlertResponse]:
        """
        Get prioritized alerts for a vehicle's current position and route.

        Args:
            session: Database session
            current_lat: Current latitude
            current_lon: Current longitude
            speed_mps: Current speed in meters per second
            heading: Current heading in degrees (0-360)
            max_alerts: Maximum number of alerts to return

        Returns:
            List of prioritized alerts
        """
        # Calculate search radius based on speed
        search_radius = self.calculate_alert_distance(speed_mps, 10.0)  # Use max severity

        # Query nearby active hazards using PostGIS
        query = text("""
            SELECT
                id,
                latitude,
                longitude,
                hazard_type,
                severity,
                confidence,
                ST_Distance(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) as distance
            FROM hazards
            WHERE
                is_active = true
                AND ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :radius
                )
            ORDER BY distance ASC
            LIMIT :limit
        """)

        result = await session.execute(
            query,
            {
                "lat": current_lat,
                "lon": current_lon,
                "radius": search_radius,
                "limit": max_alerts * 2,  # Get more for filtering
            },
        )

        hazards = result.fetchall()

        if not hazards:
            return []

        # Build alerts with priority scores
        alerts = []
        for hazard in hazards:
            alert_distance = self.calculate_alert_distance(speed_mps, hazard.severity)

            # Only alert if hazard is within alert distance
            if hazard.distance <= alert_distance:
                priority = self.calculate_priority_score(
                    hazard.distance, hazard.severity, hazard.confidence
                )

                alerts.append({
                    "hazard_id": hazard.id,
                    "distance": round(hazard.distance, 1),
                    "severity": hazard.severity,
                    "confidence": hazard.confidence,
                    "latitude": hazard.latitude,
                    "longitude": hazard.longitude,
                    "hazard_type": hazard.hazard_type,
                    "priority": priority,
                })

        # Apply alert suppression (max 1 alert per suppression radius)
        filtered_alerts = self._apply_suppression(alerts)

        # Sort by priority and limit
        filtered_alerts.sort(key=lambda x: x["priority"], reverse=True)
        top_alerts = filtered_alerts[:max_alerts]

        # Generate alert messages
        return [
            AlertResponse(
                hazard_id=alert["hazard_id"],
                distance=alert["distance"],
                severity=alert["severity"],
                confidence=alert["confidence"],
                latitude=alert["latitude"],
                longitude=alert["longitude"],
                hazard_type=HazardTypeEnum(alert["hazard_type"]),
                message=self._generate_alert_message(
                    alert["hazard_type"], alert["distance"], alert["severity"]
                ),
            )
            for alert in top_alerts
        ]

    def _apply_suppression(self, alerts: List[dict]) -> List[dict]:
        """
        Apply alert suppression to prevent warning fatigue.

        Keep only the highest priority alert within suppression radius.

        Args:
            alerts: List of alert dictionaries

        Returns:
            Filtered list of alerts
        """
        if not alerts:
            return []

        # Sort by priority
        sorted_alerts = sorted(alerts, key=lambda x: x["priority"], reverse=True)

        filtered = []
        for alert in sorted_alerts:
            # Check if too close to any already-selected alert
            too_close = False
            for selected in filtered:
                distance = self.clustering_service.haversine_distance(
                    alert["latitude"],
                    alert["longitude"],
                    selected["latitude"],
                    selected["longitude"],
                )
                if distance < self.suppression_radius:
                    too_close = True
                    break

            if not too_close:
                filtered.append(alert)

        return filtered

    def _generate_alert_message(
        self, hazard_type: str, distance: float, severity: float
    ) -> str:
        """
        Generate human-readable alert message.

        Args:
            hazard_type: Type of hazard
            distance: Distance to hazard in meters
            severity: Severity score

        Returns:
            Alert message string
        """
        # Convert distance to appropriate unit
        if distance < 1000:
            distance_str = f"{int(distance)}m"
        else:
            distance_str = f"{distance / 1000:.1f}km"

        # Severity descriptor
        if severity >= 7:
            severity_str = "severe"
        elif severity >= 4:
            severity_str = "moderate"
        else:
            severity_str = "minor"

        # Hazard type descriptor
        type_map = {
            "pothole": "pothole",
            "speed_bump": "speed bump",
            "rough_road": "rough road",
            "unknown": "road hazard",
        }
        type_str = type_map.get(hazard_type, "road hazard")

        return f"{severity_str.capitalize()} {type_str} ahead in {distance_str}"
