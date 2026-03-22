class ShipMyBoxException(Exception):
    """Base exception for ShipMyBox CLI."""
    pass

class LoginError(ShipMyBoxException):
    """Raised when login fails or session is invalid."""
    pass

class DataExtractionError(ShipMyBoxException):
    """Raised when data cannot be extracted from the page."""
    pass
