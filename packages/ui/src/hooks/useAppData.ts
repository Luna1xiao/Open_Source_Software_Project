import { startTransition, useCallback, useEffect, useState } from "react";

import type { Entry, Feed, Tag } from "../domain/types";
import { loadAppData, loadEntry } from "../services/api";

export interface AppDataState {
  feeds: Feed[];
  tags: Tag[];
  entries: Entry[];
}

const emptyData: AppDataState = {
  feeds: [],
  tags: [],
  entries: []
};

export function useAppData() {
  const [data, setData] = useState<AppDataState>(emptyData);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const next = await loadAppData();
      startTransition(() => {
        setData(next);
        setIsLoading(false);
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load app data");
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const updateEntry = useCallback((entryId: string, transform: (entry: Entry) => Entry) => {
    setData((current) => ({
      ...current,
      entries: current.entries.map((entry) => (entry.id === entryId ? transform(entry) : entry))
    }));
  }, []);

  const replaceEntry = useCallback((nextEntry: Entry) => {
    setData((current) => ({
      ...current,
      entries: current.entries.map((entry) => (entry.id === nextEntry.id ? nextEntry : entry))
    }));
  }, []);

  const refreshEntry = useCallback(async (entryId: string) => {
    const nextEntry = await loadEntry(entryId);
    replaceEntry(nextEntry);
    return nextEntry;
  }, [replaceEntry]);

  return {
    data,
    error,
    isLoading,
    reload,
    setData,
    updateEntry,
    replaceEntry,
    refreshEntry
  };
}
