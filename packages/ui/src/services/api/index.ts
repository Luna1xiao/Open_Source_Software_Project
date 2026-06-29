import {
  cleanStoredContent,
  createFeed,
  createProvider as createProviderClient,
  deleteEntry,
  deleteProvider as deleteProviderClient,
  generateSummary,
  getEntries,
  getEntry,
  getFeeds,
  getProviders as getProvidersClient,
  getTags,
  importOpml,
  IpcError,
  getEntryWebPage,
  setDefaultProvider as setDefaultProviderClient,
  setEntryReadState,
  setEntryStarState,
  syncAllFeeds,
  testProvider as testProviderClient,
  translateArticle as translateArticleClient,
  updateProvider as updateProviderClient
} from "@mercury/ipc-client";
import type { components } from "@mercury/shared-types";

import type { Entry, Feed, Tag } from "../../domain/types";
import { backendBaseUrl, mercuryClient } from "./client";
import { toUiEntry, toUiFeed, toUiTag } from "./mappers";

export interface AppDataPayload {
  feeds: Feed[];
  tags: Tag[];
  entries: Entry[];
}

export async function loadAppData(): Promise<AppDataPayload> {
  const [feeds, tags, entries] = await Promise.all([
    getFeeds(mercuryClient),
    getTags(mercuryClient),
    getEntries(mercuryClient)
  ]);

  return {
    feeds: feeds.map(toUiFeed),
    tags: tags.map(toUiTag),
    entries: entries.map(toUiEntry)
  };
}

export async function loadEntry(entryId: string): Promise<Entry> {
  return toUiEntry(await getEntry(mercuryClient, entryId));
}

export async function updateEntryReadState(entryId: string, isRead: boolean): Promise<Entry> {
  return toUiEntry(await setEntryReadState(mercuryClient, entryId, { is_read: isRead }));
}

export async function updateEntryStarState(entryId: string, isStarred: boolean): Promise<Entry> {
  return toUiEntry(await setEntryStarState(mercuryClient, entryId, { is_starred: isStarred }));
}

export async function removeEntry(entryId: string): Promise<void> {
  await deleteEntry(mercuryClient, entryId);
}

export async function requestSummary(entryId: string): Promise<components["schemas"]["SummaryResult"]> {
  return generateSummary(mercuryClient, { entry_id: entryId });
}

interface SummaryStreamStartEvent {
  type: "start";
  entry_id: string;
  provider: string;
  model: string;
  strategy: string;
}

interface SummaryStreamChunkEvent {
  type: "chunk";
  chunk_index: number;
  delta_text: string;
  summary_text: string;
  phase: string;
  failed: boolean;
}

interface SummaryStreamCompleteEvent {
  type: "complete";
  result: components["schemas"]["SummaryResult"];
}

type SummaryStreamEvent =
  | SummaryStreamStartEvent
  | SummaryStreamChunkEvent
  | SummaryStreamCompleteEvent;

export async function requestSummaryStream(
  entryId: string,
  handlers: {
    onStart?: (event: SummaryStreamStartEvent) => void;
    onChunk: (event: SummaryStreamChunkEvent) => void;
    onComplete: (result: components["schemas"]["SummaryResult"]) => void;
  }
): Promise<void> {
  const response = await fetch(`${backendBaseUrl}/agents/summary/stream`, {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body: JSON.stringify({ entry_id: entryId })
  });

  if (!response.ok) {
    const text = await response.text();
    const parsed = text.length > 0 ? JSON.parse(text) : undefined;
    throw new IpcError(response.status, response.url, parsed);
  }

  if (!response.body) {
    throw new Error("Streaming response body is unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const event = parseSummarySseEvent(rawEvent);
      if (!event) {
        continue;
      }
      if (event.type === "start") {
        handlers.onStart?.(event);
      } else if (event.type === "chunk") {
        handlers.onChunk(event);
      } else if (event.type === "complete") {
        handlers.onComplete(event.result);
      }
    }

    if (done) {
      if (buffer.trim()) {
        const event = parseSummarySseEvent(buffer);
        if (event?.type === "start") {
          handlers.onStart?.(event);
        } else if (event?.type === "chunk") {
          handlers.onChunk(event);
        } else if (event?.type === "complete") {
          handlers.onComplete(event.result);
        }
      }
      break;
    }
  }
}

export async function requestTranslation(
  entryId: string,
  targetLang: string
): Promise<components["schemas"]["TranslationResult"]> {
  return mercuryClient.request<
    components["schemas"]["TranslationResult"],
    components["schemas"]["TranslationRequest"]
  >("POST", "/agents/translation", { body: { entry_id: entryId, target_lang: targetLang } });
}

interface TranslationStreamStartEvent {
  type: "start";
  entry_id: string;
  target_lang: string;
  provider: string;
  model: string;
}

interface TranslationStreamChunkEvent {
  type: "chunk";
  chunk_index: number;
  delta_html: string;
  translation_html: string;
  failed: boolean;
}

interface TranslationStreamCompleteEvent {
  type: "complete";
  result: components["schemas"]["TranslationResult"];
}

type TranslationStreamEvent =
  | TranslationStreamStartEvent
  | TranslationStreamChunkEvent
  | TranslationStreamCompleteEvent;

export async function requestTranslationStream(
  entryId: string,
  targetLang: string,
  handlers: {
    onStart?: (event: TranslationStreamStartEvent) => void;
    onChunk: (event: TranslationStreamChunkEvent) => void;
    onComplete: (result: components["schemas"]["TranslationResult"]) => void;
  }
): Promise<void> {
  const response = await fetch(`${backendBaseUrl}/agents/translation/stream`, {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body: JSON.stringify({ entry_id: entryId, target_lang: targetLang })
  });

  if (!response.ok) {
    const text = await response.text();
    const parsed = text.length > 0 ? JSON.parse(text) : undefined;
    throw new IpcError(response.status, response.url, parsed);
  }

  if (!response.body) {
    throw new Error("Streaming response body is unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const event = parseSseEvent(rawEvent);
      if (!event) {
        continue;
      }
      if (event.type === "start") {
        handlers.onStart?.(event);
      } else if (event.type === "chunk") {
        handlers.onChunk(event);
      } else if (event.type === "complete") {
        handlers.onComplete(event.result);
      }
    }

    if (done) {
      if (buffer.trim()) {
        const event = parseSseEvent(buffer);
        if (event?.type === "start") {
          handlers.onStart?.(event);
        } else if (event?.type === "chunk") {
          handlers.onChunk(event);
        } else if (event?.type === "complete") {
          handlers.onComplete(event.result);
        }
      }
      break;
    }
  }
}

export async function subscribeToFeed(url: string, sync = true): Promise<Feed> {
  return toUiFeed(await createFeed(mercuryClient, { url, sync }));
}

export async function importOpmlFile(file: File): Promise<components["schemas"]["OPMLImportResult"]> {
  return importOpml(mercuryClient, await file.text());
}

export async function syncFeeds(): Promise<components["schemas"]["SyncResult"][]> {
  return syncAllFeeds(mercuryClient);
}

export async function ensureEntryContent(entryId: string): Promise<components["schemas"]["CleanContentResponse"]> {
  return cleanStoredContent(mercuryClient, entryId);
}

export async function requestEntryWebPage(entryId: string): Promise<components["schemas"]["WebPageResponse"]> {
  return getEntryWebPage(mercuryClient, entryId);
}

export async function getProviders() {
  return getProvidersClient(mercuryClient);
}

export async function createProvider(body: { name: string; kind?: string; model?: string; base_url?: string; api_key?: string; api_key_header?: string; is_default?: boolean }) {
  return createProviderClient(mercuryClient, body);
}

export async function updateProvider(name: string, body: { kind?: string; model?: string; base_url?: string; api_key?: string; api_key_header?: string; is_default?: boolean }) {
  return updateProviderClient(mercuryClient, name, body);
}

export async function deleteProvider(name: string) {
  return deleteProviderClient(mercuryClient, name);
}

export async function setDefaultProvider(name: string) {
  return setDefaultProviderClient(mercuryClient, name);
}

export async function testProvider(name: string) {
  return testProviderClient(mercuryClient, name);
}

export async function translateArticle(entryId: string, targetLang: string) {
  return translateArticleClient(mercuryClient, { entry_id: entryId, target_lang: targetLang });
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof IpcError) {
    if (hasDetail(error.body)) {
      const detail = error.body.detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
    return `Request failed (${error.status})`;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Request failed";
}

function hasDetail(value: unknown): value is { detail?: unknown } {
  return typeof value === "object" && value !== null && "detail" in value;
}

function parseSseEvent(rawEvent: string): TranslationStreamEvent | null {
  return parseTypedSseEvent<TranslationStreamEvent>(rawEvent);
}

function parseSummarySseEvent(rawEvent: string): SummaryStreamEvent | null {
  return parseTypedSseEvent<SummaryStreamEvent>(rawEvent);
}

function parseTypedSseEvent<T extends { type: string }>(rawEvent: string): T | null {
  const lines = rawEvent
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean);

  let eventType = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  const parsed = JSON.parse(dataLines.join("\n")) as T;
  if (parsed.type !== eventType && parsed.type) {
    return parsed;
  }
  return parsed;
}
