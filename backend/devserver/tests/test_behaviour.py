"""Behaviour of the dev adapter that the contract suite does not pin down (security, privacy, safety, idempotency).

All calls go through contract.harness, i.e. every response is additionally validated against the OpenAPI document.
"""
import io
import re
import time

from contract.harness import PASSWORD, Harness
from contract.scenarios import happy_path
from devserver.app import SCREENING, pub


def test_password_reset_is_single_use_revokes_sessions_and_needs_a_strong_password():
    h = Harness()
    old = h.login("u@ex.com")
    h.call("POST", "/auth/password-reset/request", {"identifier": "u@ex.com"})
    tok = h.captured("u@ex.com", "password_reset")["secret"]
    assert h.call("POST", "/auth/password-reset/confirm", {"token": tok, "new_password": "alllowercase1"}).status in (400, 422)   # weak (rule beyond minLength)
    assert h.call("POST", "/auth/password-reset/confirm", {"token": tok, "new_password": "N3wStrongPassword"}).status == 200
    assert h.call("POST", "/auth/password-reset/confirm", {"token": tok, "new_password": "N3wStrongPassword"}).status == 400      # single use
    assert h.call("GET", "/profile", token=old).status == 401                                                                    # sessions revoked
    assert h.call("POST", "/auth/login", {"identifier": "u@ex.com", "password": "N3wStrongPassword"}).status == 200
    assert h.problems == []


def test_profile_preferences_roundtrip_and_validation():
    h = Harness(); t = h.login("p@ex.com")
    r = h.call("PATCH", "/profile", {"display_name": "Sara", "country": "IR", "timezone": "Asia/Tehran", "calendar": "jalali", "digit_style": "persian", "language": "en"}, token=t)
    assert r.status == 200 and r.body["language"] == "en" and r.body["calendar"] == "jalali" and r.body["onboarding_status"] == "not_started"
    assert h.call("PATCH", "/profile", {"language": "xx"}, token=t).status == 400
    assert h.call("GET", "/profile", token=t).body["display_name"] == "Sara"


def test_consent_is_append_only_and_withdrawal_blocks_health_endpoints_again():
    h = Harness(); t = h.login("c@ex.com")
    docs = h.call("GET", "/consents/documents", token=t).body
    assert {d["type"] for d in docs} == {"terms", "health_data"} and all("OPEN-004" in d["body"] and d["version"] == 0 for d in docs)
    d = next(x for x in docs if x["type"] == "health_data")
    assert h.call("GET", "/health/profile", token=t).status == 403
    assert h.call("POST", "/consents", {"document_id": d["id"], "granted": True}, token=t).status == 201
    assert h.call("GET", "/health/profile", token=t).status == 200
    r = h.call("POST", "/consents", {"document_id": d["id"], "granted": False}, token=t)
    assert r.status == 201 and r.body["granted"] is False
    assert h.call("GET", "/health/profile", token=t).status == 403
    assert len([c for c in h.store.consents if c["type"] == "health_data_processing"]) == 2          # history kept, nothing overwritten
    assert all(c["at"] for c in h.store.consents)


def test_ai_chat_policy_free_vs_pro_and_production_fallback():
    h = Harness(); t = h.login("ai@ex.com"); h.onboard(t); h.call("POST", "/onboarding/complete", token=t)
    assert h.call("POST", "/workouts/generate", {}, token=t).body["plan"]
    uid = h.store.by_email["ai@ex.com"]
    medical = h.call("POST", "/ai/chat", {"purpose": "general", "message": "can you diagnose my knee"}, token=t)
    assert medical.status == 200 and medical.body["mode"] == "rule_based_fallback" and medical.problems == []
    why = h.call("POST", "/ai/chat", {"purpose": "explain_plan", "message": "why this plan?"}, token=t)
    assert why.status == 200 and why.body["mode"] == "rule_based_fallback" and why.body["decision"]["status"] != "STOP_AND_REFER"   # deterministic answers are free
    assert h.call("POST", "/ai/chat", {"purpose": "general", "message": "tell me something motivating"}, token=t).status == 402
    h.app.sub.activate(uid, "pro")                                                                          # as a verified payment webhook would
    r = h.call("POST", "/ai/chat", {"purpose": "general", "message": "tell me something motivating"}, token=t)
    assert r.status == 200 and r.body["mode"] == "llm" and r.body["sources"] == []                           # dev StubProvider, no sources
    # an active safety stop beats the plan: even pro users get only the fixed safety text
    h.call("POST", "/health/pain-logs", {"region": "knee", "intensity": 7, "timing": "during"}, token=t)
    r = h.call("POST", "/ai/chat", {"purpose": "general", "message": "tell me something motivating"}, token=t)
    assert r.body["mode"] == "rule_based_fallback" and r.body["decision"]["status"] == "STOP_AND_REFER"
    assert Harness(dev=False).app.ai.provider.code == "unconfigured"


def test_admin_rules_for_plans_rule_sets_and_exercise_drafts():
    h = Harness(); tk = happy_path(h)
    free = pub("plan_code", "free")
    bad = h.call("PUT", f"/admin/plans/{free}/features", {"features": [{"code": "safety_screening", "enabled": False}]}, token=tk["admin"])
    assert bad.status in (400, 422) and bad.problems == []
    plans = {p["code"]: p for p in h.call("GET", "/subscriptions/plans").body["plans"]}
    assert next(f for f in plans["free"]["features"] if f["code"] == "safety_screening")["enabled"] is True           # unchanged
    h.store.rule_sets[11] = {"status": "draft_unreviewed"}
    rid = pub("rs", 11)
    no_ref = h.call("POST", f"/admin/safety/rule-sets/{rid}/publish", {"confirm_sources_attached": True}, token=tk["reviewer"])
    assert no_ref.status in (400, 422) and h.store.rule_sets[11]["status"] == "draft_unreviewed"                      # no expert sign-off reference, no publication
    ok = h.call("POST", f"/admin/safety/rule-sets/{rid}/publish", {"confirm_sources_attached": True, "notes": "EXP-77 signed"}, token=tk["reviewer"])
    assert ok.status == 200 and ok.body["status"] == "published" and ok.body["reviewed_by"]
    n = len(h.call("GET", "/exercises?page_size=100", token=tk["user"]).body["results"])
    h.call("POST", "/admin/exercises", {"stable_code": "draft_only", "movement_pattern": "core", "difficulty": "beginner"}, token=tk["content_admin"])
    assert len(h.call("GET", "/exercises?page_size=100", token=tk["user"]).body["results"]) == n                    # drafts are never public
    rows = h.call("GET", "/admin/users", token=tk["admin"]).body
    assert rows and all(set(u) <= {"id", "status", "roles"} for u in rows)                                         # no e-mail / health data for admins


def test_user_initiated_health_access_grant_and_only_professionals_can_be_grantees():
    h = Harness(); t = h.login("g@ex.com"); h.login("pro@ex.com", role="professional"); h.login("adm@ex.com", role="admin")
    pid = h.store.by_email["pro@ex.com"]
    assert h.call("POST", "/health/access-grants", {"professional_id": pid}, token=t).status == 200
    assert h.call("POST", "/health/access-grants", {"professional_id": h.store.by_email["adm@ex.com"]}, token=t).status == 404


def test_privacy_export_excludes_secrets_and_erasure_needs_password_and_removes_everything():
    h = Harness(); t = h.login("e@ex.com"); h.onboard(t)
    h.call("POST", "/body/measurements", {"metric": "weight", "value": 70, "unit": "kg", "source": "measured"}, token=t)
    ex = h.call("POST", "/privacy/export", token=t)
    assert ex.status == 202 and ex.body["status"] == "requested"                                    # no delivery endpoint in DOC-07 (OPEN-009)
    stored = next(iter(h.store.privacy_requests.values()))["data"]
    flat = str(stored)
    assert "pw" not in flat and "scrypt" not in flat and stored["metrics"] and "e@ex.com" in flat
    assert h.call("POST", "/privacy/delete", {"password": "wrong-password-1", "confirm": True}, token=t).status == 400
    assert h.call("GET", "/profile", token=t).status == 200
    uid = h.store.by_email["e@ex.com"]
    d = h.call("POST", "/privacy/delete", {"password": PASSWORD, "confirm": True}, token=t)
    assert d.status == 202 and d.body["status"] == "completed"
    assert h.call("GET", "/profile", token=t).status == 401
    assert uid not in h.store.users and "e@ex.com" not in h.store.by_email and uid not in h.store.metrics and uid not in h.store.health
    assert h.call("POST", "/auth/login", {"identifier": "e@ex.com", "password": PASSWORD}).status == 401


def test_set_logging_is_idempotent_and_handles_skipped_and_timed_sets():
    h = Harness(); t = happy_path(h)["user"]
    plan = h.call("GET", "/workouts/current", token=t).body
    day = plan["days"][1]
    ss = h.call("POST", "/workouts/sessions", {"day_id": day["day_id"]}, token=t).body
    e = day["exercises"][0]["exercise_id"]
    body = {"client_uuid": "abcdefab-abcd-4abc-8abc-abcdefabcdef", "exercise_id": e, "set_no": 1, "reps": 10, "load_kg": 30}
    a = h.call("POST", f"/workouts/sessions/{ss['id']}/logs", body, token=t)
    b = h.call("POST", f"/workouts/sessions/{ss['id']}/logs", body, token=t)                         # offline retry
    assert a.status == b.status == 201 and a.body == b.body
    assert len(h.store.workout_sessions[next(k for k in h.store.workout_sessions if pub("wks", k) == ss["id"])]["logs"]) == 1
    sk = h.call("POST", f"/workouts/sessions/{ss['id']}/logs", {"client_uuid": "abcdefab-abcd-4abc-8abc-abcdefabcde1", "exercise_id": e, "set_no": 2, "skipped": True}, token=t)
    tm = h.call("POST", f"/workouts/sessions/{ss['id']}/logs", {"client_uuid": "abcdefab-abcd-4abc-8abc-abcdefabcde2", "exercise_id": e, "set_no": 3, "duration_sec": 45}, token=t)
    bad = h.call("POST", f"/workouts/sessions/{ss['id']}/logs", {"client_uuid": "abcdefab-abcd-4abc-8abc-abcdefabcde3", "exercise_id": e, "set_no": 4}, token=t)
    assert sk.status == tm.status == 201 and sk.body["personal_record"] is False and tm.body["personal_record"] is False
    assert bad.status == 422                                                                           # neither reps, duration nor skipped
    fin = h.call("POST", f"/workouts/sessions/{ss['id']}/finish", {"aborted_reason": "fatigue"}, token=t).body
    assert fin["sets_done"] == 2 and fin["volume_kg"] == 300                                           # skipped sets are not counted
    assert next(s for s in h.call("GET", "/workouts/sessions", token=t).body if s["id"] == ss["id"])["status"] == "aborted"
    assert h.problems == []


def test_login_cookie_is_secure_outside_dev_and_expiry_is_enforced():
    h = Harness(dev=False, allow=False)
    h.register("s@ex.com"); h.store.users[h.store.by_email["s@ex.com"]]["verified"] = True
    r = h.call("POST", "/auth/login", {"identifier": "s@ex.com", "password": PASSWORD})
    assert all("Secure" in c for c in r.headers["Set-Cookie"].split("\n"))
    exp = int(time.mktime(time.strptime(r.body["expires_at"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone)
    assert 13 * 86400 < exp - time.time() <= 14 * 86400 + 5


def test_dashboard_surfaces_the_blocking_decision_as_an_alert():
    h = Harness(); t = h.login("d@ex.com"); h.onboard(t); h.call("POST", "/onboarding/complete", token=t)
    assert h.call("GET", "/dashboard", token=t).body["alerts"] == []
    h.call("POST", "/health/pain-logs", {"region": "knee", "intensity": 7, "timing": "during"}, token=t)
    d = h.call("GET", "/dashboard", token=t)
    assert d.problems == [] and d.body["alerts"][0]["status"] == "STOP_AND_REFER"


def test_nutrition_explain_progression_routes():
    h = Harness(); t = h.login("n@ex.com"); h.onboard(t); h.call("POST", "/onboarding/complete", token=t)
    n = {"sex": "male", "height_cm": 180, "weight_kg": 80, "activity": "moderate", "goal": "lose",
         "screening": {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}}
    body = h.call("PUT", "/nutrition/profile", n, token=t).body
    assert body["status"] == "OK" and body["goal_adjustment"] == "disabled_pending_expert_review" and "not_medical_advice" in body["labels"]
    assert h.call("POST", "/nutrition/meals", {"slot": "breakfast", "name": "Oats", "kcal": 350, "protein_g": 12}, token=t).status == 201
    h.call("POST", "/nutrition/water", {"ml": 500}, token=t)
    sm = h.call("GET", "/nutrition/summary", token=t).body
    assert sm["kcal"] == 350 and sm["water_ml"] == 500
    n2 = {**n, "screening": {**n["screening"], "eating_disorder_risk": True}}
    assert h.call("PUT", "/nutrition/profile", n2, token=t).body["status"] == "REFER"
    for m, path, body in (("POST", "/nutrition/meals", {"slot": "lunch", "name": "Rice", "kcal": 300}), ("GET", "/nutrition/meals", None), ("GET", "/nutrition/summary", None)):
        assert h.call(m, path, body, token=t).status == 409          # no calorie tracking for a REFER (eating-disorder risk) profile
    ex = h.call("GET", "/safety/explain", token=t).body
    assert ex["status"] in ("ALLOW", "ALLOW_WITH_MODIFICATION") and ex["items"] and all("why" in i for i in ex["items"])
    assert h.call("GET", "/workouts/progression", token=t).status == 404          # no plan yet
    assert h.call("POST", "/workouts/generate", {}, token=t).status == 200
    prog = h.call("GET", "/workouts/progression", token=t).body["items"]
    assert prog and all(i["action"] == "insufficient_data" for i in prog)


def test_static_index_served_with_security_headers():
    h = Harness(); out = {}
    env = {"REQUEST_METHOD": "GET", "PATH_INFO": "/", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b"")}
    body = b"".join(h.app(env, lambda st, hd: out.update(st=st, h=dict(hd))))
    assert out["st"].startswith("200") and b'dir="rtl"' in body and "Content-Security-Policy" in out["h"]


def test_session_history_carries_logged_sets_and_outcome_for_resuming_and_the_history_page():
    h = Harness(); t = happy_path(h)["user"]
    day = h.call("GET", "/workouts/current", token=t).body["days"][0]
    ss = h.call("POST", "/workouts/sessions", {"day_id": day["day_id"]}, token=t).body
    e = day["exercises"][1]["exercise_id"]
    h.call("POST", f"/workouts/sessions/{ss['id']}/logs", {"client_uuid": "abcdefab-abcd-4abc-8abc-abcdefabcd01", "exercise_id": e, "set_no": 1, "reps": 8, "load_kg": 20}, token=t)
    row = next(s for s in h.call("GET", "/workouts/sessions", token=t).body if s["id"] == ss["id"])
    assert row["status"] == "in_progress" and row["sets_done"] == 1 and row["volume_kg"] == 160 and row["day_title"]
    assert row["logged_sets"] == [{"exercise_id": e, "set_no": 1, "reps": 8, "load_kg": 20.0, "skipped": False, "personal_record": False}]
    h.call("POST", f"/workouts/sessions/{ss['id']}/finish", {"aborted_reason": "pain", "perceived_difficulty": 7}, token=t)
    row = next(s for s in h.call("GET", "/workouts/sessions", token=t).body if s["id"] == ss["id"])
    assert row["status"] == "aborted" and row["aborted_reason"] == "pain" and row["perceived_difficulty"] == 7
    assert h.call("POST", f"/workouts/sessions/{ss['id']}/logs", {"client_uuid": "abcdefab-abcd-4abc-8abc-abcdefabcd02", "exercise_id": e, "set_no": 2, "reps": 8}, token=t).status == 409
    assert h.problems == []


def test_exercise_list_labels_review_status_and_filters_by_pattern_and_equipment():
    h = Harness(); t = happy_path(h)["user"]
    rows = h.call("GET", "/exercises?page_size=100", token=t).body["results"]
    assert rows and all(r["review_status"] for r in rows)
    assert all(r["review_status"] != "published" for r in rows)                  # dev content is never presented as reviewed
    pat = rows[0]["movement_pattern"]
    only = h.call("GET", f"/exercises?pattern={pat}&page_size=100", token=t).body["results"]
    assert only and all(r["movement_pattern"] == pat for r in only)
    assert h.problems == []
