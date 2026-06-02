import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export interface GetEntriesQuery {
  feed_id?: string;
  keyword?: string;
  limit?: number;
  offset?: number;
}

export function getEntries(client: IpcClient, query?: GetEntriesQuery) {
  const requestQuery = query
    ? {
        feed_id: query.feed_id,
        keyword: query.keyword,
        limit: query.limit,
        offset: query.offset
      }
    : undefined;

  return client.request<components["schemas"]["Entry"][]>("GET", "/entries", { query: requestQuery });
}

export function getEntry(client: IpcClient, entryId: string) {
  return client.request<components["schemas"]["Entry"]>("GET", `/entries/${entryId}`);
}

export function setEntryReadState(
  client: IpcClient,
  entryId: string,
  body: components["schemas"]["EntryReadStateRequest"]
) {
  return client.request<components["schemas"]["Entry"], components["schemas"]["EntryReadStateRequest"]>(
    "PATCH",
    `/entries/${entryId}/read`,
    { body }
  );
}

export function setEntryStarState(
  client: IpcClient,
  entryId: string,
  body: components["schemas"]["EntryStarStateRequest"]
) {
  return client.request<components["schemas"]["Entry"], components["schemas"]["EntryStarStateRequest"]>(
    "PATCH",
    `/entries/${entryId}/star`,
    { body }
  );
}

export function deleteEntry(client: IpcClient, entryId: string) {
  return client.request<components["schemas"]["EntryDeleteResult"]>("DELETE", `/entries/${entryId}`);
}
