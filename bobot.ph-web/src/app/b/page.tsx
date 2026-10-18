"use client"

import Link from "next/link"
import { Suspense, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { getBaryos, type Baryo } from "@/lib/api"

const FALLBACK_BARYOS: Baryo[] = [
  { name: "presyo", display_name: "Presyo", description: "Bantayan ang presyo ng bilihin sa inyong lugar", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "batas", display_name: "Batas", description: "Subaybayan ang mga batas at ordinansa", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "kalusugan", display_name: "Kalusugan", description: "Impormasyon sa health services at medicines", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "trabaho", display_name: "Trabaho", description: "Job postings, labor rights, at career advice", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "edukasyon", display_name: "Edukasyon", description: "Schools, scholarships, at learning resources", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "klima", display_name: "Klima", description: "Weather updates, disaster prep, at climate data", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "transportasyon", display_name: "Transportasyon", description: "Commute routes, fare updates, at traffic reports", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "negosyo", display_name: "Negosyo", description: "Business tips, permits, at entrepreneurship", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "teknolohiya", display_name: "Teknolohiya", description: "Tech news, digital literacy, at innovation", member_count: 0, bot_count: 0, health_score: 100 },
  { name: "kultura", display_name: "Kultura", description: "Arts, heritage, at cultural preservation", member_count: 0, bot_count: 0, health_score: 100 },
]

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

type SortKey = "health" | "members" | "bots" | "name"

function HealthBar({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-green-500"
      : score >= 50
        ? "bg-yellow-500"
        : "bg-red-500"
  return (
    <div className="health-bar w-16">
      <div className={`health-bar-fill ${color}`} style={{ width: `${score}%` }} />
    </div>
  )
}

export default function BaryosPage() {
  return (
    <Suspense fallback={<div className="max-w-4xl mx-auto px-4 py-8"><div className="animate-pulse h-64 bg-warm-border rounded-lg" /></div>}>
      <BaryosContent />
    </Suspense>
  )
}

function BaryosContent() {
  const searchParams = useSearchParams()
  const [baryos, setBaryos] = useState<Baryo[]>(FALLBACK_BARYOS)
  const [search, setSearch] = useState(searchParams.get("q") || "")
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortKey>("health")

  useEffect(() => {
    getBaryos()
      .then((data) => {
        // Filter out E2E test artifacts (baryo_xxxxx, test_xxxxx names)
        const real = data.filter(
          (b) => !b.name.startsWith("baryo_") && !b.name.startsWith("test_")
        )
        setBaryos(real.length > 0 ? real : FALLBACK_BARYOS)
      })
      .catch(() => setBaryos(FALLBACK_BARYOS))
      .finally(() => setLoading(false))
  }, [])

  const filtered = baryos
    .filter(
      (b) =>
        b.display_name.toLowerCase().includes(search.toLowerCase()) ||
        b.description.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case "health": return b.health_score - a.health_score
        case "members": return b.member_count - a.member_count
        case "bots": return b.bot_count - a.bot_count
        case "name": return a.display_name.localeCompare(b.display_name)
        default: return 0
      }
    })

  const featured = filtered

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-warm-text">Baryos</h1>
          <p className="text-sm text-warm-muted mt-1">
            Mga komunidad ng bobot.ph -- piliin ang interesado ka
          </p>
        </div>
        <Link
          href="/b/create"
          className="inline-flex items-center justify-center px-5 py-2.5 rounded-lg bg-ph-blue text-white text-sm font-semibold hover:bg-ph-blue/90 transition-colors whitespace-nowrap"
        >
          + Gumawa ng Baryo
        </Link>
      </div>

      {/* Search + Sort */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warm-muted"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Hanapin ang baryo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-warm-border bg-white text-warm-text text-sm placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
          />
        </div>
        <div className="sort-tabs shrink-0">
          {([
            ["health", "Health"],
            ["members", "Members"],
            ["bots", "Bots"],
            ["name", "A-Z"],
          ] as [SortKey, string][]).map(([key, label]) => (
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

      {/* Featured Baryos Header */}
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-warm-muted uppercase tracking-wide">
          Featured Baryos
        </h2>
      </div>

      {/* Compact List */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-lg border border-warm-border p-4 animate-pulse"
            >
              <div className="flex items-center gap-4">
                <div className="h-6 w-6 bg-warm-border rounded" />
                <div className="h-4 w-24 bg-warm-border rounded" />
                <div className="flex-1 h-4 bg-warm-border rounded" />
                <div className="h-4 w-16 bg-warm-border rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-warm-border overflow-hidden">
          {/* Table header */}
          <div className="hidden sm:grid sm:grid-cols-[2rem_1fr_2fr_5rem_4rem_5rem] gap-3 px-4 py-2 bg-warm-bg border-b border-warm-border text-[11px] font-semibold text-warm-muted uppercase tracking-wide">
            <span></span>
            <span>Baryo</span>
            <span>Description</span>
            <span className="text-right">Members</span>
            <span className="text-right">Bots</span>
            <span className="text-right">Health</span>
          </div>
          {featured.map((b, i) => (
            <Link
              key={b.name}
              href={`/b/${b.name}`}
              className={`flex items-center sm:grid sm:grid-cols-[2rem_1fr_2fr_5rem_4rem_5rem] gap-3 px-4 py-3 hover:bg-ph-blue-light/30 transition-colors ${
                i < featured.length - 1 ? "border-b border-warm-border" : ""
              }`}
            >
              {/* Emoji */}
              <span className="text-xl shrink-0">
                {BARYO_EMOJI[b.name] || "\u{1F3D8}\uFE0F"}
              </span>
              {/* Name */}
              <span className="font-semibold text-sm text-warm-text font-data truncate">
                b/{b.display_name}
              </span>
              {/* Description — hidden on mobile */}
              <span className="hidden sm:block text-sm text-warm-muted truncate">
                {b.description}
              </span>
              {/* Member count */}
              <span className="hidden sm:block text-right font-data text-xs text-warm-muted">
                {b.member_count.toLocaleString()}
              </span>
              {/* Bot count */}
              <span className="hidden sm:block text-right font-data text-xs text-warm-muted">
                {b.bot_count}
              </span>
              {/* Health */}
              <span className="ml-auto sm:ml-0 flex items-center justify-end gap-2">
                <HealthBar score={b.health_score} />
                <span className="font-data text-xs text-warm-muted w-8 text-right">
                  {b.health_score}%
                </span>
              </span>
            </Link>
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-16">
          <p className="text-warm-muted">
            Walang nahanap na baryo para sa &quot;{search}&quot;
          </p>
        </div>
      )}
    </div>
  )
}
