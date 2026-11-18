"""Admin panel: roles (owner vs admin), media overrides, uploads, staff management, audit. Non-OpenAPI routes (op=None)."""
import base64
import io

import pytest

from contract.harness import Harness

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


@pytest.fixture()
def env():
    h = Harness()
    return h, h.login("owner@ex.com", role="super_admin"), h.login("adm@ex.com", role="admin"), h.login("user@ex.com")


def call(h, m, p, t=None, body=None, **kw):
    return h.call(m, p, body, token=t, check=False, **kw)


def test_public_overrides_readable_without_login_and_empty(env):
    h, *_ = env
    r = call(h, "GET", "/media/overrides")
    assert r.status == 200 and r.body == {"overrides": {}}


def test_plain_user_is_forbidden_everywhere(env):
    h, o, a, u = env
    for m, p, b in (("PUT", "/admin/media/bird_dog", {"photo": False}), ("POST", "/admin/media-bulk", {"codes": ["bird_dog"], "set": {"photo": False}}),
                    ("POST", "/admin/media-files", {"data_base64": base64.b64encode(PNG).decode()}), ("GET", "/admin/staff", None), ("GET", "/admin/audit", None)):
        assert call(h, m, p, u, b).status == 403, (m, p)
    assert call(h, "GET", "/admin/staff").status == 401


def test_admin_controls_media_and_public_view_reflects_it(env):
    h, o, a, u = env
    r = call(h, "PUT", "/admin/media/bird_dog", a, {"anim3d": False, "default": "video", "video_id": "dQw4w9WgXcQ", "note": "3D wrong"})
    assert r.status == 200 and r.body["anim3d"] is False and r.body["default"] == "video"
    pub = call(h, "GET", "/media/overrides").body["overrides"]["bird_dog"]
    assert pub["anim3d"] is False and "updated_by" not in pub
    assert call(h, "DELETE", "/admin/media/bird_dog", a).status == 200
    assert call(h, "GET", "/media/overrides").body["overrides"] == {}
    assert call(h, "DELETE", "/admin/media/bird_dog", a).status == 404


@pytest.mark.parametrize("body", [{"evil": 1}, {"photo": "yes"}, {"default": "gif"}, {"video_id": "short"}, {"note": "<script>"}, {"photo_file": "mf-00000000"},
                                  {"default": "photo", "photo": False}])
def test_invalid_override_rejected(env, body):
    h, o, a, u = env
    assert call(h, "PUT", "/admin/media/bird_dog", a, body).status in (400, 422)
    assert call(h, "GET", "/media/overrides").body["overrides"] == {}


def test_bulk_and_bad_code(env):
    h, o, a, u = env
    assert call(h, "POST", "/admin/media-bulk", a, {"codes": ["a_b", "c_d"], "set": {"anim3d": False}}).body == {"updated": 2}
    assert set(call(h, "GET", "/media/overrides").body["overrides"]) == {"a_b", "c_d"}
    assert call(h, "POST", "/admin/media-bulk", a, {"codes": ["a_b"], "set": {"note": "x"}}).status in (400, 422)   # per-exercise fields are not bulk-settable
    assert call(h, "PUT", "/admin/media/Bad%20Code", a, {"photo": True}).status in (400, 422)


def test_upload_serve_and_attach(env):
    h, o, a, u = env
    up = call(h, "POST", "/admin/media-files", a, {"data_base64": base64.b64encode(PNG).decode(), "name": "x.png"})
    assert up.status == 200 and up.body["mime"] == "image/png"
    fid = up.body["id"]
    assert call(h, "PUT", "/admin/media/bird_dog", a, {"photo_file": fid}).status == 200
    assert call(h, "DELETE", f"/admin/media-files/{fid}", a).status == 409      # in use
    # served raw, publicly, with the sniffed type and nosniff
    out = {}
    env_ = {"REQUEST_METHOD": "GET", "PATH_INFO": f"/api/v1/media/files/{fid}", "QUERY_STRING": "", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b"")}
    body = b"".join(h.app(env_, lambda s, hd: out.update(status=s, headers=dict(hd))))
    assert out["status"].startswith("200") and body == PNG and out["headers"]["Content-Type"] == "image/png" and out["headers"]["X-Content-Type-Options"] == "nosniff"


def test_upload_rejects_svg_html_garbage_and_oversize(env):
    h, o, a, u = env
    for data in (b"<svg onload=alert(1)/>", b"<html></html>", b"GIF89a....", b""):
        assert call(h, "POST", "/admin/media-files", a, {"data_base64": base64.b64encode(data).decode()}).status in (400, 422)
    assert call(h, "POST", "/admin/media-files", a, {"data_base64": "!!notb64"}).status in (400, 422)
    big = base64.b64encode(PNG + b"\x00" * 310_000).decode()
    assert call(h, "POST", "/admin/media-files", a, {"data_base64": big}).status in (400, 413, 422)


def test_only_owner_manages_admins(env):
    h, o, a, u = env
    assert call(h, "GET", "/admin/staff", a).status == 403 and call(h, "POST", "/admin/staff", a, {"email": "user@ex.com"}).status == 403
    assert call(h, "POST", "/admin/staff", o, {"email": "user@ex.com"}).body["role"] == "admin"
    # the new admin can now manage media but still not staff
    assert call(h, "PUT", "/admin/media/x_y", u, {"photo": True}).status == 200
    assert call(h, "GET", "/admin/staff", u).status == 403
    assert call(h, "POST", "/admin/staff", o, {"email": "nobody@ex.com"}).status == 404
    uid = h.store.by_email["user@ex.com"]
    assert call(h, "DELETE", f"/admin/staff/{uid}", o).status == 200
    assert call(h, "PUT", "/admin/media/x_y", u, {"photo": True}).status == 403           # demoted immediately


def test_owner_and_reviewer_roles_are_protected(env):
    h, o, a, u = env
    h.login("rev@ex.com", role="clinical_safety_reviewer")
    assert call(h, "POST", "/admin/staff", o, {"email": "rev@ex.com"}).status == 409
    assert call(h, "POST", "/admin/staff", o, {"email": "owner@ex.com"}).status == 409
    oid = h.store.by_email["owner@ex.com"]
    assert call(h, "DELETE", f"/admin/staff/{oid}", o).status == 404


def test_audit_trail_owner_only_and_complete(env):
    h, o, a, u = env
    call(h, "PUT", "/admin/media/bird_dog", a, {"anim3d": False})
    call(h, "POST", "/admin/staff", o, {"email": "user@ex.com"})
    assert call(h, "GET", "/admin/audit", a).status == 403
    rows = call(h, "GET", "/admin/audit", o).body["entries"]
    assert [r["action"] for r in rows] == ["staff.add_admin", "media.update"]
    assert rows[1]["before"] == {} and rows[1]["after"] == {"anim3d": False}
    assert "password" not in str(rows).lower()


def test_admin_me_reports_role(env):
    h, o, a, u = env
    assert call(h, "GET", "/admin/me", o).body["role"] == "super_admin" and call(h, "GET", "/admin/me", u).body["role"] == "user"


def test_owner_bootstrap_by_verified_email_only_once(monkeypatch):
    h = Harness()
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAIL", "Boss@Ex.com")
    other = h.login("someone@ex.com")
    assert call(h, "GET", "/admin/me", other).body["role"] == "user"                      # a different email never gets it
    boss = h.login("boss@ex.com")
    assert call(h, "GET", "/admin/me", boss).body["role"] == "super_admin"
    assert call(h, "GET", "/admin/staff", boss).status == 200
    assert [r["action"] for r in call(h, "GET", "/admin/audit", boss).body["entries"]] == ["owner.bootstrap"]


def test_owner_bootstrap_never_when_owner_exists_or_unset(monkeypatch):
    h = Harness()
    h.login("owner@ex.com", role="super_admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAIL", "late@ex.com")
    assert call(h, "GET", "/admin/me", h.login("late@ex.com")).body["role"] == "user"      # an owner already exists
    monkeypatch.delenv("ADMIN_BOOTSTRAP_EMAIL")
    h2 = Harness()
    assert call(h2, "GET", "/admin/me", h2.login("late@ex.com")).body["role"] == "user"    # not configured
