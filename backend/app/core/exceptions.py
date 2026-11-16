class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundException(AppException):
    def __init__(self, entity_name: str, entity_id: any):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' not found.",
            status_code=404,
            details={"entity": entity_name, "id": str(entity_id)},
        )


class DatabaseConnectionException(AppException):
    def __init__(self, message: str = "Database connection error"):
        super().__init__(
            message=message,
            status_code=503,
            details={"type": "database_unavailable"},
        )


class BusinessRuleValidationException(AppException):
    def __init__(self, message: str, rule: str = None):
        super().__init__(
            message=message,
            status_code=422,
            details={"rule": rule} if rule else {},
        )


class DomainValidationException(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=400,
            details=details or {},
        )
