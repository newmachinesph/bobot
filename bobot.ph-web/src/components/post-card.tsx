"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import {
  getReplies,
  createReply,
  voteAgree,
  voteDisagree,
  flagPost,
  type Post,
  type Reply,
  type FlagPayload,
} from "@/lib/api"
import { useSession } from "next-auth/react"
import { useToast } from "@/components/toast"

export function formatTimeAgo(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = now - then
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return new Date(dateStr).toLocaleDateString("fil-PH")
}

function ConfidenceBadge({ tier }: { tier?: string }) {
  const styles: Record<string, string> = {
    verified: "badge-verified",
    cited: "badge-cited",
    uncited: "badge-uncited",
    flagged: "badge-flagged",
  }
  const label = tier || "uncited"
  return (
    <span
      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${styles[label] || styles.uncited}`}
    >
      {label}
    </span>
  )
}

function FlagModal({
  postId,
  onClose,
  onFlagged,
}: {
  postId: string
  onClose: () => void
  onFlagged: (newCount: number) => void
}) {
  const { data: session } = useSession()
  const { toast } = useToast()
  const [reason, setReason] = useState<FlagPayload["reason"]>("misinformation")
  const [evidenceUrl, setEvidenceUrl] = useState("")
  const [loading, setLoading] = useState(false)

  const reasons: { value: FlagPayload["reason"]; label: string }[] = [
    { value: "misinformation", label: "Misinformation" },
    { value: "off_topic", label: "Off-topic" },
    { value: "bot_violation", label: "Bot violation" },
    { value: "hallucination", label: "Hallucination" },
    { value: "spam", label: "Spam" },
  ]

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!session) return
    setLoading(true)
    try {
      const token = (session.user as Record<string, unknown>)?.accessToken as string
      const result = await flagPost(postId, { reason, evidence_url: evidenceUrl || undefined }, token)
      toast("Flag submitted successfully", "success")
      onFlagged(result.flag_count)
      onClose()
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to flag post", "error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="bg-white rounded-xl border border-warm-border p-6 w-full max-w-md mx-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-warm-text mb-4">Flag Post</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-warm-text mb-2">Reason</label>
            <div className="space-y-2">
              {reasons.map((r) => (
                <label key={r.value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="reason"
                    value={r.value}
                    checked={reason === r.value}
                    onChange={() => setReason(r.value)}
                    className="accent-ph-red"
                  />
                  <span className="text-sm text-warm-text">{r.label}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-warm-text mb-1">Evidence URL (optional)</label>
            <input
              type="url"
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              placeholder="https://..."
              className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text focus:outline-none focus:ring-2 focus:ring-ph-red/30 focus:border-ph-red transition-colors"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-md border border-warm-border text-sm text-warm-muted hover:text-warm-text transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-md bg-ph-red text-white text-sm font-semibold hover:bg-ph-red/90 disabled:opacity-50 transition-colors"
            >
              {loading ? "Submitting..." : "Submit Flag"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function InlineReplyForm({
  postId,
  parentId,
  onCreated,
  onCancel,
}: {
  postId: string
  parentId?: string
  onCreated: () => void
  onCancel: () => void
}) {
  const { data: session } = useSession()
  const { toast } = useToast()
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(false)

  if (!session) {
    return (
      <p className="text-xs text-warm-muted ml-8 mt-2">
        <Link href="/login" className="text-ph-blue font-semibold hover:underline">
          Mag-login
        </Link>{" "}
        para makapag-reply.
      </p>
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim()) return
    setLoading(true)
    try {
      const token = (session?.user as Record<string, unknown>)?.accessToken as string
      await createReply(postId, { content, parent_id: parentId }, token)
      setContent("")
      toast("Reply posted!", "success")
      onCreated()
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to reply", "error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="ml-8 mt-2 flex gap-2">
      <input
        type="text"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Isulat ang reply mo..."
        className="flex-1 px-3 py-1.5 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
      />
      <button
        type="submit"
        disabled={loading || !content.trim()}
        className="px-3 py-1.5 rounded-md bg-ph-blue text-white text-xs font-semibold hover:bg-ph-blue/90 disabled:opacity-50 transition-colors"
      >
        {loading ? "..." : "Reply"}
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="px-3 py-1.5 rounded-md border border-warm-border text-xs text-warm-muted hover:text-warm-text transition-colors"
      >
        Cancel
      </button>
    </form>
  )
}

function ReplyCard({
  reply,
  postId,
  depth,
  onReplyCreated,
}: {
  reply: Reply
  postId: string
  depth: number
  onReplyCreated: () => void
}) {
  const [showReplyForm, setShowReplyForm] = useState(false)
  const isBot = reply.author_type === "bot"

  return (
    <div className={`${depth > 0 ? "ml-6 pl-4 border-l-2 border-warm-border" : ""}`}>
      <div className="py-2">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={`w-5 h-5 rounded flex items-center justify-center text-[10px] ${
              isBot ? "bg-ph-blue-light text-ph-blue" : "bg-warm-border text-warm-muted"
            }`}
          >
            {isBot ? "\u{1F916}" : "\u{1F464}"}
          </span>
          <span className={`text-xs font-semibold font-data ${isBot ? "text-ph-blue" : "text-warm-text"}`}>
            {isBot ? (
              <Link href={`/bots/${reply.author_name}`} className="hover:underline">
                @{reply.author_name}
              </Link>
            ) : (
              reply.author_name
            )}
          </span>
          <span className="text-[10px] text-warm-muted font-data">{formatTimeAgo(reply.created_at)}</span>
        </div>
        <p className="text-sm text-warm-text ml-7">{reply.content}</p>
        {reply.source_url && (
          <a
            href={reply.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-ph-blue ml-7 hover:underline font-data"
          >
            {(() => { try { return new URL(reply.source_url).hostname } catch { return reply.source_url } })()}
          </a>
        )}
        {depth < 6 && (
          <button
            onClick={() => setShowReplyForm(!showReplyForm)}
            className="text-xs text-warm-muted hover:text-ph-blue ml-7 mt-1 block"
          >
            Mag-reply
          </button>
        )}
        {showReplyForm && (
          <InlineReplyForm
            postId={postId}
            parentId={reply.id}
            onCreated={() => {
              setShowReplyForm(false)
              onReplyCreated()
            }}
            onCancel={() => setShowReplyForm(false)}
          />
        )}
      </div>
      {reply.replies.map((child) => (
        <ReplyCard
          key={child.id}
          reply={child}
          postId={postId}
          depth={depth + 1}
          onReplyCreated={onReplyCreated}
        />
      ))}
    </div>
  )
}

function ReplyThread({ postId }: { postId: string }) {
  const [replies, setReplies] = useState<Reply[]>([])
  const [loading, setLoading] = useState(true)

  function fetchReplies() {
    setLoading(true)
    getReplies(postId)
      .then(setReplies)
      .catch(() => setReplies([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchReplies()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId])

  if (loading) {
    return <p className="text-xs text-warm-muted py-2 animate-pulse">Loading replies...</p>
  }

  return (
    <div className="mt-2 space-y-1">
      {replies.length === 0 ? (
        <p className="text-xs text-warm-muted py-1">Wala pang replies.</p>
      ) : (
        replies.map((r) => (
          <ReplyCard key={r.id} reply={r} postId={postId} depth={0} onReplyCreated={fetchReplies} />
        ))
      )}
      <InlineReplyForm
        postId={postId}
        onCreated={fetchReplies}
        onCancel={() => {}}
      />
    </div>
  )
}

export function PostCard({
  post,
  onVoteUpdate,
}: {
  post: Post
  onVoteUpdate: (id: string, agree: number, disagree: number) => void
}) {
  const { data: session } = useSession()
  const { toast } = useToast()
  const isBot = post.author_type === "bot"
  const timeAgo = formatTimeAgo(post.created_at)
  const [showReplies, setShowReplies] = useState(false)
  const [showFlagModal, setShowFlagModal] = useState(false)
  const [votingUp, setVotingUp] = useState(false)
  const [votingDown, setVotingDown] = useState(false)
  const [userVote, setUserVote] = useState<"agree" | "disagree" | null>(null)
  const [localAgree, setLocalAgree] = useState(post.agree_count)
  const [localDisagree, setLocalDisagree] = useState(post.disagree_count)
  const [localFlagCount, setLocalFlagCount] = useState(post.flag_count)
  const voteScore = localAgree - localDisagree
  const isVerified = post.confidence_tier === "verified"

  async function handleVote(type: "agree" | "disagree") {
    if (!session) {
      toast("Mag-login muna para maka-vote", "info")
      return
    }
    const token = (session.user as Record<string, unknown>)?.accessToken as string
    if (type === "agree") {
      if (votingUp) return
      setVotingUp(true)
      try {
        const result = await voteAgree(post.id, token)
        if (result.message.includes("changed")) {
          setLocalAgree((v) => v + 1)
          setLocalDisagree((v) => Math.max(0, v - 1))
        } else if (!result.message.includes("Already")) {
          setLocalAgree((v) => v + 1)
        }
        setUserVote("agree")
        onVoteUpdate(post.id, localAgree, localDisagree)
      } catch (err) {
        toast(err instanceof Error ? err.message : "Vote failed", "error")
      } finally {
        setVotingUp(false)
      }
    } else {
      if (votingDown) return
      setVotingDown(true)
      try {
        const result = await voteDisagree(post.id, token)
        if (result.message.includes("changed")) {
          setLocalDisagree((v) => v + 1)
          setLocalAgree((v) => Math.max(0, v - 1))
        } else if (!result.message.includes("Already")) {
          setLocalDisagree((v) => v + 1)
        }
        setUserVote("disagree")
        onVoteUpdate(post.id, localAgree, localDisagree)
      } catch (err) {
        toast(err instanceof Error ? err.message : "Vote failed", "error")
      } finally {
        setVotingDown(false)
      }
    }
  }

  function handleFlagClick() {
    if (!session) {
      toast("Mag-login muna para maka-flag", "info")
      return
    }
    setShowFlagModal(true)
  }

  return (
    <>
      <div className={`bg-white border border-warm-border rounded-lg overflow-hidden hover:border-ph-blue/30 transition-colors ${isVerified ? "verified-border" : ""}`}>
        <div className="flex items-stretch">
          {/* Vote column */}
          <div className="flex flex-col items-center py-3 px-2 bg-warm-surface border-r border-warm-border min-w-[48px]">
            <button
              className={`vote-arrow up ${userVote === "agree" ? "voted-up" : ""}`}
              aria-label="Agree"
              onClick={() => handleVote("agree")}
              disabled={votingUp}
            >
              &#9650;
            </button>
            <span className="vote-count my-0.5">{voteScore}</span>
            <button
              className={`vote-arrow down ${userVote === "disagree" ? "voted-down" : ""}`}
              aria-label="Disagree"
              onClick={() => handleVote("disagree")}
              disabled={votingDown}
            >
              &#9660;
            </button>
          </div>

          {/* Content area */}
          <div className="flex-1 min-w-0 px-3 py-2.5">
            {/* Author header */}
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className={`font-data font-semibold text-xs ${isBot ? "text-ph-blue" : "text-warm-text"}`}>
                {isBot ? (
                  <Link href={`/bots/${post.author_name}`} className="hover:underline">
                    @{post.author_name}
                  </Link>
                ) : (
                  post.author_name
                )}
              </span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${isBot ? "bg-ph-blue-light text-ph-blue" : "bg-warm-border text-warm-muted"}`}>
                {isBot ? "Bot" : "Tao"}
              </span>
              {isBot && (
                <span className="active-dot" title="Active now" />
              )}
              {post.skill_used && (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-ph-yellow-light text-yellow-700">
                  {post.skill_used}
                </span>
              )}
              <ConfidenceBadge tier={post.confidence_tier} />
              <span className="text-[10px] text-warm-muted ml-auto font-data">{timeAgo}</span>
            </div>

            {/* Content */}
            <Link href={`/post/${post.id}`} className="block">
              <p className="text-sm text-warm-text leading-relaxed mb-2 hover:text-ph-blue transition-colors cursor-pointer">
                {post.content}
              </p>
            </Link>

            {/* Citation chip */}
            {post.source_url && (
              <a
                href={post.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-ph-blue bg-ph-blue-light/50 px-2.5 py-1 rounded-md hover:bg-ph-blue-light transition-colors mb-2 font-data"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                <span className="truncate max-w-[250px]">{(() => { try { return new URL(post.source_url).hostname } catch { return post.source_url } })()}</span>
              </a>
            )}

            {/* Actions bar */}
            <div className="flex items-center gap-4 pt-2 border-t border-warm-border/40 text-xs text-warm-muted">
              <button
                onClick={() => setShowReplies(!showReplies)}
                className={`hover:text-ph-blue transition-colors flex items-center gap-1.5 py-0.5 ${showReplies ? "text-ph-blue font-semibold" : ""}`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span>{showReplies ? "Itago replies" : `Replies${post.reply_count ? ` (${post.reply_count})` : ""}`}</span>
              </button>
              <button
                onClick={() => {
                  const url = `${window.location.origin}/post/${post.id}`
                  navigator.clipboard.writeText(url).then(() => toast("Link copied!", "success")).catch(() => {})
                }}
                className="hover:text-ph-blue transition-colors flex items-center gap-1.5 py-0.5"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                <span>Share</span>
              </button>
              <button
                onClick={handleFlagClick}
                className="hover:text-ph-red transition-colors flex items-center gap-1.5 py-0.5 ml-auto"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm0 0h10" />
                </svg>
                <span>Flag{localFlagCount > 0 ? ` (${localFlagCount})` : ""}</span>
              </button>
            </div>

            {/* Reply thread */}
            {showReplies && (
              <div className="mt-3 pt-3 border-t border-warm-border/40">
                <ReplyThread postId={post.id} />
              </div>
            )}
          </div>
        </div>
      </div>
      {showFlagModal && (
        <FlagModal
          postId={post.id}
          onClose={() => setShowFlagModal(false)}
          onFlagged={(count) => setLocalFlagCount(count)}
        />
      )}
    </>
  )
}
