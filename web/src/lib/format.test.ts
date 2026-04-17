import { describe, expect, it } from 'vitest';
import { formatBytes } from './format';

describe('formatBytes', () => {
  it('returns "0 B" for zero and invalid inputs', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(-1)).toBe('0 B');
    expect(formatBytes(Number.NaN)).toBe('0 B');
  });

  it('uses bytes for values < 1 KB without a fractional part', () => {
    expect(formatBytes(1)).toBe('1 B');
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(1023)).toBe('1023 B');
  });

  it('uses KB for values >= 1 KB and < 1 MB', () => {
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(1024 * 1023)).toBe('1023 KB');
  });

  it('uses MB for values >= 1 MB and < 1 GB', () => {
    expect(formatBytes(1024 * 1024)).toBe('1 MB');
    expect(formatBytes(5 * 1024 * 1024)).toBe('5 MB');
    expect(formatBytes(Math.round(2.5 * 1024 * 1024))).toBe('2.5 MB');
  });

  it('uses GB for values >= 1 GB and < 1 TB', () => {
    expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GB');
    expect(formatBytes(3 * 1024 * 1024 * 1024)).toBe('3 GB');
  });

  it('supports a custom fraction-digits setting', () => {
    expect(formatBytes(Math.round(2.123 * 1024 * 1024), 2)).toBe('2.12 MB');
    expect(formatBytes(Math.round(2.123 * 1024 * 1024), 0)).toBe('2 MB');
  });
});
