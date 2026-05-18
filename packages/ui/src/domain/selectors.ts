import type { Entry, Feed, FeedScope, TagMatchMode } from "./types";

export interface EntryQuery {
  feedScope: FeedScope;
  selectedTagIds: string[];
  tagMatchMode: TagMatchMode;
  unreadOnly: boolean;
  searchText: string;
  searchScope: "currentFeed" | "allFeeds";
}

export function feedIdFromScope(scope: FeedScope): string | null {
  return scope.startsWith("feed:") ? scope.slice("feed:".length) : null;
}

export function scopeTitle(scope: FeedScope, feeds: Feed[]): "all" | "starred" | string {
  if (scope === "all") {
    return "all";
  }
  if (scope === "starred") {
    return "starred";
  }
  const feedId = feedIdFromScope(scope);
  return feeds.find((feed) => feed.id === feedId)?.title ?? "all";
}

export function matchesTags(entry: Entry, selectedTagIds: string[], mode: TagMatchMode): boolean {
  if (selectedTagIds.length === 0) {
    return true;
  }
  if (mode === "all") {
    return selectedTagIds.every((tagId) => entry.tagIds.includes(tagId));
  }
  return selectedTagIds.some((tagId) => entry.tagIds.includes(tagId));
}

export function filterEntries(entries: Entry[], query: EntryQuery): Entry[] {
  const search = query.searchText.trim().toLocaleLowerCase();
  const scopedFeedId = feedIdFromScope(query.feedScope);
  const searchUsesAllFeeds = search.length > 0 && query.searchScope === "allFeeds";

  return entries.filter((entry) => {
    if (query.feedScope === "starred" && !entry.isStarred) {
      return false;
    }
    if (!searchUsesAllFeeds && scopedFeedId && entry.feedId !== scopedFeedId) {
      return false;
    }
    if (query.unreadOnly && entry.isRead) {
      return false;
    }
    if (!matchesTags(entry, query.selectedTagIds, query.tagMatchMode)) {
      return false;
    }
    if (search.length > 0) {
      const searchableText = `${entry.title} ${entry.summary}`.toLocaleLowerCase();
      return searchableText.includes(search);
    }
    return true;
  });
}

export function nextSelectedEntryId(
  currentId: string | null,
  filteredEntries: Entry[],
  selectFirst: boolean
): string | null {
  if (currentId && filteredEntries.some((entry) => entry.id === currentId)) {
    return currentId;
  }
  if (!selectFirst) {
    return null;
  }
  return filteredEntries[0]?.id ?? null;
}

export function queryScopedReadState(
  entries: Entry[],
  query: EntryQuery,
  isRead: boolean
): Entry[] {
  const targetIds = new Set(filterEntries(entries, query).map((entry) => entry.id));
  return entries.map((entry) => (targetIds.has(entry.id) ? { ...entry, isRead } : entry));
}

export function visiblePage<T>(items: T[], pageSize: number): { items: T[]; hasMore: boolean } {
  return {
    items: items.slice(0, pageSize),
    hasMore: items.length > pageSize
  };
}
