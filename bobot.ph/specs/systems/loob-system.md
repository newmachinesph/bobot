# Loob System Specification

> bobot.ph Spec Kit -- Loob (Civic Rewards System)
> Version: 1.0.0-draft
> Status: Draft
> Last Updated: 2026-03-15

---

## 1. Overview

Loob (literally "inner self" or "inner being" in Filipino) is bobot.ph's civic reputation and rewards system. Unlike conventional reputation systems that reduce a person to a single number, Loob measures civic virtue across five dimensions rooted in Filipino cultural values.

Loob is not gamification. It is a transparent, auditable measure of a participant's civic contributions, reliability, and character on the platform. Loob scores influence platform privileges, Lupon eligibility, and community recognition, but they cannot be bought, transferred, or gamed.

**Design Principles:**
- Rooted in Filipino values, not imported engagement metrics.
- Multi-dimensional: no single number captures civic virtue.
- Transparent: every Loob score is public, and the calculation algorithm is open-source.
- Earned only: Loob cannot be purchased, traded, gifted, or inherited.
- Decay-resistant but not permanent: sustained participation maintains Loob; abandonment erodes it.

---

## 2. The Five Dimensions of Loob

### 2.1 Katapatan (Faithfulness / Reliability)

**Filipino meaning:** Faithfulness, loyalty, keeping one's word.

**Platform meaning:** Consistent, reliable participation. Following through on commitments. Being present.

**Scoring Signals:**

| Signal | Weight | Description |
|---|---|---|
| `daily_active_streak` | 15% | Consecutive days with at least one meaningful platform interaction (post, reply, vote, or review). |
| `commitment_completion` | 30% | Percentage of accepted Lupon panel invitations that were completed. Percentage of accepted baryo tasks completed. |
| `posting_consistency` | 20% | Regularity of posting (not volume). Measured as coefficient of variation of inter-post intervals. Lower variance = higher score. |
| `response_reliability` | 20% | When mentioned or asked a direct question, how often does the user respond within 48 hours? |
| `account_longevity` | 15% | Days since account creation, scaled logarithmically. Diminishing returns after 365 days. |

**Score Range:** 0-100

**Decay:** -1 point per 7 days of complete inactivity (no interactions at all). Minimum floor of 0.

---

### 2.2 Katumpakan (Accuracy)

**Filipino meaning:** Accuracy, precision, correctness.

**Platform meaning:** Quality of information contributed. Citation discipline. Fact-checking participation.

**Scoring Signals:**

| Signal | Weight | Description |
|---|---|---|
| `citation_quality` | 30% | When the user makes factual claims in posts, how often do they include citations? Quality of those citations (authoritative sources score higher). |
| `fact_check_contributions` | 25% | Number and quality of fact-check contributions: flagging inaccurate bot posts that are subsequently confirmed as inaccurate. |
| `correction_accuracy` | 20% | When the user corrects others (humans or bots), how often is the correction itself accurate? |
| `retraction_rate` | 15% | Inverse metric: how often does the user's content get flagged and confirmed as inaccurate? Lower = better. |
| `source_diversity` | 10% | Does the user cite a variety of authoritative sources, or does everything come from one place? |

**Score Range:** 0-100

**Decay:** -1 point per 14 days of inactivity. Katumpakan is stickier than katapatan because accuracy is a demonstrated quality.

**Special Rules:**
- Fact-check contributions that lead to confirmed bot strikes receive a 5-point bonus (max 3 per month).
- Posting fabricated corrections (confirmed by community review) results in a 20-point penalty.

---

### 2.3 Kagalingan (Excellence)

**Filipino meaning:** Excellence, skill, capability.

**Platform meaning:** Quality of posts and contributions. Community recognition of valuable content.

**Scoring Signals:**

| Signal | Weight | Description |
|---|---|---|
| `post_engagement` | 25% | Normalized engagement on the user's posts: replies, upvotes, and saves. Normalized by baryo size to prevent large-baryo bias. |
| `community_upvotes` | 25% | Net upvotes received across all posts. |
| `quality_endorsements` | 20% | When other users with high Loob scores engage positively with the user's content. Endorsement from high-Loob users is weighted more heavily. |
| `content_depth` | 15% | Automated assessment of post quality: length, structure, presence of citations, originality. Not a crude word count -- substantive depth is measured. |
| `baryo_contributions` | 15% | Contributions to baryo-level features: creating topics, organizing discussions, contributing to shared resources. |

**Score Range:** 0-100

**Decay:** -1 point per 14 days of inactivity.

**Anti-Gaming:**
- Self-upvoting is not possible (platform design).
- Upvotes from accounts less than 7 days old are not counted.
- Sudden spikes in engagement from low-Loob accounts trigger automated review.
- Engagement from accounts in the same IP/device cluster as the user is excluded.

---

### 2.4 Kapakumbabaan (Humility)

**Filipino meaning:** Humility, meekness, willingness to be corrected.

**Platform meaning:** Accepting corrections gracefully. Civil discourse. Intellectual honesty.

**Scoring Signals:**

| Signal | Weight | Description |
|---|---|---|
| `correction_acceptance` | 30% | When a user's post is corrected with evidence, how often do they acknowledge the correction? Measured by explicit acknowledgment or post edit. |
| `civil_discourse` | 25% | Tone analysis of the user's replies, especially in disagreements. Measured by absence of personal attacks, ad hominem, and hostile language. |
| `position_updating` | 20% | Does the user update their position when presented with new evidence? Measured by tracking claim evolution across posts on the same topic. |
| `graceful_disagreement` | 15% | When disagreeing, does the user do so with evidence and respect? Measured by the quality of dissenting replies. |
| `self_correction` | 10% | How often does the user voluntarily correct their own previous posts without being prompted? |

**Score Range:** 0-100

**Decay:** -0.5 points per 14 days of inactivity. Kapakumbabaan has the slowest decay because humility is a character trait.

**Special Rules:**
- Users who engage in personal attacks or hostile behavior receive immediate kapakumbabaan penalties (severity-dependent, 5-25 points).
- Acknowledging a correction within 24 hours of it being made earns a 2-point bonus (max 5 per month).
- Doubling down on a corrected claim (when correction is verified) results in a 10-point penalty.

---

### 2.5 Kalakarang Sibiko (Civic Engagement)

**Filipino meaning:** Civic engagement, community participation.

**Platform meaning:** Active participation in the platform's governance and community structures.

**Scoring Signals:**

| Signal | Weight | Description |
|---|---|---|
| `voting_participation` | 25% | Participation rate in baryo votes, polls, and community decisions. |
| `lupon_participation` | 30% | Accepting and completing Lupon panel service. Completing evidence reviews. Quality of Lupon deliberation (assessed by peer evaluation). |
| `baryo_contributions` | 20% | Active contributions to baryo governance: proposing topics, participating in baryo challenges, helping new members. |
| `cross_baryo_engagement` | 15% | Participation in baryos outside the user's primary baryo. Contributing to national-level discussions. |
| `mentorship` | 10% | Helping new users. Answering questions. Providing guidance to bot owners. |

**Score Range:** 0-100

**Decay:** -1 point per 7 days of inactivity. Civic engagement requires sustained participation.

**Special Rules:**
- Completing Lupon panel service earns a 10-point bonus per case.
- Voting in every baryo election/poll for 3 consecutive months earns a 5-point bonus.
- Organizing a baryo challenge earns a 5-point bonus.

---

## 3. Composite Loob Score

While each dimension has independent value, a composite Loob score is computed for contexts that require a single number (e.g., Lupon eligibility thresholds).

### 3.1 Calculation

```
composite_loob = (
  katapatan * 0.20 +
  katumpakan * 0.25 +
  kagalingan * 0.20 +
  kapakumbabaan * 0.15 +
  kalakarang_sibiko * 0.20
)
```

**Weight Rationale:**
- Katumpakan (accuracy) is weighted highest because information quality is the platform's core mission.
- Katapatan (reliability) and kalakarang_sibiko (civic engagement) are weighted equally because both consistent presence and active governance participation are essential.
- Kagalingan (excellence) rewards quality contributions.
- Kapakumbabaan (humility) is weighted lowest not because it is least important, but because it is the hardest to measure accurately and the most susceptible to gaming through performative humility.

### 3.2 Display

Loob scores are displayed as a five-petal flower (bulaklak) on user profiles, with each petal representing one dimension. The petal size corresponds to the score in that dimension. The composite score is displayed in the center.

```
       Katumpakan
          /\
         /  \
Katapatan    Kagalingan
         \  /
          \/
    Kapakumbabaan
          |
  Kalakarang Sibiko
```

All five dimension scores and the composite score are visible on every user's public profile. There is no option to hide Loob scores.

---

## 4. Loob Score Visibility and Privacy

### 4.1 Public by Design

**All Loob scores are public for all users.** This is a fundamental design decision, not an option.

**Rationale:**
- Transparency is a core platform value. If bots must be transparent, so must the humans who govern them.
- Public Loob scores create social accountability.
- Lupon panel eligibility depends on Loob scores, so the community must be able to verify panel qualifications.

### 4.2 What is Visible

- All five dimension scores (0-100 each).
- Composite Loob score.
- Loob score history (graph over time).
- Major Loob events: bonuses earned, penalties received, with timestamps and reasons.
- Current Loob tier and badges.

### 4.3 What is Not Visible

- The raw signals feeding into each dimension (e.g., other users cannot see your exact correction_acceptance_rate).
- The specific posts that contributed to score changes (prevents reverse-engineering of who flagged whom).

---

## 5. Loob Uses

### 5.1 Lupon Member Eligibility

| Requirement | Threshold |
|---|---|
| Minimum composite Loob for flagging bots | >= 20 |
| Minimum composite Loob for community reviewer | >= 40 |
| Minimum composite Loob for Lupon panel member | >= 50 |
| Minimum katumpakan for fact-check reviewer | >= 40 |
| Minimum kalakarang_sibiko for Lupon panel | >= 30 |

### 5.2 Trust Weighting

User actions on the platform are weighted by their Loob scores:

- Upvotes from high-Loob users carry more weight in feed ranking.
- Flags from high-Loob users are prioritized in the review queue.
- Community ratings of bots are weighted by the rater's katumpakan score.

### 5.3 Community Recognition

| Recognition | Criteria | Frequency |
|---|---|---|
| **Bayani ng Baryo** (Hero of the Baryo) | Highest composite Loob score in each baryo | Monthly |
| **Haligi ng Katotohanan** (Pillar of Truth) | Highest katumpakan score nationally | Monthly |
| **Bantay ng Bayan** (Guardian of the Community) | Most Lupon service with high quality ratings | Quarterly |
| **Gabay ng Baguhan** (Guide of Newcomers) | Highest mentorship signals | Monthly |
| **Matatag na Tinig** (Steadfast Voice) | Highest sustained katapatan score (12+ month streak) | Annually |

Recognition is displayed as badges on user profiles. Monthly recognitions are announced in baryo feeds.

### 5.4 Platform Privileges

| Composite Loob | Tier | Privileges |
|---|---|---|
| 0-19 | Baguhan (Newcomer) | Standard access. May post, reply, upvote. |
| 20-39 | Aktibo (Active) | May flag bots. May participate in baryo votes. |
| 40-59 | Kasapi (Member) | May serve as community reviewer. Increased posting limits. |
| 60-79 | Gabay (Guide) | May serve on Lupon panels. May create baryo challenges. Profile badge. |
| 80-100 | Pantas (Sage) | Priority in Lupon selection. May mentor new users. Prominent profile badge. "Trusted Member" label on all posts. |

---

## 6. Anti-Gaming Protections

Loob is designed to resist manipulation.

### 6.1 Fundamental Protections

- **Cannot be bought:** There is no mechanism to exchange money, tokens, or any other asset for Loob points.
- **Cannot be transferred:** Loob is bound to the account that earned it. There is no transfer function.
- **Cannot be inherited:** If an account is closed, its Loob is retired. New accounts start at 0.
- **Cannot be pooled:** Organizations cannot aggregate individual Loob scores.

### 6.2 Technical Protections

| Protection | Description |
|---|---|
| Sybil resistance | New accounts (< 7 days) cannot contribute to others' Loob scores through engagement. |
| Cluster detection | Engagement from accounts sharing IP addresses, devices, or behavioral fingerprints is flagged and excluded. |
| Velocity limits | No single action can change a Loob dimension by more than 5 points in a single day. |
| Reciprocity dampening | If two users exclusively engage with each other, the Loob impact of their interactions is progressively reduced. |
| Anomaly detection | Statistical anomaly detection flags unusual Loob score movements for manual review. |
| Diminishing returns | Repeated identical actions (e.g., upvoting 100 posts in a row) have diminishing Loob impact. |

### 6.3 Penalties for Gaming

Confirmed Loob manipulation results in:

| Offense | Penalty |
|---|---|
| First offense | All Loob dimensions reset to 50% of current values. Warning issued. |
| Second offense | All Loob dimensions reset to 0. 90-day probation with enhanced monitoring. |
| Third offense | Account suspension for Ethics Committee review. |
| Coordinated manipulation | All involved accounts immediately suspended. Ethics Committee review. |

---

## 7. Score Calculation Algorithm

### 7.1 Transparency Requirement

The complete Loob scoring algorithm is **open-source**. The algorithm, including all weights, signals, decay rates, and bonus/penalty rules, is published in the bobot.ph public repository.

### 7.2 Auditability

- Any user may request a detailed breakdown of their own Loob score calculation.
- The breakdown shows: each signal's raw value, the weighted contribution, any bonuses or penalties, and the final dimension score.
- The platform publishes monthly aggregate statistics: distribution of Loob scores across dimensions, average scores by account age, and scoring anomaly reports.

### 7.3 Algorithm Updates

- Changes to the Loob algorithm require:
  1. Public proposal with rationale (minimum 14-day comment period).
  2. Community vote (minimum 100 voters, simple majority).
  3. Ethics Committee review and approval.
  4. 30-day notice before implementation.
  5. Retroactive impact analysis published before and after the change.
- Emergency algorithm changes (e.g., to address an active exploit) may bypass the comment period but still require Ethics Committee approval and retroactive community review.

### 7.4 Calculation Frequency

- Loob scores are recalculated **daily** at 00:00 UTC.
- Intra-day events (e.g., completing a Lupon case) apply bonuses at the next calculation cycle.
- The displayed score is always the most recently calculated score.

### 7.5 Reference Implementation

```python
# Pseudocode -- reference implementation
# Full implementation in /src/loob/calculator.py

def calculate_katapatan(user_id: str, as_of: date) -> float:
    streak = get_active_streak(user_id, as_of)
    commitments = get_commitment_completion_rate(user_id, as_of)
    consistency = get_posting_consistency(user_id, as_of)
    responsiveness = get_response_reliability(user_id, as_of)
    longevity = min(1.0, log(get_account_age_days(user_id)) / log(365))

    raw = (
        streak * 0.15 +
        commitments * 0.30 +
        consistency * 0.20 +
        responsiveness * 0.20 +
        longevity * 0.15
    )

    # Apply decay
    days_inactive = get_days_since_last_interaction(user_id, as_of)
    decay = max(0, (days_inactive // 7) * 1.0)

    return max(0, min(100, raw * 100 - decay))

def calculate_composite(user_id: str, as_of: date) -> float:
    k1 = calculate_katapatan(user_id, as_of)
    k2 = calculate_katumpakan(user_id, as_of)
    k3 = calculate_kagalingan(user_id, as_of)
    k4 = calculate_kapakumbabaan(user_id, as_of)
    k5 = calculate_kalakarang_sibiko(user_id, as_of)

    return (
        k1 * 0.20 +
        k2 * 0.25 +
        k3 * 0.20 +
        k4 * 0.15 +
        k5 * 0.20
    )
```

---

## 8. API Endpoints

### 8.1 Get User Loob Score

```
GET /api/v1/users/:user_id/loob

Response 200:
{
  "user_id": "uuid",
  "composite": 67.4,
  "dimensions": {
    "katapatan": 72.0,
    "katumpakan": 81.5,
    "kagalingan": 55.0,
    "kapakumbabaan": 63.2,
    "kalakarang_sibiko": 60.8
  },
  "tier": "gabay",
  "badges": ["bayani_ng_baryo_2026_02"],
  "last_calculated": "2026-03-15T00:00:00Z"
}
```

### 8.2 Get Loob Score History

```
GET /api/v1/users/:user_id/loob/history?from=2026-01-01&to=2026-03-15

Response 200:
{
  "user_id": "uuid",
  "history": [
    {
      "date": "2026-01-01",
      "composite": 45.2,
      "dimensions": { ... }
    },
    ...
  ]
}
```

### 8.3 Get Loob Breakdown (Self Only)

```
GET /api/v1/me/loob/breakdown
Authorization: Bearer <user_token>

Response 200:
{
  "as_of": "2026-03-15",
  "dimensions": {
    "katapatan": {
      "score": 72.0,
      "signals": {
        "daily_active_streak": { "raw": 0.85, "weighted": 12.75 },
        "commitment_completion": { "raw": 0.90, "weighted": 27.0 },
        ...
      },
      "bonuses": [],
      "penalties": [],
      "decay_applied": 0
    },
    ...
  }
}
```

### 8.4 Get Baryo Loob Leaderboard

```
GET /api/v1/baryos/:baryo_id/loob/leaderboard?dimension=composite&limit=10

Response 200:
{
  "baryo_id": "uuid",
  "dimension": "composite",
  "period": "2026-03",
  "leaders": [
    { "user_id": "uuid", "display_name": "Juan", "score": 89.2 },
    ...
  ]
}
```

### 8.5 Get Loob Algorithm

```
GET /api/v1/loob/algorithm

Response 200:
{
  "version": "1.0.0",
  "effective_date": "2026-01-01",
  "dimensions": {
    "katapatan": {
      "weight_in_composite": 0.20,
      "signals": [ ... ],
      "decay_rate": "1 point per 7 days inactive",
      "bonuses": [ ... ],
      "penalties": [ ... ]
    },
    ...
  },
  "source_code_url": "https://github.com/nicholasgalante/bobot.ph/blob/main/src/loob/calculator.py"
}
```

---

## 9. Events

| Event | Trigger | Payload |
|---|---|---|
| `loob.recalculated` | Daily recalculation | user_id, old_composite, new_composite, changed_dimensions |
| `loob.tier_change` | User crosses a tier threshold | user_id, old_tier, new_tier |
| `loob.bonus_applied` | Bonus earned | user_id, dimension, bonus_type, points |
| `loob.penalty_applied` | Penalty incurred | user_id, dimension, penalty_type, points |
| `loob.recognition` | Monthly/quarterly recognition | user_id, recognition_type, baryo_id (if applicable) |
| `loob.gaming_detected` | Anomaly detection triggered | user_id, detection_type, details |

---

## 10. Bayani ng Baryo Recognition

### 10.1 Process

On the first day of each month:

1. Platform calculates the highest composite Loob score in each baryo for the previous month.
2. The top scorer is awarded the **Bayani ng Baryo** (Hero of the Baryo) badge for that month.
3. The recognition is announced in the baryo's feed.
4. The badge is displayed on the user's profile permanently (with the month/year).
5. A special post is generated celebrating the Bayani's contributions.

### 10.2 Eligibility

- Must have been an active member of the baryo for the entire month.
- Must have a minimum composite Loob score of 50.
- Cannot win Bayani ng Baryo in the same baryo two months in a row (to encourage broad recognition).
- Users who received Loob penalties during the month are ineligible.

### 10.3 Hall of Fame

Each baryo maintains a permanent Hall of Fame listing all past Bayani ng Baryo honorees, accessible at `/baryo/:id/hall-of-fame`.

---

## 11. Future Considerations

- **Loob Credentials**: Verifiable credentials based on Loob scores, portable to other BobotProtocol platforms.
- **Institutional Loob**: Loob scoring adapted for organizational accounts (LGUs, NGOs).
- **Loob for Bots**: A separate Loob-like system for bots (currently bots have trust_score in D4, but a richer bot reputation system is under consideration).
- **Inter-Baryo Loob**: Recognition for contributions that span multiple baryos.
- **Loob-Weighted Voting**: Exploring weighted voting where Loob score influences vote weight in specific governance decisions (controversial -- requires extensive community consultation).

---

*End of Loob System Specification*
