// Exercise library query logic (filters mirror GET /exercises).
export const LIBRARY_MUSCLES = ["abdominals", "abductors", "adductors", "biceps", "calves", "chest", "forearms", "glutes", "hamstrings", "lats", "lower back", "middle back", "neck",
  "quadriceps", "shoulders", "traps", "triceps"] as const;
export const LIBRARY_EQUIPMENT = ["bodyweight", "dumbbell", "barbell", "bench", "box", "band", "machine", "kettlebell", "pull_up_bar", "cable"] as const;
export const LIBRARY_DIFFICULTY = ["beginner", "intermediate", "advanced"] as const;
export const PAGE_SIZE = 20;

export type Filters = { q: string; muscle: string; equipment: string; difficulty: string };
export const NO_FILTERS: Filters = { q: "", muscle: "", equipment: "", difficulty: "" };

export function libraryQuery(f: Filters, page: number): { page: number; page_size: number; q?: string; muscle?: string; equipment?: string; difficulty?: string } {
  const q: ReturnType<typeof libraryQuery> = { page: Math.max(1, Math.floor(page) || 1), page_size: PAGE_SIZE };
  if (f.q.trim()) q.q = f.q.trim();
  if (f.muscle) q.muscle = f.muscle;
  if (f.equipment) q.equipment = f.equipment;
  if (f.difficulty) q.difficulty = f.difficulty;
  return q;
}

export function pageCount(total: number): number { return Math.max(1, Math.ceil(total / PAGE_SIZE)); }
