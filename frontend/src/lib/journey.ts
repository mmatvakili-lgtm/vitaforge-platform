/** Pure "what should the user do next" logic for the Today hub. No I/O: the page feeds it facts it already fetched. */
export type JourneyFacts = {
  onboardingDone: boolean;
  assessed: boolean;
  hasPlan: boolean;
  totalSessions: number;
  sessionsThisWeek: number;
  plannedPerWeek: number;      // 0 = unknown
};
export type StepKey = "onboarding" | "assessment" | "plan" | "train" | "review";
export type JourneyStep = { key: StepKey; done: boolean; href: string };
export type Journey = { steps: JourneyStep[]; next: StepKey; doneCount: number };

const PATH: Record<StepKey, string> = { onboarding: "onboarding", assessment: "assessment", plan: "plan", train: "plan", review: "analytics" };

export function journey(f: JourneyFacts): Journey {
  const flags: Record<StepKey, boolean> = {
    onboarding: f.onboardingDone,
    assessment: f.assessed,
    plan: f.hasPlan,
    train: f.totalSessions > 0,
    review: f.totalSessions >= 3,
  };
  const order: StepKey[] = ["onboarding", "assessment", "plan", "train", "review"];
  const steps = order.map((key) => ({ key, done: flags[key], href: PATH[key] }));
  // Next = first unfinished prerequisite; once the plan exists the next action is the week's training until the weekly target is met.
  let next: StepKey = "review";
  if (!f.onboardingDone) next = "onboarding";
  else if (!f.assessed) next = "assessment";
  else if (!f.hasPlan) next = "plan";
  else if (f.plannedPerWeek > 0 ? f.sessionsThisWeek < f.plannedPerWeek : f.sessionsThisWeek === 0) next = "train";
  return { steps, next, doneCount: steps.filter((s) => s.done).length };
}

/** Today's plan day: the one after the most recently trained day title (wraps), otherwise the first. */
export function pickTodayDay<T extends { title?: string }>(days: T[], lastDayTitle?: string | null): T | undefined {
  if (days.length === 0) return undefined;
  if (!lastDayTitle) return days[0];
  const i = days.findIndex((d) => d.title === lastDayTitle);
  return i < 0 ? days[0] : days[(i + 1) % days.length];
}

/** Which header items are primary (tab bar) vs. under "More". Kept here so the test pins the information architecture. */
export const PRIMARY_NAV = ["dashboard", "plan", "nutrition", "analytics"] as const;
export const MORE_NAV = ["exercises", "history", "body", "assessment", "health", "foods", "profile", "onboarding"] as const;
