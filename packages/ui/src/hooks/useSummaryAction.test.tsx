import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSummaryAction } from "./useSummaryAction";

const requestSummaryStream = vi.fn();

vi.mock("../services/api", () => ({
  getApiErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "Request failed"),
  requestSummaryStream: (...args: unknown[]) => requestSummaryStream(...args)
}));

describe("useSummaryAction", () => {
  beforeEach(() => {
    requestSummaryStream.mockReset();
  });

  it("streams summary chunks and refreshes the entry", async () => {
    requestSummaryStream.mockImplementation(async (_entryId, handlers) => {
      handlers.onChunk({ summary_text: "Partial summary" });
      handlers.onComplete({
        summary_text: "Stored summary",
        status: "success"
      });
    });
    const refreshEntry = vi.fn().mockResolvedValue({ id: "entry-1" });
    const updateEntry = vi.fn();
    const { result } = renderHook(() => useSummaryAction(refreshEntry, updateEntry));

    await act(async () => {
      await result.current.runSummary("entry-1");
    });

    expect(requestSummaryStream).toHaveBeenCalledWith("entry-1", expect.any(Object));
    expect(updateEntry).toHaveBeenCalled();
    expect(refreshEntry).toHaveBeenCalledWith("entry-1");
    expect(result.current.status).toBe("idle");
    expect(result.current.errorMessage).toBeNull();
  });

  it("captures API errors without throwing", async () => {
    requestSummaryStream.mockRejectedValue(new Error("Entry not found"));
    const refreshEntry = vi.fn();
    const { result } = renderHook(() => useSummaryAction(refreshEntry));

    await act(async () => {
      await result.current.runSummary("missing");
    });

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("Entry not found");
  });
});
