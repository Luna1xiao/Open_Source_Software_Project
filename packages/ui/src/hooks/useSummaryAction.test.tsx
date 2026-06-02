import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSummaryAction } from "./useSummaryAction";

const requestSummary = vi.fn();

vi.mock("../services/api", () => ({
  getApiErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "Request failed"),
  requestSummary: (...args: unknown[]) => requestSummary(...args)
}));

describe("useSummaryAction", () => {
  beforeEach(() => {
    requestSummary.mockReset();
  });

  it("runs summary generation and refreshes the entry", async () => {
    requestSummary.mockResolvedValue({ summary_text: "Stored summary" });
    const refreshEntry = vi.fn().mockResolvedValue({ id: "entry-1" });
    const { result } = renderHook(() => useSummaryAction(refreshEntry));

    await act(async () => {
      await result.current.runSummary("entry-1");
    });

    expect(requestSummary).toHaveBeenCalledWith("entry-1");
    expect(refreshEntry).toHaveBeenCalledWith("entry-1");
    expect(result.current.status).toBe("idle");
    expect(result.current.errorMessage).toBeNull();
  });

  it("captures API errors without throwing", async () => {
    requestSummary.mockRejectedValue(new Error("Entry not found"));
    const refreshEntry = vi.fn();
    const { result } = renderHook(() => useSummaryAction(refreshEntry));

    await act(async () => {
      await result.current.runSummary("missing");
    });

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("Entry not found");
  });
});
