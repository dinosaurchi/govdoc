import { describe, it, expect } from 'vitest';
import { formatErrorPayload } from './api';

describe('formatErrorPayload', () => {
  it('reads message from top-level error object (JSONResponse handlers)', () => {
    expect(
      formatErrorPayload({
        error: { code: 'AI_MODEL_UNAVAILABLE', message: 'upstream timeout', details: {} },
      }),
    ).toBe('upstream timeout');
  });

  it('reads message from FastAPI HTTPException detail.error', () => {
    expect(
      formatErrorPayload({
        detail: {
          error: {
            code: 'MISSING_ROLE_HEADER',
            message: 'X-GovDoc-Role header is required',
            details: {},
          },
        },
      }),
    ).toBe('X-GovDoc-Role header is required');
  });

  it('handles string detail', () => {
    expect(formatErrorPayload({ detail: 'Simple message' })).toBe('Simple message');
  });
});
