"use client"

import Link from "next/link"
import { useEffect, useState, use } from "react"
import {
  getBaryo,
  getPosts,
  createPost,
  joinBaryo,
  type Baryo,
  type Post,
} from "@/lib/api"
import { useSession } from "next-auth/react"
import { useToast } from "@/components/toast"
import { PostCard } from "@/components/post-card"
import { BaryoHeaderSkeleton, FeedSkeleton } from "@/components/skeletons"
import { NewPostsBanner } from "@/components/new-posts-banner"

const BARYO_EMOJI: Record<string, string> = {
  presyo: "\u{1F6D2}",
  batas: "\u2696\uFE0F",
  kalusugan: "\u{1F3E5}",
  trabaho: "\u{1F4BC}",
  edukasyon: "\u{1F4DA}",
  klima: "\u{1F326}\uFE0F",
  transportasyon: "\u{1F68C}",
  negosyo: "\u{1F3EA}",
  teknolohiya: "\u{1F4BB}",
  kultura: "\u{1F3AD}",
  luto: "\u{1F373}",
  sports: "\u{1F3C0}",
  gaming: "\u{1F3AE}",
  ofw: "\u{1F30D}",
  showbiz: "\u{1F3AC}",
  memes: "\u{1F602}",
  crypto: "\u{1F4B0}",
}

type SortMode = "hot" | "new" | "top" | "rising" | "verified"

function CreatePostForm({
  baryoName,
  onCreated,
}: {
  baryoName: string
  onCreated: (p: Post) => void
}) {
  const { data: session } = useSession()
  const { toast } = useToast()
  const [content, setContent] = useState("")
  const [sourceUrl, setSourceUrl] = useState("")
  const [loading, setLoading] = useState(false)

  if (!session) {
    return (
      <div className="bg-white rounded-lg border border-warm-border p-4 text-center">
        <p className="text-sm text-warm-muted">
          <Link
            href="/login"
            className="text-ph-blue font-semibold hover:underline"
          >
            Mag-login
          </Link>{" "}
          para makapag-post sa baryo na ito.
        </p>
      </div>
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim()) return
    setLoading(true)
    try {
      const token = (session?.user as Record<string, unknown>)
        ?.accessToken as string
      const post = await createPost(
        baryoName,
        {
          content,
          source_url: sourceUrl || undefined,
        },
        token
      )
      onCreated(post)
      setContent("")
      setSourceUrl("")
      toast("Post created!", "success")
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create post", "error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-lg border border-warm-border p-4 space-y-3"
    >
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Ano ang gusto mong ibahagi sa baryo?"
        rows={3}
        className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors resize-none"
      />
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="url"
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="Source URL (optional pero recommended)"
          className="flex-1 px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !content.trim()}
          className="px-5 py-2 rounded-md bg-ph-blue text-white text-sm font-semibold hover:bg-ph-blue/90 disabled:opacity-50 transition-colors whitespace-nowrap"
        >
          {loading ? "Nag-popost..." : "Mag-post"}
        </button>
      </div>
    </form>
  )
}

export default function BaryoDetailPage({
  params,
}: {
  params: Promise<{ name: string }>
}) {
  const { name } = use(params)
  const { data: session } = useSession()
  const { toast } = useToast()
  const [baryo, setBaryo] = useState<Baryo | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [postsLoading, setPostsLoading] = useState(false)
  const [sortMode, setSortMode] = useState<SortMode>("hot")

  // Initial load: fetch baryo + posts
  useEffect(() => {
    setLoading(true)
    const apiSort = sortMode === "verified" ? "verified_only" : sortMode
    Promise.all([
      getBaryo(name).catch(() => null),
      getPosts(name, apiSort).catch(() => []),
    ]).then(([b, p]) => {
      setBaryo(b)
      setPosts(p)
      setLoading(false)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name])

  // Sort change: only refetch posts with loading indicator
  useEffect(() => {
    if (loading) return // skip on initial load
    setPostsLoading(true)
    const apiSort = sortMode === "verified" ? "verified_only" : sortMode
    getPosts(name, apiSort)
      .then(setPosts)
      .catch(() => setPosts([]))
      .finally(() => setPostsLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortMode])

  function handleVoteUpdate(postId: string, agree: number, disagree: number) {
    setPosts((prev) =>
      prev.map((p) =>
        p.id === postId ? { ...p, agree_count: agree, disagree_count: disagree } : p
      )
    )
  }

  function handleRefresh() {
    setPostsLoading(true)
    const apiSort = sortMode === "verified" ? "verified_only" : sortMode
    getPosts(name, apiSort)
      .then(setPosts)
      .catch(() => setPosts([]))
      .finally(() => setPostsLoading(false))
  }

  const emoji = BARYO_EMOJI[name] || "\u{1F3D8}\uFE0F"

  const healthScore = baryo?.health_score ?? 100
  const healthColor = healthScore >= 80 ? "bg-green-500" : healthScore >= 50 ? "bg-yellow-500" : "bg-red-500"

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Main feed skeleton */}
          <div className="flex-1 min-w-0 space-y-3">
            <FeedSkeleton />
          </div>
          {/* Sidebar baryo header skeleton */}
          <aside className="w-full lg:w-72 shrink-0">
            <BaryoHeaderSkeleton />
          </aside>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Sort tabs */}
          <div className="flex gap-1 p-1 bg-white border border-warm-border rounded-lg">
            {([
              ["hot", "Hot"],
              ["new", "New"],
              ["top", "Top"],
              ["rising", "Rising"],
              ["verified", "Verified Only"],
            ] as [SortMode, string][]).map(([mode, label]) => (
              <button
                key={mode}
                onClick={() => setSortMode(mode)}
                className={`px-3 py-1.5 text-sm font-semibold rounded-md whitespace-nowrap transition-all ${
                  sortMode === mode
                    ? "bg-ph-blue text-white"
                    : "text-warm-muted hover:text-warm-text hover:bg-warm-bg"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Create post */}
          <CreatePostForm
            baryoName={name}
            onCreated={(p) => setPosts((prev) => [p, ...prev])}
          />

          {/* New posts polling banner */}
          <NewPostsBanner
            baryoName={name}
            latestPostId={posts[0]?.id ?? null}
            onRefresh={handleRefresh}
          />

          {/* Posts feed */}
          {postsLoading ? (
            <FeedSkeleton />
          ) : posts.length === 0 ? (
            <div className="bg-white rounded-lg border border-warm-border p-8 text-center">
              <p className="text-warm-muted text-sm">
                {sortMode === "verified"
                  ? "Walang verified posts pa sa baryo na ito."
                  : "Wala pang posts sa baryo na ito. Maging una!"}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {posts.map((p) => (
                <PostCard key={p.id} post={p} onVoteUpdate={handleVoteUpdate} />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <aside className="w-full lg:w-72 shrink-0">
          <div className="sticky-sidebar space-y-3">
            {/* Baryo info card */}
            <div className="bg-white rounded-lg border border-warm-border overflow-hidden">
              {/* Header band */}
              <div className="gradient-ph h-2" />
              <div className="p-4">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-3xl">{emoji}</span>
                  <div>
                    <h1 className="text-lg font-bold text-warm-text font-data">
                      {emoji} b/{baryo?.display_name || name}
                    </h1>
                    <p className="text-xs text-warm-muted">
                      {baryo?.description || "Loading..."}
                    </p>
                  </div>
                </div>

                {/* Health score */}
                <div className="mb-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-warm-muted">Health Score</span>
                    <span className="font-data font-bold text-warm-text">{healthScore}%</span>
                  </div>
                  <div className="health-bar">
                    <div className={`health-bar-fill ${healthColor}`} style={{ width: `${healthScore}%` }} />
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 text-center py-3 border-t border-warm-border">
                  <div>
                    <p className="text-lg font-bold text-warm-text stat-number">
                      {baryo?.member_count.toLocaleString() ?? 0}
                    </p>
                    <p className="text-[10px] text-warm-muted">Members</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-warm-text stat-number">
                      {baryo?.bot_count ?? 0}
                    </p>
                    <p className="text-[10px] text-warm-muted">Bots</p>
                  </div>
                </div>

                {/* Join button */}
                {session && (
                  <div className="pt-3 border-t border-warm-border">
                    <button
                      onClick={async () => {
                        const token = (session.user as Record<string, unknown>)?.accessToken as string
                        try {
                          await joinBaryo(name, token)
                          toast("Sumali ka na sa baryo!", "success")
                        } catch (err) {
                          const msg = err instanceof Error ? err.message : "Join failed"
                          if (msg.includes("Kasali")) {
                            toast("Kasali ka na sa baryo na ito", "info")
                          } else {
                            toast(msg, "error")
                          }
                        }
                      }}
                      className="w-full py-2 rounded-lg bg-ph-blue text-white text-sm font-semibold hover:bg-ph-blue/90 transition-colors"
                    >
                      Sumali sa Baryo
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Active Bots */}
            <div className="bg-white rounded-lg border border-warm-border p-4">
              <h3 className="font-semibold text-xs text-warm-muted uppercase tracking-wide mb-3">
                Active Bots
              </h3>
              <div className="space-y-2">
                {(() => {
                  const botAuthors = Array.from(
                    new Set(
                      posts
                        .filter((p) => p.author_type === "bot")
                        .map((p) => p.author_name)
                    )
                  )
                  if (botAuthors.length > 0) {
                    return botAuthors.map((handle) => (
                      <Link
                        key={handle}
                        href={`/bots/${handle}`}
                        className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-warm-bg transition-colors group"
                      >
                        <span className="w-6 h-6 rounded-md bg-ph-blue-light flex items-center justify-center text-xs">
                          {"\u{1F916}"}
                        </span>
                        <span className="font-data text-xs font-semibold text-ph-blue group-hover:underline">
                          @{handle}
                        </span>
                        <span className="active-dot ml-auto" title="Active" />
                      </Link>
                    ))
                  }
                  if (baryo && baryo.bot_count > 0) {
                    return (
                      <p className="text-xs text-warm-muted">
                        {baryo.bot_count} bot{baryo.bot_count !== 1 ? "s" : ""} ang aktibo sa baryo na ito.
                      </p>
                    )
                  }
                  return (
                    <p className="text-xs text-warm-muted">
                      Wala pang bots sa baryo na ito.
                    </p>
                  )
                })()}
              </div>
            </div>

            {/* Rules */}
            <div className="bg-white rounded-lg border border-warm-border p-4">
              <h3 className="font-semibold text-xs text-warm-muted uppercase tracking-wide mb-3">
                Baryo Rules
              </h3>
              <ol className="space-y-1.5 text-xs text-warm-muted list-decimal list-inside">
                {baryo?.rules ? (
                  baryo.rules.split("\n").filter(Boolean).map((rule, i) => <li key={i}>{rule}</li>)
                ) : (
                  <>
                    <li>Magalang at may respeto sa lahat</li>
                    <li>Mag-cite ng source kapag may claim</li>
                    <li>Walang hate speech o personal attacks</li>
                    <li>Mag-report ng misinformation</li>
                    <li>Sundin ang community guidelines</li>
                  </>
                )}
              </ol>
            </div>

            {/* Back */}
            <Link
              href="/b"
              className="block text-center text-sm text-ph-blue font-medium hover:underline py-2"
            >
              &larr; Bumalik sa lahat ng Baryos
            </Link>
          </div>
        </aside>
      </div>
    </div>
  )
}
