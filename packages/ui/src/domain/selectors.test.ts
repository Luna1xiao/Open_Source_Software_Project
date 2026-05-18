import { describe, expect, it } from "vitest";
import { entries } from "./fixtures";
import { filterEntries, nextSelectedEntryId, queryScopedReadState, visiblePage } from "./selectors";

describe("entry query policy", () => {
  it("filters by current feed, unread state, and title or summary search", () => {
    const result = filterEntries(entries, {
      feedScope: "feed:hn",
      selectedTagIds: [],
      tagMatchMode: "any",
      unreadOnly: true,
      searchText: "agent",
      searchScope: "currentFeed"
    });

    expect(result.map((entry) => entry.id)).toEqual(["e1", "e7"]);
  });

  it("allows non-empty all-feed search to escape the selected feed scope", () => {
    const result = filterEntries(entries, {
      feedScope: "feed:swift",
      selectedTagIds: [],
      tagMatchMode: "any",
      unreadOnly: false,
      searchText: "dense",
      searchScope: "allFeeds"
    });

    expect(result.map((entry) => entry.id)).toEqual(["e3"]);
  });

  it("applies any and all tag matching", () => {
    const anyResult = filterEntries(entries, {
      feedScope: "all",
      selectedTagIds: ["ai", "swift"],
      tagMatchMode: "any",
      unreadOnly: false,
      searchText: "",
      searchScope: "allFeeds"
    });
    const allResult = filterEntries(entries, {
      feedScope: "all",
      selectedTagIds: ["ai", "swift"],
      tagMatchMode: "all",
      unreadOnly: false,
      searchText: "",
      searchScope: "allFeeds"
    });

    expect(anyResult.map((entry) => entry.id)).toEqual(["e1", "e2", "e5", "e7"]);
    expect(allResult.map((entry) => entry.id)).toEqual(["e5"]);
  });

  it("keeps selection only when the selected entry remains in the query", () => {
    expect(nextSelectedEntryId("e1", entries, true)).toBe("e1");
    expect(nextSelectedEntryId("missing", entries, true)).toBe("e1");
    expect(nextSelectedEntryId("missing", entries, false)).toBeNull();
  });

  it("marks entries read by query scope instead of visible page scope", () => {
    const query = {
      feedScope: "all" as const,
      selectedTagIds: ["ai"],
      tagMatchMode: "any" as const,
      unreadOnly: false,
      searchText: "",
      searchScope: "allFeeds" as const
    };
    const updated = queryScopedReadState(entries, query, true);
    const changed = updated.filter((entry) => entry.tagIds.includes("ai"));

    expect(changed.every((entry) => entry.isRead)).toBe(true);
    expect(updated.find((entry) => entry.id === "e3")?.isRead).toBe(true);
    expect(updated.find((entry) => entry.id === "e4")?.isRead).toBe(false);
  });

  it("exposes explicit pagination state", () => {
    const page = visiblePage(entries, 3);

    expect(page.items).toHaveLength(3);
    expect(page.hasMore).toBe(true);
  });
});
