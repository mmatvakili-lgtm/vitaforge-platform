"use client";
import { useEffect, useState } from "react";
import { useApi, useT } from "../../lib/react/context.tsx";
import { ButtonLink, Card, Loading } from "../../components/ui.tsx";

export default function Home() {
  const { locale, t } = useT();
  const api = useApi();
  const [state, setState] = useState<"loading" | "in" | "out">("loading");
  useEffect(() => {
    let live = true;
    api.call("API-PRO-001").then((r) => live && setState(r.ok ? "in" : "out"));
    return () => { live = false; };
  }, [api]);
  return (
    <Card title={t("app.name")}>
      <p>{t("app.tagline")}</p>
      {state === "loading" && <Loading />}
      {state === "out" && (<div className="row"><ButtonLink href={`/${locale}/register`}>{t("nav.register")}</ButtonLink><ButtonLink href={`/${locale}/login`} secondary>{t("nav.login")}</ButtonLink></div>)}
      {state === "in" && (<div className="row"><ButtonLink href={`/${locale}/onboarding`}>{t("home.cta")}</ButtonLink><ButtonLink href={`/${locale}/plan`} secondary>{t("home.cta2")}</ButtonLink></div>)}
      <p className="notice">{t("notice.experimental")}</p>
    </Card>
  );
}
