"""Custom exceptions for the CPCC Enrollment API."""

from typing import Optional, Dict, Any


class CPCCAPIException(Exception):
    """Base exception for CPCC API related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CPCCSessionError(CPCCAPIException):
    """Exception raised when CPCC session management fails."""
    pass


class CPCCAuthenticationError(CPCCAPIException):
    """Exception raised when CPCC authentication fails."""
    pass


class CPCCRequestError(CPCCAPIException):
    """Exception raised when CPCC API requests fail."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        super().__init__(message, details)


class CPCCParsingError(CPCCAPIException):
    """Exception raised when parsing CPCC responses fails."""
    pass


class CacheError(Exception):
    """Exception raised when cache operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        self.message = message
        self.operation = operation
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


class RateLimitError(CPCCAPIException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class ServiceUnavailableError(CPCCAPIException):
    """Exception raised when CPCC service is unavailable."""
    pass


class ConfigurationError(Exception):
    """Exception raised when configuration is invalid."""
    pass


# Additional exception classes for specific error types
class CPCCError(CPCCAPIException):
    """General CPCC service error."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(CPCCAuthenticationError):
    """Authentication error with CPCC system."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.error_code = error_code
        super().__init__(message)


class NetworkError(CPCCRequestError):
    """Network-related error when communicating with CPCC."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.error_code = error_code
        super().__init__(message)