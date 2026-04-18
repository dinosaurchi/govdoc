/** Same-origin `/api/v1` works with Vite proxy (local dev) and nginx proxy (docker). */
export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Role label to API role ID mapping.
 * The frontend uses human-readable labels, but the API expects machine-readable IDs.
 */
const ROLE_MAP: Record<string, string> = {
  'Intake Clerk': 'intake_clerk',
  'Department Reviewer': 'reviewer',
  'Consultant': 'consultant',
  'Supervisor': 'supervisor',
};

function getRoleId(): string | null {
  const label = localStorage.getItem('govdoc_role');
  if (label) return ROLE_MAP[label] || label;
  // Fallback: try legacy key
  const legacy = localStorage.getItem('activeRole');
  if (legacy) return ROLE_MAP[legacy] || legacy;
  return null;
}

function getHeaders(role?: string): Record<string, string> {
  const headers: Record<string, string> = {};
  const roleId = role ? (ROLE_MAP[role] || role) : getRoleId();
  if (roleId) headers['X-GovDoc-Role'] = roleId;
  return headers;
}

/**
 * Normalize error JSON from the API. Supports:
 * - Custom handlers: `{ error: { message, code } }` (no `detail` wrapper)
 * - FastAPI HTTPException: `{ detail: string | { error: { message } } }`
 * - Validation: `{ detail: [ { msg, loc }, ... ] }`
 */
/** Exported for unit tests — normalizes JSON error bodies from `/api/v1`. */
export function formatErrorPayload(body: unknown): string {
  if (!body || typeof body !== 'object') {
    return 'API request failed';
  }
  const o = body as Record<string, unknown>;

  // Shape from app exception handlers (JSONResponse content={ error: {...} })
  const topError = o.error;
  if (topError && typeof topError === 'object' && 'message' in topError) {
    const msg = (topError as { message?: string }).message;
    if (typeof msg === 'string' && msg.length > 0) return msg;
  }

  if (!('detail' in o)) {
    return 'API request failed';
  }

  const d = o.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d
      .map((item) =>
        typeof item === 'object' && item && 'msg' in item
          ? String((item as { msg: string }).msg)
          : JSON.stringify(item),
      )
      .join('; ');
  }
  if (d && typeof d === 'object') {
    const err = d as { error?: { message?: string; code?: string } };
    if (err.error?.message) return err.error.message;
    return JSON.stringify(d);
  }
  return 'API request failed';
}

async function throwIfNotOk(res: Response): Promise<void> {
  if (res.ok) return;
  const text = await res.text();
  let body: unknown = {};
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      throw new Error(`HTTP ${res.status} ${res.statusText}: ${text.slice(0, 300)}`);
    }
  }
  const msg = formatErrorPayload(body);
  if (msg !== 'API request failed') {
    throw new Error(msg);
  }
  throw new Error(
    text.trim()
      ? `HTTP ${res.status} ${res.statusText}: ${text.slice(0, 300)}`
      : `HTTP ${res.status} ${res.statusText}`,
  );
}

export async function apiGet<T>(path: string, role?: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { headers: getHeaders(role) });
  if (!res.ok) {
    await throwIfNotOk(res);
  }
  return res.json();
}

export type PagedResult<T> = {
  items: T[];
  total: number | null;
};

/** Paged GET helper: reads `X-Total-Count` alongside the JSON body, so pages
 *  can implement "load more" pagination without making a second count call. */
export async function apiGetPaged<T>(path: string, role?: string): Promise<PagedResult<T>> {
  const res = await fetch(`${API_BASE_URL}${path}`, { headers: getHeaders(role) });
  if (!res.ok) {
    await throwIfNotOk(res);
  }
  const items = (await res.json()) as T[];
  const header = res.headers.get('x-total-count');
  const total = header != null ? Number(header) : null;
  return {
    items,
    total: Number.isFinite(total) ? total : null,
  };
}

export async function apiPost<T>(path: string, body?: unknown, role?: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { ...getHeaders(role), 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    await throwIfNotOk(res);
  }
  return res.json();
}

export async function apiUpload<T>(path: string, file: File, role?: string): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: getHeaders(role),
    body: formData,
  });
  if (!res.ok) {
    await throwIfNotOk(res);
  }
  return res.json();
}

/** Legacy helper — used by pages that haven't been migrated yet. */
export async function fetchApi(path: string, options: RequestInit = {}) {
  const role = getRoleId();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };
  if (role) headers['X-GovDoc-Role'] = role;

  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    await throwIfNotOk(res);
  }

  return res.json();
}

/** Multipart upload — do not set Content-Type (browser sets boundary). */
export async function uploadDocument<T = unknown>(file: File, role?: string): Promise<T> {
  return apiUpload<T>('/documents/', file, role);
}
