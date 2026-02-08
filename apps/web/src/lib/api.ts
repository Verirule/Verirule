export async function apiFetch(path: string, accessToken?: string): Promise<unknown> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const url = `${baseUrl.replace(/\/$/, "")}${path}`;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    method: "GET",
    headers,
    cache: "no-store",
  });

  const body = (await response.json().catch(() => ({}))) as unknown;

  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }

  return body;
}
