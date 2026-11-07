class PolicyViolation(Exception):
    """Raised when a request would break a hard data/safety policy (never degraded silently)."""
