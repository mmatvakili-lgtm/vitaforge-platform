import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

/** WCAG AA guard for the colour pairs the UI actually uses (found while auditing: white on ember was 3.1:1). */
const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
const tok = (name: string): string => {
  const m = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  assert.ok(m, `token --${name} missing`);
  return m[1];
};
const lum = (hex: string) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a: string, b: string) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

const PAIRS: [string, string, string][] = [
  ["fg", "bg", "body text"], ["muted", "bg", "secondary text"], ["muted", "card", "secondary text on cards"],
  ["accent", "bg", "links"], ["accent", "card", "links on cards"], ["accent-fg", "accent", "button label on ember"],
  ["err", "card", "error text"], ["warn", "card", "warning text"], ["ok", "card", "success text"], ["info", "card", "info text"], ["heat-3", "card", "highlight text"],
];
for (const [fg, bg, what] of PAIRS) {
  test(`contrast AA: ${what} (${fg} on ${bg})`, () => assert.ok(ratio(tok(fg), tok(bg)) >= 4.5, `${fg}/${bg} = ${ratio(tok(fg), tok(bg)).toFixed(2)}`));
}
