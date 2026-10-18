import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        username: { label: "Username" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) return null

        try {
          const res = await fetch(`${API_URL}/v1/accounts/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              username: credentials.username,
              password: credentials.password,
            }),
          })

          if (!res.ok) return null

          const data = await res.json()
          return {
            id: data.user.id,
            name: data.user.username,
            accessToken: data.access_token,
            tier: data.user.tier,
          }
        } catch {
          return null
        }
      },
    }),
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.tier = (user as Record<string, unknown>).tier
        token.accessToken = (user as Record<string, unknown>).accessToken
      }
      return token
    },
    session({ session, token }) {
      if (session.user) {
        const user = session.user as unknown as Record<string, unknown>
        user.id = token.id
        user.tier = token.tier
        user.accessToken = token.accessToken
      }
      return session
    },
  },
  pages: {
    signIn: "/login",
  },
})
