#!/usr/bin/env python3
"""
Basic example of using the Peloton Data Sync application.

This example demonstrates:
1. Setting up the application
2. Performing a basic data sync
3. Querying the synchronized data
"""

import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import peloton_sync
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from peloton_sync.main import PelotonDataSync
from peloton_sync.database import get_db_session
from peloton_sync.models import User, Workout, Ride, Instructor
from peloton_sync.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def main():
    """Run the basic sync example."""
    logger.info("Starting basic Peloton data sync example")
    
    # Initialize the application
    app = PelotonDataSync()
    
    try:
        # Initialize application components
        if not app.initialize():
            logger.error("Failed to initialize application")
            return 1
        
        logger.info("Application initialized successfully")
        
        # Perform a sync with limited workouts for demonstration
        logger.info("Starting data synchronization (limited to 10 workouts)")
        success = app.sync_data(max_workouts=10, include_performance=True)
        
        if not success:
            logger.error("Data synchronization failed")
            return 1
        
        logger.info("Data synchronization completed successfully")
        
        # Query and display some of the synchronized data
        display_sync_results()
        
        return 0
        
    except Exception as e:
        logger.error("Example failed", error=str(e))
        return 1
    
    finally:
        # Clean up resources
        app.cleanup()


def display_sync_results():
    """Display some of the synchronized data."""
    logger.info("Displaying synchronized data")
    
    with get_db_session() as session:
        # Get user information
        user = session.query(User).first()
        if user:
            logger.info("User information", 
                       username=user.username,
                       first_name=user.first_name,
                       last_name=user.last_name)
        
        # Get recent workouts
        recent_workouts = session.query(Workout).order_by(
            Workout.start_time.desc()
        ).limit(5).all()
        
        logger.info("Recent workouts", count=len(recent_workouts))
        
        for workout in recent_workouts:
            # Get associated ride and instructor information
            ride = session.query(Ride).filter(Ride.id == workout.ride_id).first()
            instructor = None
            if ride and ride.instructor_id:
                instructor = session.query(Instructor).filter(
                    Instructor.id == ride.instructor_id
                ).first()
            
            workout_info = {
                "id": workout.id,
                "fitness_discipline": workout.fitness_discipline,
                "start_time": workout.start_time.isoformat() if workout.start_time else None,
                "status": workout.status,
                "total_work": workout.total_work,
                "leaderboard_rank": workout.leaderboard_rank,
                "ride_title": ride.title if ride else None,
                "instructor_name": instructor.name if instructor else None,
            }
            
            logger.info("Workout details", **workout_info)
        
        # Get instructor count
        instructor_count = session.query(Instructor).count()
        logger.info("Total instructors synchronized", count=instructor_count)
        
        # Get ride count by discipline
        disciplines = session.query(Workout.fitness_discipline).distinct().all()
        for (discipline,) in disciplines:
            count = session.query(Workout).filter(
                Workout.fitness_discipline == discipline
            ).count()
            logger.info("Workouts by discipline", discipline=discipline, count=count)


if __name__ == "__main__":
    sys.exit(main())
