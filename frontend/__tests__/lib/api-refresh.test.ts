import { describe, it, expect, vi, afterEach } from "vitest";
import { apiFetch, setAccessToken } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
  setAccessToken(null);
});

describe("apiFetch refresh single-flight", () => {
  it("coalesces concurrent 401s into a single /refresh call", async () => {
    let refreshCalls = 0;
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/api/v1/auth/refresh")) {
        refreshCalls += 1;
        return new Response(JSON.stringify({ access_token: "new-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      const auth = (init?.headers as Headers | undefined)?.get?.("Authorization");
      if (!auth) return new Response("unauthorized", { status: 401 });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken(null);

    // Two protected requests fire concurrently; both 401 and both want a refresh.
    const [a, b] = await Promise.all([apiFetch("/a"), apiFetch("/b")]);

    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
    expect(refreshCalls).toBe(1);
  });
});
