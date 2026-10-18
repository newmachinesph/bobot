export const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function fetchApi<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  }

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error: ${res.status}`)
  }

  return res.json()
}
