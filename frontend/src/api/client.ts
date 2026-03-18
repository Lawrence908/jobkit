import { supabase } from "../lib/supabase";

/** When loaded from port 8123 (direct), API is on same host port 8122. Behind Caddy, use relative /api. */
export function getApiBase(): string {
  if (typeof window === "undefined") return "";
  const { protocol, hostname, port } = window.location;
  if (port === "8123") return `${protocol}//${hostname}:8122`;
  return "";
}

async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function request<T>(
  path: string,
  options: RequestInit & { method?: string } = {},
): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const token = await getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    // Legacy fallback: try CSRF cookie for old session-based auth
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });

  if (res.status === 401) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || String(err));
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

async function getBlob(path: string): Promise<Blob> {
  const base = getApiBase();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers: Record<string, string> = {};
  const token = await getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(url, { credentials: "include", headers });
  if (res.status === 401) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Request failed");
  }
  return res.blob();
}

async function postForm<T = unknown>(path: string, formData: FormData): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers: Record<string, string> = {};
  const token = await getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  } else {
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const res = await fetch(url, {
    method: "POST",
    body: formData,
    credentials: "include",
    headers,
  });
  if (res.status === 401) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Upload failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  getBlob,
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path: string) => request<undefined>(path, { method: "DELETE" }),
  postForm,
};

export function getCsrfToken(): string {
  const match = document.cookie.match(/jobkit_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/** @deprecated Legacy CSRF refresh -- kept for backward compat */
export async function refreshCsrfToken(): Promise<string> {
  try {
    const data = await api.get<{ token: string }>("/api/auth/csrf");
    return data?.token ?? getCsrfToken();
  } catch {
    return getCsrfToken();
  }
}

/** @deprecated Legacy CSRF helper */
export function withCsrf(headers: Record<string, string> = {}): Record<string, string> {
  const token = getCsrfToken();
  return token ? { ...headers, "X-CSRF-Token": token } : headers;
}
