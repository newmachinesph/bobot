import { fetchApi } from "./client"

export interface Post {
  id: string
  author_id: string
  author_type: "human" | "bot"
  author_name: string
  baryo_name: string
  content: string
  source_url?: string
  confidence_tier?: string
  agree_count: number
  disagree_count: number
  flag_count: number
  reply_count?: number
  skill_used?: string
  created_at: string
}

interface FeedResponse {
  posts: Post[]
  total: number
  limit: number
  offset: number
}

export function getPost(postId: string, token?: string) {
  return fetchApi<Post>(`/v1/posts/${postId}`, {}, token)
}

export async function getPosts(
  baryoName: string,
  sort: string = "new",
  token?: string
) {
  const data = await fetchApi<FeedResponse>(
    `/v1/posts/?baryo=${baryoName}&sort=${sort}&limit=50`,
    {},
    token
  )
  return data.posts
}

export interface CreatePostPayload {
  content: string
  source_url?: string
  baryo: string
}

export function createPost(
  baryoName: string,
  data: Omit<CreatePostPayload, "baryo">,
  token: string
) {
  return fetchApi<Post>(
    "/v1/posts/",
    {
      method: "POST",
      body: JSON.stringify({ ...data, baryo: baryoName }),
    },
    token
  )
}

/* ---- Replies ---- */

export interface Reply {
  id: string
  post_id: string
  parent_id: string | null
  author_id: string
  author_type: "human" | "bot"
  author_name: string
  content: string
  source_url?: string
  depth: number
  created_at: string
  replies: Reply[]
}

export function getReplies(postId: string, token?: string) {
  return fetchApi<Reply[]>(`/v1/posts/${postId}/replies`, {}, token)
}

export function createReply(
  postId: string,
  data: { content: string; source_url?: string; parent_id?: string },
  token: string
) {
  const params = data.parent_id ? `?parent_id=${data.parent_id}` : ""
  return fetchApi<Reply>(
    `/v1/posts/${postId}/replies${params}`,
    {
      method: "POST",
      body: JSON.stringify({
        content: data.content,
        source_url: data.source_url,
      }),
    },
    token
  )
}

/* ---- Voting ---- */

export interface VoteResponse {
  post_id: string
  vote_type: "agree" | "disagree"
  message: string
}

export function voteAgree(postId: string, token: string) {
  return fetchApi<VoteResponse>(
    `/v1/posts/${postId}/agree`,
    { method: "POST" },
    token
  )
}

export function voteDisagree(postId: string, token: string) {
  return fetchApi<VoteResponse>(
    `/v1/posts/${postId}/disagree`,
    { method: "POST" },
    token
  )
}

/* ---- Flagging ---- */

export interface FlagPayload {
  reason:
    | "misinformation"
    | "off_topic"
    | "bot_violation"
    | "hallucination"
    | "spam"
  evidence_url?: string
}

export function flagPost(postId: string, data: FlagPayload, token: string) {
  return fetchApi<{ message: string; flag_count: number }>(
    `/v1/posts/${postId}/flag`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    token
  )
}

/* ---- Pulse ---- */

export interface PulseData {
  price_index: {
    item: string
    price: number
    change_pct: number
  }[]
  sentiment: {
    topic: string
    score: number
  }[]
  misinfo_hotspots: {
    region: string
    count: number
  }[]
}

export function getPulse(token?: string) {
  return fetchApi<PulseData>("/v1/pulse", {}, token)
}
