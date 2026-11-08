"""
HTTP exceptions for Sajjad API.

All inherit from SajjadAPIError so main.py's single handler
converts them to a consistent JSON envelope:
  {"error": "ClassName", "message": "..."}

HTTPException is not used here to keep the format explicit
and avoid FastAPI's default detail/detail nesting.
"""

class SajjadAPIError(Exception):
    status_code: int = 500
    message: str = "Internal server error."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class NotFound(SajjadAPIError):
    status_code = 404
    message = "Resource not found."


class Forbidden(SajjadAPIError):
    status_code = 403
    message = "Access denied."


class Conflict(SajjadAPIError):
    status_code = 409
    message = "Resource already exists."


class Unauthorized(SajjadAPIError):
    status_code = 401
    message = "Invalid or expired credentials."


class UnprocessableEntity(SajjadAPIError):
    status_code = 422
    message = "Unprocessable entity."


class PlanLimitExceeded(SajjadAPIError):
    status_code = 402
    message = "Plan limit exceeded. Upgrade your subscription."


class DomainNotVerified(SajjadAPIError):
    status_code = 400
    message = (
        "Domain ownership not verified. "
        "Add the DNS TXT record and click Verify."
    )


class ScanAlreadyRunning(SajjadAPIError):
    status_code = 409
    message = "A scan is already running for this domain."


class BillingDisabled(SajjadAPIError):
    """La pasarela de pagos no está habilitada todavía."""

    status_code = 503
    message = "Online payments are not enabled yet."
