/** The password policy as live checks (mirrors the server rule: ≥10 characters, an uppercase letter, a digit). Display only; the server decides. */
export interface PasswordChecks { len: boolean; upper: boolean; digit: boolean; score: 0 | 1 | 2 | 3 }
export function passwordChecks(pw: string): PasswordChecks {
  const len = pw.length >= 10, upper = /[A-Z]/.test(pw), digit = /[0-9]/.test(pw);
  return { len, upper, digit, score: ((len ? 1 : 0) + (upper ? 1 : 0) + (digit ? 1 : 0)) as 0 | 1 | 2 | 3 };
}
