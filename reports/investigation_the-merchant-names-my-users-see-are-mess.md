# Investigation: merchant-name quality

**Complaint:** "the merchant names my users see are messy and often blank"

**Routed to:** merchant-name errors  |  **Scope:** 52 transactions

**Headline:** merchant-name accuracy in scope is **54%** (24 of 52 wrong).

## Error clusters, ranked by impact (volume x confidently-wrong)

| Rank | Root cause | Errors | % of errors | Mean conf | Impact |
|---|---|---|---|---|---|
| 1 | `coverage_gap` | 24 | 100% | 0.23 | 17.59 |

## Fix this first: `coverage_gap`

It is 100% of the errors in scope, and the system was 23% confident while wrong, so these reach customers.

Examples: `SQ *RAINBOW NAILS & SPA`, `DD *DOORDASH SUSHIYA`, `UBER EATS`

**Recommendation:** The merchant was not resolved at all (blank/Unknown). This is a knowledge-base coverage gap, not a parsing bug. Add these merchants to the KB or fall back to a cleaned descriptor string rather than emitting nothing.

## All recommendations

- **`coverage_gap`** (24 errors): The merchant was not resolved at all (blank/Unknown). This is a knowledge-base coverage gap, not a parsing bug. Add these merchants to the KB or fall back to a cleaned descriptor string rather than emitting nothing.