import dataclasses

from .ports import MailSender


@dataclasses.dataclass(frozen=True)
class MailRuntime:
    sender: MailSender
    secret: str                    # key material for token derivation (DJANGO_SECRET_KEY)
    frontend_base_url: str


def capture_runtime(store, secret: str, frontend_base_url: str = "http://localhost:3000") -> MailRuntime:
    """Explicit development/test runtime: messages go to the store's `captured_mail` collection; nothing is delivered."""
    from .adapters import CaptureSender
    store.__dict__.setdefault("captured_mail", {})
    return MailRuntime(CaptureSender(store.captured_mail), secret, frontend_base_url)
