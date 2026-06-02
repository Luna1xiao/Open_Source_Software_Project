import { useCallback, useState } from "react";

import { getApiErrorMessage, importOpmlFile, subscribeToFeed, syncFeeds } from "../services/api";

type FeedActionStatus = "idle" | "running" | "error";

export function useFeedActions(onDataRefresh: () => Promise<void>) {
  const [status, setStatus] = useState<FeedActionStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const addFeed = useCallback(async (url: string, sync = true) => {
    setStatus("running");
    setErrorMessage(null);
    setNotice(null);
    try {
      const feed = await subscribeToFeed(url, sync);
      await onDataRefresh();
      setStatus("idle");
      setNotice(sync ? `Imported ${feed.title} and fetched its latest entries.` : `Imported ${feed.title}.`);
      return feed;
    } catch (error) {
      setStatus("error");
      setErrorMessage(getApiErrorMessage(error));
      throw error;
    }
  }, [onDataRefresh]);

  const importFeedsFromOpml = useCallback(async (file: File, syncAfterImport: boolean) => {
    setStatus("running");
    setErrorMessage(null);
    setNotice(null);
    try {
      const result = await importOpmlFile(file);
      const didImportFeeds = result.imported > 0;
      if (syncAfterImport && didImportFeeds) {
        await syncFeeds();
      }
      await onDataRefresh();
      setStatus("idle");
      setNotice(
        syncAfterImport && didImportFeeds
          ? `Imported ${result.imported} feeds, skipped ${result.skipped}, and synced entries.`
          : `Imported ${result.imported} feeds and skipped ${result.skipped}.`
      );
      return result;
    } catch (error) {
      setStatus("error");
      setErrorMessage(getApiErrorMessage(error));
      throw error;
    }
  }, [onDataRefresh]);

  const syncAll = useCallback(async () => {
    setStatus("running");
    setErrorMessage(null);
    setNotice(null);
    try {
      const results = await syncFeeds();
      await onDataRefresh();
      setStatus("idle");
      const fetched = results.reduce((sum, result) => sum + result.fetched, 0);
      const saved = results.reduce((sum, result) => sum + result.saved, 0);
      setNotice(`Synced ${results.length} feeds, fetched ${fetched} entries, saved ${saved}.`);
      return results;
    } catch (error) {
      setStatus("error");
      setErrorMessage(getApiErrorMessage(error));
      throw error;
    }
  }, [onDataRefresh]);

  const clearMessages = useCallback(() => {
    setErrorMessage(null);
    setNotice(null);
    if (status === "error") {
      setStatus("idle");
    }
  }, [status]);

  return {
    status,
    errorMessage,
    notice,
    addFeed,
    importFeedsFromOpml,
    syncAll,
    clearMessages
  };
}
