"use client";
import { Children, isValidElement, useEffect, useId, useRef, useState, type ChangeEvent, type KeyboardEvent as KbEvent, type ReactElement, type ReactNode } from "react";

type Opt = { value: string; label: string };

/** Drop-in replacement for a native <select>: same props (id, value, onChange(e.target.value), <option> children) but
 *  - up to 5 options -> segmented choice chips (one tap, no popup; wraps on phones),
 *  - more options   -> accessible listbox that opens as a dropdown (desktop) or a bottom sheet (phone). */
export function Select({ id, value, onChange, children, disabled, "aria-label": ariaLabel }: {
  id?: string; value: string; onChange: (e: ChangeEvent<HTMLSelectElement>) => void; children?: ReactNode; disabled?: boolean; "aria-label"?: string;
}) {
  const opts: Opt[] = [];
  Children.forEach(children, (c) => {
    if (isValidElement(c) && c.type === "option") {
      const p = (c as ReactElement<{ value?: string | number; children?: ReactNode }>).props;
      const label = Children.toArray(p.children).join("");
      opts.push({ value: String(p.value ?? label), label });
    }
  });
  const emit = (v: string) => onChange({ target: { value: v }, currentTarget: { value: v } } as unknown as ChangeEvent<HTMLSelectElement>);
  const real = opts.filter((o) => o.value !== "");
  const placeholder = opts.find((o) => o.value === "")?.label ?? "";
  const uid = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const away = (e: Event) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  if (real.length <= 5) {
    return (
      <div className="choice" role="radiogroup" id={id} aria-label={ariaLabel} aria-labelledby={!ariaLabel && id ? `${id}-lbl` : undefined} aria-disabled={disabled}>
        {real.map((o) => (
          <button key={o.value} type="button" role="radio" aria-checked={value === o.value} disabled={disabled} className={value === o.value ? "on" : ""}
            onClick={() => emit(value === o.value && placeholder ? "" : o.value)}>{o.label}</button>
        ))}
      </div>
    );
  }

  const cur = opts.find((o) => o.value === value);
  const pick = (v: string) => { emit(v); setOpen(false); };
  const onKey = (e: KbEvent) => {
    if (e.key === "Escape") return setOpen(false);
    if (e.key === "ArrowDown") { e.preventDefault(); if (!open) { setOpen(true); setActive(Math.max(0, opts.findIndex((o) => o.value === value))); } else setActive((a) => Math.min(opts.length - 1, a + 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    if ((e.key === "Enter" || e.key === " ") && open) { e.preventDefault(); pick(opts[active].value); }
  };
  return (
    <div className="sel" ref={wrap}>
      <button type="button" id={id} className="sel-btn" aria-haspopup="listbox" aria-expanded={open} aria-controls={`${uid}-l`} aria-label={ariaLabel} aria-labelledby={!ariaLabel && id ? `${id}-lbl ${id}` : undefined}
        disabled={disabled} onClick={() => { setOpen(!open); setActive(Math.max(0, opts.findIndex((o) => o.value === value))); }} onKeyDown={onKey}>
        <span className={cur && cur.value !== "" ? "" : "muted"}>{cur && cur.value !== "" ? cur.label : placeholder || "—"}</span>
        <svg aria-hidden="true" viewBox="0 0 20 20" width="18" height="18"><path d="M5 8l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      {open && <div className="sel-scrim" aria-hidden="true" onClick={() => setOpen(false)} />}
      {open && (
        <ul className="sel-list" role="listbox" id={`${uid}-l`} aria-activedescendant={`${uid}-${active}`}>
          {opts.map((o, i) => (
            <li key={o.value || "_"} id={`${uid}-${i}`} role="option" aria-selected={o.value === value} className={(o.value === value ? "on " : "") + (i === active ? "act" : "")}
              onPointerEnter={() => setActive(i)} onClick={() => pick(o.value)}>
              <span>{o.label || placeholder || "—"}</span>
              {o.value === value && <svg aria-hidden="true" viewBox="0 0 20 20" width="16" height="16"><path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
