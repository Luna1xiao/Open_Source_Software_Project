import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export function getTags(client: IpcClient, keyword?: string) {
  return client.request<components["schemas"]["Tag"][]>("GET", "/tags", {
    query: { keyword }
  });
}
