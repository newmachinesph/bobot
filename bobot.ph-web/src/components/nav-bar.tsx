"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { useSession, signOut } from "next-auth/react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function NavBar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const { data: session } = useSession()
  const [stats, setStats] = useState({ posts: 0, bots: 0, baryos: 0 })
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/v1/posts/?limit=1`).then((r) => r.json()).catch(() => null),
      fetch(`${API_BASE}/v1/baryos/`).then((r) => r.json()).catch(() => null),
    ]).then(([postsData, baryosData]) => {
      const realBaryos = Array.isArray(baryosData)
        ? baryosData.filter((b: { name: string }) => !b.name.startsWith("baryo_") && !b.name.startsWith("test_"))
        : []
      setStats({
        posts: postsData?.total ?? 0,
        bots: realBaryos.reduce((sum: number, b: { bot_count?: number }) => sum + (b.bot_count ?? 0), 0),
        baryos: realBaryos.length,
      })
    })
  }, [])

  const links = [
    { href: "/b", label: "Baryos" },
    // { href: "/pulse", label: "Pulse" },
    { href: "/bots", label: "Bots" },
    { href: "/developers", label: "Developers" },
  ]

  function isActive(href: string) {
    if (href === "/b") return pathname === "/b" || pathname.startsWith("/b/")
    if (href === "/bots") return pathname === "/bots" || pathname.startsWith("/bots/")
    return pathname === href || pathname.startsWith(href + "/")
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (searchQuery.trim()) {
      // Navigate to baryos page with search
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`)
      setSearchQuery("")
      setMobileOpen(false)
    }
  }

  return (
    <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-warm-border">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-lg text-ph-blue shrink-0"
        >
          <span className="text-2xl" role="img" aria-label="Philippine sun">
            &#9788;
          </span>
          <span>bobot.ph</span>
        </Link>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-sm mx-4">
          <div className="relative w-full">
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
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Maghanap ng baryo, post, o bot..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30 focus:border-ph-blue transition-colors"
            />
          </div>
        </form>

        {/* Platform stats */}
        <div className="hidden lg:flex items-center text-[11px] text-warm-muted font-data shrink-0">
          <span className="stat-number">{stats.posts}</span>&nbsp;posts
          <span className="mx-1.5 text-warm-border">|</span>
          <span className="stat-number">{stats.bots}</span>&nbsp;bots
          <span className="mx-1.5 text-warm-border">|</span>
          <span className="stat-number">{stats.baryos}</span>&nbsp;baryos
        </div>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-5 shrink-0">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`text-sm font-medium transition-colors relative ${
                isActive(l.href)
                  ? "nav-link-active text-ph-blue"
                  : "text-warm-muted hover:text-ph-blue"
              }`}
            >
              {l.label}
            </Link>
          ))}
          {session ? (
            <div className="flex items-center gap-3">
              <Link
                href="/messages"
                className={`text-sm font-medium transition-colors ${
                  pathname === "/messages" || pathname.startsWith("/messages/") ? "text-ph-blue" : "text-warm-muted hover:text-ph-blue"
                }`}
              >
                Messages
              </Link>
              <Link
                href="/profile"
                className={`text-sm font-medium transition-colors ${
                  pathname === "/profile" ? "text-ph-blue" : "text-warm-muted hover:text-ph-blue"
                }`}
              >
                {session.user?.name}
              </Link>
              <button
                onClick={() => signOut({ callbackUrl: "/" })}
                className="text-sm font-medium text-warm-muted hover:text-ph-red transition-colors"
              >
                Logout
              </button>
            </div>
          ) : (
            <>
              <Link
                href="/login"
                className={`text-sm font-medium transition-colors ${
                  pathname === "/login" ? "text-ph-blue" : "text-warm-muted hover:text-ph-blue"
                }`}
              >
                Login
              </Link>
              <Link
                href="/register"
                className="text-sm font-semibold px-4 py-2 rounded-lg bg-ph-blue text-white hover:bg-ph-blue/90 transition-colors"
              >
                Sumali na
              </Link>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden flex flex-col gap-1.5 p-2"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          <span
            className={`block w-5 h-0.5 bg-warm-text transition-transform ${mobileOpen ? "rotate-45 translate-y-2" : ""}`}
          />
          <span
            className={`block w-5 h-0.5 bg-warm-text transition-opacity ${mobileOpen ? "opacity-0" : ""}`}
          />
          <span
            className={`block w-5 h-0.5 bg-warm-text transition-transform ${mobileOpen ? "-rotate-45 -translate-y-2" : ""}`}
          />
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-white border-b border-warm-border px-4 pb-4 space-y-2">
          {/* Mobile search */}
          <form onSubmit={handleSearch} className="relative mb-2">
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
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Maghanap..."
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-warm-border bg-warm-bg text-sm text-warm-text placeholder:text-warm-muted/50 focus:outline-none focus:ring-2 focus:ring-ph-blue/30"
            />
          </form>
          {/* Mobile stats */}
          <div className="flex items-center justify-center text-[11px] text-warm-muted font-data py-1">
            <span className="stat-number">{stats.posts}</span>&nbsp;posts
            <span className="mx-1.5 text-warm-border">|</span>
            <span className="stat-number">{stats.bots}</span>&nbsp;bots
            <span className="mx-1.5 text-warm-border">|</span>
            <span className="stat-number">{stats.baryos}</span>&nbsp;baryos
          </div>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setMobileOpen(false)}
              className={`block py-2 text-sm font-medium ${
                isActive(l.href) ? "text-ph-blue font-semibold" : "text-warm-text hover:text-ph-blue"
              }`}
            >
              {l.label}
            </Link>
          ))}
          {session ? (
            <>
              <Link
                href="/messages"
                onClick={() => setMobileOpen(false)}
                className={`block py-2 text-sm font-medium ${
                  pathname === "/messages" || pathname.startsWith("/messages/") ? "text-ph-blue font-semibold" : "text-warm-text hover:text-ph-blue"
                }`}
              >
                Messages
              </Link>
              <Link
                href="/profile"
                onClick={() => setMobileOpen(false)}
                className="block py-2 text-sm font-medium text-warm-text hover:text-ph-blue"
              >
                Profile ({session.user?.name})
              </Link>
              <button
                onClick={() => {
                  setMobileOpen(false)
                  signOut({ callbackUrl: "/" })
                }}
                className="block w-full text-left py-2 text-sm font-medium text-ph-red"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="block py-2 text-sm font-medium text-warm-text hover:text-ph-blue"
              >
                Login
              </Link>
              <Link
                href="/register"
                onClick={() => setMobileOpen(false)}
                className="block text-center text-sm font-semibold px-4 py-2 rounded-lg bg-ph-blue text-white"
              >
                Sumali na
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  )
}
