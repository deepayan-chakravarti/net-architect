"""NetArchitect - Recommendation & Config Engine (CIC-307 mini-project).

Pipeline: Input ingestion -> L1/L2 media engine -> L3 VLSM & routing ->
explainable exporter (Cisco IOS configs + architectural rationale log).
"""

from .engine import VERSION, plan
from .errors import (AddressSpaceExhaustedError, NetArchitectError,
                     PhysicalDistanceViolationError, ValidationError)

__version__ = VERSION
__all__ = ["plan", "NetArchitectError", "ValidationError", "PhysicalDistanceViolationError",
           "AddressSpaceExhaustedError", "__version__"]
