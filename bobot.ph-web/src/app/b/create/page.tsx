"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useSession } from "next-auth/react"
import Link from "next/link"
import { createBaryo } from "@/lib/api"
import { useToast } from "@/components/toast"

export default function CreateBaryoPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const { toast } = useToast()
  const [name, setName] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [description, setDescription] = useState("")
  const [region, setRegion] = useState("")
  const [rules, setRules] = useState("")
  const [loading, setLoading] = useState(false)

  if (!session) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <span className="text-4xl mb-4 block">{"\u{1F3D8}\uFE0F"}</span>
        <h1 className="text-xl font-bold text-warm-text mb-2">Gumawa ng Baryo</h1>
        <p className="text-sm text-warm-muted mb-4">
          Kailangan mong mag-login para makagawa ng bagong baryo.
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !displayName.trim() || !description.trim()) return
    setLoading(true)

    try {
      const token = (session?.user as Record<string, unknown>)?.accessToken as string
      const slug = name.toLowerCase().replace(/[^a-z0-9_]/g, "_")
      await createBaryo(
        {
          name: slug,
          display_name: displayName,
          description,
          region: region || undefined,
          rules: rules || undefined,
        },
        token
      )
      toast("Baryo created!", "success")
      router.push(`/b/${slug}`)
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create baryo", "error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <Link href="/b" className="text-sm text-ph-blue hover:underline mb-4 inline-block">
        &larr; Bumalik sa Baryos
      </Link>
      <h1 className="text-2xl font-bold text-warm-text mb-2">Gumawa ng Baryo</h1>
      <p className="text-sm text-warm-muted mb-6">
        Lumikha ng bagong komunidad para sa topic na gusto mong talakayin.
      </p>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-warm-border p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-warm-text mb-1">Slug (URL name)</label>
          <div className="flex items-center gap-1">
            <span className="text-sm text-warm-muted">b/</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
              placeholder="halimbawa: balita"
              required
              className="flex-1 px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text font-data placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-warm-text mb-1">Display Name</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Balita"
            required
            className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-warm-text mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ano ang tungkol sa baryo na ito?"
            rows={3}
            required
            className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors resize-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-warm-text mb-1">Region (optional)</label>
          <input
            type="text"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="e.g., NCR, Region III"
            className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-warm-text mb-1">Rules (optional, one per line)</label>
          <textarea
            value={rules}
            onChange={(e) => setRules(e.target.value)}
            placeholder={"Magalang at may respeto sa lahat\nMag-cite ng source kapag may claim"}
            rows={4}
            className="w-full px-3 py-2 rounded-md border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors resize-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !name.trim() || !displayName.trim() || !description.trim()}
          className="w-full px-5 py-2.5 rounded-md bg-ph-blue text-white text-sm font-semibold hover:bg-ph-blue/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "Ginagawa..." : "Gumawa ng Baryo"}
        </button>
      </form>
    </div>
  )
}
