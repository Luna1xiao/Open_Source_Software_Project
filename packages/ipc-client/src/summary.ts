import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export function generateSummary(
  client: IpcClient,
  body: components["schemas"]["SummaryRequest"]
) {
  return client.request<components["schemas"]["SummaryResult"], components["schemas"]["SummaryRequest"]>(
    "POST",
    "/agents/summary/generate",
    { body }
  );
}
