import { createClient } from "@mercury/ipc-client";

import { resolveBackendBaseUrl } from "./base-url";

export const backendBaseUrl = resolveBackendBaseUrl();

export const mercuryClient = createClient({
  baseUrl: backendBaseUrl
});
