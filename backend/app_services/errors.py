class AppError(Exception):
    code = "error"
    http = 400

    def __init__(self, detail: str = ""):
        super().__init__(detail or self.code)
        self.detail = detail


class ValidationFailed(AppError): code, http = "validation_failed", 422
class AuthFailed(AppError): code, http = "auth_failed", 401
class Locked(AppError): code, http = "account_locked", 423
class Conflict(AppError): code, http = "conflict", 409
class NotFound(AppError): code, http = "not_found", 404
class Forbidden(AppError): code, http = "forbidden", 403
class PreconditionRequired(AppError): code, http = "precondition_required", 428
class SafetyBlocked(AppError):
    code, http = "safety_blocked", 409

    def __init__(self, status: str, reasons=(), decision_id=None):
        super().__init__(status)
        self.status, self.reasons, self.decision_id = status, tuple(reasons), decision_id
