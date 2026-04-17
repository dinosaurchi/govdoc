/** Same-origin `/api/v1` works with Vite proxy (local dev) and nginx proxy (docker). */
export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

function formatErrorPayload(body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return JSON.stringify(d);
    if (d && typeof d === 'object') return JSON.stringify(d);
  }
  return 'API request failed';
}

export async function fetchApi(path: string, options: RequestInit = {}) {
  const role = localStorage.getItem('activeRole') || 'Intake Clerk';

  const headers: Record<string, string> = {
    'X-Role': role,
    ...(options.headers as Record<string, string>),
  };

  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(formatErrorPayload(error));
  }

  return res.json();
}

/** Multipart upload — do not set Content-Type (browser sets boundary). */
export async function uploadDocument(formData: FormData) {
  const role = localStorage.getItem('activeRole') || 'Intake Clerk';

  const res = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    headers: {
      'X-Role': role,
    },
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(formatErrorPayload(error));
  }

  return res.json();
}
