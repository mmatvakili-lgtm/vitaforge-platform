"use client";
import { useEffect, useRef, useState } from "react";
import codes from "../../lib/motion.codes.json";
import { useApi, useT } from "../../lib/react/context.tsx";
import { useCountUp, useInViewOnce } from "../../lib/react/useInView.ts";
import { ButtonLink, Card } from "../ui.tsx";
import { Body3D } from "../Body3D.tsx";

const STORY = [["quadriceps", "glutes", "hamstrings", "calves"], ["chest", "shoulders", "triceps"], ["lats", "middle back", "biceps", "traps"], ["abdominals", "lower back", "glutes"]] as const;
const STEPS = ["assess", "plan", "track"] as const;
const VERDICTS = ["ok", "caution", "blocked"] as const;

type State = "loading" | "in" | "out";

function Cta({ state, big }: { state: State; big?: boolean }) {
  const { locale, t } = useT();
  const cls = big ? "lp-cta-row lp-cta-big" : "lp-cta-row";
  if (state === "in") return (<div className={cls}><ButtonLink href={`/${locale}/dashboard`}>{t("nav.dashboard")}</ButtonLink><ButtonLink href={`/${locale}/plan`} secondary>{t("home.cta2")}</ButtonLink></div>);
  return (<div className={cls}><ButtonLink href={`/${locale}/register`}>{t("nav.register")}</ButtonLink><ButtonLink href={`/${locale}/login`} secondary>{t("nav.login")}</ButtonLink></div>);
}

function Hero({ state }: { state: State }) {
  const { t } = useT();
  const [spot, setSpot] = useState(0);
  useEffect(() => {
    if (typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = window.setInterval(() => setSpot((s) => (s + 1) % STORY.length), 2600);
    return () => window.clearInterval(id);
  }, []);
  const focus: Record<string, "focus"> = {};
  for (const r of STORY[spot]) focus[r] = "focus";
  return (
    <section className="lp-hero bleed" aria-labelledby="lp-h1">
      <div className="lp-hero-inner">
        <div className="lp-hero-copy">
          <h1 id="lp-h1" className="lp-h1">
            <span className="lp-line"><span>{t("landing.h1a")}</span></span>
            <span className="lp-line"><span>{t("landing.h1b")}</span></span>
          </h1>
          <p className="lp-lede">{t("landing.lede")}</p>
          <Cta state={state} />
        </div>
        <div className="lp-hero-stage">
          <div className="lp-forge" aria-hidden="true" />
          <Body3D height={560} status={focus} label={t("home.bodyAria")} />
          <div className="lp-anvil" aria-hidden="true" />
        </div>
      </div>
    </section>
  );
}

function PhotoStrip() {
  const { t } = useT();
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => {
    let live = true;
    fetch("/exercise-media/index.json").then((r) => (r.ok ? r.json() : {})).then((j: Record<string, unknown>) => { if (live) setNames(Object.keys(j).sort().filter((_, i) => i % 6 === 0).slice(0, 24)); }).catch(() => undefined);
    return () => { live = false; };
  }, []);
  if (names.length === 0) return <div className="lp-strip-gap" aria-hidden="true" />;
  const row = (dup: boolean) => names.map((c) => <li key={`${dup ? "b" : "a"}-${c}`} aria-hidden={dup ? "true" : undefined}><img src={`/exercise-media/${c}/0.webp`} alt={dup ? "" : c.replace(/_/g, " ")} loading="lazy" decoding="async" width={320} height={240} /></li>);
  return (
    <section className="lp-strip bleed" aria-label={t("landing.strip")}>
      <ul className="lp-strip-track">{row(false)}{row(true)}</ul>
    </section>
  );
}

function MuscleStory() {
  const { t } = useT();
  const [i, setI] = useState(0);
  const steps = useRef<(HTMLLIElement | null)[]>([]);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver((es) => {
      for (const e of es) if (e.isIntersecting) setI(Number((e.target as HTMLElement).dataset.i ?? 0));
    }, { rootMargin: "-45% 0px -45% 0px" });
    steps.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, []);
  const focus: Record<string, "focus"> = {};
  for (const r of STORY[i]) focus[r] = "focus";
  return (
    <section className="lp-story" aria-labelledby="lp-story-h">
      <h2 id="lp-story-h" className="lp-h2">{t("landing.story.title")}</h2>
      <div className="lp-story-grid">
        <div className="lp-story-sticky"><div className="body-stage"><Body3D height={420} status={focus} label={t("home.bodyAria")} /></div></div>
        <ol className="lp-story-steps">
          {STORY.map((_, k) => (
            <li key={k} data-i={k} ref={(el) => { steps.current[k] = el; }} className={k === i ? "on" : ""}>
              <h3>{t(`landing.story.${k}.t`)}</h3>
              <p>{t(`landing.story.${k}.b`)}</p>
            </li>
          ))}
        </ol>
      </div>
      <p className="lp-story-foot">{t("home.f.body.body")}</p>
    </section>
  );
}

function Safety() {
  const { t } = useT();
  return (
    <section className="lp-safety" aria-labelledby="lp-safety-h">
      <div className="lp-safety-head">
        <h2 id="lp-safety-h" className="lp-h2">{t("landing.safety.title")}</h2>
        <p className="lp-p">{t("landing.safety.body")}</p>
      </div>
      <ul className="lp-ledger">
        {VERDICTS.map((v) => (
          <li key={v} className={`lp-verdict lp-${v}`}>
            <span className="lp-verdict-tag">{t(`landing.safety.${v}`)}</span>
            <strong>{t(`landing.safety.${v}.ex`)}</strong>
            <span className="muted">{t(`landing.safety.${v}.why`)}</span>
          </li>
        ))}
      </ul>
      <p className="muted lp-sample">{t("landing.safety.sample")}</p>
    </section>
  );
}

function Counter({ value, label, run }: { value: number; label: string; run: boolean }) {
  const v = useCountUp(value, run);
  return (<div className="lp-num"><span className="num lp-num-v" aria-label={String(value)}>{v}</span><span className="lp-num-l">{label}</span></div>);
}

function Numbers() {
  const { t } = useT();
  const [ref, seen] = useInViewOnce<HTMLDivElement>();
  const [photos, setPhotos] = useState(0);
  const [videos, setVideos] = useState(0);
  useEffect(() => {
    let live = true;
    const len = (u: string) => fetch(u).then((r) => (r.ok ? r.json() : {})).then((j: Record<string, unknown>) => Object.keys(j).length).catch(() => 0);
    len("/exercise-media/index.json").then((n) => live && setPhotos(n));
    len("/exercise-media/videos.json").then((n) => live && setVideos(n));
    return () => { live = false; };
  }, []);
  return (
    <section className="lp-numbers" aria-label={t("landing.n.title")}>
      <div ref={ref} className="lp-numbers-row">
        <Counter value={(codes as unknown[]).length} label={t("landing.n.moves")} run={seen} />
        <Counter value={photos} label={t("landing.n.photos")} run={seen && photos > 0} />
        <Counter value={videos} label={t("landing.n.videos")} run={seen && videos > 0} />
      </div>
    </section>
  );
}

/** Oversized outline words that drift sideways with scroll (CSS scroll-driven; static where unsupported). */
function Band() {
  const { t } = useT();
  const words = [t("landing.band.0"), t("landing.band.1"), t("landing.band.2")];
  return (
    <div className="lp-band bleed" aria-hidden="true">
      <div className="lp-band-row">{[...words, ...words].map((w, i) => <span key={i} className={i % 3 === 1 ? "solid" : ""}>{w}</span>)}</div>
    </div>
  );
}

const BENTO = ["lib", "safe", "food", "prog", "lang"] as const;
function Bento() {
  const { t } = useT();
  return (
    <section className="lp-bento-sec" aria-labelledby="lp-bento-h">
      <h2 id="lp-bento-h" className="lp-h2">{t("landing.bento.title")}</h2>
      <ul className="lp-bento">
        {BENTO.map((k) => (
          <li key={k} className={`lp-cell lp-cell-${k}`}>
            <div className="lp-cell-art" aria-hidden="true">
              {k === "lib" && <><i /><i /><i /></>}
              {k === "safe" && <><b className="ok" /><b className="caution" /><b className="blocked" /></>}
              {k === "food" && <span className="lp-macro" />}
              {k === "prog" && <>{[40, 65, 30, 85, 55, 95, 70].map((h, i) => <em key={i} style={{ blockSize: `${h}%` }} />)}</>}
              {k === "lang" && <><span>فا</span><span>EN</span></>}
            </div>
            <h3>{t(`landing.bento.${k}.t`)}</h3>
            <p>{t(`landing.bento.${k}.b`)}</p>
          </li>
        ))}
      </ul>
      <p className="muted lp-sample">{t("landing.bento.sample")}</p>
    </section>
  );
}

function Steps() {
  const { t } = useT();
  return (
    <section className="lp-steps" aria-labelledby="lp-steps-h">
      <h2 id="lp-steps-h" className="lp-h2">{t("landing.steps.title")}</h2>
      <ol className="lp-timeline">
        {STEPS.map((k, n) => (
          <li key={k}>
            <span className="lp-step-n num" aria-hidden="true">{n + 1}</span>
            <h3>{t(`home.f.${k}.title`)}</h3>
            <p>{t(`home.f.${k}.body`)}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function Landing() {
  const { t } = useT();
  const api = useApi();
  const [state, setState] = useState<State>("loading");
  useEffect(() => {
    let live = true;
    api.call("API-PRO-001").then((r) => live && setState(r.ok ? "in" : "out"));
    return () => { live = false; };
  }, [api]);
  return (
    <>
      <Hero state={state} />
      <PhotoStrip />
      <MuscleStory />
      <Band />
      <Bento />
      <Safety />
      <Steps />
      <Numbers />
      <section className="lp-final">
        <h2 className="lp-h2 lp-final-h">{t("landing.final")}</h2>
        <Cta state={state} big />
      </section>
      <Card title={t("home.honest.title")}>
        <p className="notice">{t("notice.experimental")}</p>
        <p className="muted">{t("home.honest.body")}</p>
      </Card>
    </>
  );
}
