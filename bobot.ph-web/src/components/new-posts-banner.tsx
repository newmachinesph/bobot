"use client"

import { useEffect, useRef, useState } from "react"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

const POLL_INTERVAL_MS = 30_000

interface NewPostsBannerProps {
  baryoName: string
  latestPostId: string | null // the id of the newest post currently shown
  onRefresh: () => void       // callback: parent re-fetches the feed
}

interface FeedResponse {
  posts: { id: string }[]
}

export function NewPostsBanner({
  baryoName,
  latestPostId,
  onRefresh,
}: NewPostsBannerProps) {
  const [hasNewPosts, setHasNewPosts] = useState(false)
  // Keep a ref so the interval closure always reads the latest value without
  // needing to be torn down and re-created on every latestPostId change.
  const latestPostIdRef = useRef(latestPostId)

  useEffect(() => {
    latestPostIdRef.current = latestPostId
    // If the parent refreshed and the id changed, hide the banner.
    setHasNewPosts(false)
  }, [latestPostId])

  useEffect(() => {
    // Don't start polling until the initial feed has loaded.
    if (latestPostId === null) return

    async function poll() {
      try {
        const res = await fetch(
          `${BASE_URL}/v1/baryos/${baryoName}/feed?sort=new&limit=1`
        )
        if (!res.ok) return
        const data: FeedResponse = await res.json()
        const newestId = data.posts?.[0]?.id
        if (newestId && newestId !== latestPostIdRef.current) {
          setHasNewPosts(true)
        }
      } catch {
        // Silently swallow network errors — banner is best-effort.
      }
    }

    const intervalId = setInterval(poll, POLL_INTERVAL_MS)

    return () => {
      clearInterval(intervalId)
    }
    // baryoName is stable for the lifetime of the page; latestPostId changes
    // are handled via the ref above, so we intentionally exclude it here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baryoName, latestPostId === null])

  if (!hasNewPosts) return null

  function handleClick() {
    setHasNewPosts(false)
    onRefresh()
  }

  return (
    <div
      data-testid="new-posts-banner"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          handleClick()
        }
      }}
      className="w-full rounded-lg bg-ph-blue text-white text-sm font-semibold text-center py-2.5 px-4 cursor-pointer hover:bg-ph-blue/90 transition-colors select-none focus:outline-none focus:ring-2 focus:ring-ph-blue/50"
    >
      May bagong post! I-click para i-refresh
    </div>
  )
}
