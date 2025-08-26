"""Peloton API client with authentication, rate limiting, and error handling."""

import time
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry

from .config import get_config
from .logging_config import get_logger

logger = get_logger(__name__)


class PelotonAPIError(Exception):
    """Base exception for Peloton API errors."""
    pass


class PelotonAuthenticationError(PelotonAPIError):
    """Authentication-related errors."""
    pass


class PelotonRateLimitError(PelotonAPIError):
    """Rate limit exceeded errors."""
    pass


class PelotonAPIClient:
    """Client for interacting with the Peloton API."""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """Initialize the Peloton API client.
        
        Args:
            username: Peloton username or email
            password: Peloton password
        """
        app_config, _, peloton_config = get_config()
        
        self.username = username or peloton_config.username
        self.password = password or peloton_config.password
        self.base_url = peloton_config.base_url
        
        self.max_retries = app_config.max_retries
        self.retry_delay = app_config.retry_delay
        self.rate_limit_calls = app_config.rate_limit_calls
        self.rate_limit_period = app_config.rate_limit_period
        
        self.session = self._create_session()
        self.user_id: Optional[str] = None
        self._authenticated = False
        
        logger.info("Peloton API client initialized", username=self.username)
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "User-Agent": "PelotonDataSync/1.0.0",
            "Content-Type": "application/json",
        })
        
        return session
    
    @sleep_and_retry
    @limits(calls=60, period=60)  # Default rate limit
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a rate-limited HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            PelotonAPIError: For API-related errors
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limit exceeded, waiting", retry_after=retry_after)
                time.sleep(retry_after)
                raise PelotonRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error("API request failed", method=method, endpoint=endpoint, error=str(e))
            raise PelotonAPIError(f"API request failed: {e}")
    
    def authenticate(self) -> bool:
        """Authenticate with the Peloton API.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            PelotonAuthenticationError: If authentication fails
        """
        if self._authenticated:
            return True
        
        payload = {
            "username_or_email": self.username,
            "password": self.password
        }
        
        try:
            response = self._make_request("POST", "/auth/login", json=payload)
            auth_data = response.json()
            
            self.user_id = auth_data.get("user_id")
            if not self.user_id:
                raise PelotonAuthenticationError("No user ID in authentication response")
            
            self._authenticated = True
            logger.info("Authentication successful", user_id=self.user_id)
            return True
            
        except Exception as e:
            logger.error("Authentication failed", error=str(e))
            raise PelotonAuthenticationError(f"Authentication failed: {e}")
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information.
        
        Returns:
            User information dictionary
        """
        self._ensure_authenticated()
        response = self._make_request("GET", "/api/me")
        return response.json()
    
    def get_user_workouts(self, limit: int = 100, page: int = 0, 
                         joins: Optional[str] = None) -> Dict[str, Any]:
        """Get user workouts.
        
        Args:
            limit: Maximum number of workouts to retrieve
            page: Page number (0-based)
            joins: Comma-separated list of related data to include
            
        Returns:
            Workouts data dictionary
        """
        self._ensure_authenticated()
        
        params = {
            "limit": limit,
            "page": page
        }
        
        if joins:
            params["joins"] = joins
        
        endpoint = f"/api/user/{self.user_id}/workouts"
        response = self._make_request("GET", endpoint, params=params)
        return response.json()
    
    def _ensure_authenticated(self) -> None:
        """Ensure the client is authenticated."""
        if not self._authenticated:
            self.authenticate()

    def get_workout_details(self, workout_id: str, joins: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific workout.

        Args:
            workout_id: Peloton workout ID
            joins: Comma-separated list of related data to include

        Returns:
            Workout details dictionary
        """
        self._ensure_authenticated()

        params = {}
        if joins:
            params["joins"] = joins

        endpoint = f"/api/workout/{workout_id}"
        response = self._make_request("GET", endpoint, params=params)
        return response.json()

    def get_workout_performance_graph(self, workout_id: str, every_n: int = 5) -> Dict[str, Any]:
        """Get performance graph data for a workout.

        Args:
            workout_id: Peloton workout ID
            every_n: Sample every N seconds

        Returns:
            Performance graph data dictionary
        """
        self._ensure_authenticated()

        params = {"every_n": every_n}
        endpoint = f"/api/workout/{workout_id}/performance_graph"
        response = self._make_request("GET", endpoint, params=params)
        return response.json()

    def get_ride_details(self, ride_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific ride/class.

        Args:
            ride_id: Peloton ride ID

        Returns:
            Ride details dictionary
        """
        endpoint = f"/api/ride/{ride_id}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_instructor_info(self, instructor_id: str) -> Dict[str, Any]:
        """Get information about a specific instructor.

        Args:
            instructor_id: Peloton instructor ID

        Returns:
            Instructor information dictionary
        """
        endpoint = f"/api/instructor/{instructor_id}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_all_instructors(self) -> Dict[str, Any]:
        """Get information about all instructors.

        Returns:
            All instructors data dictionary
        """
        endpoint = "/api/instructor"
        response = self._make_request("GET", endpoint)
        return response.json()

    def get_recent_workouts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent workouts with ride and instructor information.

        Args:
            limit: Maximum number of workouts to retrieve

        Returns:
            List of workout dictionaries
        """
        workouts_data = self.get_user_workouts(
            limit=limit,
            joins="ride,ride.instructor"
        )
        return workouts_data.get("data", [])

    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            logger.info("API client session closed")
