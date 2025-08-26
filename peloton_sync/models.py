"""SQLAlchemy models for Peloton workout data."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """Peloton user information."""
    
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # Peloton user ID
    username = Column(String, nullable=False)
    email = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    location = Column(String)
    timezone = Column(String)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    workouts = relationship("Workout", back_populates="user")
    
    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
    )


class Instructor(Base):
    """Peloton instructor information."""
    
    __tablename__ = "instructors"
    
    id = Column(String, primary_key=True)  # Peloton instructor ID
    name = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    bio = Column(Text)
    image_url = Column(String)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    rides = relationship("Ride", back_populates="instructor")
    
    __table_args__ = (
        Index("idx_instructors_name", "name"),
    )


class Ride(Base):
    """Peloton ride/class information."""
    
    __tablename__ = "rides"
    
    id = Column(String, primary_key=True)  # Peloton ride ID
    title = Column(String, nullable=False)
    description = Column(Text)
    instructor_id = Column(String, ForeignKey("instructors.id"))
    fitness_discipline = Column(String, nullable=False)  # cycling, running, etc.
    fitness_discipline_display_name = Column(String)
    duration = Column(Integer)  # Duration in seconds
    difficulty_estimate = Column(Float)
    difficulty_rating_avg = Column(Float)
    difficulty_rating_count = Column(Integer)
    overall_rating_avg = Column(Float)
    overall_rating_count = Column(Integer)
    total_workouts = Column(Integer)
    original_air_time = Column(DateTime)
    scheduled_start_time = Column(DateTime)
    is_archived = Column(Boolean, default=False)
    is_explicit = Column(Boolean, default=False)
    language = Column(String)
    location = Column(String)
    image_url = Column(String)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    instructor = relationship("Instructor", back_populates="rides")
    workouts = relationship("Workout", back_populates="ride")
    
    __table_args__ = (
        Index("idx_rides_fitness_discipline", "fitness_discipline"),
        Index("idx_rides_instructor_id", "instructor_id"),
        Index("idx_rides_original_air_time", "original_air_time"),
    )


class Workout(Base):
    """User workout sessions."""

    __tablename__ = "workouts"

    id = Column(String, primary_key=True)  # Peloton workout ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    ride_id = Column(String, ForeignKey("rides.id"))
    name = Column(String)
    status = Column(String, nullable=False)  # COMPLETE, IN_PROGRESS, etc.
    fitness_discipline = Column(String, nullable=False)
    workout_type = Column(String)  # class, just_ride, etc.
    device_type = Column(String)
    device_type_display_name = Column(String)
    platform = Column(String)

    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    created_at_peloton = Column(DateTime, nullable=False)
    device_time_created_at = Column(DateTime)
    timezone = Column(String)

    # Performance summary
    total_work = Column(Float)
    leaderboard_rank = Column(Integer)
    total_leaderboard_users = Column(Integer)
    is_total_work_personal_record = Column(Boolean, default=False)

    # Metrics flags
    has_leaderboard_metrics = Column(Boolean, default=False)
    has_pedaling_metrics = Column(Boolean, default=False)
    metrics_type = Column(String)

    # External integrations
    fitbit_id = Column(String)
    strava_id = Column(String)

    # Metadata
    title = Column(String)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="workouts")
    ride = relationship("Ride", back_populates="workouts")
    performance_summary = relationship("WorkoutPerformanceSummary", back_populates="workout", uselist=False)
    performance_metrics = relationship("WorkoutPerformanceMetric", back_populates="workout")
    achievements = relationship("WorkoutAchievement", back_populates="workout")

    __table_args__ = (
        Index("idx_workouts_user_id", "user_id"),
        Index("idx_workouts_ride_id", "ride_id"),
        Index("idx_workouts_start_time", "start_time"),
        Index("idx_workouts_fitness_discipline", "fitness_discipline"),
        Index("idx_workouts_status", "status"),
    )


class WorkoutPerformanceSummary(Base):
    """Overall performance summary for a workout."""

    __tablename__ = "workout_performance_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(String, ForeignKey("workouts.id"), nullable=False, unique=True)

    # Averages
    avg_cadence = Column(Float)
    avg_heart_rate = Column(Float)
    avg_power = Column(Float)
    avg_resistance = Column(Float)
    avg_speed = Column(Float)

    # Maximums
    max_cadence = Column(Float)
    max_heart_rate = Column(Float)
    max_power = Column(Float)
    max_resistance = Column(Float)
    max_speed = Column(Float)

    # Totals
    total_work = Column(Float)
    calories = Column(Float)
    distance = Column(Float)

    # Timing
    seconds_since_pedaling_start = Column(Integer)
    instant = Column(DateTime)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    workout = relationship("Workout", back_populates="performance_summary")

    __table_args__ = (
        Index("idx_performance_summary_workout_id", "workout_id"),
    )


class WorkoutPerformanceMetric(Base):
    """Time-series performance metrics for a workout."""

    __tablename__ = "workout_performance_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(String, ForeignKey("workouts.id"), nullable=False)

    # Time offset from workout start
    seconds_since_pedaling_start = Column(Integer, nullable=False)

    # Metrics
    cadence = Column(Float)
    heart_rate = Column(Float)
    power = Column(Float)
    resistance = Column(Float)
    speed = Column(Float)

    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    workout = relationship("Workout", back_populates="performance_metrics")

    __table_args__ = (
        Index("idx_performance_metrics_workout_id", "workout_id"),
        Index("idx_performance_metrics_time", "workout_id", "seconds_since_pedaling_start"),
        UniqueConstraint("workout_id", "seconds_since_pedaling_start", name="uq_workout_metric_time"),
    )


class WorkoutAchievement(Base):
    """Achievements earned during workouts."""

    __tablename__ = "workout_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(String, ForeignKey("workouts.id"), nullable=False)

    # Achievement details
    achievement_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    slug = Column(String)
    image_url = Column(String)

    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    workout = relationship("Workout", back_populates="achievements")

    __table_args__ = (
        Index("idx_achievements_workout_id", "workout_id"),
        Index("idx_achievements_achievement_id", "achievement_id"),
        UniqueConstraint("workout_id", "achievement_id", name="uq_workout_achievement"),
    )


class SyncLog(Base):
    """Log of data synchronization operations."""

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Sync details
    sync_type = Column(String, nullable=False)  # full, incremental
    status = Column(String, nullable=False)  # success, error, partial
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    # Statistics
    workouts_processed = Column(Integer, default=0)
    workouts_created = Column(Integer, default=0)
    workouts_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Error details
    error_message = Column(Text)
    error_details = Column(JSON)

    created_at = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        Index("idx_sync_logs_user_id", "user_id"),
        Index("idx_sync_logs_started_at", "started_at"),
        Index("idx_sync_logs_status", "status"),
    )
