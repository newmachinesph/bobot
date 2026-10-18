import { fetchApi } from "./client"

/* ---- Auth ---- */

export interface RegisterPayload {
  username: string
  email: string
  password: string
  region?: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: {
    id: string
    username: string
    tier: string
  }
}

export function register(data: RegisterPayload) {
  return fetchApi<AuthResponse>("/v1/accounts/register", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function login(data: LoginPayload) {
  return fetchApi<AuthResponse>("/v1/accounts/login", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

/* ---- User Profile ---- */

export interface UserProfile {
  id: string
  username: string
  tier: string
  region?: string
  bio?: string
  karma: number
  loob_dimensions: Record<string, number>
  created_at: string
}

export function getMyProfile(token: string) {
  return fetchApi<UserProfile>("/v1/accounts/me", {}, token)
}

export interface LoobScores {
  katapatan: number
  katumpakan: number
  kagalingan: number
  kapakumbabaan: number
  kalakarang_sibiko: number
}

export function getLoob(username: string) {
  return fetchApi<LoobScores>(`/v1/accounts/${username}/loob`)
}

export function updateProfile(
  data: { username?: string; region?: string; bio?: string },
  token: string
) {
  return fetchApi<UserProfile>("/v1/accounts/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  }, token)
}
