from contract.harness import Harness


def _ready(email, goal_extra=None, equip_extra=None):
    h = Harness()
    t = h.login(email)
    h.onboard(t)
    g = {"goal": "muscle_gain", "level": "beginner", **(goal_extra or {})}
    r = h.call("PUT", "/onboarding/steps/2", {"answers": g}, token=t, check=False)
    return h, t, r


def test_invalid_priority_and_environment_rejected():
    h, t, _ = _ready("pri@ex.com")
    bad = lambda a, n: h.call("PUT", f"/onboarding/steps/{n}", {"answers": a}, token=t, check=False).status
    assert bad({"goal": "strength", "level": "beginner", "priority_muscles": ["nope"]}, 2) == 422
    assert bad({"goal": "strength", "level": "beginner", "priority_muscles": ["chest"] * 4}, 2) == 422
    assert bad({"equipment": [], "environment": "moon"}, 4) == 422
    assert bad({"equipment": [], "environment": "home"}, 4) == 200


def _reasons(h, t):
    h.call("POST", "/onboarding/complete", token=t)
    gen = h.call("POST", "/workouts/generate", {"preferred_structure": "auto"}, token=t, check=False).body
    return gen


def test_priority_muscle_is_a_preference_not_an_override():
    h, t, r = _ready("pri2@ex.com", {"priority_muscles": ["chest"]})
    assert r.status == 200
    gen = _reasons(h, t)
    assert gen["decision"]["status"] in ("ALLOW", "ALLOW_WITH_MODIFICATION")
    assert gen["plan"] is not None                       # still gated by the Safety Core; priority never bypasses it
