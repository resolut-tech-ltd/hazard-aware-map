from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.models import Detection, Hazard, User
from app.core.config import settings
import numpy as np


class HazardValidationService:
    """Service for validating and scoring hazards."""

    def __init__(self):
        self.temporal_weight_days = settings.TEMPORAL_WEIGHT_DAYS
        self.confidence_decay_days = settings.CONFIDENCE_DECAY_DAYS
        self.min_detections = settings.MIN_DETECTIONS_FOR_HAZARD

    def calculate_temporal_weight(self, detection_date: datetime) -> float:
        """
        Calculate temporal weight for a detection based on its age.

        Recent detections (within TEMPORAL_WEIGHT_DAYS) receive higher weight.

        Args:
            detection_date: When the detection occurred

        Returns:
            Weight value between 0.0 and 1.0
        """
        days_old = (datetime.utcnow() - detection_date).days

        if days_old <= self.temporal_weight_days:
            return 1.0
        elif days_old >= self.confidence_decay_days:
            return 0.1  # Minimum weight for very old detections
        else:
            # Linear decay between temporal_weight_days and confidence_decay_days
            decay_range = self.confidence_decay_days - self.temporal_weight_days
            decay_amount = (days_old - self.temporal_weight_days) / decay_range
            return 1.0 - (0.9 * decay_amount)  # Decay from 1.0 to 0.1

    def calculate_confidence_score(
        self,
        detection_count: int,
        unique_user_count: int,
        days_since_last_detection: int,
        positive_verifications: int,
        total_verifications: int,
    ) -> float:
        """
        Calculate comprehensive confidence score for a hazard.

        Factors:
        - Number of detections
        - Number of unique users
        - Recency of detections
        - User verifications

        Args:
            detection_count: Total number of detections
            unique_user_count: Number of unique users who reported
            days_since_last_detection: Days since most recent detection
            positive_verifications: Number of positive user verifications
            total_verifications: Total number of verifications

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Component 1: Detection count (0-0.4)
        detection_score = min(0.4, (detection_count / 10) * 0.4)

        # Component 2: Unique users (0-0.3)
        user_score = min(0.3, (unique_user_count / 5) * 0.3)

        # Component 3: Recency (0-0.2)
        if days_since_last_detection <= 7:
            recency_score = 0.2
        elif days_since_last_detection <= 30:
            recency_score = 0.15
        elif days_since_last_detection <= 60:
            recency_score = 0.1
        else:
            recency_score = 0.05

        # Component 4: Verification (0-0.1)
        if total_verifications > 0:
            verification_ratio = positive_verifications / total_verifications
            verification_score = verification_ratio * 0.1
        else:
            verification_score = 0.0

        total_confidence = detection_score + user_score + recency_score + verification_score

        return round(min(1.0, total_confidence), 3)

    def is_outlier(
        self, magnitude: float, accuracy: float, cluster_magnitudes: List[float]
    ) -> bool:
        """
        Detect if a detection is a statistical outlier.

        Args:
            magnitude: Detection magnitude
            accuracy: GPS accuracy
            cluster_magnitudes: List of magnitudes in the cluster

        Returns:
            True if the detection should be filtered out
        """
        # Filter by GPS accuracy
        if accuracy > settings.MAX_GPS_ACCURACY_METERS:
            return True

        # Filter by magnitude (statistical outlier detection)
        if len(cluster_magnitudes) >= 3:
            mean_mag = np.mean(cluster_magnitudes)
            std_mag = np.std(cluster_magnitudes)

            # Z-score method: flag if more than 2 standard deviations away
            if std_mag > 0:
                z_score = abs((magnitude - mean_mag) / std_mag)
                if z_score > 2.5:
                    return True

        return False

    async def get_hazard_statistics(
        self, session: AsyncSession, hazard_id: int
    ) -> dict:
        """
        Get comprehensive statistics for a hazard.

        Args:
            session: Database session
            hazard_id: ID of the hazard

        Returns:
            Dictionary with statistics
        """
        # Get detection count and unique users
        detection_query = (
            select(
                func.count(Detection.id).label("count"),
                func.count(func.distinct(Detection.user_id)).label("unique_users"),
                func.max(Detection.timestamp).label("last_detection"),
                func.avg(Detection.magnitude).label("avg_magnitude"),
            )
            .where(Detection.hazard_id == hazard_id)
        )

        result = await session.execute(detection_query)
        stats = result.first()

        if not stats:
            return {}

        days_since_last = (
            (datetime.utcnow() - stats.last_detection).days if stats.last_detection else 999
        )

        return {
            "detection_count": stats.count or 0,
            "unique_user_count": stats.unique_users or 0,
            "days_since_last_detection": days_since_last,
            "avg_magnitude": float(stats.avg_magnitude or 0),
        }

    def classify_hazard_type(self, magnitudes: List[float], severities: List[float]) -> str:
        """
        Classify hazard type based on detection patterns.

        Args:
            magnitudes: List of detection magnitudes
            severities: List of severity scores

        Returns:
            Hazard type classification
        """
        if not magnitudes:
            return "unknown"

        avg_magnitude = np.mean(magnitudes)
        max_magnitude = np.max(magnitudes)
        magnitude_std = np.std(magnitudes)

        # Speed bumps: high consistent magnitude
        if avg_magnitude > 2.5 and magnitude_std < 0.5:
            return "speed_bump"

        # Potholes: very high peak magnitude, variable
        if max_magnitude > 3.5:
            return "pothole"

        # Rough road: moderate consistent magnitude
        if avg_magnitude > 1.5 and magnitude_std < 1.0:
            return "rough_road"

        return "unknown"

    def should_deactivate_hazard(
        self, last_detected: datetime, confidence: float
    ) -> bool:
        """
        Determine if a hazard should be deactivated.

        Args:
            last_detected: Date of last detection
            confidence: Current confidence score

        Returns:
            True if hazard should be deactivated
        """
        days_old = (datetime.utcnow() - last_detected).days

        # Deactivate if very old and low confidence (likely repaired)
        if days_old > self.confidence_decay_days and confidence < 0.3:
            return True

        return False
