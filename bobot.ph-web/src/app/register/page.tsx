"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { register as apiRegister } from "@/lib/api"
import { signIn } from "next-auth/react"

const PH_REGIONS = [
  "NCR - National Capital Region",
  "CAR - Cordillera Administrative Region",
  "Region I - Ilocos",
  "Region II - Cagayan Valley",
  "Region III - Central Luzon",
  "Region IV-A - CALABARZON",
  "Region IV-B - MIMAROPA",
  "Region V - Bicol",
  "Region VI - Western Visayas",
  "Region VII - Central Visayas",
  "Region VIII - Eastern Visayas",
  "Region IX - Zamboanga Peninsula",
  "Region X - Northern Mindanao",
  "Region XI - Davao",
  "Region XII - SOCCSKSARGEN",
  "Region XIII - Caraga",
  "BARMM - Bangsamoro",
  "Overseas Filipino",
]

export default function RegisterPage() {
  const router = useRouter()
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    region: "",
    acceptTerms: false,
  })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  function update(field: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")

    if (!form.acceptTerms) {
      setError("Kailangan mong tanggapin ang Terms of Service.")
      return
    }

    setLoading(true)

    try {
      await apiRegister({
        username: form.username,
        email: form.email,
        password: form.password,
        region: form.region || undefined,
      })

      // Auto-login after registration
      const res = await signIn("credentials", {
        redirect: false,
        username: form.username,
        password: form.password,
      })

      if (res?.error) {
        router.push("/login")
      } else {
        router.push("/b")
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "May problema sa registration. Subukan ulit."
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <span className="text-4xl block mb-3">&#9788;</span>
          <h1 className="text-2xl font-bold text-warm-text">
            Sumali sa bobot.ph
          </h1>
          <p className="text-sm text-warm-muted mt-1">
            Libre at bukas para sa lahat ng Pilipino
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl border border-warm-border p-6 space-y-4"
        >
          {error && (
            <div className="bg-ph-red-light text-ph-red text-sm p-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-warm-text mb-1"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              minLength={3}
              maxLength={30}
              value={form.username}
              onChange={(e) => update("username", e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-warm-border bg-warm-bg text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
              placeholder="juandelacruz"
            />
          </div>

          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-warm-text mb-1"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-warm-border bg-warm-bg text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
              placeholder="juan@email.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-warm-text mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-warm-border bg-warm-bg text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
              placeholder="********"
            />
            {form.password.length > 0 && (() => {
              const pw = form.password
              const hasUpper = /[A-Z]/.test(pw)
              const hasLower = /[a-z]/.test(pw)
              const hasNumber = /[0-9]/.test(pw)
              const hasSpecial = /[^A-Za-z0-9]/.test(pw)
              const isStrong = pw.length >= 8 && hasUpper && hasLower && hasNumber && hasSpecial
              const isMedium = pw.length >= 8 && (hasUpper || hasLower) && (hasNumber || hasSpecial)
              const level = isStrong ? "strong" : isMedium ? "medium" : "weak"
              const color = level === "strong" ? "#22c55e" : level === "medium" ? "#eab308" : "#ef4444"
              const width = level === "strong" ? "100%" : level === "medium" ? "60%" : "30%"
              const label = level === "strong" ? "Malakas" : level === "medium" ? "Katamtaman" : "Mahina"
              return (
                <div style={{ marginTop: "6px" }}>
                  <div style={{ height: "4px", borderRadius: "2px", backgroundColor: "#e5e7eb", overflow: "hidden" }}>
                    <div style={{ height: "100%", width, backgroundColor: color, borderRadius: "2px", transition: "all 0.3s ease" }} />
                  </div>
                  <p style={{ fontSize: "11px", color, marginTop: "3px", fontWeight: 600 }}>
                    {label}
                  </p>
                </div>
              )
            })()}
            {form.password.length === 0 && (
              <p className="text-xs text-warm-muted mt-1">
                Hindi bababa sa 8 characters
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="region"
              className="block text-sm font-medium text-warm-text mb-1"
            >
              Region <span className="text-warm-muted">(optional)</span>
            </label>
            <select
              id="region"
              value={form.region}
              onChange={(e) => update("region", e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-warm-border bg-warm-bg text-warm-text focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
            >
              <option value="">Piliin ang region</option>
              {PH_REGIONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.acceptTerms}
              onChange={(e) => update("acceptTerms", e.target.checked)}
              className="mt-1 w-4 h-4 rounded border-warm-border text-ph-blue focus:ring-ph-blue/30"
            />
            <span className="text-sm text-warm-muted">
              Tinatanggap ko ang{" "}
              <Link href="/terms" className="text-ph-blue hover:underline">
                Terms of Service
              </Link>{" "}
              at{" "}
              <Link href="/privacy" className="text-ph-blue hover:underline">
                Privacy Policy
              </Link>{" "}
              ng bobot.ph
            </span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-ph-blue text-white font-semibold hover:bg-ph-blue/90 disabled:opacity-50 transition-colors"
          >
            {loading ? "Nagre-register..." : "Mag-register"}
          </button>
        </form>

        <p className="text-center text-sm text-warm-muted mt-6">
          May account ka na?{" "}
          <Link
            href="/login"
            className="text-ph-blue font-semibold hover:underline"
          >
            Mag-login
          </Link>
        </p>
      </div>
    </div>
  )
}
