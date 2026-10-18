export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-warm-text mb-6">Privacy Policy</h1>
      <div className="prose prose-sm text-warm-text space-y-4">
        <p className="text-warm-muted">Last updated: March 16, 2026</p>

        <h2 className="text-lg font-semibold mt-6">1. Data na Kinokolekta Namin</h2>
        <ul className="list-disc list-inside space-y-1 text-warm-muted">
          <li><strong>Username</strong> — publicly visible</li>
          <li><strong>Email</strong> — stored as SHA-256 hash only, hindi namin alam ang actual email</li>
          <li><strong>Password</strong> — bcrypt hashed, hindi ma-reverse</li>
          <li><strong>Region</strong> — optional, para sa community features</li>
          <li><strong>Posts at Replies</strong> — publicly visible sa platform</li>
          <li><strong>Votes at Flags</strong> — anonymous, walang makikita kung sino ang nag-vote</li>
        </ul>

        <h2 className="text-lg font-semibold mt-6">2. Paano Namin Ginagamit ang Data</h2>
        <ul className="list-disc list-inside space-y-1 text-warm-muted">
          <li>Authentication at account management</li>
          <li>Loob score calculation (reputation)</li>
          <li>Platform analytics (Pulse dashboard)</li>
          <li>Community moderation (Lupon)</li>
        </ul>

        <h2 className="text-lg font-semibold mt-6">3. Ang Hindi Namin Ginagawa</h2>
        <ul className="list-disc list-inside space-y-1 text-warm-muted">
          <li>Hindi namin ibinebenta ang data mo</li>
          <li>Walang third-party ads o tracking</li>
          <li>Walang data sharing sa advertisers</li>
          <li>Hindi namin sini-store ang plaintext email o password</li>
        </ul>

        <h2 className="text-lg font-semibold mt-6">4. Data Security</h2>
        <p className="text-warm-muted">
          Gumagamit kami ng SHA-256 hashing para sa email, bcrypt para sa passwords, at encrypted API keys. Ang database ay hosted sa Neon PostgreSQL (Singapore region) para sa mababang latency sa Pilipinas.
        </p>

        <h2 className="text-lg font-semibold mt-6">5. Open Source Transparency</h2>
        <p className="text-warm-muted">
          Ang buong codebase ay MIT licensed at publicly available. Kaya mo i-audit ang exactly kung paano namin hina-handle ang data mo.
        </p>

        <h2 className="text-lg font-semibold mt-6">6. Data Deletion</h2>
        <p className="text-warm-muted">
          Pwede mong i-request ang deletion ng account mo sa pamamagitan ng pag-contact sa amin. I-delete namin ang lahat ng personal data mo.
        </p>

        <h2 className="text-lg font-semibold mt-6">7. Contact</h2>
        <p className="text-warm-muted">
          Para sa privacy concerns, mag-post sa b/teknolohiya o i-flag ang isyu sa GitHub repository.
        </p>
      </div>
    </div>
  )
}
