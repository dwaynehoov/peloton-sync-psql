"""Data loading and synchronization logic for Peloton workout data."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, desc

from .models import (
    User, Instructor, Ride, Workout, WorkoutPerformanceSummary,
    WorkoutPerformanceMetric, WorkoutAchievement, SyncLog
)
from .database import get_db_session
from .data_transformer import DataTransformer
from .api_client import PelotonAPIClient
from .logging_config import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Handles loading and synchronizing Peloton data to the database."""
    
    def __init__(self, api_client: PelotonAPIClient):
        """Initialize data loader.
        
        Args:
            api_client: Authenticated Peloton API client
        """
        self.api_client = api_client
        self.transformer = DataTransformer()
    
    def sync_user_data(self, session: Session) -> User:
        """Sync current user data to database.
        
        Args:
            session: Database session
            
        Returns:
            User model instance
        """
        logger.info("Syncing user data")
        
        # Get user data from API
        user_data = self.api_client.get_user_info()
        user = self.transformer.transform_user_data(user_data)
        
        # Upsert user data
        existing_user = session.query(User).filter(User.id == user.id).first()
        if existing_user:
            # Update existing user
            for key, value in user.__dict__.items():
                if not key.startswith('_') and key != 'id':
                    setattr(existing_user, key, value)
            existing_user.updated_at = datetime.now(timezone.utc)
            user = existing_user
            logger.info("Updated existing user", user_id=user.id)
        else:
            # Create new user
            session.add(user)
            logger.info("Created new user", user_id=user.id)
        
        session.flush()
        return user
    
    def upsert_instructor(self, session: Session, instructor: Instructor) -> Instructor:
        """Upsert instructor data to database.
        
        Args:
            session: Database session
            instructor: Instructor model instance
            
        Returns:
            Instructor model instance (existing or new)
        """
        existing = session.query(Instructor).filter(Instructor.id == instructor.id).first()
        if existing:
            # Update existing instructor
            for key, value in instructor.__dict__.items():
                if not key.startswith('_') and key not in ['id', 'created_at']:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            return existing
        else:
            # Create new instructor
            session.add(instructor)
            return instructor
    
    def upsert_ride(self, session: Session, ride: Ride) -> Ride:
        """Upsert ride data to database.
        
        Args:
            session: Database session
            ride: Ride model instance
            
        Returns:
            Ride model instance (existing or new)
        """
        existing = session.query(Ride).filter(Ride.id == ride.id).first()
        if existing:
            # Update existing ride
            for key, value in ride.__dict__.items():
                if not key.startswith('_') and key not in ['id', 'created_at']:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            return existing
        else:
            # Create new ride
            session.add(ride)
            return ride
    
    def upsert_workout(self, session: Session, workout: Workout) -> Tuple[Workout, bool]:
        """Upsert workout data to database.
        
        Args:
            session: Database session
            workout: Workout model instance
            
        Returns:
            Tuple of (workout instance, is_new)
        """
        existing = session.query(Workout).filter(Workout.id == workout.id).first()
        if existing:
            # Update existing workout
            for key, value in workout.__dict__.items():
                if not key.startswith('_') and key not in ['id', 'created_at']:
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            return existing, False
        else:
            # Create new workout
            session.add(workout)
            return workout, True
    
    def sync_workout_performance_data(self, session: Session, workout_id: str) -> None:
        """Sync performance data for a specific workout.
        
        Args:
            session: Database session
            workout_id: Workout ID to sync performance data for
        """
        logger.info("Syncing performance data", workout_id=workout_id)
        
        try:
            # Get performance graph data
            perf_data = self.api_client.get_workout_performance_graph(workout_id)
            
            # Process performance summary if available
            summary_data = perf_data.get("summaries", [])
            if summary_data:
                # Usually there's one summary at the end
                final_summary = summary_data[-1] if summary_data else {}
                if final_summary:
                    perf_summary = self.transformer.transform_performance_summary_data(
                        workout_id, final_summary
                    )
                    
                    # Upsert performance summary
                    existing_summary = session.query(WorkoutPerformanceSummary).filter(
                        WorkoutPerformanceSummary.workout_id == workout_id
                    ).first()
                    
                    if existing_summary:
                        for key, value in perf_summary.__dict__.items():
                            if not key.startswith('_') and key not in ['id', 'created_at']:
                                setattr(existing_summary, key, value)
                        existing_summary.updated_at = datetime.now(timezone.utc)
                    else:
                        session.add(perf_summary)
            
            # Process time-series metrics
            metrics_data = perf_data.get("metrics", [])
            if metrics_data:
                # Clear existing metrics for this workout
                session.query(WorkoutPerformanceMetric).filter(
                    WorkoutPerformanceMetric.workout_id == workout_id
                ).delete()
                
                # Add new metrics
                metrics = self.transformer.transform_performance_metrics_data(
                    workout_id, metrics_data
                )
                session.add_all(metrics)
                
                logger.info("Synced performance metrics", 
                           workout_id=workout_id, metrics_count=len(metrics))
            
        except Exception as e:
            logger.error("Failed to sync performance data",
                        workout_id=workout_id, error=str(e))
            # Don't raise - performance data is optional

    def sync_workout_achievements(self, session: Session, workout_data: Dict[str, Any]) -> None:
        """Sync achievement data for a workout.

        Args:
            session: Database session
            workout_data: Workout data containing achievements
        """
        workout_id = workout_data.get("id")
        if not workout_id:
            return

        achievements_data = workout_data.get("achievement_templates", [])
        if not achievements_data:
            return

        logger.info("Syncing achievements", workout_id=workout_id, count=len(achievements_data))

        # Clear existing achievements for this workout
        session.query(WorkoutAchievement).filter(
            WorkoutAchievement.workout_id == workout_id
        ).delete()

        # Add new achievements
        achievements = self.transformer.transform_achievement_data(
            workout_id, achievements_data
        )
        session.add_all(achievements)

    def sync_workouts(self, session: Session, user_id: str, limit: int = 100,
                     include_performance: bool = True) -> Dict[str, int]:
        """Sync user workouts to database.

        Args:
            session: Database session
            user_id: User ID to sync workouts for
            limit: Maximum number of workouts to sync
            include_performance: Whether to include performance data

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Syncing workouts", user_id=user_id, limit=limit)

        stats = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "errors": 0
        }

        try:
            # Get workouts from API
            workouts_data = self.api_client.get_user_workouts(
                limit=limit,
                joins="ride,ride.instructor"
            )

            workouts = workouts_data.get("data", [])
            stats["processed"] = len(workouts)

            for workout_data in workouts:
                try:
                    # Extract components
                    instructor, ride, workout = self.transformer.extract_workout_components(workout_data)

                    # Upsert instructor if present
                    if instructor:
                        self.upsert_instructor(session, instructor)

                    # Upsert ride if present
                    if ride:
                        self.upsert_ride(session, ride)

                    # Upsert workout
                    workout, is_new = self.upsert_workout(session, workout)
                    if is_new:
                        stats["created"] += 1
                    else:
                        stats["updated"] += 1

                    # Sync achievements
                    self.sync_workout_achievements(session, workout_data)

                    # Sync performance data if requested and workout is complete
                    if (include_performance and
                        workout.status == "COMPLETE" and
                        workout.has_pedaling_metrics):
                        self.sync_workout_performance_data(session, workout.id)

                    # Commit after each workout to avoid large transactions
                    session.commit()

                except Exception as e:
                    logger.error("Failed to sync workout",
                               workout_id=workout_data.get("id"), error=str(e))
                    stats["errors"] += 1
                    session.rollback()

        except Exception as e:
            logger.error("Failed to sync workouts", user_id=user_id, error=str(e))
            stats["errors"] += 1
            session.rollback()

        logger.info("Workout sync completed", user_id=user_id, stats=stats)
        return stats

    def create_sync_log(self, session: Session, user_id: str, sync_type: str,
                       status: str, stats: Dict[str, int],
                       error_message: Optional[str] = None) -> SyncLog:
        """Create a sync log entry.

        Args:
            session: Database session
            user_id: User ID
            sync_type: Type of sync (full, incremental)
            status: Sync status (success, error, partial)
            stats: Sync statistics
            error_message: Error message if applicable

        Returns:
            SyncLog model instance
        """
        sync_log = SyncLog(
            user_id=user_id,
            sync_type=sync_type,
            status=status,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            workouts_processed=stats.get("processed", 0),
            workouts_created=stats.get("created", 0),
            workouts_updated=stats.get("updated", 0),
            errors_count=stats.get("errors", 0),
            error_message=error_message,
        )

        session.add(sync_log)
        return sync_log

    def get_last_sync_time(self, session: Session, user_id: str) -> Optional[datetime]:
        """Get the timestamp of the last successful sync for a user.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            Datetime of last successful sync or None
        """
        last_sync = session.query(SyncLog).filter(
            and_(
                SyncLog.user_id == user_id,
                SyncLog.status == "success"
            )
        ).order_by(desc(SyncLog.completed_at)).first()

        return last_sync.completed_at if last_sync else None

    def full_sync(self, user_id: Optional[str] = None,
                  max_workouts: int = 100,
                  include_performance: bool = True) -> Dict[str, Any]:
        """Perform a full data synchronization.

        Args:
            user_id: User ID to sync (if None, uses authenticated user)
            max_workouts: Maximum number of workouts to sync
            include_performance: Whether to include performance data

        Returns:
            Dictionary with sync results
        """
        logger.info("Starting full sync", max_workouts=max_workouts)

        with get_db_session() as session:
            try:
                # Sync user data
                user = self.sync_user_data(session)
                target_user_id = user_id or user.id

                # Sync workouts
                stats = self.sync_workouts(
                    session,
                    target_user_id,
                    limit=max_workouts,
                    include_performance=include_performance
                )

                # Determine sync status
                status = "success"
                if stats["errors"] > 0:
                    status = "partial" if stats["created"] + stats["updated"] > 0 else "error"

                # Create sync log
                sync_log = self.create_sync_log(
                    session, target_user_id, "full", status, stats
                )

                session.commit()

                result = {
                    "status": status,
                    "user_id": target_user_id,
                    "stats": stats,
                    "sync_log_id": sync_log.id
                }

                logger.info("Full sync completed", result=result)
                return result

            except Exception as e:
                logger.error("Full sync failed", error=str(e))
                session.rollback()
                raise
