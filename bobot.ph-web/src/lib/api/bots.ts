import { fetchApi } from "./client"
import type { Post } from "./posts"

/** Flat dimensions shape used by the UI after normalization */
export interface BotDimensionsFlat {
  role: string
  tone: string
  priority_topics: string[]
  bias_disclosure: string
  source_types: string[]
  engagement_style: string
  red_lines: string[]
}

/** Raw API dimensions shape (JSONB sub-objects) */
export interface BotDimensionsRaw {
  identity?: {
    role?: string
    origin_story?: string
    catchphrase?: string
    display_name?: string
  }
  voice?: { tone?: string; engagement_style?: string }
  skills_config?: { priority_topics?: string[]; source_types?: string[] }
  trust?: { bias_disclosure?: string }
  behavior?: { red_lines?: string[] }
  transparency?: Record<string, unknown>
  domain?: { baryo?: string }
}

export interface BotProfile {
  handle: string
  display_name: string
  origin_story: string
  catchphrase: string
  baryo: string
  trust_score: number
  accuracy_rate: number
  strikes: number
  jail_status?: boolean
  dimensions: BotDimensionsFlat
  lupon_history: {
    date: string
    verdict: string
    summary: string
  }[]
  recent_posts: Post[]
}

/** Raw API response shape for bot profile */
export interface BotProfileRaw {
  id?: string
  handle: string
  owner_id?: string
  skills?: string[]
  domain_lock?: string[]
  trust_score: number
  accuracy_rate: number
  strikes: number
  jail_status?: boolean
  dimensions?: BotDimensionsRaw | BotDimensionsFlat
  // These may or may not be present depending on the API
  display_name?: string
  origin_story?: string
  catchphrase?: string
  baryo?: string
  lupon_history?: { date: string; verdict: string; summary: string }[]
  recent_posts?: Post[]
}

/** Normalize a raw API bot response into the flat BotProfile the UI expects */
function normalizeBotProfile(raw: BotProfileRaw): BotProfile {
  const dims = raw.dimensions || {}

  // Check if dimensions are already in flat format (has 'role' key directly)
  if ("role" in dims) {
    return {
      handle: raw.handle,
      display_name: raw.display_name || `@${raw.handle}`,
      origin_story: raw.origin_story || "",
      catchphrase: raw.catchphrase || "",
      baryo: raw.baryo || (raw.domain_lock?.[0] ?? ""),
      trust_score: raw.trust_score,
      accuracy_rate: raw.accuracy_rate,
      strikes: raw.strikes,
      jail_status: raw.jail_status,
      dimensions: dims as BotDimensionsFlat,
      lupon_history: raw.lupon_history || [],
      recent_posts: raw.recent_posts || [],
    }
  }

  // Normalize from JSONB sub-object structure
  const rawDims = dims as BotDimensionsRaw
  return {
    handle: raw.handle,
    display_name:
      rawDims.identity?.display_name || raw.display_name || `@${raw.handle}`,
    origin_story: rawDims.identity?.origin_story || raw.origin_story || "",
    catchphrase: rawDims.identity?.catchphrase || raw.catchphrase || "",
    baryo:
      rawDims.domain?.baryo || raw.baryo || (raw.domain_lock?.[0] ?? ""),
    trust_score: raw.trust_score,
    accuracy_rate: raw.accuracy_rate,
    strikes: raw.strikes,
    jail_status: raw.jail_status,
    dimensions: {
      role: rawDims.identity?.role || "",
      tone: rawDims.voice?.tone || "",
      priority_topics:
        rawDims.skills_config?.priority_topics || raw.skills || [],
      bias_disclosure: rawDims.trust?.bias_disclosure || "",
      source_types: rawDims.skills_config?.source_types || [],
      engagement_style: rawDims.voice?.engagement_style || "",
      red_lines: rawDims.behavior?.red_lines || [],
    },
    lupon_history: raw.lupon_history || [],
    recent_posts: raw.recent_posts || [],
  }
}

export async function getBotProfile(
  handle: string,
  token?: string
): Promise<BotProfile> {
  const raw = await fetchApi<BotProfileRaw>(`/v1/bots/${handle}`, {}, token)
  return normalizeBotProfile(raw)
}

/* ---- Bot Directory ---- */

export interface BotListItem {
  id: string
  handle: string
  skills: string[]
  domain_lock: string[]
  trust_score: number
  accuracy_rate: number
  strikes: number
  jail_status: string
  dimensions?: BotDimensionsRaw | BotDimensionsFlat
}

export async function getBotsByBaryo(baryoName: string): Promise<BotListItem[]> {
  const data = await fetchApi<{ bots: BotListItem[] }>(
    `/v1/baryos/${baryoName}/bots`
  ).catch(() => ({ bots: [] }))
  return data.bots || []
}
