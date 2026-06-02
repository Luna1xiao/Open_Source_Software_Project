export function resolveBackendBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_MERCURY_BASE_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }

  const port = typeof window === "undefined" ? undefined : window.__BACKEND_PORT__;
  if (typeof port === "number" && Number.isFinite(port)) {
    return `http://127.0.0.1:${port}`;
  }

  return "http://127.0.0.1:8000";
}
