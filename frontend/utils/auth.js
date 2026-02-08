const TOKEN_KEY = "verirule_token";

function getApiBaseUrl() {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!baseUrl) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
  }
  return baseUrl;
}

export async function login(email, password) {
  const response = await fetch(${getApiBaseUrl()}/login, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = data.detail || "Login failed";
    throw new Error(message);
  }

  const data = await response.json();
  if (data.access_token) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
  }
  return data;
}

export async function logout() {
  const token = getToken();
  if (token) {
    await fetch(${getApiBaseUrl()}/logout, {
      method: "POST",
      headers: { Authorization: Bearer  },
    }).catch(() => undefined);
  }
  localStorage.removeItem(TOKEN_KEY);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function isTokenValid() {
  const token = getToken();
  if (!token) return false;

  try {
    const payload = JSON.parse(atob(token.split(".")[1] || ""));
    if (payload.exp && Date.now() >= payload.exp * 1000) {
      localStorage.removeItem(TOKEN_KEY);
      return false;
    }
    return true;
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    return false;
  }
}

export function requireAuth(router) {
  if (!isTokenValid()) {
    router.replace("/login");
  }
}
