from typing import Any, Optional


class AppException(Exception):
    """Base application exception with HTTP mapping support."""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class InvalidInputError(AppException):
    """Raised when client provides bad or malformed input."""
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_INPUT",
            details=details,
        )


class ContractNotFoundError(AppException):
    """Raised when a requested contract is not found."""
    def __init__(self, contract_id: int) -> None:
        super().__init__(
            message=f"Contract with ID {contract_id} not found.",
            status_code=404,
            error_code="CONTRACT_NOT_FOUND",
            details={"contract_id": contract_id},
        )


class BusinessRuleValidationError(AppException):
    """Raised when extracted contract data violates business domain rules (HTTP 422)."""
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="BUSINESS_RULE_VIOLATION",
            details=details,
        )


class LLMRateLimitError(AppException):
    """Raised when LLM provider rate limit / quota is exhausted."""
    def __init__(self, message: str = "LLM provider rate limit exceeded. Please try again later.") -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_code="LLM_RATE_LIMIT_EXCEEDED",
        )


class LLMTimeoutError(AppException):
    """Raised when LLM provider request times out after retries."""
    def __init__(self, message: str = "LLM extraction request timed out.") -> None:
        super().__init__(
            message=message,
            status_code=504,
            error_code="LLM_GATEWAY_TIMEOUT",
        )


class LLMAuthenticationError(AppException):
    """Raised when LLM API Key is missing or invalid."""
    def __init__(self, message: str = "LLM service authentication failed. Check API key.") -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="LLM_AUTHENTICATION_ERROR",
        )


class LLMSchemaDecodeError(AppException):
    """Raised when LLM returns invalid JSON or schema mismatch."""
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            status_code=502,
            error_code="LLM_SCHEMA_DECODE_ERROR",
            details=details,
        )


class LLMProviderError(AppException):
    """Raised for unexpected upstream LLM API communication errors."""
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(
            message=message,
            status_code=502,
            error_code="LLM_PROVIDER_ERROR",
            details=details,
        )
