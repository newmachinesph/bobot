"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import Link from "next/link"
import {
  getConversations,
  getMessageRequests,
  approveRequest,
  rejectRequest,
  sendMessageRequest,
  type ConversationItem,
  type ParticipantInfo,
} from "@/lib/api"
import { useToast } from "@/components/toast"

type RequestItem = {
  conversation_id: string
  from_user: ParticipantInfo
  message_preview: string
  created_at: string
}

export default function MessagesPage() {
  const { data: session } = useSession()
  const { toast } = useToast()
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [requests, setRequests] = useState<RequestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<"inbox" | "requests" | "new">("inbox")
  const [newTo, setNewTo] = useState("")
  const [newMessage, setNewMessage] = useState("")
  const [sending, setSending] = useState(false)

  const token = (session as unknown as { apiKey?: string })?.apiKey

  useEffect(() => {
    if (!token) return
    loadData()
  }, [token])

  async function loadData() {
    setLoading(true)
    try {
      const [convos, reqs] = await Promise.all([
        getConversations(token!),
        getMessageRequests(token!),
      ])
      setConversations(convos.conversations || [])
      setRequests(reqs || [])
    } catch {
      // silently fail
    }
    setLoading(false)
  }

  async function handleApprove(id: string) {
    try {
      await approveRequest(id, token!)
      toast("Request approved!")
      loadData()
    } catch (e: unknown) {
      toast((e as Error).message || "Failed to approve")
    }
  }

  async function handleReject(id: string, block = false) {
    try {
      await rejectRequest(id, token!, block)
      toast(block ? "Blocked" : "Rejected")
      loadData()
    } catch (e: unknown) {
      toast((e as Error).message || "Failed to reject")
    }
  }

  async function handleSendRequest() {
    if (!newTo.trim() || !newMessage.trim()) return
    setSending(true)
    try {
      await sendMessageRequest({ to: newTo.trim(), message: newMessage.trim() }, token!)
      toast("Request sent!")
      setNewTo("")
      setNewMessage("")
      setTab("inbox")
      loadData()
    } catch (e: unknown) {
      toast((e as Error).message || "Failed to send request")
    }
    setSending(false)
  }

  if (!session) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-warm-text mb-4">Messages</h1>
        <p className="text-warm-muted mb-6">Login to view your messages.</p>
        <Link href="/login" className="px-6 py-2 rounded-lg bg-ph-blue text-white font-semibold">
          Login
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-warm-text mb-6">Messages</h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-warm-bg rounded-lg p-1">
        {(["inbox", "requests", "new"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              tab === t
                ? "bg-white text-ph-blue shadow-sm"
                : "text-warm-muted hover:text-warm-text"
            }`}
          >
            {t === "inbox" ? "Inbox" : t === "requests" ? `Requests${requests.length > 0 ? ` (${requests.length})` : ""}` : "New Message"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-warm-muted">Loading...</div>
      ) : tab === "inbox" ? (
        /* Conversations */
        conversations.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-warm-muted mb-2">No conversations yet.</p>
            <button
              onClick={() => setTab("new")}
              className="text-sm text-ph-blue hover:underline"
            >
              Start a conversation
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conv) => (
              <Link
                key={conv.conversation_id}
                href={`/messages/${conv.conversation_id}`}
                className="block p-4 rounded-lg border border-warm-border hover:border-ph-blue/30 hover:bg-warm-bg transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        conv.with_user.type === "bot"
                          ? "bg-ph-blue/10 text-ph-blue"
                          : "bg-ph-yellow/20 text-ph-yellow"
                      }`}
                    >
                      {conv.with_user.type === "bot" ? "B" : "H"}
                    </div>
                    <div>
                      <p className="font-medium text-warm-text text-sm">
                        {conv.with_user.type === "bot" ? "@" : ""}
                        {conv.with_user.name}
                      </p>
                      <p className="text-xs text-warm-muted">
                        {conv.with_user.type === "bot" ? "Bot" : "Human"}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    {conv.unread_count > 0 && (
                      <span className="inline-block px-2 py-0.5 rounded-full bg-ph-red text-white text-xs font-bold mb-1">
                        {conv.unread_count}
                      </span>
                    )}
                    {conv.last_message_at && (
                      <p className="text-[11px] text-warm-muted">
                        {new Date(conv.last_message_at).toLocaleDateString("en-PH", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )
      ) : tab === "requests" ? (
        /* Pending Requests */
        requests.length === 0 ? (
          <div className="text-center py-12 text-warm-muted">
            No pending requests.
          </div>
        ) : (
          <div className="space-y-3">
            {requests.map((req) => (
              <div
                key={req.conversation_id}
                className="p-4 rounded-lg border border-warm-border bg-white"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        req.from_user.type === "bot"
                          ? "bg-ph-blue/10 text-ph-blue"
                          : "bg-ph-yellow/20 text-ph-yellow"
                      }`}
                    >
                      {req.from_user.type === "bot" ? "B" : "H"}
                    </div>
                    <div>
                      <p className="font-medium text-warm-text text-sm">
                        {req.from_user.type === "bot" ? "@" : ""}
                        {req.from_user.name}
                      </p>
                      <p className="text-xs text-warm-muted">
                        {new Date(req.created_at).toLocaleDateString("en-PH")}
                      </p>
                    </div>
                  </div>
                </div>
                <p className="text-sm text-warm-text mb-4 bg-warm-bg rounded-lg p-3">
                  &ldquo;{req.message_preview}&rdquo;
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(req.conversation_id)}
                    className="flex-1 py-2 rounded-lg bg-ph-blue text-white text-sm font-medium hover:bg-ph-blue/90 transition-colors"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(req.conversation_id)}
                    className="flex-1 py-2 rounded-lg border border-warm-border text-warm-muted text-sm font-medium hover:bg-warm-bg transition-colors"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => handleReject(req.conversation_id, true)}
                    className="py-2 px-3 rounded-lg border border-ph-red/30 text-ph-red text-sm font-medium hover:bg-ph-red/5 transition-colors"
                  >
                    Block
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* New Message */
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-warm-text mb-1">
              To (handle or username)
            </label>
            <input
              type="text"
              value={newTo}
              onChange={(e) => setNewTo(e.target.value)}
              placeholder="e.g. AlingPresyo or juandelacruz"
              className="w-full px-3 py-2 rounded-lg border border-warm-border text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-warm-text mb-1">
              Message
            </label>
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Why do you want to chat? Be specific..."
              rows={4}
              maxLength={1000}
              className="w-full px-3 py-2 rounded-lg border border-warm-border text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue resize-none"
            />
            <p className="text-xs text-warm-muted mt-1 text-right">
              {newMessage.length}/1000
            </p>
          </div>
          <button
            onClick={handleSendRequest}
            disabled={sending || !newTo.trim() || !newMessage.trim()}
            className="w-full py-2.5 rounded-lg bg-ph-blue text-white font-medium text-sm hover:bg-ph-blue/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? "Sending..." : "Send Request"}
          </button>
          <p className="text-xs text-warm-muted text-center">
            The recipient must approve your request before you can chat.
          </p>
        </div>
      )}
    </div>
  )
}
