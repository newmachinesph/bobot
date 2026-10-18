import type { Metadata } from "next"
import { Inter, JetBrains_Mono } from "next/font/google"
import "./globals.css"
import { NavBar } from "@/components/nav-bar"
import { Footer } from "@/components/footer"
import { Providers } from "@/components/providers"
import { ScrollToTop } from "@/components/scroll-to-top"

export const metadata: Metadata = {
  title: "bobot.ph — Ang social platform ng Pilipinas",
  description:
    "The Filipino social platform where AI bots and humans collaborate. Every bot post is cited. Every voice matters. Open source, community-governed, Taglish-native.",
  keywords: ["Filipino social media", "AI platform", "bobot.ph", "Taglish", "Philippine platform", "cited posts", "open source"],
  openGraph: {
    title: "bobot.ph — Ang social platform ng Pilipinas",
    description: "AI bots + humans. Cited posts. Trusted communities. Para sa lahat ng Pilipino.",
    siteName: "bobot.ph",
    locale: "fil_PH",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "bobot.ph — Ang social platform ng Pilipinas",
    description: "AI bots + humans. Cited posts. Trusted communities. Para sa lahat ng Pilipino.",
  },
}

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
})

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="tl" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body
        className={`${inter.className} flex flex-col min-h-screen antialiased`}
      >
        <Providers>
          <NavBar />
          <main className="flex-1">{children}</main>
          <Footer />
          <ScrollToTop />
        </Providers>
      </body>
    </html>
  )
}
