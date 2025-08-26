#!/usr/bin/env python3
"""
Performance analysis example using synchronized Peloton data.

This example demonstrates:
1. Querying performance data from the database
2. Analyzing workout trends
3. Generating performance insights
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the parent directory to the path so we can import peloton_sync
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from peloton_sync.database import get_db_session
from peloton_sync.models import (
    Workout, WorkoutPerformanceSummary, WorkoutPerformanceMetric,
    Ride, Instructor
)
from peloton_sync.logging_config import setup_logging, get_logger
from sqlalchemy import func, and_

# Setup logging
setup_logging()
logger = get_logger(__name__)


def main():
    """Run the performance analysis example."""
    logger.info("Starting Peloton performance analysis example")
    
    try:
        # Analyze recent cycling workouts
        analyze_cycling_performance()
        
        # Analyze workout frequency
        analyze_workout_frequency()
        
        # Analyze favorite instructors
        analyze_favorite_instructors()
        
        # Analyze performance trends
        analyze_performance_trends()
        
        return 0
        
    except Exception as e:
        logger.error("Performance analysis failed", error=str(e))
        return 1


def analyze_cycling_performance():
    """Analyze cycling workout performance."""
    logger.info("Analyzing cycling workout performance")
    
    with get_db_session() as session:
        # Get cycling workouts with performance summaries
        cycling_workouts = session.query(
            Workout, WorkoutPerformanceSummary
        ).join(
            WorkoutPerformanceSummary,
            Workout.id == WorkoutPerformanceSummary.workout_id
        ).filter(
            and_(
                Workout.fitness_discipline == "cycling",
                Workout.status == "COMPLETE"
            )
        ).order_by(Workout.start_time.desc()).limit(20).all()
        
        if not cycling_workouts:
            logger.info("No cycling workouts with performance data found")
            return
        
        logger.info("Found cycling workouts", count=len(cycling_workouts))
        
        # Calculate performance statistics
        total_work_values = [summary.total_work for _, summary in cycling_workouts if summary.total_work]
        avg_power_values = [summary.avg_power for _, summary in cycling_workouts if summary.avg_power]
        avg_cadence_values = [summary.avg_cadence for _, summary in cycling_workouts if summary.avg_cadence]
        
        if total_work_values:
            avg_total_work = sum(total_work_values) / len(total_work_values)
            max_total_work = max(total_work_values)
            logger.info("Total work statistics", 
                       avg=round(avg_total_work, 2),
                       max=round(max_total_work, 2),
                       count=len(total_work_values))
        
        if avg_power_values:
            avg_power = sum(avg_power_values) / len(avg_power_values)
            max_power = max(avg_power_values)
            logger.info("Power statistics",
                       avg=round(avg_power, 2),
                       max=round(max_power, 2),
                       count=len(avg_power_values))
        
        if avg_cadence_values:
            avg_cadence = sum(avg_cadence_values) / len(avg_cadence_values)
            max_cadence = max(avg_cadence_values)
            logger.info("Cadence statistics",
                       avg=round(avg_cadence, 2),
                       max=round(max_cadence, 2),
                       count=len(avg_cadence_values))


def analyze_workout_frequency():
    """Analyze workout frequency patterns."""
    logger.info("Analyzing workout frequency")
    
    with get_db_session() as session:
        # Get workouts from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        recent_workouts = session.query(Workout).filter(
            and_(
                Workout.start_time >= thirty_days_ago,
                Workout.status == "COMPLETE"
            )
        ).order_by(Workout.start_time.desc()).all()
        
        if not recent_workouts:
            logger.info("No recent workouts found")
            return
        
        logger.info("Recent workouts analysis", 
                   total_workouts=len(recent_workouts),
                   period_days=30)
        
        # Group by fitness discipline
        discipline_counts = {}
        for workout in recent_workouts:
            discipline = workout.fitness_discipline
            discipline_counts[discipline] = discipline_counts.get(discipline, 0) + 1
        
        logger.info("Workouts by discipline", **discipline_counts)
        
        # Calculate weekly average
        weekly_avg = len(recent_workouts) / 4.3  # Approximate weeks in 30 days
        logger.info("Weekly workout average", avg=round(weekly_avg, 1))


def analyze_favorite_instructors():
    """Analyze favorite instructors based on workout count."""
    logger.info("Analyzing favorite instructors")
    
    with get_db_session() as session:
        # Get instructor workout counts
        instructor_stats = session.query(
            Instructor.name,
            func.count(Workout.id).label('workout_count'),
            func.avg(WorkoutPerformanceSummary.total_work).label('avg_total_work')
        ).join(
            Ride, Instructor.id == Ride.instructor_id
        ).join(
            Workout, Ride.id == Workout.ride_id
        ).outerjoin(
            WorkoutPerformanceSummary, 
            Workout.id == WorkoutPerformanceSummary.workout_id
        ).filter(
            Workout.status == "COMPLETE"
        ).group_by(
            Instructor.id, Instructor.name
        ).order_by(
            func.count(Workout.id).desc()
        ).limit(10).all()
        
        if not instructor_stats:
            logger.info("No instructor data found")
            return
        
        logger.info("Top instructors by workout count")
        for name, workout_count, avg_total_work in instructor_stats:
            avg_work_str = f"{avg_total_work:.0f}" if avg_total_work else "N/A"
            logger.info("Instructor stats",
                       name=name,
                       workout_count=workout_count,
                       avg_total_work=avg_work_str)


def analyze_performance_trends():
    """Analyze performance trends over time."""
    logger.info("Analyzing performance trends")
    
    with get_db_session() as session:
        # Get cycling workouts with performance data over time
        cycling_performance = session.query(
            Workout.start_time,
            WorkoutPerformanceSummary.total_work,
            WorkoutPerformanceSummary.avg_power,
            WorkoutPerformanceSummary.avg_cadence
        ).join(
            WorkoutPerformanceSummary,
            Workout.id == WorkoutPerformanceSummary.workout_id
        ).filter(
            and_(
                Workout.fitness_discipline == "cycling",
                Workout.status == "COMPLETE",
                WorkoutPerformanceSummary.total_work.isnot(None)
            )
        ).order_by(Workout.start_time.asc()).all()
        
        if len(cycling_performance) < 2:
            logger.info("Insufficient data for trend analysis")
            return
        
        logger.info("Performance trend analysis", data_points=len(cycling_performance))
        
        # Calculate trend for total work
        first_half = cycling_performance[:len(cycling_performance)//2]
        second_half = cycling_performance[len(cycling_performance)//2:]
        
        first_half_avg = sum(row.total_work for row in first_half if row.total_work) / len(first_half)
        second_half_avg = sum(row.total_work for row in second_half if row.total_work) / len(second_half)
        
        trend_change = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        logger.info("Total work trend",
                   first_half_avg=round(first_half_avg, 2),
                   second_half_avg=round(second_half_avg, 2),
                   change_percent=round(trend_change, 1))
        
        # Find personal records
        max_work_row = max(cycling_performance, key=lambda x: x.total_work or 0)
        max_power_row = max(cycling_performance, key=lambda x: x.avg_power or 0)
        
        logger.info("Personal records",
                   max_total_work=round(max_work_row.total_work, 2),
                   max_work_date=max_work_row.start_time.date().isoformat(),
                   max_avg_power=round(max_power_row.avg_power, 2) if max_power_row.avg_power else "N/A",
                   max_power_date=max_power_row.start_time.date().isoformat())


if __name__ == "__main__":
    sys.exit(main())
