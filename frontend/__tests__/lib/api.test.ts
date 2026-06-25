import { describe, it, expect, vi, afterEach } from "vitest";
import { apiJson, setAccessToken } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
  setAccessToken(null);
});

describe("apiJson", () => {
  it("returns undefined for a 204 No Content (e.g. DELETE)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const result = await apiJson("/api/v1/habits/x", { method: "DELETE" });
    expect(result).toBeUndefined();
  });

  it("throws instead of swallowing a server error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(apiJson("/api/v1/habits/x", { method: "DELETE" })).rejects.toThrow("Boom");
  });
});
