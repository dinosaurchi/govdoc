/**
 * Human-readable formatters shared across pages.
 */

/**
 * Format a byte count as a human readable string with an appropriate unit
 * (B, KB, MB, GB, TB). Uses binary units (1 KB = 1024 B), which is the
 * convention used by most file managers on Linux/Windows.
 *
 * Examples:
 *   formatBytes(0)           -> "0 B"
 *   formatBytes(512)         -> "512 B"
 *   formatBytes(1536)        -> "1.5 KB"
 *   formatBytes(5 * 1024**2) -> "5 MB"
 *   formatBytes(2.5 * 1024**3, 2) -> "2.50 GB"
 */
export function formatBytes(bytes: number, maxFractionDigits = 1): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '0 B';
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const base = 1024;
  const magnitude = Math.min(
    Math.floor(Math.log(bytes) / Math.log(base)),
    units.length - 1,
  );
  const value = bytes / Math.pow(base, magnitude);

  // Integer bytes (< 1 KB) should not have a fractional part.
  const fractionDigits = magnitude === 0 ? 0 : maxFractionDigits;
  const rounded = Number(value.toFixed(fractionDigits));
  // Drop trailing zeros for a cleaner display (e.g. "5 MB" not "5.0 MB").
  const display = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(fractionDigits);
  return `${display} ${units[magnitude]}`;
}
