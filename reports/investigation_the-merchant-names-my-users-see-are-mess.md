# Investigation: merchant-name quality

**Complaint:** "the merchant names my users see are messy and often blank"

**Routed to:** merchant-name errors  |  **Scope:** 55 transactions

**Headline:** merchant-name accuracy in scope is **51%** (27 of 55 wrong).

## Error clusters, ranked by impact (volume x confidently-wrong)

| Rank | Root cause | Errors | % of errors | Mean conf | Impact |
|---|---|---|---|---|---|
| 1 | `coverage_gap` | 27 | 100% | 0.24 | 19.9 |

## Fix this first: `coverage_gap`

It is 100% of the errors in scope, and the system was 24% confident while wrong, so these reach customers.

Examples: `SQ *RAINBOW NAILS & SPA`, `DD *DOORDASH SUSHIYA`, `UBER EATS`

**Recommendation:** The merchant was not resolved at all (blank/Unknown). This is a knowledge-base coverage gap, not a parsing bug. Add these merchants to the KB or fall back to a cleaned descriptor string rather than emitting nothing.

## All recommendations

- **`coverage_gap`** (27 errors): The merchant was not resolved at all (blank/Unknown). This is a knowledge-base coverage gap, not a parsing bug. Add these merchants to the KB or fall back to a cleaned descriptor string rather than emitting nothing.