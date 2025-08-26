"""Main application entry point for Peloton Data Sync."""

import sys
import argparse
from typing import Optional
from datetime import datetime

from .logging_config import setup_logging, get_logger
from .config import get_config
from .database import init_database, test_database_connection
from .api_client import PelotonAPIClient, PelotonAuthenticationError
from .data_loader import DataLoader

# Setup logging first
setup_logging()
logger = get_logger(__name__)


class PelotonDataSync:
    """Main application class for Peloton data synchronization."""
    
    def __init__(self):
        """Initialize the application."""
        self.app_config, self.db_config, self.peloton_config = get_config()
        self.api_client: Optional[PelotonAPIClient] = None
        self.data_loader: Optional[DataLoader] = None
    
    def initialize(self) -> bool:
        """Initialize the application components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        logger.info("Initializing Peloton Data Sync application")
        
        try:
            # Test database connection
            if not test_database_connection():
                logger.error("Database connection test failed")
                return False
            
            # Initialize database tables
            init_database()
            logger.info("Database initialized successfully")
            
            # Initialize API client
            self.api_client = PelotonAPIClient()
            
            # Test API authentication
            if not self.api_client.authenticate():
                logger.error("Peloton API authentication failed")
                return False
            
            # Initialize data loader
            self.data_loader = DataLoader(self.api_client)
            
            logger.info("Application initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Application initialization failed", error=str(e))
            return False
    
    def sync_data(self, max_workouts: Optional[int] = None, 
                  include_performance: bool = True) -> bool:
        """Synchronize Peloton data to database.
        
        Args:
            max_workouts: Maximum number of workouts to sync
            include_performance: Whether to include performance data
            
        Returns:
            True if sync successful, False otherwise
        """
        if not self.data_loader:
            logger.error("Data loader not initialized")
            return False
        
        max_workouts = max_workouts or self.app_config.max_workouts_per_sync
        include_performance = include_performance and self.app_config.include_performance_data
        
        logger.info("Starting data synchronization", 
                   max_workouts=max_workouts, 
                   include_performance=include_performance)
        
        try:
            result = self.data_loader.full_sync(
                max_workouts=max_workouts,
                include_performance=include_performance
            )
            
            if result["status"] == "success":
                logger.info("Data synchronization completed successfully", result=result)
                return True
            elif result["status"] == "partial":
                logger.warning("Data synchronization completed with errors", result=result)
                return True
            else:
                logger.error("Data synchronization failed", result=result)
                return False
                
        except Exception as e:
            logger.error("Data synchronization failed", error=str(e))
            return False
    
    def cleanup(self) -> None:
        """Clean up application resources."""
        if self.api_client:
            self.api_client.close()
        logger.info("Application cleanup completed")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Peloton Data Sync - Sync your Peloton workout data to PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sync                    # Sync with default settings
  %(prog)s sync --max-workouts 50  # Sync up to 50 workouts
  %(prog)s sync --no-performance   # Sync without performance data
  %(prog)s test-db                 # Test database connection
  %(prog)s test-api                # Test API authentication
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Synchronize Peloton data")
    sync_parser.add_argument(
        "--max-workouts", 
        type=int, 
        help="Maximum number of workouts to sync"
    )
    sync_parser.add_argument(
        "--no-performance", 
        action="store_true", 
        help="Skip performance data synchronization"
    )
    
    # Test commands
    subparsers.add_parser("test-db", help="Test database connection")
    subparsers.add_parser("test-api", help="Test API authentication")
    subparsers.add_parser("init-db", help="Initialize database tables")
    
    return parser


def main() -> int:
    """Main application entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    app = PelotonDataSync()
    
    try:
        if args.command == "test-db":
            logger.info("Testing database connection")
            if test_database_connection():
                logger.info("Database connection test successful")
                return 0
            else:
                logger.error("Database connection test failed")
                return 1
        
        elif args.command == "test-api":
            logger.info("Testing API authentication")
            try:
                api_client = PelotonAPIClient()
                if api_client.authenticate():
                    logger.info("API authentication test successful")
                    api_client.close()
                    return 0
                else:
                    logger.error("API authentication test failed")
                    return 1
            except PelotonAuthenticationError as e:
                logger.error("API authentication failed", error=str(e))
                return 1
        
        elif args.command == "init-db":
            logger.info("Initializing database")
            try:
                init_database()
                logger.info("Database initialization successful")
                return 0
            except Exception as e:
                logger.error("Database initialization failed", error=str(e))
                return 1
        
        elif args.command == "sync":
            # Initialize application
            if not app.initialize():
                logger.error("Application initialization failed")
                return 1
            
            # Perform sync
            include_performance = not args.no_performance
            success = app.sync_data(
                max_workouts=args.max_workouts,
                include_performance=include_performance
            )
            
            return 0 if success else 1
        
        else:
            logger.error("Unknown command", command=args.command)
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        return 1
    
    finally:
        app.cleanup()


if __name__ == "__main__":
    sys.exit(main())
