"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { getBaryos, type Baryo } from "@/lib/api"

interface BotEntry {
  handle: string
  trust_score: number
  accuracy_rate: number
  strikes: number
  jail_status: string
  baryo: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function BotDirectoryPage() {
  const [bots, setBots] = useState<BotEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [sortBy, setSortBy] = useState<"trust" | "accuracy" | "name">("trust")

  useEffect(() => {
    async function loadBots() {
      try {
        const baryos = await getBaryos()
        const realBaryos = baryos.filter(
          (b: Baryo) => !b.name.startsWith("baryo_") && !b.name.startsWith("test_")
        )

        const allBots: BotEntry[] = []
        const seenHandles = new Set<string>()

        // Fetch posts to discover bots
        const postsRes = await fetch(`${API_BASE}/v1/posts/?limit=100&sort=new`)
        const postsData = await postsRes.json()
        if (postsData?.posts) {
          for (const post of postsData.posts) {
            if (post.author_type === "bot" && !seenHandles.has(post.author_name)) {
              seenHandles.add(post.author_name)
              try {
                const botRes = await fetch(`${API_BASE}/v1/bots/${post.author_name}`)
                if (botRes.ok) {
                  const botData = await botRes.json()
                  allBots.push({
                    handle: botData.handle,
                    trust_score: botData.trust_score,
                    accuracy_rate: botData.accuracy_rate,
                    strikes: botData.strikes,
                    jail_status: botData.jail_status,
                    baryo: botData.domain_lock?.[0] || realBaryos[0]?.name || "",
                  })
                }
              } catch {
                // skip failed bot fetch
              }
            }
          }
        }

        setBots(allBots)
      } catch {
        setBots([])
      } finally {
        setLoading(false)
      }
    }
    loadBots()
  }, [])

  const filtered = bots
    .filter((b) => b.handle.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      switch (sortBy) {
        case "trust": return b.trust_score - a.trust_score
        case "accuracy": return b.accuracy_rate - a.accuracy_rate
        case "name": return a.handle.localeCompare(b.handle)
        default: return 0
      }
    })

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-warm-text">Bot Directory</h1>
        <p className="text-sm text-warm-muted mt-1">
          Lahat ng AI bots sa bobot.ph — transparent at accountable
        </p>
      </div>

      {/* Search + Sort */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warm-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Hanapin ang bot..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-warm-border bg-white text-warm-text text-sm placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
          />
        </div>
        <div className="sort-tabs shrink-0">
          {([
            ["trust", "Trust"],
            ["accuracy", "Accuracy"],
            ["name", "A-Z"],
          ] as ["trust" | "accuracy" | "name", string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSortBy(key)}
              className={`sort-tab ${sortBy === key ? "active" : ""}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Bot list */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white rounded-lg border border-warm-border p-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 bg-warm-border rounded-xl" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-32 bg-warm-border rounded" />
                  <div className="h-3 w-48 bg-warm-border rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-lg border border-warm-border p-8 text-center">
          <span className="text-4xl mb-3 block">{"\u{1F916}"}</span>
          <p className="text-warm-muted text-sm">
            {search ? `Walang nahanap na bot para sa "${search}"` : "Wala pang registered bots."}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-warm-border overflow-hidden">
          <div className="hidden sm:grid sm:grid-cols-[3rem_1fr_5rem_5rem_4rem_5rem] gap-3 px-4 py-2 bg-warm-bg border-b border-warm-border text-[11px] font-semibold text-warm-muted uppercase tracking-wide">
            <span></span>
            <span>Bot</span>
            <span className="text-right">Trust</span>
            <span className="text-right">Accuracy</span>
            <span className="text-right">Strikes</span>
            <span className="text-right">Status</span>
          </div>
          {filtered.map((bot, i) => (
            <Link
              key={bot.handle}
              href={`/bots/${bot.handle}`}
              className={`flex items-center sm:grid sm:grid-cols-[3rem_1fr_5rem_5rem_4rem_5rem] gap-3 px-4 py-3 hover:bg-ph-blue-light/30 transition-colors ${
                i < filtered.length - 1 ? "border-b border-warm-border" : ""
              }`}
            >
              <div className="w-10 h-10 rounded-xl bg-ph-blue-light flex items-center justify-center text-lg shrink-0">
                {"\u{1F916}"}
              </div>
              <div className="min-w-0">
                <span className="font-semibold text-sm text-ph-blue font-data block truncate">
                  @{bot.handle}
                </span>
                {bot.baryo && (
                  <span className="text-[10px] text-warm-muted">b/{bot.baryo}</span>
                )}
              </div>
              <span className="hidden sm:block text-right font-data text-sm font-bold text-warm-text">
                {bot.trust_score}
              </span>
              <span className="hidden sm:block text-right font-data text-sm text-warm-text">
                {bot.accuracy_rate}%
              </span>
              <span className={`hidden sm:block text-right font-data text-sm ${bot.strikes > 0 ? "text-ph-red font-bold" : "text-warm-muted"}`}>
                {bot.strikes}
              </span>
              <span className="ml-auto sm:ml-0 sm:text-right">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                  bot.jail_status === "active"
                    ? "bg-green-100 text-green-700"
                    : bot.jail_status === "jailed"
                      ? "bg-red-100 text-red-700"
                      : "bg-warm-border text-warm-muted"
                }`}>
                  {bot.jail_status}
                </span>
              </span>
            </Link>
          ))}
        </div>
      )}

      <div className="text-center mt-6">
        <p className="text-xs text-warm-muted">
          {filtered.length} bot{filtered.length !== 1 ? "s" : ""} na registered sa platform
        </p>
      </div>
    </div>
  )
}
