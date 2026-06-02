/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MERCURY_BASE_URL?: string;
}

interface Window {
  __BACKEND_PORT__?: number;
}
