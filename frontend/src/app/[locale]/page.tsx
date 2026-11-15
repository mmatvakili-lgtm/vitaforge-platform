"use client";
import { useEffect, useState } from "react";
import { useApi, useT } from "../../lib/react/context.tsx";
import { ButtonLink, Card, Loading } from "../../components/ui.tsx";
import { Body3D } from "../../components/Body3D.tsx";

const SPOTLIGHT = [["quadriceps", "glutes", "hamstrings", "calves"], ["chest", "shoulders", "triceps"], ["lats", "middle back", "biceps", "traps"], ["abdominals", "lower back", "glutes"]] as const;
const FEATURES = ["assess", "plan", "track", "body"] as const;

export default function Home() {
  const { locale, t } = useT();
  const api = useApi();
  const [state, setState] = useState<"loading" | "in" | "out">("loading");
  const [spot, setSpot] = useState(0);
  useEffect(() => {
    let live = true;
    api.call("API-PRO-001").then((r) => live && setState(r.ok ? "in" : "out"));
    return () => { live = false; };
  }, [api]);
  useEffect(() => {
    if (typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = window.setInterval(() => setSpot((s) => (s + 1) % SPOTLIGHT.length), 2600);
    return () => window.clearInterval(id);
  }, []);
  const focus: Record<string, "focus"> = {};
  for (const r of SPOTLIGHT[spot]) focus[r] = "focus";
  return (
    <>
      <section className="hero">
        <div className="hero-text">
          <p className="kicker">{t("home.kicker")}</p>
          <h1 className="hero-title">{t("home.title")}</h1>
          <p className="lede">{t("app.tagline")}</p>
          {state === "loading" && <Loading />}
          {state === "out" && (<div className="row"><ButtonLink href={`/${locale}/register`}>{t("nav.register")}</ButtonLink><ButtonLink href={`/${locale}/login`} secondary>{t("nav.login")}</ButtonLink></div>)}
          {state === "in" && (<div className="row"><ButtonLink href={`/${locale}/onboarding`}>{t("home.cta")}</ButtonLink><ButtonLink href={`/${locale}/plan`} secondary>{t("home.cta2")}</ButtonLink><ButtonLink href={`/${locale}/dashboard`} secondary>{t("nav.dashboard")}</ButtonLink></div>)}
        </div>
        <div className="hero-stage"><Body3D height={420} status={focus} label={t("home.bodyAria")} /></div>
      </section>
      <div className="feature-grid">
        {FEATURES.map((k) => (
          <div key={k} className="feature">
            <h2>{t(`home.f.${k}.title`)}</h2>
            <p className="muted">{t(`home.f.${k}.body`)}</p>
          </div>
        ))}
      </div>
      <Card title={t("home.honest.title")}>
        <p className="notice">{t("notice.experimental")}</p>
        <p className="muted">{t("home.honest.body")}</p>
      </Card>
    </>
  );
}
