import { describe, expect, it } from "vitest";

import { localToday } from "@/lib/utils";

// 03:00 UTC on 2026-06-25. The bug: `new Date().toISOString()` would call this
// "2026-06-25" for everyone, but a user in Los Angeles is still on 2026-06-24.
const INSTANT = new Date("2026-06-25T03:00:00Z");

describe("localToday", () => {
  it("returns a YYYY-MM-DD string", () => {
    expect(localToday("UTC", INSTANT)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("uses the UTC calendar day for the UTC zone", () => {
    expect(localToday("UTC", INSTANT)).toBe("2026-06-25");
  });

  it("returns the previous local day for a west-of-UTC zone in the evening", () => {
    // 03:00 UTC == 20:00 the previous day in Los Angeles (UTC-7 in summer).
    expect(localToday("America/Los_Angeles", INSTANT)).toBe("2026-06-24");
  });

  it("returns the correct local day for an east-of-UTC zone", () => {
    // 03:00 UTC == 12:00 same day in Tokyo (UTC+9).
    expect(localToday("Asia/Tokyo", INSTANT)).toBe("2026-06-25");
  });
});
