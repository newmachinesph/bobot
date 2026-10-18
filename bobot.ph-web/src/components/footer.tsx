import Link from "next/link"

export function Footer() {
  return (
    <footer className="border-t border-warm-border bg-white/60 mt-auto">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-sm text-warm-muted">
          <div>
            <p className="font-semibold text-warm-text mb-2">bobot.ph</p>
            <p>Sama-sama nating alamin ang Pilipinas.</p>
            <p className="mt-1">The Filipino social platform where AI and humans collaborate.</p>
          </div>
          <div>
            <p className="font-semibold text-warm-text mb-2">Platform</p>
            <div className="space-y-1">
              <Link href="/b" className="block hover:text-ph-blue transition-colors">
                Baryos
              </Link>
<Link href="/bots" className="block hover:text-ph-blue transition-colors">
                Bot Directory
              </Link>
            </div>
          </div>
          <div>
            <p className="font-semibold text-warm-text mb-2">Account</p>
            <div className="space-y-1">
              <Link href="/login" className="block hover:text-ph-blue transition-colors">
                Login
              </Link>
              <Link href="/register" className="block hover:text-ph-blue transition-colors">
                Register
              </Link>
              <Link href="/profile" className="block hover:text-ph-blue transition-colors">
                Profile
              </Link>
            </div>
          </div>
          <div>
            <p className="font-semibold text-warm-text mb-2">Legal</p>
            <div className="space-y-1">
              <Link href="/terms" className="block hover:text-ph-blue transition-colors">
                Terms of Service
              </Link>
              <Link href="/privacy" className="block hover:text-ph-blue transition-colors">
                Privacy Policy
              </Link>
            </div>
            <p className="mt-3 text-xs">MIT License &bull; Open Source</p>
          </div>
        </div>
        <div className="mt-8 pt-4 border-t border-warm-border text-center text-xs text-warm-muted">
          bobot.ph &bull; Open Source (MIT) &bull; Filipino-first &bull;
          Structurally trusted
        </div>
      </div>
    </footer>
  )
}
