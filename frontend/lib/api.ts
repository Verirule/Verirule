export type ApiError = {
  status: number;
  message: string;
};

function getBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!baseUrl) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
  }
  return baseUrl;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("verirule_token");
}

function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("verirule_token");
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401 || response.status === 403) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = data?.detail || "Request failed";
    throw { status: response.status, message } as ApiError;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", Bearer );
  }

  const response = await fetch(${getBaseUrl()}, {
    ...options,
    headers,
  });

  return handleResponse<T>(response);
}

export const api = {
  get<T>(path: string) {
    return apiRequest<T>(path, { method: "GET" });
  },
  post<T>(path: string, body?: unknown) {
    return apiRequest<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  },
  put<T>(path: string, body?: unknown) {
    return apiRequest<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  },
  patch<T>(path: string, body?: unknown) {
    return apiRequest<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  },
};
