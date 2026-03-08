// API client — defaults to the same-origin Next.js proxy and can target an
// explicit backend when an absolute API base URL is configured.

const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
const API_BASE = configuredApiBase !== undefined ? configuredApiBase.replace(/\/$/, '') : '';

type ErrorMessageBody = {
  detail?: unknown;
  message?: string;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function extractMessage(body: unknown, fallback: string): string {
  if (typeof body === 'string' && body.trim()) {
    return body;
  }

  if (isObject(body)) {
    const typed = body as ErrorMessageBody;
    if (typeof typed.message === 'string' && typed.message.trim()) {
      return typed.message;
    }
    if (typeof typed.detail === 'string' && typed.detail.trim()) {
      return typed.detail;
    }
    if (isObject(typed.detail) && typeof typed.detail.message === 'string') {
      return typed.detail.message;
    }
  }

  return fallback;
}

async function readBody(res: Response): Promise<unknown> {
  if (res.status === 204) {
    return undefined;
  }

  const contentType = res.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return res.json();
  }

  const text = await res.text();
  return text || undefined;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly detail?: unknown,
    public readonly body?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  const body = await readBody(res);

  if (!res.ok) {
    const fallbackMessage = `API ${res.status}: ${path}`;
    const detail = isObject(body) ? body.detail ?? body : body;
    throw new ApiError(res.status, extractMessage(body, fallbackMessage), detail, body);
  }

  return body as T;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },

  post<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  patch<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  },

  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' });
  },
};
