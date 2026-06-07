class ShipMyBoxException(Exception):
    """Base exception for ShipMyBox CLI."""
    pass

class LoginError(ShipMyBoxException):
    """Raised when login fails or session is invalid."""
    pass

class DataExtractionError(ShipMyBoxException):
    """Raised when parsing/extraction of data fails."""
    pass

class NotificationError(ShipMyBoxException):
    """Raised when sending a notification fails."""
    pass
