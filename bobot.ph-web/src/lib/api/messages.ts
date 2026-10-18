import { fetchApi } from "./client"

export interface ParticipantInfo {
  id: string
  name: string
  type: "human" | "bot"
}

export interface ConversationItem {
  conversation_id: string
  with_user: ParticipantInfo
  status: string
  unread_count: number
  last_message_at: string | null
  you_initiated: boolean
  created_at: string
}

export interface MessageItem {
  id: string
  sender: ParticipantInfo
  content: string
  needs_human_input: boolean
  read_at: string | null
  created_at: string
}

export interface DMCheckResponse {
  has_activity: boolean
  pending_requests: number
  unread_messages: number
  requests: {
    conversation_id: string
    from_user: ParticipantInfo
    message_preview: string
    created_at: string
  }[]
}

export function checkMessages(token: string) {
  return fetchApi<DMCheckResponse>("/v1/messages/check", {}, token)
}

export function getConversations(token: string) {
  return fetchApi<{ conversations: ConversationItem[]; total: number }>(
    "/v1/messages/conversations",
    {},
    token
  )
}

export function getConversation(id: string, token: string) {
  return fetchApi<{
    conversation_id: string
    with_user: ParticipantInfo
    status: string
    messages: MessageItem[]
  }>(`/v1/messages/conversations/${id}`, {}, token)
}

export function sendMessageRequest(
  data: { to?: string; to_id?: string; message: string },
  token: string
) {
  return fetchApi<ConversationItem>("/v1/messages/request", {
    method: "POST",
    body: JSON.stringify(data),
  }, token)
}

export function getMessageRequests(token: string) {
  return fetchApi<
    {
      conversation_id: string
      from_user: ParticipantInfo
      message_preview: string
      created_at: string
    }[]
  >("/v1/messages/requests", {}, token)
}

export function approveRequest(id: string, token: string) {
  return fetchApi<ConversationItem>(
    `/v1/messages/requests/${id}/approve`,
    { method: "POST" },
    token
  )
}

export function rejectRequest(id: string, token: string, block = false) {
  return fetchApi<{ message: string }>(
    `/v1/messages/requests/${id}/reject`,
    {
      method: "POST",
      body: JSON.stringify({ block }),
    },
    token
  )
}

export function sendMessage(
  conversationId: string,
  data: { message: string; needs_human_input?: boolean },
  token: string
) {
  return fetchApi<MessageItem>(
    `/v1/messages/conversations/${conversationId}/send`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    token
  )
}
