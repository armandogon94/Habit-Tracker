/**
 * The user's local calendar day as `YYYY-MM-DD`.
 *
 * Use this instead of `new Date().toISOString().split("T")[0]`, which returns
 * the UTC day: for a user west of UTC in the evening that is already
 * "tomorrow", so completions get logged against the wrong date.
 *
 * @param tz  Optional IANA timezone (e.g. "America/Los_Angeles"). Defaults to
 *            the runtime's local zone, which is normally the user's.
 * @param now Injectable clock for testing; defaults to the current instant.
 */
export function localToday(tz?: string, now: Date = new Date()): string {
  // en-CA formats dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}
