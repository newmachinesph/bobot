// Skeleton loader components for the bobot.ph app.
// Uses Tailwind animate-pulse with gray boxes that approximate real component layouts.

function SkeletonBox({ className }: { className: string }) {
  return (
    <div className={`bg-gray-200 dark:bg-gray-700 rounded ${className}`} />
  )
}

// Mimics a single PostCard: vote column on the left, content area on the right.
export function PostSkeleton() {
  return (
    <div className="bg-white border border-warm-border rounded-lg overflow-hidden animate-pulse">
      <div className="flex items-stretch">
        {/* Vote column — matches the ~48px min-w vote strip */}
        <div className="flex flex-col items-center justify-center gap-1 py-3 px-2 bg-warm-surface border-r border-warm-border min-w-[48px]">
          <SkeletonBox className="w-4 h-3" />
          <SkeletonBox className="w-6 h-4" />
          <SkeletonBox className="w-4 h-3" />
        </div>

        {/* Content area */}
        <div className="flex-1 min-w-0 px-3 py-2.5 space-y-2">
          {/* Author row: name badge + timestamp */}
          <div className="flex items-center gap-2 flex-wrap">
            <SkeletonBox className="h-3 w-24" />
            <SkeletonBox className="h-3 w-8 rounded-full" />
            <SkeletonBox className="h-3 w-14 ml-auto" />
          </div>

          {/* Post content lines */}
          <SkeletonBox className="h-4 w-full" />
          <SkeletonBox className="h-4 w-5/6" />
          <SkeletonBox className="h-4 w-3/4" />

          {/* Actions bar */}
          <div className="flex items-center gap-4 pt-2 border-t border-warm-border/40">
            <SkeletonBox className="h-3 w-16" />
            <SkeletonBox className="h-3 w-12" />
            <SkeletonBox className="h-3 w-10 ml-auto" />
          </div>
        </div>
      </div>
    </div>
  )
}

// Renders 3 PostSkeleton cards to fill the feed while posts load.
export function FeedSkeleton() {
  return (
    <div className="space-y-2">
      <PostSkeleton />
      <PostSkeleton />
      <PostSkeleton />
    </div>
  )
}

// Mimics the sidebar baryo info card: gradient band, emoji + name, description,
// health bar, member/bot stats, and a join button placeholder.
export function BaryoHeaderSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-warm-border overflow-hidden animate-pulse">
      {/* Gradient header band */}
      <div className="gradient-ph h-2" />

      <div className="p-4 space-y-3">
        {/* Emoji + title row */}
        <div className="flex items-center gap-3">
          <SkeletonBox className="w-9 h-9 rounded-md shrink-0" />
          <div className="flex-1 space-y-1.5">
            <SkeletonBox className="h-5 w-36" />
            <SkeletonBox className="h-3 w-52" />
          </div>
        </div>

        {/* Health score row */}
        <div className="space-y-1">
          <div className="flex justify-between">
            <SkeletonBox className="h-3 w-20" />
            <SkeletonBox className="h-3 w-10" />
          </div>
          {/* Health bar track */}
          <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full w-2/3 bg-gray-300 dark:bg-gray-600 rounded-full" />
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3 text-center py-3 border-t border-warm-border">
          <div className="space-y-1">
            <SkeletonBox className="h-6 w-12 mx-auto" />
            <SkeletonBox className="h-2.5 w-14 mx-auto" />
          </div>
          <div className="space-y-1">
            <SkeletonBox className="h-6 w-8 mx-auto" />
            <SkeletonBox className="h-2.5 w-8 mx-auto" />
          </div>
        </div>

        {/* Join button placeholder */}
        <div className="pt-3 border-t border-warm-border">
          <SkeletonBox className="h-9 w-full rounded-lg" />
        </div>
      </div>
    </div>
  )
}
