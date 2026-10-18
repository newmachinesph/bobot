"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import Link from "next/link"
import { getMyProfile, getLoob, updateProfile, type UserProfile, type LoobScores } from "@/lib/api"
import { useToast } from "@/components/toast"

const LOOB_LABELS: Record<string, { label: string; desc: string }> = {
  katapatan: { label: "Katapatan", desc: "Faithfulness & Reliability" },
  katumpakan: { label: "Katumpakan", desc: "Accuracy & Precision" },
  kagalingan: { label: "Kagalingan", desc: "Excellence & Quality" },
  kapakumbabaan: { label: "Kapakumbabaan", desc: "Humility & Openness" },
  kalakarang_sibiko: { label: "Kalakarang Sibiko", desc: "Civic Engagement" },
}

function LoobFlower({ scores }: { scores: LoobScores }) {
  const dims = Object.entries(LOOB_LABELS)
  const maxScore = 100

  return (
    <div className="space-y-3">
      {dims.map(([key, { label, desc }]) => {
        const score = (scores as unknown as Record<string, number>)[key] ?? 50
        const pct = (score / maxScore) * 100
        const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-ph-red"

        return (
          <div key={key}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-warm-text font-medium">{label}</span>
              <span className="font-data text-warm-muted">{score.toFixed(1)}</span>
            </div>
            <div className="w-full bg-warm-border rounded-full h-2">
              <div className={`h-2 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
            </div>
            <p className="text-[10px] text-warm-muted mt-0.5">{desc}</p>
          </div>
        )
      })}
    </div>
  )
}

export default function ProfilePage() {
  const { data: session } = useSession()
  const { toast } = useToast()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loob, setLoob] = useState<LoobScores | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [bio, setBio] = useState("")
  const [region, setRegion] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!session) {
      setLoading(false)
      return
    }
    const token = (session.user as Record<string, unknown>)?.accessToken as string
    const username = session.user?.name || ""

    Promise.all([
      getMyProfile(token).catch(() => null),
      getLoob(username).catch(() => null),
    ]).then(([p, l]) => {
      setProfile(p)
      setLoob(l)
      if (p) {
        setBio(p.bio || "")
        setRegion(p.region || "")
      }
      setLoading(false)
    })
  }, [session])

  if (!session) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <span className="text-4xl mb-4 block">{"\u{1F464}"}</span>
        <h1 className="text-xl font-bold text-warm-text mb-2">Profile</h1>
        <p className="text-sm text-warm-muted mb-4">
          Mag-login para makita ang iyong profile.
        </p>
        <Link
          href="/login"
          className="inline-flex items-center justify-center px-6 py-2.5 rounded-lg bg-ph-blue text-white text-sm font-semibold hover:bg-ph-blue/90 transition-colors"
        >
          Mag-login
        </Link>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 bg-warm-border rounded" />
          <div className="h-64 bg-warm-border rounded-xl" />
        </div>
      </div>
    )
  }

  async function handleSave() {
    if (!session) return
    setSaving(true)
    try {
      const token = (session.user as Record<string, unknown>)?.accessToken as string
      const updated = await updateProfile({ bio, region: region || undefined }, token)
      setProfile(updated)
      setEditing(false)
      toast("Profile updated!", "success")
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to update", "error")
    } finally {
      setSaving(false)
    }
  }

  const tierLabels: Record<string, string> = {
    "1": "Baguhan",
    "2": "Aktibo",
    "3": "Kasapi",
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main profile */}
        <div className="flex-1 space-y-4">
          <div className="bg-white rounded-2xl border border-warm-border overflow-hidden">
            <div className="gradient-ph h-2" />
            <div className="p-6">
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 rounded-2xl bg-ph-blue-light flex items-center justify-center text-2xl">
                  {"\u{1F464}"}
                </div>
                <div className="flex-1">
                  <h1 className="text-xl font-bold text-warm-text">
                    {profile?.username}
                  </h1>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-ph-blue-light text-ph-blue">
                      Tier {profile?.tier} — {tierLabels[profile?.tier || "1"] || "Baguhan"}
                    </span>
                    {profile?.region && (
                      <span className="text-xs text-warm-muted">{profile.region}</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setEditing(!editing)}
                  className="text-xs text-ph-blue hover:underline font-medium"
                >
                  {editing ? "Cancel" : "Edit"}
                </button>
              </div>

              {editing ? (
                <div className="mt-4 space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-warm-text mb-1">Bio</label>
                    <textarea
                      value={bio}
                      onChange={(e) => setBio(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors resize-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-warm-text mb-1">Region</label>
                    <input
                      type="text"
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                      className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
                    />
                  </div>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-4 py-2 rounded-md bg-ph-blue text-white text-sm font-semibold hover:bg-ph-blue/90 disabled:opacity-50 transition-colors"
                  >
                    {saving ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              ) : (
                <p className="mt-3 text-sm text-warm-muted">
                  {profile?.bio || "Wala pang bio. I-click ang Edit para magdagdag."}
                </p>
              )}

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="text-center p-3 bg-warm-bg rounded-xl">
                  <p className="text-xl font-bold text-ph-blue stat-number">{profile?.karma ?? 0}</p>
                  <p className="text-xs text-warm-muted">Karma</p>
                </div>
                <div className="text-center p-3 bg-warm-bg rounded-xl">
                  <p className="text-xs font-medium text-warm-muted">
                    Joined {profile?.created_at ? new Date(profile.created_at).toLocaleDateString("fil-PH") : "—"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Loob sidebar */}
        <aside className="w-full lg:w-80 shrink-0">
          <div className="bg-white rounded-2xl border border-warm-border p-6">
            <h2 className="text-sm font-semibold text-warm-text mb-1">Loob Scores</h2>
            <p className="text-xs text-warm-muted mb-4">
              Reputation mo base sa 5 Filipino values
            </p>
            {loob ? (
              <LoobFlower scores={loob} />
            ) : (
              <p className="text-xs text-warm-muted">Hindi pa ma-load ang Loob scores.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
