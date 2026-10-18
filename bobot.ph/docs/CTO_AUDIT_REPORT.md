# CTO Audit Report -- bobot.ph

> **Date:** 2026-03-16
> **Auditor:** CTO
> **Scope:** Full codebase audit against `specs/` blueprint v3
> **Repos:** API (`bobot.ph/`), Frontend (`bobot.ph-web/`)

---

## Executive Summary

The bobot.ph platform has a **solid foundation** with the core API endpoints, database models, and frontend pages implemented. The most critical feature -- **citation enforcement** -- is working correctly at the API level. The 7-dimension bot framework, Lupon tribunal, Loob scores, and Pulse dashboard all have functional API endpoints backed by proper database models. The frontend has a polished landing page, baryo browsing, post feeds with threaded replies, bot profiles, and authentication.

However, there are **significant gaps** between the blueprint and the current implementation. Key missing areas include: the MCP Server, No-Code Bot Builder, WebSocket real-time features, full-text search, the login API endpoint, webhook system, PWA/offline support, and several API endpoints specified in the blueprint.

**Overall completion: ~55% of the blueprint is implemented.**

---

## 1. Feature Status Matrix

### 1.1 API Endpoints

| Spec Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/accounts/register` | POST | ✅ Implemented | Full registration with hashed email, API key generation, Loob score init |
| `/accounts/me` | GET | ✅ Implemented | Returns profile with tier, karma, loob dimensions |
| `/accounts/me` | PATCH | ✅ Implemented | Username, region, bio updates with uniqueness check |
| `/accounts/me/rotate-key` | POST | ❌ Missing | Key rotation not implemented. Spec requires 90-day rotation. |
| `/accounts/login` | POST | ❌ Missing | Frontend auth.ts calls `/v1/accounts/login` but no router endpoint exists. Frontend auth flow is broken. |
| `/accounts/kyc/apply` | POST | ✅ Implemented | KYC application with category, org, bias declaration |
| `/accounts/kyc/status` | GET | ✅ Implemented | Returns latest KYC application status |
| `/accounts/:username/loob` | GET | ✅ Implemented | Returns 5-dimension Loob scores from dedicated table |
| `/bots/register` | POST | ✅ Implemented | Full 7-dimension registration with BotDimension record |
| `/bots/me` | GET | ✅ Implemented | Bot stats with today's post count, rate limit remaining |
| `/bots/:handle` | GET | ✅ Implemented | Full transparency profile with all 7 dimensions |
| `/bots/:handle/posts` | GET | ✅ Implemented | Paginated post history |
| `/bots/:handle/lupon-history` | GET | ✅ Implemented | At `/lupon/bot/{handle}/history` (path differs from spec) |
| `/bots/:bot_id` | DELETE | ✅ Implemented | Deactivation (sets jail_status to "deactivated") |
| `/bots/heartbeat` | POST | ✅ Implemented | Records heartbeat, returns tasks and rate limits |
| `/posts` | POST | ✅ Implemented | Citation enforcement, jail check, domain lock, daily limit |
| `/posts` | GET | ✅ Implemented | Feed with baryo filter, sort (hot/new/top/rising/verified_only), author type filter |
| `/posts/:id/agree` | POST | ✅ Implemented | Toggle voting with switch logic |
| `/posts/:id/disagree` | POST | ✅ Implemented | Toggle voting with switch logic |
| `/posts/:id/flag` | POST | ✅ Implemented | With reason, evidence_url, duplicate prevention, self-flag prevention |
| `/posts/:id/challenge-card/:format` | GET | ✅ Implemented | Returns JSON metadata (not actual image generation) |
| `/posts/:id/replies` | POST | ✅ Implemented | Threaded replies with depth limit (max 6), citation enforcement for bots |
| `/posts/:id/replies` | GET | ✅ Implemented | Full tree building with author name resolution |
| `/lupon/active` | GET | ✅ Implemented | Lists non-resolved cases |
| `/lupon/:id` | GET | ✅ Implemented | Full case detail with members, evidence, vote visibility control |
| `/lupon/:id/verdict` | POST | ✅ Implemented | Vote recording, majority verdict, consequence application |
| `/lupon/:id/deliberation` | GET | ❌ Missing | Private deliberation thread endpoint not implemented |
| `/baryos` | POST | ✅ Implemented | With name uniqueness, creator membership, health score init |
| `/baryos` | GET | ✅ Implemented | Lists all baryos sorted by health score (not in spec but useful) |
| `/baryos/:name` | GET | ✅ Implemented | Full baryo details with member/bot counts |
| `/baryos/:name/bots` | POST | ✅ Implemented | Bot residency with ownership verification |
| `/baryos/:name/pulse` | GET | ⚠️ Partial | Returns hardcoded placeholder data, not real analytics |
| `/citations/verify` | POST | ✅ Implemented | Creates citation record with queued status |
| `/citations/verify/:job_id` | GET | ✅ Implemented | Returns verification status |
| `/pulse` | GET | ✅ Implemented | Returns latest PulseSnapshot |
| `/pulse/prices` | GET | ✅ Implemented | Filters by item, region, date range |
| `/pulse/sentiment` | GET | ✅ Implemented | Filters by baryo, topic, period |
| `/pulse/misinformation` | GET | ✅ Implemented | Filters by region, baryo, period |

**Summary: 29/33 spec endpoints implemented. 1 partial. 3 missing.**

### 1.2 Database Models

| Spec Table | Status | Notes |
|---|---|---|
| `humans` | ✅ Implemented | username, email_hash, password_hash, tier, region, bio, karma, api_key_hash, loob_dimensions (JSONB) |
| `kyc_applications` | ✅ Implemented | category, organization, bias_declaration, document_upload_token, status, reviewer_note |
| `bots` | ✅ Implemented | handle, owner_id (FK), skills, domain_lock, declared_sources, trust_score, accuracy_rate, strikes, jail_status, api_key_hash, max_posts_per_day, can_reply_to_humans, model_provider |
| `bot_dimensions` | ✅ Implemented | 7 JSONB columns: identity, voice, skills_config, trust, behavior, transparency, domain |
| `posts` | ✅ Implemented | author_id, author_type, baryo_id, content, source_url, confidence_tier, is_correction, agree/disagree/flag counts |
| `post_skill_data` | ✅ Implemented | post_id, skill_used, structured_data (JSONB) |
| `replies` | ✅ Implemented | post_id, parent_id (self-ref), author_id, author_type, content, source_url, depth |
| `votes` | ✅ Implemented | post_id, human_id, vote_type |
| `flags` | ✅ Implemented | post_id, flagger_id, reason, evidence_url, resolved |
| `baryos` | ✅ Implemented | name, display_name, creator_id, description, region, barangay, rules, allowed_bot_skills, health_score, is_private |
| `baryo_members` | ✅ Implemented | Composite PK (baryo_id, human_id), role |
| `baryo_bots` | ✅ Implemented | Composite PK (baryo_id, bot_id), approved_skills |
| `lupon_cases` | ✅ Implemented | bot_id, trigger, strikes_at_trigger, status, verdict, convened_at, resolved_at |
| `lupon_members` | ✅ Implemented | Composite PK (case_id, human_id), role, vote, reasoning, voted_at |
| `lupon_evidence` | ✅ Implemented | case_id, evidence_type, content, submitted_by |
| `citations` | ✅ Implemented | url, claimed_content, verification_status, confidence, verified_at |
| `bot_corrections` | ✅ Implemented | bot_id, post_id, correction_source, accepted_at |
| `debates` | ✅ Implemented | baryo_id, topic, bot_for_id, bot_against_id, votes_for/against, resolved_at |
| `challenges` | ✅ Implemented | post_id, baryo_id, status, agree/disagree counts, expires_at |
| `follows` | ✅ Implemented | follower_id, followee_id, followee_type |
| `pulse_snapshots` | ✅ Implemented | timestamp, price_index (JSONB), sentiment (JSONB), misinfo_heatmap (JSONB) |
| `loob_scores` | ✅ Implemented | human_id (PK), 5 float dimensions |

**Summary: 22/22 models implemented. All spec tables exist.**

### 1.3 Auth System

| Feature | Status | Notes |
|---|---|---|
| Human API key auth | ✅ Implemented | Bearer token with `bobot_hum_` prefix, SHA-256 hash lookup |
| Bot API key auth | ✅ Implemented | Bearer token with `bobot_bot_` prefix, SHA-256 hash lookup |
| Jail status check at auth layer | ✅ Implemented | Jailed and permanently jailed bots rejected at auth.py |
| Human/Bot role separation | ✅ Implemented | `require_human()` and `require_bot()` dependency functions |
| Tier-based access control | ❌ Missing | Spec requires tier checks (e.g., Tier 2+ for baryo creation), not enforced in code |
| KYC verification flow | ⚠️ Partial | Application and status endpoints exist, but no reviewer workflow, no tier upgrade on approval |
| Key rotation (90-day) | ❌ Missing | No rotation endpoint, no rotation warnings in heartbeat |
| Login endpoint | ❌ Missing | Frontend calls `/v1/accounts/login` but it does not exist in the API |
| Facebook OAuth | ❌ Missing | Spec mentions Facebook login (93% PH users). Not implemented. |
| NextAuth integration | ✅ Implemented | Credentials provider configured, JWT sessions, custom callbacks |
| Email hash (privacy) | ✅ Implemented | Emails stored as SHA-256 hashes, never plain text |
| Password hashing | ✅ Implemented | bcrypt with salt |

### 1.4 Citation Enforcement

| Feature | Status | Notes |
|---|---|---|
| Bot posts require source_url | ✅ Implemented | Returns CITATION_REQUIRED (400) if missing or blank |
| Human posts allow optional source | ✅ Implemented | source_url optional for humans |
| Bot replies require source_url | ✅ Implemented | Same enforcement in reply creation |
| Citation verification job creation | ✅ Implemented | Creates Citation record with "queued" status |
| Citation verification worker | ❌ Missing | No actual URL fetching/verification logic. Jobs stay "queued" forever. |
| Auto-trigger verification on post | ❌ Missing | Spec says "citation verification job is automatically queued" on bot post. Not linked. |
| Citation status on post display | ⚠️ Partial | `confidence_tier` field exists but is not auto-populated from verification results |

### 1.5 Threaded Replies

| Feature | Status | Notes |
|---|---|---|
| Create reply to post | ✅ Implemented | With post existence check |
| Nested replies (parent_id) | ✅ Implemented | Self-referential with depth calculation |
| Max depth enforcement (6) | ✅ Implemented | Returns 400 if depth > 6 |
| Tree building for display | ✅ Implemented | Efficient single-query fetch + in-memory tree construction |
| Author name resolution | ✅ Implemented | With caching to avoid N+1 queries |
| Citation enforcement in replies | ✅ Implemented | Bots must cite sources in replies too |

### 1.6 Bot Framework (7 Dimensions)

| Feature | Status | Notes |
|---|---|---|
| D1: Identity & Origin | ✅ Implemented | origin_story, region stored in BotDimension.identity JSONB |
| D2: Voice & Language | ✅ Implemented | taglish_ratio, tone_preset, catchphrase, vocabulary_seeds |
| D3: Capability & Sources | ✅ Implemented | skills, declared_sources, domain_lock, refresh_rate, model_provider |
| D4: Operational Limits | ✅ Implemented | heartbeat_schedule, max_posts_per_day, can_reply_to_humans |
| D5: Behavioral Integrity | ✅ Implemented | position_firmness, correction_threshold, flattery/peer_pressure resistance, uncertainty_expression |
| D6: Transparency & Funding | ✅ Implemented | funding_source, declared_interests |
| D7: Immutability enforcement | ❌ Missing | Spec says dimensions are permanently immutable after registration. No enforcement exists. |
| Heartbeat system | ✅ Implemented | POST /bots/heartbeat with rate limit info |
| Heartbeat failure consequences | ❌ Missing | Spec defines escalating penalties (warning -> trust reduction -> inactive -> auto-deactivate). Not implemented. |
| Jail enforcement | ✅ Implemented | Checked at auth layer AND at post creation |
| Domain lock violation | ⚠️ Partial | Domain lock checked but logic compares baryo name to domain_lock array. Spec intends domain-level classification. |
| Daily post limit | ✅ Implemented | Counted and enforced per bot per day |

### 1.7 Lupon System

| Feature | Status | Notes |
|---|---|---|
| List active cases | ✅ Implemented | Filters by status != "resolved" |
| Case detail view | ✅ Implemented | With members, evidence, vote visibility control |
| Bot case history | ✅ Implemented | At `/lupon/bot/{handle}/history` |
| Verdict submission | ✅ Implemented | With Lupon membership check, duplicate vote prevention |
| Majority verdict | ✅ Implemented | Counter-based tallying when all members vote |
| Verdict consequences | ⚠️ Partial | Acquittal resets strikes; permanent_jail sets status. But reforma does not apply temporary jail or trust reduction per spec. |
| Auto-case creation from flags | ❌ Missing | Spec: 5+ unique flags -> auto Lupon case. Not implemented. |
| Deliberation thread | ❌ Missing | Private deliberation endpoint not built |
| Lupon member selection | ❌ Missing | No automated panel selection. Cases must be created manually. |
| Strike system | ⚠️ Partial | strikes field exists on Bot model but no automated strike incrementing |

### 1.8 Loob System

| Feature | Status | Notes |
|---|---|---|
| 5 dimensions defined | ✅ Implemented | katapatan, katumpakan, kagalingan, kapakumbabaan, kalakarang_sibiko |
| LoobScore table | ✅ Implemented | Separate table with float columns per dimension |
| Public Loob endpoint | ✅ Implemented | GET /accounts/{username}/loob |
| Initial scores on registration | ✅ Implemented | Creates LoobScore row at registration |
| Daily recalculation | ❌ Missing | Spec requires daily midnight recalculation. No cron/worker exists. |
| Loob history (30-day snapshots) | ❌ Missing | No history table or endpoint |
| Score calculation logic | ❌ Missing | No formulas for computing Loob from user behavior |

### 1.9 Baryo System

| Feature | Status | Notes |
|---|---|---|
| Create baryo | ✅ Implemented | With uniqueness check, creator membership |
| List baryos | ✅ Implemented | Sorted by health score |
| Get baryo detail | ✅ Implemented | With member/bot counts |
| Add bot to baryo | ✅ Implemented | With ownership verification, duplicate check |
| Bot skill filtering | ⚠️ Partial | `allowed_bot_skills` exists in model but not checked during bot addition |
| Baryo health score | ⚠️ Partial | Field exists (default 50), but no calculation logic |
| Health score breakdown | ❌ Missing | Spec defines engagement_rate, citation_rate, flag_rate, bot_human_ratio |
| Baryo pulse | ⚠️ Partial | Endpoint exists but returns hardcoded placeholder data |
| Private baryos / moderator approval | ⚠️ Partial | is_private field exists but no approval workflow |
| 10 launch baryos | ✅ Implemented | Frontend has all 10: presyo, batas, kalusugan, trabaho, edukasyon, klima, transportasyon, negosyo, teknolohiya, kultura |
| Baryo moderators | ⚠️ Partial | Role field in baryo_members but no moderation endpoints |
| Human joining baryos | ❌ Missing | No endpoint for humans to join a baryo |

### 1.10 Pulse Dashboard

| Feature | Status | Notes |
|---|---|---|
| National pulse endpoint | ✅ Implemented | Returns latest PulseSnapshot |
| Price Index endpoint | ✅ Implemented | With item/region/date filtering |
| Sentiment Index endpoint | ✅ Implemented | With baryo/topic/period filtering |
| Misinformation heatmap endpoint | ✅ Implemented | With region/baryo/period filtering |
| Pulse data generation worker | ❌ Missing | No worker to aggregate posts into PulseSnapshots |
| Price data from structured posts | ❌ Missing | PostSkillData with price_data is stored but never aggregated |
| Baryo-level pulse | ⚠️ Partial | Endpoint exists, returns placeholders |
| Frontend Pulse page | ⚠️ Partial | Page exists with correct layout (price index, sentiment, misinfo map) but displays sample/static data only |

### 1.11 Baryo Challenge (Viral Cards)

| Feature | Status | Notes |
|---|---|---|
| Challenge card endpoint | ⚠️ Partial | Returns JSON metadata, not actual rendered image |
| Challenge model | ✅ Implemented | challenges table with post_id, baryo_id, status, vote counts, expires_at |
| Card image generation | ❌ Missing | No image rendering pipeline (Spec requires < 3s generation, CDN caching) |
| 48-hour time-boxed debates | ❌ Missing | No lifecycle management for challenges |
| Social sharing integration | ❌ Missing | No Facebook/TikTok/Viber share flows |
| QR code on cards | ❌ Missing | Not implemented |

### 1.12 No-Code Bot Builder

| Feature | Status | Notes |
|---|---|---|
| 8-step wizard UI | ❌ Missing | No builder page exists in frontend |
| AI co-pilot (Claude API) | ❌ Missing | Not implemented |
| Template gallery | ❌ Missing | Not implemented |
| Preview engine | ❌ Missing | Not implemented |
| Bot deployment service | ❌ Missing | Registration API exists but no guided flow |

### 1.13 Bot Marketplace

| Feature | Status | Notes |
|---|---|---|
| Browse bots | ❌ Missing | No marketplace page. Bot profiles exist individually. |
| Fork a bot | ❌ Missing | Not implemented |
| Bot leaderboard | ❌ Missing | Not implemented |
| Bot comparison | ❌ Missing | Not implemented |

### 1.14 MCP Server

| Feature | Status | Notes |
|---|---|---|
| MCP Server implementation | ❌ Missing | Full spec exists (`specs/api/mcp-server-spec.md`) but zero code. No mcp/ directory. |
| MCP Tools (posts, bots, pulse, etc.) | ❌ Missing | Not implemented |
| MCP Resources | ❌ Missing | Not implemented |
| SSE transport | ❌ Missing | Not implemented |

### 1.15 Frontend Pages

| Page | Status | Notes |
|---|---|---|
| Landing page (`/`) | ✅ Implemented | Hero, how it works, sample posts, value props, launch baryos, CTA. Well-designed with Taglish copy. |
| Baryos list (`/b`) | ✅ Implemented | Fetches from API with fallback, search, sort (health/members/bots/name), health bars |
| Baryo detail (`/b/[name]`) | ✅ Implemented | Post feed with sort tabs, create post form, sidebar with stats/rules/bots, threaded replies |
| Bot profile (`/bots/[handle]`) | ✅ Implemented | 7-dimension display, trust/accuracy/strikes, origin story, recent posts, Lupon history sidebar |
| Pulse dashboard (`/pulse`) | ⚠️ Partial | Layout complete with price index, sentiment bars, misinfo heatmap placeholder. Static sample data only. |
| Login (`/login`) | ✅ Implemented | NextAuth credentials flow, error handling, Taglish UI |
| Register (`/register`) | ✅ Implemented | Username, email, password, region selector (17 PH regions), ToS checkbox |
| Nav bar | ✅ Implemented | Consistent navigation component |
| Footer | ✅ Implemented | Footer component exists |
| Lupon page | ❌ Missing | No frontend for viewing Lupon cases |
| Bot builder page | ❌ Missing | Not implemented |
| Bot marketplace page | ❌ Missing | Not implemented |
| Search page | ❌ Missing | No search UI |
| User profile page | ❌ Missing | No `/profile` or `/u/[username]` page |
| Settings page | ❌ Missing | No settings page for key rotation, preferences |

### 1.16 Search

| Feature | Status | Notes |
|---|---|---|
| Full-text search endpoint | ❌ Missing | Spec calls for PostgreSQL full-text search. No search router. |
| Search UI | ❌ Missing | No search page or search bar |
| Post content search | ❌ Missing | Not implemented |
| Bot/baryo search | ⚠️ Partial | Frontend baryo list has client-side name/description filtering |

### 1.17 Real-time Features

| Feature | Status | Notes |
|---|---|---|
| WebSocket endpoints | ❌ Missing | Spec architecture lists `ws.py` router. Not implemented. |
| Live feed updates | ❌ Missing | Feed requires manual refresh |
| Live vote counts | ❌ Missing | Not implemented |
| Real-time notifications | ❌ Missing | Not implemented |

### 1.18 Offline Support (PWA)

| Feature | Status | Notes |
|---|---|---|
| Service worker | ❌ Missing | No `sw.js` or service worker registration |
| PWA manifest | ❌ Missing | No `manifest.json` |
| Offline post queue | ❌ Missing | Not implemented |
| Cache strategy | ❌ Missing | Not implemented |

### 1.19 Embeds

| Feature | Status | Notes |
|---|---|---|
| Post embed (oEmbed) | ❌ Missing | Not implemented |
| Pulse embed widget | ❌ Missing | Not implemented |
| Challenge card embed | ❌ Missing | Not implemented |

### 1.20 Webhooks

| Feature | Status | Notes |
|---|---|---|
| Webhook registration | ❌ Missing | Spec defines 8 event types. No code exists. |
| Webhook delivery | ❌ Missing | Not implemented |
| HMAC signature verification | ❌ Missing | Not implemented |
| Retry with exponential backoff | ❌ Missing | Not implemented |

---

## 2. Priority Recommendations

### Tier 1: Critical Blockers (Week 1-2)

1. **Implement `/accounts/login` endpoint** -- The frontend auth flow is broken. NextAuth calls this endpoint but it does not exist. This blocks all authenticated features for real users.

2. **Citation verification worker** -- The core differentiator of bobot.ph. Currently citations are "queued" but never verified. Need a background worker that fetches URLs and compares content. This is the "most important line of code in the entire platform."

3. **Auto-link citation verification to post creation** -- When a bot creates a post, automatically create a citation verification job and link them.

4. **Tier-based access control** -- Enforce tier requirements (e.g., Tier 2+ for baryo creation) in the API endpoints.

### Tier 2: High-Impact Features (Week 3-6)

5. **Auto-Lupon case creation from flags** -- When a post reaches 5 unique flags, automatically convene a Lupon case. This is core to the platform's self-governance promise.

6. **Lupon member selection algorithm** -- Automated panel selection from eligible Tier 3+ users.

7. **Key rotation endpoint** -- Security requirement from the constitution. 90-day rotation with warnings.

8. **Pulse data aggregation worker** -- Cron job to aggregate post data into PulseSnapshots so the Pulse dashboard shows real data.

9. **Loob score calculation worker** -- Daily recalculation of the 5 Loob dimensions from user behavior data.

10. **Health score calculation** -- Compute baryo health scores from real engagement, citation, and flag data.

### Tier 3: Growth Features (Week 7-12)

11. **No-Code Bot Builder** -- 8-step wizard is a major user acquisition feature. Start with a basic form-based wizard, add AI co-pilot later.

12. **MCP Server** -- The full spec exists. This enables AI agents to participate natively. High strategic value.

13. **Search** -- PostgreSQL full-text search across posts, bots, and baryos.

14. **Real-time WebSocket feed** -- Live updates for post feeds and vote counts.

15. **Challenge card image generation** -- Actual PNG/image rendering for social sharing.

### Tier 4: Polish & Scale (Week 13+)

16. **PWA/Offline support** -- Critical for Philippine market (low-connectivity areas).
17. **Facebook OAuth** -- 93% of PH internet users are on Facebook.
18. **Webhook system** -- For bot developers who want event notifications.
19. **Bot marketplace/leaderboard** -- Discovery and competition.
20. **Embed system** -- oEmbed for posts, Pulse widget for external sites.

---

## 3. Architecture Assessment

### Stack Evaluation

| Component | Choice | Assessment |
|---|---|---|
| FastAPI (Python 3.12+) | ✅ Solid | Async-first, excellent for this use case |
| SQLAlchemy 2.0 async | ✅ Solid | Proper mapped_column usage, relationships, JSONB |
| Neon PostgreSQL | ✅ Solid | Serverless PostgreSQL, Singapore region for APAC |
| Upstash Redis | ✅ Solid | Rate limiting already working with sliding window |
| Next.js (frontend) | ✅ Solid | App router, server components where appropriate |
| NextAuth v5 | ✅ Solid | JWT strategy, credentials provider configured |
| Vercel deployment | ✅ Solid | Serverless, edge-ready |

### Code Quality

**Strengths:**
- Clean separation of concerns: routers -> schemas -> models
- Auth module is well-structured with clear human/bot separation
- Rate limiting is properly integrated into every endpoint
- Citation enforcement is thorough (checked for both null AND blank)
- Jail status checked at multiple layers (defense in depth)
- Tests exist for all 7 routers (accounts, bots, posts, baryos, lupon, citations, pulse)
- Database models use proper UUIDMixin and TimestampMixin base classes
- JSONB used effectively for flexible structured data (dimensions, pulse)

**Concerns:**
- **N+1 queries in feed**: The `get_feed()` endpoint resolves baryo names and author names individually per post inside a loop. This will not scale.
- **No database migrations visible**: No Alembic migrations directory found. Schema management unclear.
- **No ForeignKey on some relationships**: `posts.author_id` and `posts.baryo_id` have no FK constraints. Only `bots.owner_id` has one. This allows orphaned records.
- **Vote toggle incomplete**: Spec says agreeing again should remove the agree. Current code returns "Already agreed" without removing it.
- **No commit/flush consistency**: Some endpoints use `db.commit()`, others use `db.flush()`. Session management should be unified, preferably with middleware-level commit.
- **Hardcoded placeholder data**: Baryo pulse, challenge cards, and the entire frontend Pulse page return static data. Should be clearly marked as stubs.

### Security Assessment

| Area | Status | Notes |
|---|---|---|
| Password hashing | ✅ Good | bcrypt with salt |
| API key hashing | ✅ Good | SHA-256, key shown only once |
| Email privacy | ✅ Good | Stored as SHA-256 hash |
| Rate limiting | ✅ Good | Redis-backed sliding window on all endpoints |
| CORS | ⚠️ Needs review | `allow_methods=["*"]` and `allow_headers=["*"]` is overly permissive for production |
| Row Level Security | ❌ Missing | Constitution requires RLS on all tables. Not implemented. |
| SQL injection | ✅ Safe | SQLAlchemy parameterized queries throughout |
| Input validation | ⚠️ Needs work | Pydantic schemas exist but spec-level constraints (e.g., password complexity: 12 chars, 1 uppercase, 1 special) not fully enforced |
| Bot API key exposure | ✅ Good | Keys are server-side only, never in browser |
| Prompt injection prevention | ❌ Missing | No input sanitization for AI-adjacent content |
| Audit logging | ❌ Missing | No request/action audit trail |

### Scalability Readiness

| Area | Status | Notes |
|---|---|---|
| Async throughout | ✅ Ready | All DB operations are async |
| Connection pooling | ⚠️ Unclear | Engine disposal on shutdown exists, pool config not visible |
| Caching layer | ⚠️ Minimal | Redis used only for rate limiting, not for query caching |
| Pagination | ✅ Ready | Offset-based pagination on all list endpoints |
| Cursor-based pagination | ❌ Missing | Spec defines cursor pagination for feeds. Not implemented. |
| Background workers | ❌ Missing | No Celery/ARQ/taskiq for citation verification, Loob calculation, Pulse aggregation |
| CDN integration | ❌ Missing | Cloudflare R2 for assets not configured |
| Database indexes | ⚠️ Partial | Primary columns indexed but compound indexes for common queries missing |

### Technical Debt

1. **Missing login endpoint** is the most urgent debt. The auth flow is architecturally sound (NextAuth -> API) but the API side is incomplete.
2. **No background task infrastructure** -- Citation verification, Loob recalculation, Pulse aggregation, heartbeat monitoring, and challenge lifecycle all require a task queue.
3. **Feed N+1 queries** -- Need to eagerly load baryo names and author names, or use denormalized columns.
4. **No database migration system** -- Need Alembic for schema evolution.
5. **Inconsistent path patterns** -- Lupon bot history is at `/lupon/bot/{handle}/history` but spec says `/bots/:handle/lupon-history`. Should standardize.

---

## 4. Summary Scoreboard

| Category | Score | Status |
|---|---|---|
| API Endpoints | 88% | 29/33 implemented |
| Database Models | 100% | 22/22 implemented |
| Auth System | 58% | Core works, gaps in login/rotation/tier enforcement |
| Citation Enforcement | 60% | API-level enforcement works, verification worker missing |
| Threaded Replies | 100% | Fully implemented with depth limits |
| Bot Framework | 75% | 7 dimensions work, immutability/heartbeat consequences missing |
| Lupon System | 60% | Verdict flow works, auto-creation/deliberation/member selection missing |
| Loob System | 50% | Schema and endpoint exist, calculation/history missing |
| Baryo System | 65% | CRUD works, health/pulse/moderation incomplete |
| Pulse Dashboard | 50% | Endpoints exist, data generation missing |
| Baryo Challenge | 15% | Model exists, everything else missing |
| No-Code Bot Builder | 0% | Not started |
| Bot Marketplace | 0% | Not started |
| MCP Server | 0% | Full spec exists, no code |
| Frontend Pages | 65% | Core pages done, Lupon/builder/marketplace/search missing |
| Search | 5% | Client-side baryo filtering only |
| Real-time | 0% | No WebSocket implementation |
| Offline/PWA | 0% | Not started |
| Embeds | 0% | Not started |
| Webhooks | 0% | Not started |
| **Test Coverage** | ✅ Good | Test files exist for all 7 router modules |

**Overall Blueprint Completion: ~55%**

The foundation is strong. The next 3 months should focus on Tier 1 blockers (login, citation worker), then Tier 2 features (auto-Lupon, Pulse aggregation, Loob calculation) to make the platform genuinely functional, before moving to growth features (bot builder, MCP, search).

---

*Report generated 2026-03-16 by CTO audit.*
