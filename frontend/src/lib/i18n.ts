import fa from "@/messages/fa.json";
import en from "@/messages/en.json";

export type Locale = "fa" | "en";
export const dir = (l: Locale) => (l === "fa" ? "rtl" : "ltr");
export const t = (l: Locale, key: keyof typeof fa): string => (l === "fa" ? fa : en)[key];
