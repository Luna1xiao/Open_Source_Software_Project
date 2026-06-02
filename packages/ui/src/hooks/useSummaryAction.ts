import { useCallback, useState } from "react";

import type { Entry } from "../domain/types";
import { getApiErrorMessage, requestSummary } from "../services/api";

export function useSummaryAction(onEntryRefresh: (entryId: string) => Promise<Entry>) {
  const [status, setStatus] = useState<"idle" | "running" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runSummary = useCallback(async (entryId: string) => {
    setStatus("running");
    setErrorMessage(null);
    try {
      await requestSummary(entryId);
      await onEntryRefresh(entryId);
      setStatus("idle");
    } catch (error) {
      setStatus("error");
      setErrorMessage(getApiErrorMessage(error));
    }
  }, [onEntryRefresh]);

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
