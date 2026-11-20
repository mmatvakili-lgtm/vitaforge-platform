"""Admin panel services: per-exercise media overrides, uploaded media files, staff management and an audit trail.

Roles: `super_admin` (the single owner, "مدیریت") can do everything an `admin` can, plus add/remove admins and read the audit log.
`admin` manages content (media overrides, uploads). Nobody here can approve exercises/plans: that stays with Safety Core and the review roles.
Every change is recorded in `store.audit` (who, what, before/after); raw tokens/passwords are never stored.
"""
from __future__ import annotations

import base64
import binascii
import re
from typing import Optional

from .errors import Conflict, Forbidden, NotFound, ValidationFailed

OWNER, ADMIN = "super_admin", "admin"
CONTENT_ROLES = (OWNER, ADMIN)
VIEWS = ("photo", "video", "3d")
FLAGS = ("photo", "video", "anim3d")
CODE = re.compile(r"^[a-z0-9][a-z0-9_]{1,63}$")
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
FILE_ID = re.compile(r"^mf-[A-Za-z0-9_-]{8,40}$")
MAX_FILE = 300_000            # bytes after decoding (kept small: files live in the database on the free tier)
MAX_FILES = 400
MAX_NOTE = 200
KEYS = {"photo", "video", "anim3d", "default", "video_id", "video_title", "photo_file", "note", "reviewed"}
PUBLIC_KEYS = ("photo", "video", "anim3d", "default", "video_id", "video_title", "photo_file", "note", "reviewed")


def _sniff(data: bytes) -> Optional[str]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None                                  # SVG/GIF/HTML etc. are refused: only raster formats we can verify by magic bytes


class AdminPanel:
    def __init__(self, store, clock):
        self.s, self.clock = store, clock
        for n in ("media_overrides", "media_files", "site_settings"):
            self.s.__dict__.setdefault(n, {})

    # ------------------------------------------------------------------ access
    @staticmethod
    def need_content(role: str):
        if role not in CONTENT_ROLES:
            raise Forbidden()

    @staticmethod
    def need_owner(role: str):
        if role != OWNER:
            raise Forbidden()

    def _log(self, actor: str, action: str, target: str, before=None, after=None):
        self.s.audit.append({"kind": "admin_action", "at": int(self.clock()), "actor": actor, "action": action, "target": target,
                             "before": before, "after": after})

    def claim_owner(self, uid: str, bootstrap_email: Optional[str]) -> str:
        """Owner bootstrap for hosts without a shell: the VERIFIED account whose email equals ADMIN_BOOTSTRAP_EMAIL becomes the owner,
        but only while no owner exists (so it can never take over later). Returns the user's role."""
        u = self.s.users[uid]
        be = (bootstrap_email or "").strip().lower()
        if be and u.get("verified") and (u.get("email") or "").lower() == be and u["role"] == "user" \
                and not any(x["role"] == OWNER for x in self.s.users.values()):
            u["role"] = OWNER
            self._log(uid, "owner.bootstrap", uid, "user", OWNER)
        return u["role"]

    # ------------------------------------------------------------------ media overrides
    def public_overrides(self) -> dict:
        return {"overrides": {c: {k: o.get(k) for k in PUBLIC_KEYS if o.get(k) is not None} for c, o in sorted(self.s.media_overrides.items())}}

    def _clean(self, body: dict) -> dict:
        if not isinstance(body, dict) or set(body) - KEYS:
            raise ValidationFailed("unknown_field")                           # mass-assignment protection
        out: dict = {}
        for k in FLAGS + ("reviewed",):
            if k in body:
                if body[k] is not None and not isinstance(body[k], bool):
                    raise ValidationFailed(k)
                out[k] = body[k]
        if "default" in body:
            if body["default"] is not None and body["default"] not in VIEWS:
                raise ValidationFailed("default")
            out["default"] = body["default"]
        if "video_id" in body:
            v = body["video_id"]
            if v is not None and not (isinstance(v, str) and YT_ID.match(v)):
                raise ValidationFailed("video_id")
            out["video_id"] = v
        for k, lim in (("video_title", 150), ("note", MAX_NOTE)):
            if k in body:
                v = body[k]
                if v is not None and not (isinstance(v, str) and len(v) <= lim and "<" not in v and ">" not in v):
                    raise ValidationFailed(k)
                out[k] = v or None
        if "photo_file" in body:
            v = body["photo_file"]
            if v is not None and not (isinstance(v, str) and FILE_ID.match(v) and v in self.s.media_files):
                raise ValidationFailed("photo_file")
            out["photo_file"] = v
        return out

    def _apply(self, actor: str, code: str, patch: dict):
        cur = dict(self.s.media_overrides.get(code, {}))
        new = {**cur, **patch}
        new = {k: v for k, v in new.items() if v is not None}                 # None = back to the default behaviour
        if new.get("default") == "photo" and new.get("photo") is False:
            raise ValidationFailed("default_is_disabled")
        if new.get("default") == "video" and new.get("video") is False:
            raise ValidationFailed("default_is_disabled")
        if new.get("default") == "3d" and new.get("anim3d") is False:
            raise ValidationFailed("default_is_disabled")
        if new == cur:
            return cur
        if new:
            new["updated_by"], new["updated_at"] = actor, int(self.clock())
            self.s.media_overrides[code] = new
        else:
            self.s.media_overrides.pop(code, None)
        self._log(actor, "media.update", code, {k: v for k, v in cur.items() if k in PUBLIC_KEYS}, {k: v for k, v in new.items() if k in PUBLIC_KEYS})
        return new

    def put_override(self, role: str, actor: str, code: str, body: dict):
        self.need_content(role)
        if not CODE.match(code or ""):
            raise ValidationFailed("code")
        self._apply(actor, code, self._clean(body))
        return self.public_overrides()["overrides"].get(code, {})

    def reset_override(self, role: str, actor: str, code: str):
        self.need_content(role)
        old = self.s.media_overrides.pop(code, None)
        if old is None:
            raise NotFound()
        self._log(actor, "media.reset", code, {k: v for k, v in old.items() if k in PUBLIC_KEYS}, None)
        return {"message": "reset"}

    def bulk(self, role: str, actor: str, body: dict):
        self.need_content(role)
        if not isinstance(body, dict) or set(body) - {"codes", "set"}:
            raise ValidationFailed("bulk")
        codes, patch = body.get("codes"), body.get("set")
        if not isinstance(codes, list) or not 1 <= len(codes) <= 300 or len(set(codes)) != len(codes) or not all(isinstance(c, str) and CODE.match(c) for c in codes):
            raise ValidationFailed("codes")
        patch = self._clean(patch)
        if set(patch) - set(FLAGS) - {"default", "reviewed"}:
            raise ValidationFailed("bulk_fields")                             # a video id / uploaded file / note is per exercise, never bulk
        for c in codes:
            self._apply(actor, c, patch)
        return {"updated": len(codes)}

    # ------------------------------------------------------------------ uploaded files
    def upload(self, role: str, actor: str, body: dict):
        self.need_content(role)
        if not isinstance(body, dict) or set(body) - {"data_base64", "name"}:
            raise ValidationFailed("upload")
        raw = body.get("data_base64")
        if not isinstance(raw, str) or len(raw) > MAX_FILE * 4 // 3 + 8:
            raise ValidationFailed("too_large")
        try:
            data = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            raise ValidationFailed("base64")
        mime = _sniff(data)
        if mime is None or not data:
            raise ValidationFailed("file_type")
        if len(data) > MAX_FILE:
            raise ValidationFailed("too_large")
        if len(self.s.media_files) >= MAX_FILES:
            raise Conflict("too_many_files")
        fid = self.s.new_id("mf")
        fid = "mf-" + re.sub(r"[^A-Za-z0-9_-]", "", fid.split("-", 1)[-1] or "0").rjust(8, "0")
        name = str(body.get("name") or "")[:80]
        self.s.media_files[fid] = {"mime": mime, "b64": raw, "size": len(data), "by": actor, "at": int(self.clock()), "name": re.sub(r"[<>\"'\\]", "", name)}
        self._log(actor, "media.upload", fid, None, {"size": len(data), "mime": mime})
        return {"id": fid, "url": f"/api/v1/media/files/{fid}", "size": len(data), "mime": mime}

    def file(self, fid: str):
        f = self.s.media_files.get(fid) if FILE_ID.match(fid or "") else None
        if not f:
            raise NotFound()
        return f["mime"], base64.b64decode(f["b64"])

    def list_files(self, role: str):
        self.need_content(role)
        used = {o.get("photo_file") for o in self.s.media_overrides.values()}
        return {"files": [{"id": i, "mime": f["mime"], "size": f["size"], "name": f.get("name", ""), "in_use": i in used} for i, f in sorted(self.s.media_files.items())]}

    def delete_file(self, role: str, actor: str, fid: str):
        self.need_content(role)
        if fid not in self.s.media_files:
            raise NotFound()
        if any(o.get("photo_file") == fid for o in self.s.media_overrides.values()):
            raise Conflict("file_in_use")
        del self.s.media_files[fid]
        self._log(actor, "media.file_delete", fid)
        return {"message": "deleted"}

    # ------------------------------------------------------------------ dashboard statistics (aggregates only: no emails, no health data)
    def stats(self, role: str, days: int = 14) -> dict:
        self.need_content(role)
        now = int(self.clock())
        day = 86400
        today = now // day
        users = list(self.s.users.values())
        joined = {today - i: 0 for i in range(days)}
        for u in users:
            d = (u.get("created") or 0) // day
            if d in joined:
                joined[d] += 1
        acts = {today - i: 0 for i in range(days)}
        for a in self.s.audit:
            if a.get("kind") == "admin_action" and (a.get("at") or 0) // day in acts:
                acts[a["at"] // day] += 1
        roles: dict = {}
        for u in users:
            roles[u["role"]] = roles.get(u["role"], 0) + 1
        ex: dict = {}
        for m in getattr(self.s, "exercise_meta", {}).values():
            ex[m["status"]] = ex.get(m["status"], 0) + 1
        ann = self.s.site_settings.get("announcement") or {}
        return {
            "generated_at": now,
            "users": {"total": len(users), "verified": sum(1 for u in users if u.get("verified")), "roles": roles,
                      "locales": {k: sum(1 for u in users if u.get("locale") == k) for k in ("fa", "en")},
                      "joined_per_day": [{"day": d * day, "count": c} for d, c in sorted(joined.items())]},
            "activity": {"assessments": len(getattr(self.s, "assessments", {})), "plans": len(getattr(self.s, "plans", {})), "workout_sessions": len(getattr(self.s, "workout_sessions", {})),
                         "pain_logs": len(getattr(self.s, "pain_logs", {}))},
            "content": {"exercises_by_status": ex, "media_overrides": len(self.s.media_overrides), "uploaded_files": len(self.s.media_files),
                        "uploaded_bytes": sum(f.get("size", 0) for f in self.s.media_files.values()),
                        "announcement_active": bool(ann.get("enabled"))},
            "admin_actions_per_day": [{"day": d * day, "count": c} for d, c in sorted(acts.items())],
        }

    # ------------------------------------------------------------------ site announcement
    def public_announcement(self) -> dict:
        a = self.s.site_settings.get("announcement")
        if not a or not a.get("enabled") or (a.get("expires_at") and int(self.clock()) >= a["expires_at"]):
            return {"announcement": None}
        return {"announcement": {k: a.get(k) for k in ("text_fa", "text_en", "level")}}

    def get_announcement(self, role: str) -> dict:
        self.need_content(role)
        a = self.s.site_settings.get("announcement") or {"enabled": False, "text_fa": "", "text_en": "", "level": "info", "expires_at": None}
        return {k: a.get(k) for k in ("enabled", "text_fa", "text_en", "level", "expires_at")}

    def put_announcement(self, role: str, actor: str, body: dict):
        self.need_content(role)
        if not isinstance(body, dict) or set(body) - {"enabled", "text_fa", "text_en", "level", "expires_at"}:
            raise ValidationFailed("unknown_field")
        new = {"enabled": body.get("enabled"), "level": body.get("level", "info"), "expires_at": body.get("expires_at")}
        if not isinstance(new["enabled"], bool) or new["level"] not in ("info", "warning"):
            raise ValidationFailed("announcement")
        if new["expires_at"] is not None and not (isinstance(new["expires_at"], int) and not isinstance(new["expires_at"], bool) and new["expires_at"] > 0):
            raise ValidationFailed("expires_at")
        for k in ("text_fa", "text_en"):
            v = body.get(k, "")
            if not isinstance(v, str) or len(v) > 300 or "<" in v or ">" in v:
                raise ValidationFailed(k)
            new[k] = v.strip()
        if new["enabled"] and not (new["text_fa"] or new["text_en"]):
            raise ValidationFailed("text_required")
        before = self.get_announcement(role)
        self.s.site_settings["announcement"] = new
        self._log(actor, "announcement.update", "announcement", before, {k: new[k] for k in before})
        return self.get_announcement(role)

    # ------------------------------------------------------------------ users overview (owner only, masked)
    def list_users(self, role: str):
        self.need_owner(role)
        def mask(e: str) -> str:
            n, _, d = (e or "").partition("@")
            return f"{n[:1]}***@{d}" if d else "***"
        return {"users": [{"id": u["id"], "email": mask(u.get("email", "")), "role": u["role"], "verified": bool(u.get("verified"))} for u in self.s.users.values()]}

    # ------------------------------------------------------------------ staff (owner only)
    def list_staff(self, role: str):
        self.need_owner(role)
        return {"staff": [{"id": u["id"], "email": u["email"], "role": u["role"]} for u in self.s.users.values() if u["role"] in (OWNER, ADMIN)]}

    def add_admin(self, role: str, actor: str, email: str):
        self.need_owner(role)
        uid = self.s.by_email.get((email or "").strip().lower())
        u = self.s.users.get(uid) if uid else None
        if not u or not u.get("verified"):
            raise NotFound()                                                  # only an existing, verified account can be promoted
        if u["role"] == OWNER:
            raise Conflict("is_owner")
        if u["role"] not in ("user", ADMIN):
            raise Conflict("has_other_role")                                  # reviewer / professional roles are never overwritten here
        if u["role"] == ADMIN:
            return {"id": uid, "email": u["email"], "role": ADMIN}
        u["role"] = ADMIN
        self._log(actor, "staff.add_admin", uid, "user", ADMIN)
        return {"id": uid, "email": u["email"], "role": ADMIN}

    def remove_admin(self, role: str, actor: str, uid: str):
        self.need_owner(role)
        u = self.s.users.get(uid)
        if not u or u["role"] != ADMIN:
            raise NotFound()
        u["role"] = "user"
        self._log(actor, "staff.remove_admin", uid, ADMIN, "user")
        return {"message": "removed"}

    def audit(self, role: str, limit: int = 100):
        self.need_owner(role)
        rows = [a for a in self.s.audit if a.get("kind") == "admin_action"]
        return {"entries": list(reversed(rows[-max(1, min(limit, 500)):]))}
