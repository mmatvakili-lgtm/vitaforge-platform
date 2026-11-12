import type { FoodReviewRequest } from "./api/generated.ts";

export const NOTES_MIN = 5;

/** Reject/retire need a written reason; approval never needs (or accepts) a blocker bypass. Returns null when invalid. */
export function reviewRequest(decision: FoodReviewRequest["decision"], notes: string): FoodReviewRequest | null {
  const n = notes.trim();
  if (decision !== "approve" && n.length < NOTES_MIN) return null;
  return n ? { decision, notes: n.slice(0, 1000) } : { decision };
}

/** i18n key for a server blocker code ("invalid:<reason>" collapses to one key; the raw reason is shown alongside). */
export function blockerKey(code: string): { key: string; detail?: string } {
  if (code.startsWith("invalid:")) return { key: "review.blocker.invalid", detail: code.slice(8) };
  return { key: `review.blocker.${code}` };
}

export const canApprove = (blockers: readonly string[]) => blockers.length === 0;
