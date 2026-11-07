class SafetyCoreError(Exception):
    """Base error. The engine converts any exception into an ERROR_FAILSAFE decision."""


class RuleError(SafetyCoreError):
    pass


class InvalidInput(SafetyCoreError):
    pass
