# Peloton Data Sync

A Python application to retrieve data from the OnePeloton API and store it in a PostgreSQL database. This application provides comprehensive synchronization of workout data, performance metrics, user information, and instructor details.

## Features

- **Complete Data Sync**: Synchronizes workouts, rides, instructors, and user data
- **Performance Metrics**: Captures detailed time-series performance data (cadence, power, heart rate, etc.)
- **Achievement Tracking**: Records workout achievements and milestones
- **Incremental Updates**: Supports both full and incremental synchronization
- **Robust Error Handling**: Comprehensive error handling and retry logic
- **Rate Limiting**: Built-in API rate limiting to respect Peloton's limits
- **Structured Logging**: Detailed logging with JSON and colored console output
- **Database Management**: Automatic database schema creation and migration support

## Requirements

- Python 3.8+
- PostgreSQL 12+
- Valid Peloton account credentials

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/peloton-data-sync.git
cd peloton-data-sync
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials and database settings
```

4. Initialize the database:
```bash
python -m peloton_sync.main init-db
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and update the following:

### Required Settings

```env
# Peloton API Credentials
PELOTON_USERNAME=your_username_or_email
PELOTON_PASSWORD=your_password

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/peloton_data
# OR individual components:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=peloton_data
DB_USER=username
DB_PASSWORD=password
```

### Optional Settings

```env
# Application Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                   # json or text
MAX_RETRIES=3                     # API retry attempts
RATE_LIMIT_CALLS=60              # API calls per period
RATE_LIMIT_PERIOD=60             # Rate limit period in seconds

# Data Sync Configuration
MAX_WORKOUTS_PER_SYNC=100        # Maximum workouts per sync
INCLUDE_PERFORMANCE_DATA=true    # Include detailed performance metrics
INCLUDE_HEART_RATE_DATA=true     # Include heart rate data
```

## Usage

### Command Line Interface

The application provides a command-line interface with several commands:

#### Sync Data
```bash
# Sync with default settings
python -m peloton_sync.main sync

# Sync up to 50 workouts
python -m peloton_sync.main sync --max-workouts 50

# Sync without performance data (faster)
python -m peloton_sync.main sync --no-performance
```

#### Test Connections
```bash
# Test database connection
python -m peloton_sync.main test-db

# Test API authentication
python -m peloton_sync.main test-api
```

#### Database Management
```bash
# Initialize database tables
python -m peloton_sync.main init-db
```

### Programmatic Usage

You can also use the application programmatically:

```python
from peloton_sync.main import PelotonDataSync

# Initialize the application
app = PelotonDataSync()

if app.initialize():
    # Sync data
    success = app.sync_data(max_workouts=50, include_performance=True)
    
    if success:
        print("Sync completed successfully!")
    else:
        print("Sync failed!")
    
    # Clean up
    app.cleanup()
```

### Using Individual Components

```python
from peloton_sync.api_client import PelotonAPIClient
from peloton_sync.data_loader import DataLoader
from peloton_sync.database import get_db_session

# Create API client
api_client = PelotonAPIClient(username="your_username", password="your_password")
api_client.authenticate()

# Get recent workouts
workouts = api_client.get_recent_workouts(limit=10)

# Use data loader
data_loader = DataLoader(api_client)
with get_db_session() as session:
    stats = data_loader.sync_workouts(session, api_client.user_id, limit=10)
    print(f"Synced {stats['created']} new workouts")

# Clean up
api_client.close()
```

## Database Schema

The application creates the following tables:

- **users**: Peloton user information
- **instructors**: Instructor profiles and details
- **rides**: Class/ride information (cycling, running, strength, etc.)
- **workouts**: Individual workout sessions
- **workout_performance_summaries**: Overall workout performance metrics
- **workout_performance_metrics**: Time-series performance data
- **workout_achievements**: Achievements earned during workouts
- **sync_logs**: Synchronization operation logs

## Data Types Supported

- **Cycling**: Bike workouts with power, cadence, resistance metrics
- **Running**: Treadmill and outdoor runs with pace and incline data
- **Strength**: Strength training sessions
- **Yoga**: Yoga and meditation classes
- **Stretching**: Stretching and recovery sessions
- **Bootcamp**: Combined cardio and strength workouts

## Performance Considerations

- The application uses connection pooling for database efficiency
- API requests are rate-limited to respect Peloton's limits
- Large syncs are processed in batches to avoid memory issues
- Performance data sync can be disabled for faster synchronization

## Logging

The application provides comprehensive logging:

- **JSON Format**: Structured logging for production environments
- **Colored Console**: Human-readable colored output for development
- **Multiple Levels**: DEBUG, INFO, WARNING, ERROR levels
- **Context**: Rich contextual information for troubleshooting

## Error Handling

- **Automatic Retries**: Failed API requests are automatically retried
- **Graceful Degradation**: Performance data failures don't stop workout sync
- **Detailed Logging**: All errors are logged with context
- **Partial Success**: Sync can complete partially if some workouts fail

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is not officially affiliated with Peloton Interactive, Inc. Use at your own risk and ensure you comply with Peloton's Terms of Service.

## Support

For issues and questions:
1. Check the logs for detailed error information
2. Ensure your credentials and database settings are correct
3. Test individual components using the test commands
4. Open an issue on GitHub with relevant log output
