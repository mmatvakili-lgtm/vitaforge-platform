"use client";
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { createClient, type ApiClient, type ApiError } from "../api/client.ts";
import { errorMessage, formatNumber, t as tr, type Locale } from "../i18n.ts";

const LocaleCtx = createContext<Locale>("fa");
const client: ApiClient = createClient();   // one same-origin client; the Next rewrite proxies /api/v1 to Django

export function LocaleProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  return <LocaleCtx.Provider value={locale}>{children}</LocaleCtx.Provider>;
}

export function useLocale(): Locale {
  return useContext(LocaleCtx);
}

export function useT() {
  const locale = useLocale();
  return useMemo(() => ({
    locale,
    t: (key: string, vars?: Record<string, string | number>) => tr(locale, key, vars),
    n: (v: number | string) => formatNumber(locale, v),
    err: (e: ApiError) => errorMessage(locale, e.code),
  }), [locale]);
}

export function useApi(): ApiClient {
  return client;
}
