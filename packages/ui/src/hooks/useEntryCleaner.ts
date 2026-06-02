import { useCallback, useRef } from "react";

import type { Entry } from "../domain/types";
import { ensureEntryContent } from "../services/api";

export function useEntryCleaner(onEntryRefresh: (entryId: string) => Promise<Entry>) {
  const attemptedIds = useRef(new Set<string>());
  const runningIds = useRef(new Set<string>());

  const ensureCleaned = useCallback(async (entryId: string) => {
    if (attemptedIds.current.has(entryId) || runningIds.current.has(entryId)) {
      return;
    }

    runningIds.current.add(entryId);
    try {
      await ensureEntryContent(entryId);
      attemptedIds.current.add(entryId);
      await onEntryRefresh(entryId);
    } finally {
      runningIds.current.delete(entryId);
    }
  }, [onEntryRefresh]);

  return {
    ensureCleaned
  };
}
