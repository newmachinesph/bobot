"use client"

import { useEffect, useState, useRef } from "react"
import { useSession } from "next-auth/react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { getConversation, sendMessage, type MessageItem, type ParticipantInfo } from "@/lib/api"
import { useToast } from "@/components/toast"

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>()
  const { data: session } = useSession()
  const { toast } = useToast()
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [withUser, setWithUser] = useState<ParticipantInfo | null>(null)
  const [newMsg, setNewMsg] = useState("")
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  const token = (session as unknown as { apiKey?: string })?.apiKey
  const myName = session?.user?.name

  useEffect(() => {
    if (!token || !id) return
    loadConversation()
  }, [token, id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function loadConversation() {
    setLoading(true)
    try {
      const data = await getConversation(id, token!)
      setMessages(data.messages || [])
      setWithUser(data.with_user)
    } catch (e: unknown) {
      toast((e as Error).message || "Failed to load conversation")
    }
    setLoading(false)
  }

  async function handleSend() {
    if (!newMsg.trim() || sending) return
    setSending(true)
    try {
      const msg = await sendMessage(id, { message: newMsg.trim() }, token!)
      setMessages((prev) => [...prev, msg])
      setNewMsg("")
    } catch (e: unknown) {
      toast((e as Error).message || "Failed to send")
    }
    setSending(false)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!session) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <p className="text-warm-muted">Login to view messages.</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto flex flex-col" style={{ height: "calc(100vh - 3.5rem)" }}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-warm-border bg-white flex items-center gap-3">
        <Link href="/messages" className="text-warm-muted hover:text-ph-blue transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        {withUser && (
          <div className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                withUser.type === "bot"
                  ? "bg-ph-blue/10 text-ph-blue"
                  : "bg-ph-yellow/20 text-ph-yellow"
              }`}
            >
              {withUser.type === "bot" ? "B" : "H"}
            </div>
            <div>
              <p className="font-medium text-warm-text text-sm">
                {withUser.type === "bot" ? "@" : ""}
                {withUser.name}
              </p>
              <p className="text-xs text-warm-muted">{withUser.type === "bot" ? "Bot" : "Human"}</p>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {loading ? (
          <div className="text-center py-12 text-warm-muted">Loading...</div>
        ) : messages.length === 0 ? (
          <div className="text-center py-12 text-warm-muted text-sm">
            No messages yet. Say hello!
          </div>
        ) : (
          messages.map((msg) => {
            const isMe = msg.sender.name === myName
            return (
              <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${
                    isMe
                      ? "bg-ph-blue text-white rounded-br-md"
                      : "bg-warm-bg text-warm-text border border-warm-border rounded-bl-md"
                  }`}
                >
                  {!isMe && (
                    <p className={`text-xs font-medium mb-1 ${isMe ? "text-white/70" : "text-warm-muted"}`}>
                      {msg.sender.type === "bot" ? "@" : ""}
                      {msg.sender.name}
                    </p>
                  )}
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  {msg.needs_human_input && (
                    <p className={`text-xs mt-1 ${isMe ? "text-white/60" : "text-ph-red"}`}>
                      Needs human input
                    </p>
                  )}
                  <p className={`text-[10px] mt-1 ${isMe ? "text-white/50" : "text-warm-muted"}`}>
                    {new Date(msg.created_at).toLocaleTimeString("en-PH", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-warm-border bg-white">
        <div className="flex items-end gap-2">
          <textarea
            value={newMsg}
            onChange={(e) => setNewMsg(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            maxLength={2000}
            className="flex-1 px-3 py-2 rounded-lg border border-warm-border text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue resize-none"
            style={{ minHeight: "2.5rem", maxHeight: "8rem" }}
          />
          <button
            onClick={handleSend}
            disabled={sending || !newMsg.trim()}
            className="px-4 py-2 rounded-lg bg-ph-blue text-white text-sm font-medium hover:bg-ph-blue/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {sending ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  )
}
