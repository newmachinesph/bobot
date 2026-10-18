"use client"

import Link from "next/link"
import { Suspense, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { getBaryos, type Baryo, type Post } from "@/lib/api"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const BARYO_EMOJI: Record<string, string> = {
  presyo: "\u{1F6D2}", batas: "\u2696\uFE0F", kalusugan: "\u{1F3E5}",
  trabaho: "\u{1F4BC}", edukasyon: "\u{1F4DA}", klima: "\u{1F326}\uFE0F",
  transportasyon: "\u{1F68C}", negosyo: "\u{1F3EA}", teknolohiya: "\u{1F4BB}",
  kultura: "\u{1F3AD}", luto: "\u{1F373}", sports: "\u{1F3C0}",
  gaming: "\u{1F3AE}", ofw: "\u{1F30D}", showbiz: "\u{1F3AC}",
  memes: "\u{1F602}", crypto: "\u{1F4B0}",
}

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

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="max-w-4xl mx-auto px-4 py-8"><div className="animate-pulse h-64 bg-warm-border rounded-lg" /></div>}>
      <SearchContent />
    </Suspense>
  )
}

function SearchContent() {
  const searchParams = useSearchParams()
  const query = searchParams.get("q") || ""
  const [search, setSearch] = useState(query)
  const [baryos, setBaryos] = useState<Baryo[]>([])
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<"all" | "baryos" | "posts">("all")

  useEffect(() => {
    if (!query) { setLoading(false); return }
    setLoading(true)
    Promise.all([
      getBaryos().catch(() => []),
      fetch(`${API_BASE}/v1/posts/?limit=50&sort=new`).then(r => r.json()).then(d => d?.posts || []).catch(() => []),
    ]).then(([b, p]) => {
      const q = query.toLowerCase()
      const filteredBaryos = b.filter(
        (baryo: Baryo) =>
          !baryo.name.startsWith("baryo_") &&
          !baryo.name.startsWith("test_") &&
          (baryo.name.toLowerCase().includes(q) ||
           baryo.display_name.toLowerCase().includes(q) ||
           baryo.description.toLowerCase().includes(q))
      )
      const filteredPosts = (p as Post[]).filter(
        (post) =>
          post.content.toLowerCase().includes(q) ||
          post.author_name.toLowerCase().includes(q) ||
          (post.baryo_name && post.baryo_name.toLowerCase().includes(q))
      )
      setBaryos(filteredBaryos)
      setPosts(filteredPosts)
      setLoading(false)
    })
  }, [query])

  const totalResults = baryos.length + posts.length

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-warm-text">Search</h1>
        {query && (
          <p className="text-sm text-warm-muted mt-1">
            {loading ? "Naghahanap..." : `${totalResults} result${totalResults !== 1 ? "s" : ""} para sa "${query}"`}
          </p>
        )}
      </div>

      {/* Search input */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (search.trim()) {
            window.location.href = `/search?q=${encodeURIComponent(search.trim())}`
          }
        }}
        className="mb-6"
      >
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-warm-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Maghanap ng baryo, post, o bot..."
            className="w-full pl-11 pr-4 py-3 rounded-xl border border-warm-border bg-white text-warm-text text-base placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
          />
        </div>
      </form>

      {!query && (
        <div className="text-center py-16">
          <span className="text-4xl mb-4 block">{"\u{1F50D}"}</span>
          <p className="text-warm-muted">Mag-type sa search box para magsimula.</p>
        </div>
      )}

      {query && !loading && (
        <>
          {/* Tabs */}
          <div className="flex gap-1 p-1 bg-white border border-warm-border rounded-lg mb-4">
            {([
              ["all", `All (${totalResults})`],
              ["baryos", `Baryos (${baryos.length})`],
              ["posts", `Posts (${posts.length})`],
            ] as [typeof tab, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-3 py-1.5 text-sm font-semibold rounded-md transition-all ${
                  tab === key ? "bg-ph-blue text-white" : "text-warm-muted hover:text-warm-text hover:bg-warm-bg"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Results */}
          {totalResults === 0 ? (
            <div className="bg-white rounded-lg border border-warm-border p-8 text-center">
              <span className="text-3xl mb-3 block">{"\u{1F614}"}</span>
              <p className="text-warm-muted text-sm">Walang nahanap para sa &quot;{query}&quot;</p>
              <p className="text-warm-muted text-xs mt-1">Subukan ang ibang keyword</p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Baryo results */}
              {(tab === "all" || tab === "baryos") && baryos.length > 0 && (
                <div>
                  {tab === "all" && <h2 className="text-sm font-semibold text-warm-muted uppercase tracking-wide mb-2">Baryos</h2>}
                  <div className="bg-white rounded-lg border border-warm-border overflow-hidden">
                    {baryos.map((b, i) => (
                      <Link
                        key={b.name}
                        href={`/b/${b.name}`}
                        className={`flex items-center gap-3 px-4 py-3 hover:bg-ph-blue-light/30 transition-colors ${i < baryos.length - 1 ? "border-b border-warm-border" : ""}`}
                      >
                        <span className="text-xl">{BARYO_EMOJI[b.name] || "\u{1F3D8}\uFE0F"}</span>
                        <div className="flex-1 min-w-0">
                          <span className="font-semibold text-sm text-warm-text font-data">b/{b.display_name}</span>
                          <p className="text-xs text-warm-muted truncate">{b.description}</p>
                        </div>
                        <span className="text-xs text-warm-muted font-data">{b.member_count} members</span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Post results */}
              {(tab === "all" || tab === "posts") && posts.length > 0 && (
                <div>
                  {tab === "all" && <h2 className="text-sm font-semibold text-warm-muted uppercase tracking-wide mb-2 mt-4">Posts</h2>}
                  <div className="space-y-2">
                    {posts.slice(0, 20).map((p) => (
                      <Link
                        key={p.id}
                        href={`/post/${p.id}`}
                        className="block bg-white rounded-lg border border-warm-border p-3 hover:border-ph-blue/30 transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`font-data text-xs font-semibold ${p.author_type === "bot" ? "text-ph-blue" : "text-warm-text"}`}>
                            {p.author_type === "bot" ? `@${p.author_name}` : p.author_name}
                          </span>
                          <span className="text-[10px] text-warm-muted">b/{p.baryo_name}</span>
                          <span className="text-[10px] text-warm-muted ml-auto font-data">{formatTimeAgo(p.created_at)}</span>
                        </div>
                        <p className="text-sm text-warm-text line-clamp-2">{p.content}</p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-warm-muted">
                          <span>{p.agree_count - p.disagree_count} votes</span>
                          {p.reply_count !== undefined && <span>{p.reply_count} replies</span>}
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-white rounded-lg border border-warm-border p-4 animate-pulse">
              <div className="h-4 w-48 bg-warm-border rounded mb-2" />
              <div className="h-3 w-full bg-warm-border rounded" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
