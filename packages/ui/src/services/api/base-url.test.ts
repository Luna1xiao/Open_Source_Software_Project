import { afterEach, describe, expect, it } from "vitest";

import { resolveBackendBaseUrl } from "./base-url";

describe("resolveBackendBaseUrl", () => {
  afterEach(() => {
    delete window.__BACKEND_PORT__;
  });

  it("uses the injected backend port when available", () => {
    window.__BACKEND_PORT__ = 43123;

    expect(resolveBackendBaseUrl()).toBe("http://127.0.0.1:43123");
  });

  it("falls back to the default localhost backend", () => {
    expect(resolveBackendBaseUrl()).toBe("http://127.0.0.1:8000");
  });
});
