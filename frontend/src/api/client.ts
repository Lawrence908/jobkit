/** When loaded from port 8123 (direct), API is on same host port 8122. Behind Caddy, use relative /api. */
export function getApiBase(): string {
  if (typeof window === "undefined") return "";
  const { protocol, hostname, port } = window.location;
  if (port === "8123") return `${protocol}//${hostname}:8122`;
  return "";
}

/** Full URL to start Google OAuth (backend redirects to Google). Use for link href or location. */
export function getGoogleOAuthStartUrl(): string {
  const base = getApiBase();
  return base ? `${base}/api/google/oauth/start` : "/api/google/oauth/start";
}

/** Auth endpoints do not use CSRF; we must not call GET /api/auth/csrf before login. */
function needsCsrfToken(method: string, path: string): boolean {
  if (method !== "POST" && method !== "PATCH" && method !== "PUT") return false;
  const p = path.replace(getApiBase(), "").split("?")[0];
  return p !== "/api/auth/login" && p !== "/api/auth/logout";
}

async function request<T>(
  path: string,
  options: RequestInit & { method?: string } = {}
): Promise<T> {
  const base = getApiBase();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const method = (options.method || "GET").toUpperCase();
  const wantsCsrf = needsCsrfToken(method, path);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (wantsCsrf) {
    let token = getCsrfToken();
    if (!token) {
      try {
        token = await refreshCsrfToken();
      } catch {
        /* ignore; will send without token and may get 403 */
      }
    }
    if (token) headers["X-CSRF-Token"] = token;
  }
  let res = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (res.status === 403 && wantsCsrf) {
    try {
      const token = await refreshCsrfToken();
      if (token) {
        headers["X-CSRF-Token"] = token;
        res = await fetch(url, {
          ...options,
          credentials: "include",
          headers,
        });
      }
    } catch {
      /* fall through to error handling below */
    }
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

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
};

/** Call after auth so the CSRF cookie is set/refreshed for subsequent POSTs. Returns the token from the response body. */
export async function refreshCsrfToken(): Promise<string> {
  const data = await api.get<{ token: string }>("/api/auth/csrf");
  return data?.token ?? getCsrfToken();
}

export function getCsrfToken(): string {
  const match = document.cookie.match(/jobkit_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export function withCsrf(headers: Record<string, string> = {}): Record<string, string> {
  const token = getCsrfToken();
  return token ? { ...headers, "X-CSRF-Token": token } : headers;
}
