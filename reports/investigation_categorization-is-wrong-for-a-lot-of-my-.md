# Investigation: categorization quality

**Complaint:** "categorization is wrong for a lot of my users"

**Routed to:** categorization errors  |  **Scope:** 55 transactions

**Headline:** categorization accuracy in scope is **89%** (6 of 55 wrong).

## Error clusters, ranked by impact (volume x confidently-wrong)

| Rank | Root cause | Errors | % of errors | Mean conf | Impact |
|---|---|---|---|---|---|
| 1 | `coverage_gap` | 4 | 67% | 0.25 | 3.0 |
| 2 | `aggregator_masked` | 1 | 17% | 0.60 | 1.1 |
| 3 | `processor_prefix` | 1 | 17% | 0.60 | 1.1 |

## Fix this first: `coverage_gap`

It is 67% of the errors in scope, and the system was 25% confident while wrong, so these reach customers.

Examples: `CLAUDE.AI SUBSCRIPTION`, `RENT CAFE EPAY PROPERTYMGMT`, `EQUINOX FITNESS CLUB`

**Recommendation:** The merchant was not resolved at all (blank/Unknown). This is a knowledge-base coverage gap, not a parsing bug. Add these merchants to the KB or fall back to a cleaned descriptor string rather than emitting nothing.

## All recommendations

- **`coverage_gap`** (4 errors): The merchant was not resolved at all (blank/Unknown). This is a knowledge-base coverage gap, not a parsing bug. Add these merchants to the KB or fall back to a cleaned descriptor string rather than emitting nothing.
- **`aggregator_masked`** (1 errors): True merchant is unrecoverable from the descriptor (a platform masks it). Stop guessing the underlying merchant; label the platform and expose a lower-confidence flag so customers can handle it downstream.
- **`processor_prefix`** (1 errors): A payment-processor prefix is defeating merchant resolution. Extend the prefix-stripping rules to cover these processors before lookup.