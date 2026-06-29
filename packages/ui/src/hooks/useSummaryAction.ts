import { useCallback, useState } from "react";

import type { Entry } from "../domain/types";
import { getApiErrorMessage, requestSummaryStream } from "../services/api";

export function useSummaryAction(
  onEntryRefresh: (entryId: string) => Promise<Entry>,
  onUpdateEntry?: (entryId: string, transform: (entry: Entry) => Entry) => void
) {
  const [status, setStatus] = useState<"idle" | "running" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runSummary = useCallback(async (entryId: string) => {
    setStatus("running");
    setErrorMessage(null);
    onUpdateEntry?.(entryId, (entry) => ({ ...entry, summaryText: "" }));

    try {
      let finalStatus: string | null = null;
      await requestSummaryStream(entryId, {
        onChunk: (event) => {
          onUpdateEntry?.(entryId, (entry) => ({
            ...entry,
            summaryText: event.summary_text
          }));
        },
        onComplete: (result) => {
          finalStatus = result.status;
          onUpdateEntry?.(entryId, (entry) => ({
            ...entry,
            summaryText: result.summary_text
          }));
        }
      });

      await onEntryRefresh(entryId);

      if (finalStatus !== "success") {
        setStatus("error");
        setErrorMessage("Summary generation failed");
        return;
      }

      setStatus("idle");
    } catch (error) {
      setStatus("error");
      setErrorMessage(getApiErrorMessage(error));
    }
  }, [onEntryRefresh, onUpdateEntry]);

  const clearError = useCallback(() => {
    setErrorMessage(null);
    if (status === "error") {
      setStatus("idle");
    }
  }, [status]);

  return {
    status,
    errorMessage,
    runSummary,
    clearError
  };
}
