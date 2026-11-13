import type { FoodReviewRequest } from "./api/generated.ts";

export const NOTES_MIN = 5;

/** Reject/retire need a written reason; approval never needs (or accepts) a blocker bypass. Returns null when invalid. */
export interface Attest { allergensChecked: boolean; allergens: string[]; licenseChecked: boolean }

/** Attestations are sent only with an approval and only when the reviewer explicitly ticked them (an empty allergen list is a valid, explicit "none"). */
export function reviewRequest(decision: FoodReviewRequest["decision"], notes: string, a?: Attest): FoodReviewRequest | null {
  const n = notes.trim();
  if (decision !== "approve" && n.length < NOTES_MIN) return null;
  const req: FoodReviewRequest = n ? { decision, notes: n.slice(0, 1000) } : { decision };
  if (decision === "approve" && a) {
    if (a.allergensChecked) { req.allergens = a.allergens as FoodReviewRequest["allergens"]; req.allergens_confirmed = true; }
    if (a.licenseChecked) req.license_verified = true;
  }
  return req;
}

/** i18n key for a server blocker code ("invalid:<reason>" collapses to one key; the raw reason is shown alongside). */
export function blockerKey(code: string): { key: string; detail?: string } {
  if (code.startsWith("invalid:")) return { key: "review.blocker.invalid", detail: code.slice(8) };
  return { key: `review.blocker.${code}` };
}

export const canApprove = (blockers: readonly string[]) => blockers.length === 0;
