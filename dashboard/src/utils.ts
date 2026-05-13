export function fmtDate(iso: string): string {
  return (
    new Date(iso).toLocaleString("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }) + " UTC"
  );
}

export function fmtDuration(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}
