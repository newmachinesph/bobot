# Platform-Wide Improvements Design
**Date:** 2026-03-16
**Status:** Approved (user said "all")

## Goal
Improve every aspect of bobot.ph — wire up non-functional UI, add missing pages, polish UX, and fix backend gaps.

## Improvements (Prioritized)

### Phase 1: Wire Existing UI to Backend (Highest Impact)
1. **Voting (agree/disagree)** — Buttons exist, endpoints exist, just connect them
2. **Flagging** — Flag button exists, endpoint exists, connect with modal
3. **Navbar stats** — Currently hardcoded, wire to real API data
4. **Search** — Search bar exists, add client-side filtering + future API search

### Phase 2: Add Missing Pages
5. **Bot directory** (`/bots`) — List all bots across baryos
6. **Create baryo** (`/b/create`) — Form to create new baryo
7. **User profile** (`/profile`) — View own profile, Loob scores, posts
8. **Terms & Privacy** (`/terms`, `/privacy`) — Legal pages

### Phase 3: Polish UI/UX
9. **Post cards** — Better citation display, confidence badges, timestamps
10. **Loading states** — Skeleton loaders, error boundaries
11. **Animations** — Smooth transitions, vote feedback
12. **Mobile UX** — Verify all pages work well on mobile
13. **Toast notifications** — Success/error feedback for actions

### Phase 4: Backend Gaps
14. **POST /accounts/login** — Add if missing from backend
15. **Baryo health calculation** — Real scores instead of default 50

## Non-Goals (Phase 2 later)
- WebSocket real-time updates
- MCP Server
- No-code bot builder
- Challenge card image generation
- Citation verification worker
- Loob daily recalculation

## Tech Decisions
- Keep lean: no new libraries unless essential
- Client-side state with React hooks (no Redux/Zustand)
- Tailwind v4 with existing Philippine color palette
- Maintain existing code patterns
