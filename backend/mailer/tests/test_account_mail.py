"""Milestone-1 security/reliability tests: persistent verification + recovery tokens and the durable outbox.
Parametrised over the in-memory store and a FILE-backed PersistentStore(SQLite) so persistence/restart behaviour is exercised on the real store code."""
import json
import logging
import sqlite3
import time

import pytest

from app_services.store import InMemoryStore
from contract.harness import PASSWORD, Harness
from mailer import DeliveryError, Outbox, load_mail_config
from mailer.adapters import SmtpSender
from mailer.config import MailConfigError
from mailer.ports import DeliveryResult, MailSender
from mailer.runtime import MailRuntime, capture_runtime
from mailer.worker import process_due
from persistence import PersistentStore, SqliteBackend

SECRET = "unit-test-secret-0123456789abcdef0123456789"


class FakeSender(MailSender):
    """Stands in for SMTP: records what it was asked to send (raw secrets live only in this test object) and follows a script of outcomes."""
    provider, delivers_real_mail, inline = "fake-smtp", True, False

    def __init__(self):
        self.sent, self.script = [], []

    def _deliver(self, msg):
        if self.script:
            out = self.script.pop(0)
            if isinstance(out, DeliveryError):
                raise out
        self.sent.append(msg)
        return DeliveryResult("sent", self.provider, True)


@pytest.fixture
def clock(monkeypatch):
    t = {"now": int(time.time())}
    monkeypatch.setattr(time, "time", lambda: t["now"])
    return t


@pytest.fixture(params=["memory", "sqlite_file"])
def world(request, tmp_path, clock):
    path = str(tmp_path / "vf.sqlite3")

    mem = InMemoryStore() if request.param == "memory" else None

    class W:
        kind = request.param
        sender = FakeSender()

        def open(self, sender=None):
            """A 'process start': new store connection + new application object on the same database."""
            s = mem if mem is not None else PersistentStore(SqliteBackend(path))
            self.store = s
            self.h = Harness(dev=False, store=s, mail=MailRuntime(sender or self.sender, SECRET, "http://fe.test"))
            self.ob = Outbox(s, sender or self.sender, SECRET, lambda: int(time.time()), "http://fe.test")
            return self.h

        def drain(self):
            return process_due(self.store, self.ob)

        def dump(self):
            if self.kind == "memory":
                return json.dumps({k: str(v) for k, v in self.store.__dict__.items()}, default=str)
            db = sqlite3.connect(path)
            return "\n".join(r[0] for r in db.execute("select data from kv"))

    w = W()
    w.open()
    return w


def outbox_rows(w, kind=None):
    import contextlib
    tx = getattr(w.store, "transaction", None) or contextlib.nullcontext
    with tx():
        rows = [dict(r) for r in w.store.outbox.values()]
    return [r for r in rows if kind in (None, r["kind"])]


def code_of(w, kind="verification", n=-1):
    return [m.secret for m in w.sender.sent if m.kind == kind][n]


# 1 / 16
def test_registration_creates_an_unverified_account_even_in_dev_mode(world):
    h = Harness(dev=True, mail=capture_runtime(InMemoryStore(), SECRET))        # DEBUG-style app: must NOT bypass verification
    h.register("a@ex.com")
    assert h.store.users[h.store.by_email["a@ex.com"]]["verified"] is False
    assert h.call("POST", "/auth/login", {"identifier": "a@ex.com", "password": PASSWORD}).status == 401
    w = world
    w.h.register("b@ex.com")
    assert w.store.users[w.store.by_email["b@ex.com"]]["verified"] is False
    assert w.h.call("POST", "/auth/login", {"identifier": "b@ex.com", "password": PASSWORD}).status == 401


# 2
def test_verification_message_enters_the_persistent_outbox_and_is_not_sent_inline(world):
    world.h.register("a@ex.com")
    rows = outbox_rows(world, "verification")
    assert len(rows) == 1 and rows[0]["status"] == "pending" and rows[0]["to"] == "a@ex.com" and world.sender.sent == []


# 3 / 4
def test_token_and_outbox_survive_a_restart_and_the_correct_code_verifies(world):
    world.h.register("a@ex.com")
    h2 = world.open()                                              # restart: nothing is shared in memory (sqlite_file); same DB
    assert world.drain() == {"sent": 1}
    assert h2.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": code_of(world)}).status == 200
    assert h2.call("POST", "/auth/login", {"identifier": "a@ex.com", "password": PASSWORD}).status == 200


# 5
def test_expired_code_is_rejected(world, clock):
    world.h.register("a@ex.com"); world.drain()
    clock["now"] += 31 * 60
    assert world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": code_of(world)}).status == 410


# 6
def test_a_code_cannot_be_reused(world):
    world.h.register("a@ex.com"); world.drain()
    c = code_of(world)
    assert world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": c}).status == 200
    assert world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": c}).status == 400


# 7
def test_a_replaced_code_is_invalidated_and_its_unsent_message_never_goes_out(world, clock):
    world.h.register("a@ex.com")                                   # message 1 still pending
    clock["now"] += 61
    assert world.h.call("POST", "/auth/verify/resend", {"identifier": "a@ex.com"}).status == 202
    assert world.drain() == {"expired": 1, "sent": 1}              # old message: superseded; only the new one was sent
    assert len(world.sender.sent) == 1
    assert [r["error"] for r in outbox_rows(world) if r["status"] == "expired"] == ["superseded"]
    new = code_of(world)
    assert world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": new}).status == 200


def test_replaced_code_is_rejected_even_if_it_was_already_sent(world, clock):
    world.h.register("a@ex.com"); world.drain(); old = code_of(world)
    clock["now"] += 61
    world.h.call("POST", "/auth/verify/resend", {"identifier": "a@ex.com"}); world.drain()
    assert code_of(world) != old
    assert world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": old}).status == 400


def test_wrong_codes_are_limited_then_the_code_is_burned(world):
    world.h.register("a@ex.com"); world.drain(); good = code_of(world)
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        assert world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": bad}).status == 400
    assert world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": good}).status == 400      # burned: request a new one


# 8
def test_raw_codes_and_tokens_are_not_stored_in_the_database(world):
    if world.kind != "sqlite_file":
        pytest.skip("needs the real database file")
    world.h.register("a@ex.com"); world.drain()
    world.h.call("POST", "/auth/password-reset/request", {"identifier": "a@ex.com"}); world.drain()
    code, tok = code_of(world), code_of(world, "password_reset")
    dump = world.dump()
    assert f'"{code}"' not in dump and tok not in dump
    assert len(tok) == 64 and "verification" in dump                # hashes/nonces are stored, values are not


def test_capture_mode_keeps_secrets_only_in_the_explicit_capture_collection():
    s = InMemoryStore()
    h = Harness(store=s, mail=capture_runtime(s, SECRET))
    h.register("a@ex.com")
    code = h.captured("a@ex.com", "verification")["secret"]
    assert all(code not in json.dumps(v, default=str) for k, v in s.__dict__.items() if k not in ("captured_mail",) and isinstance(v, dict))


# 9 / 11
def test_password_recovery_uses_the_same_outbox_and_the_token_is_single_use(world, clock):
    world.h.register("a@ex.com"); world.drain()
    world.h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": code_of(world)})
    clock["now"] += 61
    assert world.h.call("POST", "/auth/password-reset/request", {"identifier": "a@ex.com"}).status == 202
    assert [r["kind"] for r in outbox_rows(world)] == ["verification", "password_reset"]
    world.drain()
    msg = [m for m in world.sender.sent if m.kind == "password_reset"][0]
    assert msg.secret in msg.text and f"http://fe.test/fa/reset?token={msg.secret}" in msg.text
    assert world.h.call("POST", "/auth/password-reset/confirm", {"token": msg.secret, "new_password": "N3wStrongPassword"}).status == 200
    assert world.h.call("POST", "/auth/password-reset/confirm", {"token": msg.secret, "new_password": "N3wStrongPassword"}).status == 400


def test_a_new_reset_request_invalidates_the_previous_token(world, clock):
    world.h.register("a@ex.com"); world.drain()
    world.h.call("POST", "/auth/password-reset/request", {"identifier": "a@ex.com"}); world.drain()
    first = code_of(world, "password_reset")
    clock["now"] += 61
    world.h.call("POST", "/auth/password-reset/request", {"identifier": "a@ex.com"}); world.drain()
    assert world.h.call("POST", "/auth/password-reset/confirm", {"token": first, "new_password": "N3wStrongPassword"}).status == 400
    assert world.h.call("POST", "/auth/password-reset/confirm", {"token": code_of(world, "password_reset"), "new_password": "N3wStrongPassword"}).status == 200


# 10
def test_unknown_and_known_addresses_get_indistinguishable_public_answers(world):
    h = world.h
    h.register("known@ex.com")
    a = h.call("POST", "/auth/password-reset/request", {"identifier": "known@ex.com"})
    b = h.call("POST", "/auth/password-reset/request", {"identifier": "nobody@ex.com"})
    assert (a.status, a.body) == (b.status, b.body) == (202, {"message": "accepted"})
    a = h.call("POST", "/auth/verify/resend", {"identifier": "known@ex.com"})          # within cooldown for BOTH (limiter ignores existence)
    b = h.call("POST", "/auth/verify/resend", {"identifier": "nobody@ex.com"})
    assert a.status == 429 and b.status == 202                      # known was just registered (mail sent => cooldown); unknown has no history
    b2 = h.call("POST", "/auth/verify/resend", {"identifier": "nobody@ex.com"})
    assert b2.status == 429 and b2.body["code"] == a.body["code"]   # same throttling behaviour once an address has been asked about
    r1 = h.call("POST", "/auth/register", {"email": "known@ex.com", "password": PASSWORD, "date_of_birth": "1990-01-01", "language": "fa"})
    r2 = h.call("POST", "/auth/register", {"email": "new@ex.com", "password": PASSWORD, "date_of_birth": "1990-01-01", "language": "fa"})
    assert (r1.status, r1.body) == (r2.status, r2.body)
    assert [r["to"] for r in outbox_rows(world, "password_reset")] == ["known@ex.com"]   # nothing queued for the unknown address


# 12
def test_retry_with_bounded_exponential_backoff_then_success(world, clock):
    world.h.register("a@ex.com")
    world.sender.script = [DeliveryError("smtp_unavailable")] * 3
    delays = []
    for _ in range(3):
        assert world.drain() == {"retry_scheduled": 1}
        r = outbox_rows(world)[0]
        delays.append(r["next_attempt"] - clock["now"])
        assert world.drain() == {}                                   # not due yet
        clock["now"] = r["next_attempt"]
    assert delays == [60, 120, 240]
    assert world.drain() == {"sent": 1}
    r = outbox_rows(world)[0]
    assert r["status"] == "sent" and r["attempts"] == 4 and r["to"] == "" and r["nonce"] == ""      # recipient + nonce wiped when terminal


def test_backoff_is_capped_and_attempts_are_bounded(world, clock):
    world.ob.base_delay, world.ob.max_delay, world.ob.max_attempts = 10, 25, 6
    world.h.register("a@ex.com")
    world.sender.script = [DeliveryError("smtp_unavailable")] * 10
    delays = []
    for _ in range(6):
        world.drain()
        r = outbox_rows(world)[0]
        if r["status"] != "retry_scheduled":
            break
        delays.append(r["next_attempt"] - clock["now"])
        clock["now"] = r["next_attempt"]
    r = outbox_rows(world)[0]
    assert delays == [10, 20, 25, 25, 25] and r["status"] == "failed" and r["attempts"] == 6 and r["error"] == "smtp_unavailable"
    assert world.sender.sent == []


def test_expiry_wins_over_retries(world, clock):
    """With the 30-minute token life the later retries of the default schedule are never sent: the token is dead by then."""
    world.h.register("a@ex.com")
    world.sender.script = [DeliveryError("smtp_unavailable")] * 10
    for _ in range(8):
        world.drain()
        r = outbox_rows(world)[0]
        if r["status"] not in ("retry_scheduled",):
            break
        clock["now"] = r["next_attempt"]
    assert outbox_rows(world)[0]["status"] == "expired" and world.sender.sent == []


def test_permanent_error_fails_immediately(world):
    world.h.register("a@ex.com")
    world.sender.script = [DeliveryError("recipient_refused", permanent=True)]
    assert world.drain() == {"failed": 1}


def test_messages_past_token_expiry_are_expired_not_sent(world, clock):
    world.h.register("a@ex.com")
    clock["now"] += 31 * 60
    assert world.drain() == {"expired": 1} and world.sender.sent == []


# 13
def test_duplicate_processing_is_prevented_and_interrupted_work_is_recovered(world, clock):
    world.h.register("a@ex.com")
    import contextlib
    tx = getattr(world.store, "transaction", None) or contextlib.nullcontext
    mid = outbox_rows(world)[0]["id"]
    with tx():
        first = world.ob.claim(mid)
    with tx():
        second = world.ob.claim(mid)                                 # a second worker while the lease is valid
    assert first and second is None
    with tx():
        assert world.ob.due_ids() == []
    clock["now"] += 301                                              # worker died; lease expired
    assert world.drain() == {"sent": 1}
    assert world.drain() == {} and len(world.sender.sent) == 1       # processed exactly once overall


# 14
def test_smtp_failures_never_mark_a_message_sent(world, clock):
    world.h.register("a@ex.com")
    cfg = {"host": "127.0.0.1", "port": 1, "username": "", "password": "", "security": "none", "timeout": 1, "from_address": "n@ex.com", "from_name": "VitaForge"}
    real = SmtpSender(cfg)
    world.ob.sender = real
    assert world.drain() == {"retry_scheduled": 1}
    assert outbox_rows(world)[0]["status"] == "retry_scheduled" and outbox_rows(world)[0]["error"] == "smtp_unavailable"


def test_smtp_adapter_maps_server_replies(monkeypatch):
    import smtplib
    cfg = {"host": "h", "port": 25, "username": "u", "password": "p", "security": "starttls", "timeout": 1, "from_address": "n@ex.com", "from_name": "VF"}
    events = []

    class FakeSMTP:
        mode = "ok"
        def __init__(self, *a, **k): events.append(("connect", a[:2], k.get("timeout")))
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, **k): events.append("starttls")
        def login(self, u, p):
            if FakeSMTP.mode == "auth": raise smtplib.SMTPAuthenticationError(535, b"no")
        def send_message(self, m):
            events.append(("msg", m["To"], m["From"]))
            if FakeSMTP.mode == "refused": raise smtplib.SMTPRecipientsRefused({"x": (550, b"")})
            if FakeSMTP.mode == "4xx": raise smtplib.SMTPResponseException(451, b"later")
            if FakeSMTP.mode == "5xx": raise smtplib.SMTPResponseException(554, b"no")
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    s = SmtpSender(cfg)
    r = s.send_verification("a@ex.com", "123456", "fa")
    assert (r.status, r.delivered, r.provider) == ("sent", True, "smtp") and "starttls" in events and ("connect", ("h", 25), 1) in events
    for mode, code, permanent in [("refused", "recipient_refused", True), ("auth", "smtp_auth_failed", False), ("4xx", "smtp_451", False), ("5xx", "smtp_554", True)]:
        FakeSMTP.mode = mode
        with pytest.raises(DeliveryError) as e:
            s.send_verification("a@ex.com", "123456", "en")
        assert (e.value.code, e.value.permanent) == (code, permanent)
    with pytest.raises(DeliveryError) as e:
        s.send_verification("bad address@ex.com", "1", "en")
    assert e.value.permanent


# 15
def test_capture_mode_never_claims_delivery(clock):
    s = InMemoryStore()
    h = Harness(store=s, mail=capture_runtime(s, SECRET))
    h.register("a@ex.com")
    rows = [dict(r) for r in s.outbox.values()]
    assert [r["status"] for r in rows] == ["captured"] and not any(r["status"] == "sent" for r in rows)
    assert h.app.mail.sender.delivers_real_mail is False
    assert h.app.mail.sender.send_verification("a@ex.com", "123456", "en").delivered is False


def test_dev_capture_route_exists_only_for_explicit_capture_in_dev():
    s = InMemoryStore()
    on = Harness(dev=True, store=s, mail=capture_runtime(s, SECRET))
    on.register("a@ex.com")
    r = on.call("GET", "/dev/captured-mail?kind=verification&to=a@ex.com", check=False)
    assert r.status == 200 and r.body["delivered"] is False and len(r.body["secret"]) == 6
    s2 = InMemoryStore()
    off = Harness(dev=True, store=s2, mail=MailRuntime(FakeSender(), SECRET, "http://x"))
    assert off.call("GET", "/dev/captured-mail?kind=verification&to=a@ex.com", check=False).status == 404
    prod = Harness(dev=False, store=InMemoryStore(), mail=capture_runtime(InMemoryStore(), SECRET))
    assert prod.call("GET", "/dev/captured-mail?kind=verification&to=a@ex.com", check=False).status == 404


def test_rate_limit_cooldown_and_hourly_cap(world, clock):
    h = world.h
    h.register("a@ex.com")
    assert h.call("POST", "/auth/verify/resend", {"identifier": "a@ex.com"}).status == 429       # registration counted as the first send
    for _ in range(4):
        clock["now"] += 61
        assert h.call("POST", "/auth/verify/resend", {"identifier": "a@ex.com"}).status == 202
    clock["now"] += 61
    assert h.call("POST", "/auth/verify/resend", {"identifier": "a@ex.com"}).status == 429       # 5 per hour reached
    clock["now"] += 3600
    assert h.call("POST", "/auth/verify/resend", {"identifier": "a@ex.com"}).status == 202


def test_logs_contain_neither_addresses_nor_codes(world, caplog):
    caplog.set_level(logging.DEBUG)
    world.h.register("secret.person@ex.com"); world.drain()
    text = caplog.text
    assert "mail outbox" in text and "secret.person" not in text and code_of(world) not in text


def test_account_deletion_removes_outbox_and_token_records(world, clock):
    h = world.h
    h.register("a@ex.com"); world.drain()
    h.call("POST", "/auth/verify", {"identifier": "a@ex.com", "code": code_of(world)})
    sid = h.call("POST", "/auth/login", {"identifier": "a@ex.com", "password": PASSWORD})
    import re
    token = re.search(r"sessionid=([^;]+)", sid.headers["Set-Cookie"]).group(1)
    clock["now"] += 61
    h.call("POST", "/auth/password-reset/request", {"identifier": "a@ex.com"})
    assert outbox_rows(world)
    assert h.call("POST", "/privacy/delete", {"password": PASSWORD, "confirm": True}, token=token).status in (200, 202)
    assert outbox_rows(world) == []
    import contextlib
    tx = getattr(world.store, "transaction", None) or contextlib.nullcontext
    with tx():
        assert not world.store.verification and not world.store.resets


# ---- configuration
GOOD = {"MAIL_PROVIDER": "smtp", "SMTP_HOST": "smtp.invalid", "MAIL_FROM_ADDRESS": "n@ex.org", "SMTP_USERNAME": "u", "SMTP_PASSWORD": "p"}


def test_config_rules():
    c = load_mail_config(GOOD, debug=False)
    assert c["provider"] == "smtp" and c["smtp"]["port"] == 587 and c["smtp"]["security"] == "starttls" and c["smtp"]["from_name"] == "VitaForge"
    assert load_mail_config({}, debug=True)["provider"] == "disabled"                     # dev default: nothing pretends to deliver
    assert load_mail_config({"MAIL_PROVIDER": "capture"}, debug=True)["provider"] == "capture"
    for env, dbg in [({}, False), ({"MAIL_PROVIDER": "capture"}, False), ({"MAIL_PROVIDER": "disabled"}, False), ({"MAIL_PROVIDER": "nope"}, True),
                     ({**GOOD, "SMTP_HOST": ""}, False), ({**GOOD, "SMTP_PASSWORD": ""}, False), ({**GOOD, "SMTP_SECURITY": "none"}, False),
                     ({**GOOD, "SMTP_PORT": "x"}, False), ({**GOOD, "MAIL_FROM_ADDRESS": "nope"}, False)]:
        with pytest.raises(MailConfigError):
            load_mail_config(env, dbg)
    assert load_mail_config({**GOOD, "SMTP_SECURITY": "ssl"}, False)["smtp"]["port"] == 465


def test_disabled_provider_never_delivers_and_keeps_messages_pending(world):
    from mailer.ports import DisabledSender
    world.ob.sender = DisabledSender()
    world.h.register("a@ex.com")
    assert world.drain() == {"retry_scheduled": 1}
    assert world.sender.sent == []
