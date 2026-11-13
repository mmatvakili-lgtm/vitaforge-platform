// Pure helpers for the Telegram verification UI (no React, no network) so the state logic is unit-tested.
export type TgPhase = "idle" | "requesting" | "pending" | "verified" | "expired" | "unavailable" | "error";

export const POLL_MS = 4000;

/** Message key for a failed link request. Credentials errors stay generic (no account enumeration). */
export function linkErrorKey(status: number): { phase: TgPhase; key: string } {
  if (status === 503) return { phase: "unavailable", key: "telegram.unavailable" };
  if (status === 429) return { phase: "error", key: "telegram.rateLimited" };
  if (status === 423) return { phase: "error", key: "error.account_locked" };
  if (status === 409) return { phase: "verified", key: "telegram.alreadyVerified" };   // password was correct and the account is already verified
  return { phase: "error", key: "telegram.linkFailed" };
}

/** Only a Telegram deep link on t.me is ever opened. */
export function safeDeepLink(url: string): string | null {
  return /^https:\/\/t\.me\/[A-Za-z0-9_]{5,32}\?start=[A-Za-z0-9_-]{20,64}$/.test(url) ? url : null;
}

export function secondsLeft(expiresAtIso: string, nowMs: number): number {
  const t = Date.parse(expiresAtIso);
  return Number.isFinite(t) ? Math.max(0, Math.ceil((t - nowMs) / 1000)) : 0;
}

export function clock(seconds: number): string {
  const m = Math.floor(seconds / 60), s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** What one poll (= normal login attempt) means while waiting: 200 -> verified; 401 -> keep waiting (the password was already proven); others are real errors. */
export function pollOutcome(status: number): "verified" | "wait" | "locked" | "error" {
  if (status === 200) return "verified";
  if (status === 401) return "wait";
  if (status === 423) return "locked";
  return "error";
}
