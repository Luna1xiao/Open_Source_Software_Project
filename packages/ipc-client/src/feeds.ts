import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export function getFeeds(client: IpcClient, keyword?: string) {
  return client.request<components["schemas"]["Feed"][]>("GET", "/feeds", {
    query: { keyword }
  });
}

export function createFeed(client: IpcClient, body: components["schemas"]["SubscribeFeedRequest"]) {
  return client.request<components["schemas"]["Feed"], components["schemas"]["SubscribeFeedRequest"]>("POST", "/feeds", {
    body
  });
}

export function importOpml(client: IpcClient, payload: string) {
  return client.request<components["schemas"]["OPMLImportResult"], string>("POST", "/feeds/opml/import", {
    body: payload,
    bodyType: "raw",
    headers: {
      "content-type": "text/x-opml; charset=utf-8"
    }
  });
}

export function syncAllFeeds(client: IpcClient) {
  return client.request<components["schemas"]["SyncResult"][]>("POST", "/feeds/sync-all");
}

export function syncFeed(client: IpcClient, feedId: string) {
  return client.request<components["schemas"]["SyncResult"]>("POST", `/feeds/${feedId}/sync`);
}
