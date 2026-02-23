class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str = ""):
        super().__init__(f"{resource} not found: {identifier}", "NOT_FOUND")


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "FORBIDDEN")


class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class ExternalServiceError(AppException):
    def __init__(self, service: str, message: str):
        super().__init__(f"{service}: {message}", "EXTERNAL_SERVICE_ERROR")


class InsufficientStockError(AppException):
    def __init__(self, product_name: str, available: int, requested: int):
        super().__init__(
            f"Insufficient stock for '{product_name}': {available} available, {requested} requested",
            "INSUFFICIENT_STOCK",
        )
