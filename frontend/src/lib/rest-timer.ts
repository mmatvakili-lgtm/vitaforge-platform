/** Rest-timer maths (wall-clock based, so a throttled background tab cannot make the countdown drift). */
export function restRemaining(endsAt: number, now: number): number {
  return Math.max(0, Math.ceil((endsAt - now) / 1000));
}

export function clock(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** Fraction of the rest already elapsed (0..1) for the progress ring. */
export function restFraction(total: number, remaining: number): number {
  return total <= 0 ? 1 : Math.min(1, Math.max(0, 1 - remaining / total));
}
