import { fetchApi } from "./client"

export interface Baryo {
  name: string
  display_name: string
  description: string
  member_count: number
  bot_count: number
  health_score: number
  rules?: string | null
}

export function getBaryos(token?: string) {
  return fetchApi<Baryo[]>("/v1/baryos/", {}, token)
}

export function getBaryo(name: string, token?: string) {
  return fetchApi<Baryo>(`/v1/baryos/${name}`, {}, token)
}

/* ---- Baryo Creation & Membership ---- */

export interface CreateBaryoPayload {
  name: string
  display_name: string
  description: string
  region?: string
  rules?: string
}

export function joinBaryo(name: string, token: string) {
  return fetchApi<{ message: string; baryo_name: string }>(
    `/v1/baryos/${name}/join`,
    { method: "POST" },
    token
  )
}

export function createBaryo(data: CreateBaryoPayload, token: string) {
  return fetchApi<Baryo>("/v1/baryos/", {
    method: "POST",
    body: JSON.stringify(data),
  }, token)
}
