"""Data transformation utilities for converting API responses to database models."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import pytz
from dateutil.parser import parse as parse_date

from .models import (
    User, Instructor, Ride, Workout, WorkoutPerformanceSummary,
    WorkoutPerformanceMetric, WorkoutAchievement
)
from .logging_config import get_logger

logger = get_logger(__name__)


class DataTransformer:
    """Transforms Peloton API data into database model instances."""
    
    @staticmethod
    def transform_user_data(user_data: Dict[str, Any]) -> User:
        """Transform user data from API response to User model.
        
        Args:
            user_data: User data from Peloton API
            
        Returns:
            User model instance
        """
        return User(
            id=user_data["id"],
            username=user_data.get("username", ""),
            email=user_data.get("email"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            location=user_data.get("location"),
            timezone=user_data.get("timezone"),
            created_at=DataTransformer._parse_timestamp(user_data.get("created_at")),
        )
    
    @staticmethod
    def transform_instructor_data(instructor_data: Dict[str, Any]) -> Instructor:
        """Transform instructor data from API response to Instructor model.
        
        Args:
            instructor_data: Instructor data from Peloton API
            
        Returns:
            Instructor model instance
        """
        return Instructor(
            id=instructor_data["id"],
            name=instructor_data.get("name", ""),
            first_name=instructor_data.get("first_name"),
            last_name=instructor_data.get("last_name"),
            bio=instructor_data.get("bio"),
            image_url=instructor_data.get("image_url"),
        )
    
    @staticmethod
    def transform_ride_data(ride_data: Dict[str, Any]) -> Ride:
        """Transform ride data from API response to Ride model.
        
        Args:
            ride_data: Ride data from Peloton API
            
        Returns:
            Ride model instance
        """
        return Ride(
            id=ride_data["id"],
            title=ride_data.get("title", ""),
            description=ride_data.get("description"),
            instructor_id=ride_data.get("instructor_id"),
            fitness_discipline=ride_data.get("fitness_discipline", ""),
            fitness_discipline_display_name=ride_data.get("fitness_discipline_display_name"),
            duration=ride_data.get("duration"),
            difficulty_estimate=ride_data.get("difficulty_estimate"),
            difficulty_rating_avg=ride_data.get("difficulty_rating_avg"),
            difficulty_rating_count=ride_data.get("difficulty_rating_count"),
            overall_rating_avg=ride_data.get("overall_rating_avg"),
            overall_rating_count=ride_data.get("overall_rating_count"),
            total_workouts=ride_data.get("total_workouts"),
            original_air_time=DataTransformer._parse_timestamp(ride_data.get("original_air_time")),
            scheduled_start_time=DataTransformer._parse_timestamp(ride_data.get("scheduled_start_time")),
            is_archived=ride_data.get("is_archived", False),
            is_explicit=ride_data.get("is_explicit", False),
            language=ride_data.get("language"),
            location=ride_data.get("location"),
            image_url=ride_data.get("image_url"),
        )
    
    @staticmethod
    def transform_workout_data(workout_data: Dict[str, Any]) -> Workout:
        """Transform workout data from API response to Workout model.
        
        Args:
            workout_data: Workout data from Peloton API
            
        Returns:
            Workout model instance
        """
        return Workout(
            id=workout_data["id"],
            user_id=workout_data.get("user_id"),
            ride_id=workout_data.get("ride", {}).get("id") if workout_data.get("ride") else None,
            name=workout_data.get("name"),
            status=workout_data.get("status", ""),
            fitness_discipline=workout_data.get("fitness_discipline", ""),
            workout_type=workout_data.get("workout_type"),
            device_type=workout_data.get("device_type"),
            device_type_display_name=workout_data.get("device_type_display_name"),
            platform=workout_data.get("platform"),
            start_time=DataTransformer._parse_timestamp(workout_data.get("start_time")),
            end_time=DataTransformer._parse_timestamp(workout_data.get("end_time")),
            created_at_peloton=DataTransformer._parse_timestamp(workout_data.get("created_at")),
            device_time_created_at=DataTransformer._parse_timestamp(workout_data.get("device_time_created_at")),
            timezone=workout_data.get("timezone"),
            total_work=workout_data.get("total_work"),
            leaderboard_rank=workout_data.get("leaderboard_rank"),
            total_leaderboard_users=workout_data.get("total_leaderboard_users"),
            is_total_work_personal_record=workout_data.get("is_total_work_personal_record", False),
            has_leaderboard_metrics=workout_data.get("has_leaderboard_metrics", False),
            has_pedaling_metrics=workout_data.get("has_pedaling_metrics", False),
            metrics_type=workout_data.get("metrics_type"),
            fitbit_id=workout_data.get("fitbit_id"),
            strava_id=workout_data.get("strava_id"),
            title=workout_data.get("title"),
        )

    @staticmethod
    def transform_performance_summary_data(
        workout_id: str,
        summary_data: Dict[str, Any]
    ) -> WorkoutPerformanceSummary:
        """Transform performance summary data to WorkoutPerformanceSummary model.

        Args:
            workout_id: Workout ID
            summary_data: Performance summary data from Peloton API

        Returns:
            WorkoutPerformanceSummary model instance
        """
        return WorkoutPerformanceSummary(
            workout_id=workout_id,
            avg_cadence=summary_data.get("avg_cadence"),
            avg_heart_rate=summary_data.get("avg_heart_rate"),
            avg_power=summary_data.get("avg_power"),
            avg_resistance=summary_data.get("avg_resistance"),
            avg_speed=summary_data.get("avg_speed"),
            max_cadence=summary_data.get("max_cadence"),
            max_heart_rate=summary_data.get("max_heart_rate"),
            max_power=summary_data.get("max_power"),
            max_resistance=summary_data.get("max_resistance"),
            max_speed=summary_data.get("max_speed"),
            total_work=summary_data.get("total_work"),
            calories=summary_data.get("calories"),
            distance=summary_data.get("distance"),
            seconds_since_pedaling_start=summary_data.get("seconds_since_pedaling_start"),
            instant=DataTransformer._parse_timestamp(summary_data.get("instant")),
        )

    @staticmethod
    def transform_performance_metrics_data(
        workout_id: str,
        metrics_data: List[Dict[str, Any]]
    ) -> List[WorkoutPerformanceMetric]:
        """Transform performance metrics data to WorkoutPerformanceMetric models.

        Args:
            workout_id: Workout ID
            metrics_data: List of performance metrics from Peloton API

        Returns:
            List of WorkoutPerformanceMetric model instances
        """
        metrics = []
        for metric_data in metrics_data:
            metric = WorkoutPerformanceMetric(
                workout_id=workout_id,
                seconds_since_pedaling_start=metric_data.get("seconds_since_pedaling_start", 0),
                cadence=metric_data.get("cadence"),
                heart_rate=metric_data.get("heart_rate"),
                power=metric_data.get("power"),
                resistance=metric_data.get("resistance"),
                speed=metric_data.get("speed"),
            )
            metrics.append(metric)
        return metrics

    @staticmethod
    def transform_achievement_data(
        workout_id: str,
        achievements_data: List[Dict[str, Any]]
    ) -> List[WorkoutAchievement]:
        """Transform achievement data to WorkoutAchievement models.

        Args:
            workout_id: Workout ID
            achievements_data: List of achievements from Peloton API

        Returns:
            List of WorkoutAchievement model instances
        """
        achievements = []
        for achievement_data in achievements_data:
            achievement = WorkoutAchievement(
                workout_id=workout_id,
                achievement_id=achievement_data.get("id", ""),
                name=achievement_data.get("name", ""),
                description=achievement_data.get("description"),
                slug=achievement_data.get("slug"),
                image_url=achievement_data.get("image_url"),
            )
            achievements.append(achievement)
        return achievements

    @staticmethod
    def extract_workout_components(
        workout_data: Dict[str, Any]
    ) -> Tuple[Optional[Instructor], Optional[Ride], Workout]:
        """Extract all components from a workout API response.

        Args:
            workout_data: Complete workout data from Peloton API

        Returns:
            Tuple of (instructor, ride, workout) model instances
        """
        instructor = None
        ride = None

        # Extract ride information if present
        ride_data = workout_data.get("ride")
        if ride_data:
            ride = DataTransformer.transform_ride_data(ride_data)

            # Extract instructor information if present in ride data
            instructor_data = ride_data.get("instructor")
            if instructor_data:
                instructor = DataTransformer.transform_instructor_data(instructor_data)

        # Transform workout data
        workout = DataTransformer.transform_workout_data(workout_data)

        return instructor, ride, workout

    @staticmethod
    def _parse_timestamp(timestamp: Optional[Any]) -> Optional[datetime]:
        """Parse timestamp from various formats to datetime object.

        Args:
            timestamp: Timestamp in various formats (int, str, or None)

        Returns:
            Parsed datetime object or None
        """
        if timestamp is None:
            return None

        try:
            # Handle Unix timestamp (int or float)
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)

            # Handle string timestamp
            if isinstance(timestamp, str):
                # Try parsing as ISO format first
                try:
                    parsed_dt = parse_date(timestamp)
                    # Ensure timezone awareness
                    if parsed_dt.tzinfo is None:
                        parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                    return parsed_dt
                except Exception:
                    # Try parsing as Unix timestamp string
                    try:
                        unix_timestamp = float(timestamp)
                        return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
                    except ValueError:
                        logger.warning("Failed to parse timestamp", timestamp=timestamp)
                        return None

            logger.warning("Unsupported timestamp format", timestamp=timestamp, type=type(timestamp))
            return None

        except Exception as e:
            logger.error("Error parsing timestamp", timestamp=timestamp, error=str(e))
            return None

    @staticmethod
    def _safe_get_nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        """Safely get nested dictionary values.

        Args:
            data: Dictionary to search
            *keys: Nested keys to traverse
            default: Default value if key not found

        Returns:
            Value at nested key or default
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
