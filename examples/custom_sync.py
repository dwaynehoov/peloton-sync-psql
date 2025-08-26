#!/usr/bin/env python3
"""
Custom synchronization example showing advanced usage.

This example demonstrates:
1. Custom API client usage
2. Selective data synchronization
3. Custom data processing
4. Error handling and recovery
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add the parent directory to the path so we can import peloton_sync
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from peloton_sync.api_client import PelotonAPIClient
from peloton_sync.data_loader import DataLoader
from peloton_sync.data_transformer import DataTransformer
from peloton_sync.database import get_db_session
from peloton_sync.models import Workout, SyncLog
from peloton_sync.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


class CustomPelotonSync:
    """Custom synchronization class with advanced features."""
    
    def __init__(self):
        """Initialize the custom sync."""
        self.api_client = None
        self.data_loader = None
        self.transformer = DataTransformer()
    
    def initialize(self) -> bool:
        """Initialize the sync components."""
        try:
            self.api_client = PelotonAPIClient()
            if not self.api_client.authenticate():
                logger.error("Authentication failed")
                return False
            
            self.data_loader = DataLoader(self.api_client)
            logger.info("Custom sync initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Initialization failed", error=str(e))
            return False
    
    def sync_recent_cycling_workouts(self, days: int = 7) -> Dict[str, Any]:
        """Sync only recent cycling workouts.
        
        Args:
            days: Number of days back to sync
            
        Returns:
            Sync statistics
        """
        logger.info("Syncing recent cycling workouts", days=days)
        
        stats = {"processed": 0, "created": 0, "updated": 0, "errors": 0}
        
        with get_db_session() as session:
            try:
                # Sync user data first
                user = self.data_loader.sync_user_data(session)
                
                # Get all workouts and filter for recent cycling
                all_workouts = self.api_client.get_user_workouts(
                    limit=200,  # Get more to ensure we capture recent ones
                    joins="ride,ride.instructor"
                )
                
                cutoff_date = datetime.now() - timedelta(days=days)
                recent_cycling_workouts = []
                
                for workout_data in all_workouts.get("data", []):
                    # Check if it's a cycling workout
                    if workout_data.get("fitness_discipline") != "cycling":
                        continue
                    
                    # Check if it's recent
                    start_time = workout_data.get("start_time")
                    if start_time:
                        workout_date = datetime.fromtimestamp(start_time)
                        if workout_date < cutoff_date:
                            continue
                    
                    recent_cycling_workouts.append(workout_data)
                
                logger.info("Found recent cycling workouts", count=len(recent_cycling_workouts))
                stats["processed"] = len(recent_cycling_workouts)
                
                # Process each workout
                for workout_data in recent_cycling_workouts:
                    try:
                        success = self._process_single_workout(session, workout_data)
                        if success:
                            stats["created"] += 1
                        else:
                            stats["updated"] += 1
                        
                        session.commit()
                        
                    except Exception as e:
                        logger.error("Failed to process workout", 
                                   workout_id=workout_data.get("id"), 
                                   error=str(e))
                        stats["errors"] += 1
                        session.rollback()
                
                # Create sync log
                self.data_loader.create_sync_log(
                    session, user.id, "custom_cycling", "success", stats
                )
                session.commit()
                
            except Exception as e:
                logger.error("Sync failed", error=str(e))
                stats["errors"] += 1
                session.rollback()
        
        logger.info("Custom cycling sync completed", stats=stats)
        return stats
    
    def _process_single_workout(self, session, workout_data: Dict[str, Any]) -> bool:
        """Process a single workout with custom logic.
        
        Args:
            session: Database session
            workout_data: Workout data from API
            
        Returns:
            True if workout was created, False if updated
        """
        # Extract components
        instructor, ride, workout = self.transformer.extract_workout_components(workout_data)
        
        # Upsert instructor and ride
        if instructor:
            self.data_loader.upsert_instructor(session, instructor)
        
        if ride:
            self.data_loader.upsert_ride(session, ride)
        
        # Upsert workout
        workout, is_new = self.data_loader.upsert_workout(session, workout)
        
        # Only sync performance data for high-intensity cycling workouts
        if (workout.fitness_discipline == "cycling" and 
            workout.status == "COMPLETE" and
            workout.has_pedaling_metrics and
            self._is_high_intensity_workout(workout_data)):
            
            logger.info("Syncing performance data for high-intensity workout", 
                       workout_id=workout.id)
            self.data_loader.sync_workout_performance_data(session, workout.id)
        
        # Sync achievements
        self.data_loader.sync_workout_achievements(session, workout_data)
        
        return is_new
    
    def _is_high_intensity_workout(self, workout_data: Dict[str, Any]) -> bool:
        """Determine if a workout is high intensity based on various factors.
        
        Args:
            workout_data: Workout data from API
            
        Returns:
            True if workout is considered high intensity
        """
        # Check ride difficulty
        ride_data = workout_data.get("ride", {})
        difficulty = ride_data.get("difficulty_estimate", 0)
        
        # Check workout duration (longer workouts get performance data)
        duration = ride_data.get("duration", 0)
        
        # Check if it's a power zone or HIIT class
        title = ride_data.get("title", "").lower()
        high_intensity_keywords = ["power zone", "hiit", "tabata", "intervals", "climb"]
        
        is_high_intensity = (
            difficulty >= 7.0 or  # High difficulty
            duration >= 1800 or   # 30+ minutes
            any(keyword in title for keyword in high_intensity_keywords)
        )
        
        return is_high_intensity
    
    def sync_missing_performance_data(self) -> Dict[str, Any]:
        """Sync performance data for workouts that don't have it yet."""
        logger.info("Syncing missing performance data")
        
        stats = {"processed": 0, "success": 0, "errors": 0}
        
        with get_db_session() as session:
            # Find cycling workouts without performance summaries
            workouts_without_perf = session.query(Workout).filter(
                Workout.fitness_discipline == "cycling",
                Workout.status == "COMPLETE",
                Workout.has_pedaling_metrics == True,
                ~Workout.performance_summary.has()  # No performance summary
            ).limit(50).all()  # Limit to avoid overwhelming the API
            
            logger.info("Found workouts without performance data", 
                       count=len(workouts_without_perf))
            stats["processed"] = len(workouts_without_perf)
            
            for workout in workouts_without_perf:
                try:
                    self.data_loader.sync_workout_performance_data(session, workout.id)
                    stats["success"] += 1
                    session.commit()
                    
                    # Add small delay to be respectful to the API
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error("Failed to sync performance data", 
                               workout_id=workout.id, error=str(e))
                    stats["errors"] += 1
                    session.rollback()
        
        logger.info("Missing performance data sync completed", stats=stats)
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        if self.api_client:
            self.api_client.close()


def main():
    """Run the custom sync example."""
    logger.info("Starting custom Peloton sync example")
    
    sync = CustomPelotonSync()
    
    try:
        if not sync.initialize():
            logger.error("Failed to initialize custom sync")
            return 1
        
        # Sync recent cycling workouts (last 14 days)
        cycling_stats = sync.sync_recent_cycling_workouts(days=14)
        logger.info("Cycling sync results", **cycling_stats)
        
        # Sync missing performance data
        perf_stats = sync.sync_missing_performance_data()
        logger.info("Performance data sync results", **perf_stats)
        
        logger.info("Custom sync completed successfully")
        return 0
        
    except Exception as e:
        logger.error("Custom sync failed", error=str(e))
        return 1
    
    finally:
        sync.cleanup()


if __name__ == "__main__":
    sys.exit(main())
