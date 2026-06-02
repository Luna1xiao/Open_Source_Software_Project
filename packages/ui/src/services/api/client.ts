import { createClient } from "@mercury/ipc-client";

import { resolveBackendBaseUrl } from "./base-url";

export const mercuryClient = createClient({
  baseUrl: resolveBackendBaseUrl()
});
