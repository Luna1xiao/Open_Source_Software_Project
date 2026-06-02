import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";

import type { Entry, Feed, Tag } from "../domain/types";
import type { AppDataState } from "./useAppData";
import { getApiErrorMessage, removeEntry, updateEntryReadState, updateEntryStarState } from "../services/api";

type SetData = Dispatch<SetStateAction<AppDataState>>;

function deriveCollections(feeds: Feed[], tags: Tag[], entries: Entry[]) {
  const unreadByFeed = new Map<string, number>();
  const unreadByTag = new Map<string, number>();
  const usageByTag = new Map<string, number>();

  for (const entry of entries) {
    if (!entry.isRead) {
      unreadByFeed.set(entry.feedId, (unreadByFeed.get(entry.feedId) ?? 0) + 1);
    }
    for (const tagId of entry.tagIds) {
      usageByTag.set(tagId, (usageByTag.get(tagId) ?? 0) + 1);
      if (!entry.isRead) {
        unreadByTag.set(tagId, (unreadByTag.get(tagId) ?? 0) + 1);
      }
    }
  }

  return {
    feeds: feeds.map((feed) => ({ ...feed, unreadCount: unreadByFeed.get(feed.id) ?? 0 })),
    tags: tags.map((tag) => ({
      ...tag,
      usageCount: usageByTag.get(tag.id) ?? 0,
      unreadCount: unreadByTag.get(tag.id) ?? 0
    }))
  };
}

function withDerivedCollections(current: AppDataState, entries: Entry[]): AppDataState {
  const nextCollections = deriveCollections(current.feeds, current.tags, entries);
  return {
    entries,
    feeds: nextCollections.feeds,
    tags: nextCollections.tags
  };
}

export function useEntryActions(setData: SetData, reload: () => Promise<void>) {
  const setReadState = useCallback(async (entry: Entry, isRead: boolean) => {
    if (entry.isRead === isRead) {
      return;
    }

    setData((current) =>
      withDerivedCollections(
        current,
        current.entries.map((candidate) => (candidate.id === entry.id ? { ...candidate, isRead } : candidate))
      )
    );

    try {
      await updateEntryReadState(entry.id, isRead);
    } catch (error) {
      await reload();
      throw new Error(getApiErrorMessage(error));
    }
  }, [reload, setData]);

  const setReadStateForEntries = useCallback(async (entries: Entry[], isRead: boolean) => {
    const targetIds = new Set(entries.filter((entry) => entry.isRead !== isRead).map((entry) => entry.id));
    if (targetIds.size === 0) {
      return;
    }

    setData((current) =>
      withDerivedCollections(
        current,
        current.entries.map((entry) => (targetIds.has(entry.id) ? { ...entry, isRead } : entry))
      )
    );

    try {
      await Promise.all([...targetIds].map((entryId) => updateEntryReadState(entryId, isRead)));
    } catch (error) {
      await reload();
      throw new Error(getApiErrorMessage(error));
    }
  }, [reload, setData]);

  const toggleStar = useCallback(async (entry: Entry) => {
    const nextStarred = !entry.isStarred;
    setData((current) =>
      withDerivedCollections(
        current,
        current.entries.map((candidate) => (candidate.id === entry.id ? { ...candidate, isStarred: nextStarred } : candidate))
      )
    );

    try {
      await updateEntryStarState(entry.id, nextStarred);
    } catch (error) {
      await reload();
      throw new Error(getApiErrorMessage(error));
    }
  }, [reload, setData]);

  const deleteOne = useCallback(async (entryId: string) => {
    setData((current) => withDerivedCollections(current, current.entries.filter((entry) => entry.id !== entryId)));

    try {
      await removeEntry(entryId);
    } catch (error) {
      await reload();
      throw new Error(getApiErrorMessage(error));
    }
  }, [reload, setData]);

  return {
    setReadState,
    setReadStateForEntries,
    toggleStar,
    deleteOne
  };
}
