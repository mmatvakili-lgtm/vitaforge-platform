import fa from "../messages/fa.json" with { type: "json" };
import en from "../messages/en.json" with { type: "json" };
import safety from "../messages/safety.generated.json" with { type: "json" };

export const LOCALES = ["fa", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "fa";

export function isLocale(v: unknown): v is Locale {
  return v === "fa" || v === "en";
}
export function dirOf(l: Locale): "rtl" | "ltr" {
  return l === "fa" ? "rtl" : "ltr";
}
export function otherLocale(l: Locale): Locale {
  return l === "fa" ? "en" : "fa";
}

const CATALOGS: Record<Locale, Record<string, string>> = { fa, en };
const SAFETY = safety as Record<Locale, Record<string, string>>;

/** Messages are looked up by key; a missing key returns the key itself so gaps are visible, never silently blank. */
export function t(locale: Locale, key: string, vars?: Record<string, string | number>): string {
  let s = CATALOGS[locale][key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(formatNumber(locale, v));
  return s;
}

const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
/** Digits follow the UI language: Persian digits in fa, Latin in en. Non-numeric strings are left untouched. */
export function formatNumber(locale: Locale, v: string | number): string {
  const s = String(v);
  return locale === "fa" ? s.replace(/\d/g, (d) => PERSIAN_DIGITS[Number(d)]) : s;
}

/** Persian digits and Arabic-Indic digits typed by the user become ASCII before they are sent. */
export function normalizeDigits(s: string): string {
  return s.replace(/[۰-۹]/g, (d) => String(PERSIAN_DIGITS.indexOf(d))).replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660));
}

/** Safety Core reason text comes from the generated catalog (mirrors safety_core/explain.py); unknown codes are shown as the code. */
export function safetyReason(locale: Locale, code: string): string {
  return SAFETY[locale][code] ?? code;
}
export function hasSafetyReason(code: string): boolean {
  return code in SAFETY.fa && code in SAFETY.en;
}

export function errorMessage(locale: Locale, code: string): string {
  const key = `error.${code}`;
  return key in CATALOGS[locale] ? CATALOGS[locale][key] : t(locale, "error.unknown");
}

export function messageKeys(locale: Locale): string[] {
  return Object.keys(CATALOGS[locale]);
}
