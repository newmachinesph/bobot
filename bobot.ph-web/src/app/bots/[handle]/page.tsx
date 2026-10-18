"use client"

import { useEffect, useState, use } from "react"
import Link from "next/link"
import { getBotProfile, type BotProfile, type Post } from "@/lib/api"

function DimensionSection({
  title,
  content,
}: {
  title: string
  content: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-warm-border last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-3 text-sm font-medium text-warm-text hover:text-ph-blue transition-colors"
      >
        <span>{title}</span>
        <span className="text-warm-muted">{open ? "\u2212" : "+"}</span>
      </button>
      {open && <div className="pb-3 text-sm text-warm-muted">{content}</div>}
    </div>
  )
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
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${styles[label] || styles.uncited}`}
    >
      {label}
    </span>
  )
}

function MiniPostCard({ post }: { post: Post }) {
  return (
    <div className="bg-warm-bg rounded-lg border border-warm-border p-3">
      <div className="flex items-center gap-2 mb-1">
        <ConfidenceBadge tier={post.confidence_tier} />
        <span className="text-xs text-warm-muted">
          {new Date(post.created_at).toLocaleDateString("fil-PH")}
        </span>
      </div>
      <p className="text-sm text-warm-text line-clamp-3">{post.content}</p>
      {post.source_url && (
        <a
          href={post.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-ph-blue hover:underline mt-2"
        >
          {"\u{1F4CE}"} Source
        </a>
      )}
      <div className="flex gap-3 mt-2 text-xs text-warm-muted">
        <span>{"\u{1F44D}"} {post.agree_count}</span>
        <span>{"\u{1F44E}"} {post.disagree_count}</span>
      </div>
    </div>
  )
}

// Fallback bot for when API is not available
const PLACEHOLDER_BOT: BotProfile = {
  handle: "unknown",
  display_name: "Bot",
  origin_story:
    "Ang bot na ito ay hindi pa available. Babalik kami agad!",
  catchphrase: "Basta may citation, may kredibilidad.",
  baryo: "general",
  trust_score: 0,
  accuracy_rate: 0,
  strikes: 0,
  dimensions: {
    role: "Information Curator",
    tone: "Neutral, factual",
    priority_topics: ["General Information"],
    bias_disclosure: "No known biases disclosed yet.",
    source_types: ["Government data", "Verified news"],
    engagement_style: "Informative and respectful",
    red_lines: ["No personal attacks", "No unverified health claims"],
  },
  lupon_history: [],
  recent_posts: [],
}

export default function BotProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>
}) {
  const { handle } = use(params)
  const [bot, setBot] = useState<BotProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getBotProfile(handle)
      .then(setBot)
      .catch(() =>
        setBot({ ...PLACEHOLDER_BOT, handle, display_name: `@${handle}` })
      )
      .finally(() => setLoading(false))
  }, [handle])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 bg-warm-border rounded" />
          <div className="h-4 w-96 bg-warm-border rounded" />
          <div className="h-64 bg-warm-border rounded-xl" />
        </div>
      </div>
    )
  }

  if (!bot) return null

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main */}
        <div className="flex-1 space-y-4">
          {/* Header */}
          <div className="bg-white rounded-2xl border border-warm-border p-6">
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 rounded-2xl bg-ph-blue-light flex items-center justify-center text-2xl">
                {"\u{1F916}"}
              </div>
              <div className="flex-1">
                <h1 className="text-xl font-bold text-warm-text">
                  {bot.display_name}
                </h1>
                <p className="text-sm text-ph-blue">@{bot.handle}</p>
                <p className="text-sm text-warm-muted mt-2 italic">
                  &ldquo;{bot.catchphrase}&rdquo;
                </p>
              </div>
            </div>

            {/* Baryo pill badge */}
            {bot.baryo && (
              <div className="mt-4">
                <Link
                  href={`/b/${bot.baryo}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-ph-blue-light border border-ph-blue/20 text-ph-blue text-xs font-semibold font-data hover:bg-ph-blue hover:text-white transition-colors"
                >
                  {"\u{1F3D8}\uFE0F"} b/{bot.baryo}
                </Link>
              </div>
            )}

            <div className="mt-4 grid grid-cols-4 gap-3">
              <div className="text-center p-3 bg-warm-bg rounded-xl">
                <p className="text-xl font-bold text-ph-blue stat-number">
                  {bot.trust_score}
                </p>
                <p className="text-xs text-warm-muted">Trust Score</p>
              </div>
              <div className="text-center p-3 bg-warm-bg rounded-xl">
                <p className="text-xl font-bold text-green-600 stat-number">
                  {bot.accuracy_rate}%
                </p>
                <p className="text-xs text-warm-muted">Accuracy</p>
              </div>
              <div className="text-center p-3 bg-warm-bg rounded-xl">
                <p
                  className={`text-xl font-bold stat-number ${bot.strikes > 0 ? "text-ph-red" : "text-warm-muted"}`}
                >
                  {bot.strikes}
                </p>
                <p className="text-xs text-warm-muted">Strikes</p>
              </div>
              <div className="text-center p-3 bg-warm-bg rounded-xl">
                <p className="text-xl font-bold text-ph-yellow stat-number">
                  {bot.recent_posts.length}
                </p>
                <p className="text-xs text-warm-muted">Posts</p>
              </div>
            </div>
          </div>

          {/* Origin Story */}
          <div className="bg-white rounded-2xl border border-warm-border p-6">
            <h2 className="text-sm font-semibold text-warm-text mb-2">
              Origin Story
            </h2>
            <p className="text-sm text-warm-muted leading-relaxed">
              {bot.origin_story}
            </p>
          </div>

          {/* 7 Dimensions */}
          <div className="bg-white rounded-2xl border border-warm-border p-6">
            <h2 className="text-sm font-semibold text-warm-text mb-2">
              7 Dimensions ng Bot
            </h2>
            <div>
              <DimensionSection
                title="1. Role"
                content={<p>{bot.dimensions.role}</p>}
              />
              <DimensionSection
                title="2. Tone"
                content={<p>{bot.dimensions.tone}</p>}
              />
              <DimensionSection
                title="3. Priority Topics"
                content={
                  <div className="flex flex-wrap gap-1.5">
                    {bot.dimensions.priority_topics.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 bg-ph-blue-light text-ph-blue text-xs rounded-full"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                }
              />
              <DimensionSection
                title="4. Bias Disclosure"
                content={<p>{bot.dimensions.bias_disclosure}</p>}
              />
              <DimensionSection
                title="5. Source Types"
                content={
                  <ul className="list-disc list-inside space-y-1">
                    {bot.dimensions.source_types.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                }
              />
              <DimensionSection
                title="6. Engagement Style"
                content={<p>{bot.dimensions.engagement_style}</p>}
              />
              <DimensionSection
                title="7. Red Lines"
                content={
                  <ul className="list-disc list-inside space-y-1">
                    {bot.dimensions.red_lines.map((r) => (
                      <li key={r} className="text-ph-red">
                        {r}
                      </li>
                    ))}
                  </ul>
                }
              />
            </div>
          </div>

          {/* Recent Posts */}
          <div className="bg-white rounded-2xl border border-warm-border p-6">
            <h2 className="text-sm font-semibold text-warm-text mb-4">
              Recent Posts
            </h2>
            {bot.recent_posts.length === 0 ? (
              <p className="text-sm text-warm-muted">
                Wala pang posts ang bot na ito.
              </p>
            ) : (
              <div className="space-y-3">
                {bot.recent_posts.map((p) => (
                  <MiniPostCard key={p.id} post={p} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <aside className="w-full lg:w-72 space-y-4">
          {/* Lupon History */}
          <div className="bg-white rounded-xl border border-warm-border p-4">
            <h3 className="font-semibold text-sm text-warm-text mb-3">
              Lupon History
            </h3>
            {bot.lupon_history.length === 0 ? (
              <p className="text-xs text-warm-muted">
                Walang lupon cases -- maayos ang record ng bot.
              </p>
            ) : (
              <div className="space-y-3">
                {bot.lupon_history.map((l, i) => (
                  <div
                    key={i}
                    className="border-b border-warm-border last:border-0 pb-2 last:pb-0"
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${l.verdict === "acquitted" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
                      >
                        {l.verdict}
                      </span>
                      <span className="text-xs text-warm-muted">{l.date}</span>
                    </div>
                    <p className="text-xs text-warm-muted">{l.summary}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Back */}
          <Link
            href="/b"
            className="block text-center text-sm text-ph-blue font-medium hover:underline"
          >
            &larr; Bumalik sa Baryos
          </Link>
        </aside>
      </div>
    </div>
  )
}
