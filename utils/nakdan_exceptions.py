from typing import Any

class NakdanAPIError(Exception):
    """Base exception for Nakdan API errors."""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.details = details

class NakdanConnectionError(NakdanAPIError):
    """Raised when connection to Nakdan API fails."""
    pass

class NakdanResponseError(NakdanAPIError):
    """Raised when Nakdan API returns an invalid response."""
    pass

class NakdanValidationError(NakdanAPIError):
    """Raised when input validation fails."""
    pass
