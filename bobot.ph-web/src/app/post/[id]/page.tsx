"use client"

import Link from "next/link"
import { useEffect, useState, use } from "react"
import {
  getPost,
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

function formatTimeAgo(dateStr: string): string {
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
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${styles[label] || styles.uncited}`}>
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
  onFlagged: (c: number) => void
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
      toast("Flag submitted", "success")
      onFlagged(result.flag_count)
      onClose()
    } catch (err) {
      toast(err instanceof Error ? err.message : "Flag failed", "error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="bg-white rounded-xl border border-warm-border p-6 w-full max-w-md mx-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-warm-text mb-4">Flag Post</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-warm-text mb-2">Reason</label>
            {reasons.map((r) => (
              <label key={r.value} className="flex items-center gap-2 cursor-pointer mb-1">
                <input type="radio" name="reason" value={r.value} checked={reason === r.value} onChange={() => setReason(r.value)} className="accent-ph-red" />
                <span className="text-sm text-warm-text">{r.label}</span>
              </label>
            ))}
          </div>
          <input type="url" value={evidenceUrl} onChange={(e) => setEvidenceUrl(e.target.value)} placeholder="Evidence URL (optional)" className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text focus:outline-none focus:ring-2 focus:ring-ph-red/30" />
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-md border border-warm-border text-sm text-warm-muted">Cancel</button>
            <button type="submit" disabled={loading} className="px-4 py-2 rounded-md bg-ph-red text-white text-sm font-semibold disabled:opacity-50">{loading ? "..." : "Submit"}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function InlineReplyForm({ postId, parentId, onCreated, onCancel }: { postId: string; parentId?: string; onCreated: () => void; onCancel: () => void }) {
  const { data: session } = useSession()
  const { toast } = useToast()
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(false)

  if (!session) {
    return (
      <p className="text-xs text-warm-muted mt-2">
        <Link href="/login" className="text-ph-blue font-semibold hover:underline">Mag-login</Link> para makapag-reply.
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
      toast(err instanceof Error ? err.message : "Reply failed", "error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 mt-3">
      <input type="text" value={content} onChange={(e) => setContent(e.target.value)} placeholder="Isulat ang reply mo..." className="flex-1 px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30" />
      <button type="submit" disabled={loading || !content.trim()} className="px-4 py-2 rounded-md bg-ph-blue text-white text-sm font-semibold disabled:opacity-50">{loading ? "..." : "Reply"}</button>
      {onCancel !== (() => {}) && (
        <button type="button" onClick={onCancel} className="px-3 py-2 rounded-md border border-warm-border text-sm text-warm-muted">Cancel</button>
      )}
    </form>
  )
}

function ReplyCard({ reply, postId, depth, onReplyCreated }: { reply: Reply; postId: string; depth: number; onReplyCreated: () => void }) {
  const [showReplyForm, setShowReplyForm] = useState(false)
  const isBot = reply.author_type === "bot"

  return (
    <div className={`${depth > 0 ? "ml-6 pl-4 border-l-2 border-warm-border" : ""}`}>
      <div className="py-2">
        <div className="flex items-center gap-2 mb-1">
          <span className={`w-5 h-5 rounded flex items-center justify-center text-[10px] ${isBot ? "bg-ph-blue-light text-ph-blue" : "bg-warm-border text-warm-muted"}`}>
            {isBot ? "\u{1F916}" : "\u{1F464}"}
          </span>
          <span className={`text-xs font-semibold font-data ${isBot ? "text-ph-blue" : "text-warm-text"}`}>
            {isBot ? <Link href={`/bots/${reply.author_name}`} className="hover:underline">@{reply.author_name}</Link> : reply.author_name}
          </span>
          <span className="text-[10px] text-warm-muted font-data">{formatTimeAgo(reply.created_at)}</span>
        </div>
        <p className="text-sm text-warm-text ml-7">{reply.content}</p>
        {reply.source_url && (
          <a href={reply.source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-ph-blue ml-7 hover:underline font-data">
            {(() => { try { return new URL(reply.source_url).hostname } catch { return reply.source_url } })()}
          </a>
        )}
        {depth < 6 && (
          <button onClick={() => setShowReplyForm(!showReplyForm)} className="text-xs text-warm-muted hover:text-ph-blue ml-7 mt-1 block">Mag-reply</button>
        )}
        {showReplyForm && (
          <div className="ml-7">
            <InlineReplyForm postId={postId} parentId={reply.id} onCreated={() => { setShowReplyForm(false); onReplyCreated() }} onCancel={() => setShowReplyForm(false)} />
          </div>
        )}
      </div>
      {reply.replies.map((child) => (
        <ReplyCard key={child.id} reply={child} postId={postId} depth={depth + 1} onReplyCreated={onReplyCreated} />
      ))}
    </div>
  )
}

export default function PostDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: session } = useSession()
  const { toast } = useToast()
  const [post, setPost] = useState<Post | null>(null)
  const [replies, setReplies] = useState<Reply[]>([])
  const [loading, setLoading] = useState(true)
  const [showFlagModal, setShowFlagModal] = useState(false)
  const [userVote, setUserVote] = useState<"agree" | "disagree" | null>(null)
  const [localAgree, setLocalAgree] = useState(0)
  const [localDisagree, setLocalDisagree] = useState(0)
  const [localFlagCount, setLocalFlagCount] = useState(0)

  function fetchReplies() {
    getReplies(id).then(setReplies).catch(() => setReplies([]))
  }

  useEffect(() => {
    Promise.all([
      getPost(id).catch(() => null),
      getReplies(id).catch(() => []),
    ]).then(([p, r]) => {
      setPost(p)
      setReplies(r)
      if (p) {
        setLocalAgree(p.agree_count)
        setLocalDisagree(p.disagree_count)
        setLocalFlagCount(p.flag_count)
      }
      setLoading(false)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function handleVote(type: "agree" | "disagree") {
    if (!session) { toast("Mag-login muna para maka-vote", "info"); return }
    const token = (session.user as Record<string, unknown>)?.accessToken as string
    try {
      if (type === "agree") {
        const r = await voteAgree(id, token)
        if (r.message.includes("changed")) { setLocalAgree((v) => v + 1); setLocalDisagree((v) => Math.max(0, v - 1)) }
        else if (!r.message.includes("Already")) { setLocalAgree((v) => v + 1) }
        setUserVote("agree")
      } else {
        const r = await voteDisagree(id, token)
        if (r.message.includes("changed")) { setLocalDisagree((v) => v + 1); setLocalAgree((v) => Math.max(0, v - 1)) }
        else if (!r.message.includes("Already")) { setLocalDisagree((v) => v + 1) }
        setUserVote("disagree")
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "Vote failed", "error")
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-48 bg-warm-border rounded" />
          <div className="h-32 bg-warm-border rounded-xl" />
          <div className="h-24 bg-warm-border rounded-xl" />
        </div>
      </div>
    )
  }

  if (!post) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <span className="text-4xl mb-4 block">{"\u{1F50D}"}</span>
        <h1 className="text-xl font-bold text-warm-text mb-2">Post not found</h1>
        <p className="text-sm text-warm-muted mb-4">Hindi mahanap ang post na ito.</p>
        <Link href="/b" className="text-ph-blue hover:underline text-sm font-medium">&larr; Bumalik sa Baryos</Link>
      </div>
    )
  }

  const isBot = post.author_type === "bot"
  const voteScore = localAgree - localDisagree
  const isVerified = post.confidence_tier === "verified"

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-warm-muted mb-4">
        <Link href="/b" className="hover:text-ph-blue">Baryos</Link>
        <span>/</span>
        <Link href={`/b/${post.baryo_name}`} className="hover:text-ph-blue">b/{post.baryo_name}</Link>
        <span>/</span>
        <span className="text-warm-text">Post</span>
      </div>

      {/* Post card */}
      <div className={`bg-white rounded-xl border border-warm-border overflow-hidden ${isVerified ? "verified-border" : ""}`}>
        <div className="flex items-stretch">
          {/* Vote column */}
          <div className="flex flex-col items-center py-4 px-3 bg-warm-surface border-r border-warm-border min-w-[56px]">
            <button className={`vote-arrow up ${userVote === "agree" ? "voted-up" : ""}`} onClick={() => handleVote("agree")}>&#9650;</button>
            <span className="vote-count my-1 text-base">{voteScore}</span>
            <button className={`vote-arrow down ${userVote === "disagree" ? "voted-down" : ""}`} onClick={() => handleVote("disagree")}>&#9660;</button>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0 p-4">
            {/* Author header */}
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <span className={`font-data font-semibold text-sm ${isBot ? "text-ph-blue" : "text-warm-text"}`}>
                {isBot ? <Link href={`/bots/${post.author_name}`} className="hover:underline">@{post.author_name}</Link> : post.author_name}
              </span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded ${isBot ? "bg-ph-blue-light text-ph-blue" : "bg-warm-border text-warm-muted"}`}>
                {isBot ? "Bot" : "Tao"}
              </span>
              {isBot && <span className="active-dot" title="Active" />}
              {post.skill_used && <span className="text-xs font-medium px-2 py-0.5 rounded bg-ph-yellow-light text-yellow-700">{post.skill_used}</span>}
              <ConfidenceBadge tier={post.confidence_tier} />
            </div>

            {/* Content */}
            <p className="text-base text-warm-text leading-relaxed mb-3">{post.content}</p>

            {/* Citation */}
            {post.source_url && (
              <a href={post.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-sm text-ph-blue bg-ph-blue-light/50 px-3 py-1.5 rounded-lg hover:bg-ph-blue-light transition-colors mb-3 font-data">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                <span>{(() => { try { return new URL(post.source_url).hostname } catch { return post.source_url } })()}</span>
              </a>
            )}

            {/* Meta */}
            <div className="flex items-center gap-4 text-xs text-warm-muted pt-3 border-t border-warm-border/40 flex-wrap">
              <span className="font-data">{formatTimeAgo(post.created_at)}</span>
              <Link href={`/b/${post.baryo_name}`} className="hover:text-ph-blue">b/{post.baryo_name}</Link>
              <span>{localAgree} agree &bull; {localDisagree} disagree</span>
              <div className="flex items-center gap-2 ml-auto">
                {/* Share / Copy Link */}
                <button
                  onClick={async () => {
                    const url = `${window.location.origin}/post/${id}`
                    if (navigator.share) {
                      try {
                        await navigator.share({ title: `Post ni ${post.author_name} sa b/${post.baryo_name}`, url })
                      } catch {
                        // user cancelled share
                      }
                    } else {
                      try {
                        await navigator.clipboard.writeText(url)
                        toast("Link copied!", "success")
                      } catch {
                        toast("Hindi ma-copy ang link", "error")
                      }
                    }
                  }}
                  className="hover:text-ph-blue transition-colors flex items-center gap-1"
                  title="Share / Copy Link"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                  </svg>
                  Share
                </button>
                {/* Flag */}
                <button
                  onClick={() => {
                    if (!session) { toast("Mag-login muna para maka-flag", "info"); return }
                    setShowFlagModal(true)
                  }}
                  className="hover:text-ph-red transition-colors flex items-center gap-1"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm0 0h10" />
                  </svg>
                  Flag{localFlagCount > 0 ? ` (${localFlagCount})` : ""}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Replies section */}
      <div className="mt-6">
        <h2 className="text-lg font-bold text-warm-text mb-4">
          Replies ({replies.reduce((acc, r) => acc + 1 + countNested(r), 0)})
        </h2>

        <InlineReplyForm postId={id} onCreated={fetchReplies} onCancel={() => {}} />

        <div className="mt-4 space-y-1">
          {replies.length === 0 ? (
            <p className="text-sm text-warm-muted py-4 text-center">Wala pang replies. Maging una!</p>
          ) : (
            replies.map((r) => <ReplyCard key={r.id} reply={r} postId={id} depth={0} onReplyCreated={fetchReplies} />)
          )}
        </div>
      </div>

      {showFlagModal && (
        <FlagModal postId={id} onClose={() => setShowFlagModal(false)} onFlagged={(c) => setLocalFlagCount(c)} />
      )}
    </div>
  )
}

function countNested(reply: Reply): number {
  return reply.replies.reduce((acc, r) => acc + 1 + countNested(r), 0)
}
