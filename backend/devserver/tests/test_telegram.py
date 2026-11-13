"""Telegram verification (primary channel). Every test goes through the real HTTP surface (spec-validated by the contract harness)."""
import time

import pytest

from contract.harness import PASSWORD, Harness
from tgverify import capture_runtime
from tgverify.service import ATTEMPTS_PER_HOUR, TOKEN_TTL_S, digest

TG = 5550001


def reg(h, email="a@ex.com"):
    h.register(email)
    return email


def user(h, email):
    return h.store.users[h.store.by_email[email]]


def test_successful_verification_then_normal_login():
    h = Harness()
    e = reg(h)
    assert h.call("POST", "/auth/login", {"identifier": e, "password": PASSWORD}).status == 401      # unverified: no session
    r, tok = h.tg_link(e)
    assert r.status == 200 and r.body["deep_link"] == f"https://t.me/{h.tg.username}?start={tok}"
    assert h.tg_start(TG, tok).status == 200
    assert user(h, e)["verified"] is True and user(h, e)["telegram"]["id"] == TG
    assert user(h, e)["telegram"]["notifications"] is False                    # consent for notifications is a separate, explicit step
    assert "verified" in h.tg.sender.sent[-1]["text"] or "تأیید" in h.tg.sender.sent[-1]["text"]
    lg = h.call("POST", "/auth/login", {"identifier": e, "password": PASSWORD})
    assert lg.status == 200
    t = h.login(e)
    assert h.call("GET", "/telegram/status", token=t).body == {"linked": True, "notifications": False}


def test_token_is_stored_only_as_hash_and_is_single_use():
    h = Harness()
    e = reg(h)
    _, tok = h.tg_link(e)
    assert tok not in repr(h.store.tg_tokens) and digest(tok) in h.store.tg_tokens
    assert h.tg_start(TG, tok).status == 200
    assert digest(tok) not in h.store.tg_tokens
    # replay by the same or another Telegram account fails and changes nothing
    sent = len(h.tg.sender.sent)
    assert h.tg_start(TG, tok).status == 200 and h.tg_start(TG + 1, tok).status == 200
    assert str(TG + 1) not in h.store.tg_links
    assert all("invalid" in m["text"] for m in h.tg.sender.sent[sent:])


def test_expired_token(monkeypatch):
    h = Harness()
    e = reg(h)
    _, tok = h.tg_link(e)
    h.store.tg_tokens[digest(tok)]["exp"] = int(time.time()) - 1
    assert h.tg_start(TG, tok).status == 200
    assert user(h, e)["verified"] is False and h.store.tg_links == {}
    assert "invalid or has expired" in h.tg.sender.sent[-1]["text"]


def test_token_ttl_is_short():
    h = Harness()
    e = reg(h)
    r, _ = h.tg_link(e)
    assert TOKEN_TTL_S <= 900


def test_invalid_and_malformed_tokens():
    h = Harness()
    e = reg(h)
    for bad in ("x" * 32, "short", "../../etc/passwd", "A" * 200):
        assert h.tg_start(TG, bad, text="/start " + bad).status == 200
    assert user(h, e)["verified"] is False and h.store.tg_links == {}


def test_new_link_invalidates_previous_one():
    h = Harness()
    e = reg(h)
    _, t1 = h.tg_link(e)
    h.store.tg_limits.clear()
    _, t2 = h.tg_link(e)
    h.tg_start(TG, t1)
    assert user(h, e)["verified"] is False
    h.tg_start(TG, t2)
    assert user(h, e)["verified"] is True


def test_telegram_id_already_linked_to_another_account():
    h = Harness()
    a, b = reg(h, "a@ex.com"), reg(h, "b@ex.com")
    h.verify_by_telegram(a, TG)
    _, tb = h.tg_link(b)
    assert h.tg_start(TG, tb).status == 200
    assert user(h, b)["verified"] is False and "telegram" not in user(h, b)
    assert h.store.tg_links[str(TG)]["user"] == h.store.by_email[a]
    assert digest(tb) in h.store.tg_tokens                                       # token not burned by the rejected attempt
    assert h.tg_start(TG + 9, tb).status == 200 and user(h, b)["verified"] is True


def test_username_is_never_used_for_identity():
    h = Harness()
    e = reg(h)
    _, tok = h.tg_link(e)
    upd = {"message": {"from": {"id": TG, "is_bot": False, "username": "victim"}, "chat": {"id": TG, "type": "private"}, "text": "/start " + tok}}
    h.call("POST", "/telegram/webhook", upd, headers={"X-Telegram-Bot-Api-Secret-Token": h.tg.webhook_secret})
    assert "victim" not in repr(h.store.users) + repr(h.store.tg_links)


@pytest.mark.parametrize("secret", [None, "", "wrong-secret-0123456789abcdef", "x"])
def test_webhook_rejects_missing_or_wrong_secret(secret):
    h = Harness()
    e = reg(h)
    _, tok = h.tg_link(e)
    hd = {} if secret is None else {"X-Telegram-Bot-Api-Secret-Token": secret}
    r = h.call("POST", "/telegram/webhook", {"message": {"from": {"id": TG}, "chat": {"id": TG, "type": "private"}, "text": "/start " + tok}}, headers=hd)
    assert r.status == 401 and user(h, e)["verified"] is False and h.tg.sender.sent == []


def test_webhook_malformed_requests():
    h = Harness()
    e = reg(h)
    _, tok = h.tg_link(e)
    s = {"X-Telegram-Bot-Api-Secret-Token": h.tg.webhook_secret}
    assert h.call("POST", "/telegram/webhook", raw=b"{not json", headers=s, check=False).status in (400, 422)
    assert h.call("POST", "/telegram/webhook", [1, 2], headers=s, check=False).status in (400, 422)
    ok = {"from": {"id": TG, "is_bot": False}, "chat": {"id": TG, "type": "private"}}
    for upd in ({}, {"message": "x"}, {"message": {**ok, "text": 5}},
                {"message": {"from": {"id": "5"}, "chat": {"id": 5, "type": "private"}, "text": "/start " + tok}},
                {"message": {"from": {"id": True}, "chat": {"id": 1, "type": "private"}, "text": "/start " + tok}},
                {"message": {"from": {"id": TG, "is_bot": True}, "chat": {"id": TG, "type": "private"}, "text": "/start " + tok}},
                {"message": {"from": {"id": TG}, "chat": {"id": TG, "type": "group"}, "text": "/start " + tok}},
                {"message": {"from": {"id": TG}, "chat": {"id": TG + 1, "type": "private"}, "text": "/start " + tok}},
                {"message": {**ok, "forward_origin": {}, "text": "/start " + tok}},
                {"edited_message": {**ok, "text": "/start " + tok}}):
        assert h.call("POST", "/telegram/webhook", upd, headers=s).status == 200
    assert user(h, e)["verified"] is False and h.tg.sender.sent == []


def test_start_without_token_gets_generic_help():
    h = Harness()
    assert h.tg_start(TG, "", text="/start").status == 200
    assert h.tg.sender.sent and h.store.tg_links == {}


def test_unverified_account_has_no_access():
    h = Harness()
    e = reg(h)
    assert h.call("POST", "/auth/login", {"identifier": e, "password": PASSWORD}).status == 401
    assert h.call("GET", "/profile").status == 401
    assert h.call("GET", "/profile", token="not-a-session").status == 401
    assert h.call("GET", "/telegram/status").status == 401
    assert h.store.sessions == {}


def test_link_requires_password_and_is_generic():
    h = Harness()
    e = reg(h)
    wrong = h.call("POST", "/auth/telegram/link", {"identifier": e, "password": "Wrong-Password-1"})
    unknown = h.call("POST", "/auth/telegram/link", {"identifier": "nobody@ex.com", "password": PASSWORD})
    assert wrong.status == unknown.status == 401 and wrong.body["code"] == unknown.body["code"] and wrong.body["message"] == unknown.body["message"]
    assert h.store.tg_tokens == {}


def test_link_rate_limited_and_cooldown():
    h = Harness()
    e = reg(h)
    assert h.tg_link(e)[0].status == 200
    assert h.tg_link(e)[0].status == 429                                         # cooldown
    n = 0
    for _ in range(10):
        h.store.tg_limits["issue:" + h.store.by_email[e]]["t"] = [time.time() - 100 - i for i in range(5)]
        n += h.tg_link(e)[0].status == 429
    assert n == 10                                                               # 5/hour cap


def test_failed_attempts_are_rate_limited_per_telegram_id():
    h = Harness()
    e = reg(h)
    _, tok = h.tg_link(e)
    for i in range(ATTEMPTS_PER_HOUR):
        h.tg_start(TG, "y" * 32)
    assert h.tg_start(TG, tok).status == 200                                     # throttled: even the right token is refused for this sender
    assert user(h, e)["verified"] is False
    assert h.tg_start(TG + 1, tok).status == 200 and user(h, e)["verified"] is True


def test_already_verified_account_conflict_and_lockout_unchanged():
    h = Harness()
    e = reg(h)
    h.verify_by_telegram(e, TG)
    assert h.call("POST", "/auth/telegram/link", {"identifier": e, "password": PASSWORD}).status == 409
    for _ in range(12):
        h.call("POST", "/auth/telegram/link", {"identifier": "z@ex.com", "password": "bad"}, check=False)
    h.register("c@ex.com")
    for _ in range(12):
        h.call("POST", "/auth/telegram/link", {"identifier": "c@ex.com", "password": "Wrong-Password-1"})
    assert h.call("POST", "/auth/telegram/link", {"identifier": "c@ex.com", "password": PASSWORD}).status == 423   # same lockout as login


def test_notifications_need_link_and_explicit_opt_in():
    h = Harness()
    e = reg(h)
    h.verify_by_telegram(e, TG)
    t = h.login(e)
    assert h.call("PUT", "/telegram/notifications", {"enabled": True}, token=t).body == {"linked": True, "notifications": True}
    assert h.call("PUT", "/telegram/notifications", {"enabled": False}, token=t).body["notifications"] is False
    assert h.call("PUT", "/telegram/notifications", {"enabled": "yes"}, token=t).status in (400, 422)
    h2 = Harness()
    h2.store.users  # noqa: B018
    t2 = h2.login("m@ex.com")                                                    # e-mail verified, no telegram
    assert h2.call("PUT", "/telegram/notifications", {"enabled": True}, token=t2).status == 409


def test_telegram_unavailable_is_reported_without_creating_tokens():
    from tgverify.runtime import TelegramRuntime
    from tgverify.ports import DisabledSender
    h = Harness(telegram=TelegramRuntime(DisabledSender(), "", ""))
    e = reg(h)
    assert h.call("POST", "/auth/telegram/link", {"identifier": e, "password": PASSWORD}).status == 503
    assert h.call("POST", "/telegram/webhook", {}, headers={"X-Telegram-Bot-Api-Secret-Token": "anything-0123456789abcdef"}).status == 503
    assert h.store.tg_tokens == {}


def test_erase_frees_telegram_id_and_tokens():
    h = Harness()
    e = reg(h)
    h.verify_by_telegram(e, TG)
    t = h.login(e)
    assert h.call("POST", "/privacy/delete", {"password": PASSWORD, "confirm": True}, token=t).status == 202
    assert str(TG) not in h.store.tg_links
    h.register("n@ex.com")
    h.verify_by_telegram("n@ex.com", TG)                                         # the id can be reused by a new account


def test_no_health_data_in_bot_messages():
    from tgverify import webhook as W
    for t in (W.SUCCESS_TEXT, W.FAILURE_TEXT, W.HELP_TEXT):
        assert "@" not in t and "http" not in t


def test_config_validation():
    from tgverify.config import TelegramConfigError, load_telegram_config as L
    good = {"TELEGRAM_BOT_TOKEN": "123456:" + "A" * 30, "TELEGRAM_BOT_USERNAME": "@vitaforge_bot", "TELEGRAM_WEBHOOK_SECRET": "s" * 24}
    assert L(good, False)["provider"] == "live"
    assert L({}, False)["provider"] == "disabled"
    with pytest.raises(TelegramConfigError):
        L({**good, "TELEGRAM_WEBHOOK_SECRET": ""}, False)
    with pytest.raises(TelegramConfigError):
        L({**good, "TELEGRAM_PROVIDER": "capture"}, False)                       # capture only in DEBUG
    assert L({**good, "TELEGRAM_PROVIDER": "capture"}, True)["provider"] == "capture"
    with pytest.raises(TelegramConfigError):
        L({**good, "TELEGRAM_BOT_TOKEN": "garbage"}, False)
    from config.env import load_config, ConfigError
    base = {"DJANGO_SECRET_KEY": "k" * 40, "DATABASE_URL": "sqlite:///x", "REDIS_URL": "redis://x", "ALLOWED_HOSTS": "a.example"}
    with pytest.raises(ConfigError):
        load_config(base)                                                       # no SMTP, no Telegram in production
    assert load_config({**base, **good})["mail"]["provider"] == "disabled"      # Telegram live: e-mail optional


def test_dev_simulate_route_still_needs_a_real_token_and_is_dev_only():
    h = Harness()
    e = reg(h)
    assert h.call("POST", "/dev/telegram/simulate-start", {"telegram_id": TG, "token": "z" * 32}).status == 200
    assert user(h, e)["verified"] is False
    _, tok = h.tg_link(e)
    assert h.call("POST", "/dev/telegram/simulate-start", {"telegram_id": TG, "token": tok}).status == 200
    assert user(h, e)["verified"] is True
    assert h.call("GET", "/dev/telegram/outbox").body["delivered"] is False
    prod = Harness(dev=False)
    assert prod.call("POST", "/dev/telegram/simulate-start", {"telegram_id": TG, "token": "z" * 32}).status == 404
