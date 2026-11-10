"""Exception hierarchy for NetArchitect.

Every error carries a machine-readable ``code`` and a CLI ``exit_code`` so the
CLI, the web API and the test-suite can all react to failures the same way.
"""

from __future__ import annotations


class NetArchitectError(Exception):
    """Base class for every engine error."""

    code = "NETARCH_ERROR"
    exit_code = 1

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        return {
            "error": type(self).__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(NetArchitectError):
    """Custom parameters failed schema / range / topology validation."""

    code = "VALIDATION_FAILED"
    exit_code = 2

    def __init__(self, issues: list[str], warnings: list[str] | None = None):
        self.issues = list(issues)
        message = f"{len(self.issues)} parameter issue(s): " + "; ".join(self.issues)
        super().__init__(message, issues=self.issues, warnings=list(warnings or []))


class InvalidAddressError(NetArchitectError):
    """Malformed IPv4 address, mask or CIDR string."""

    code = "INVALID_ADDRESS"
    exit_code = 2


class InvalidPrefixError(InvalidAddressError):
    """CIDR prefix is out of range or has host bits set."""

    code = "INVALID_PREFIX"


class PhysicalDistanceViolationError(NetArchitectError):
    """A cable run exceeds the physical reach of the requested medium."""

    code = "PHYSICAL_DISTANCE_VIOLATION"
    exit_code = 3

    def __init__(self, message: str, *, distance_m: float, limit_m: float,
                 medium: str, attenuation_warning: str, subject: str = ""):
        super().__init__(
            message,
            distance_m=distance_m,
            limit_m=limit_m,
            medium=medium,
            attenuation_warning=attenuation_warning,
            subject=subject,
        )
        self.distance_m = distance_m
        self.limit_m = limit_m
        self.medium = medium
        self.attenuation_warning = attenuation_warning


class AddressSpaceExhaustedError(NetArchitectError):
    """The root prefix cannot hold every requested subnet."""

    code = "ADDRESS_SPACE_EXHAUSTED"
    exit_code = 4

    def __init__(self, message: str, *, required: int, available: int,
                 root: str, minimum_prefix: int | None):
        super().__init__(
            message,
            required=required,
            available=available,
            root=root,
            minimum_prefix=minimum_prefix,
        )
        self.required = required
        self.available = available
        self.minimum_prefix = minimum_prefix
