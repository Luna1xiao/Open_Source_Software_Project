export function readStoredNumber(key: string, fallback: number): number {
  const value = window.localStorage.getItem(key);
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function writeStoredNumber(key: string, value: number): void {
  window.localStorage.setItem(key, String(value));
}

export function readStoredBoolean(key: string, fallback: boolean): boolean {
  const value = window.localStorage.getItem(key);
  if (!value) {
    return fallback;
  }
  return value === "true";
}

export function writeStoredBoolean(key: string, value: boolean): void {
  window.localStorage.setItem(key, String(value));
}
