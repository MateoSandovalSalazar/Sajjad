class SajjadError(Exception):
    """Base exception for all Sajjad errors."""


class ScanTimeoutError(SajjadError):
    """Raised when a scan tool exceeds its configured timeout."""


class ToolNotFoundError(SajjadError):
    """Raised when a required external tool is not in PATH."""


class ScanError(SajjadError):
    """Raised when a scanner encounters an unrecoverable error."""


class DomainNotVerifiedError(SajjadError):
    """Raised when attempting to scan an unverified domain."""


class ConfigurationError(SajjadError):
    """Raised for missing or invalid environment configuration."""
