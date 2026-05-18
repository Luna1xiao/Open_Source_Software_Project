import { describe, expect, it } from "vitest";
import { composeDigest } from "./digest";
import { digestTemplates, entries, tags } from "./fixtures";

describe("digest composition", () => {
  it("keeps digest policy outside view components", () => {
    const digest = composeDigest([entries[0]], tags, digestTemplates[0]);

    expect(digest).toContain("# A practical guide to serialized agent work queues");
    expect(digest).toContain("## Summary");
    expect(digest).toContain("## Note");
    expect(digest).toContain("Tags: AI, Infrastructure");
  });
});
