"use client"

import Link from "next/link"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import { useState } from "react"

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)

    const res = await signIn("credentials", {
      redirect: false,
      username,
      password,
    })

    setLoading(false)

    if (res?.error) {
      setError("Mali ang username o password. Subukan ulit.")
    } else {
      router.push("/b")
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <span className="text-4xl block mb-3">&#9788;</span>
          <h1 className="text-2xl font-bold text-warm-text">
            Mag-login sa bobot.ph
          </h1>
          <p className="text-sm text-warm-muted mt-1">
            Maligayang pagbabalik!
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
              Username o Email
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-warm-border bg-warm-bg text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
              placeholder="juandelacruz"
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-warm-border bg-warm-bg text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
              placeholder="********"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-ph-blue text-white font-semibold hover:bg-ph-blue/90 disabled:opacity-50 transition-colors"
          >
            {loading ? "Naglo-login..." : "Mag-login"}
          </button>
        </form>

        <p className="text-center text-sm text-warm-muted mt-6">
          Wala ka pang account?{" "}
          <Link
            href="/register"
            className="text-ph-blue font-semibold hover:underline"
          >
            Mag-register
          </Link>
        </p>
      </div>
    </div>
  )
}
