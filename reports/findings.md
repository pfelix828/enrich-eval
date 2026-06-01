# EnrichEval — what the eval found

*Data note: all numbers below come from a 55-row seed of synthetic descriptors for real merchants,
scored by a deterministic rules enricher. They are a methodology demonstration, not production
quality. The point is the method, not the magnitude.*

## Summary

Moving the baseline enricher from v1 to v2 (adding aggregator awareness, a fuller merchant knowledge
base, more processor-prefix handling, and richer recurring cues) lifted every headline metric:

| Field | v1 | v2 |
|---|---|---|
| Merchant accuracy | 51% | 82% |
| Primary category | 62% | 91% |
| Detailed category | 60% | 89% |

(Recurring detection is intentionally left out of this headline table — see Finding 4 for why it
isn't a meaningful single-transaction score.)

But the averages hide five findings that actually shape a roadmap.

## Finding 1 — v1's merchant problem is coverage, not parsing

100% of v1's merchant errors are unresolved (blank/Unknown), not mis-parsed. Every miss is a
knowledge-base gap, concentrated in bills, loans, services, and travel — the categories a young
enricher hasn't gotten to yet. The fix is coverage, not smarter normalization. This is the kind of
conclusion that redirects a quarter of work, and it falls straight out of slicing errors by cause.

## Finding 2 — the confidence score is mis-calibrated, and unevenly

Merchant-confidence ECE is ~0.16, but the aggregate hides the real story (see
`figures/confidence_by_matchtype.png`):

- The **keyword** fallback path states ~0.40 confidence and is **0% accurate**. Badly overconfident.
  These are exactly the answers that should be suppressed or sent to review, and right now they look
  trustworthy.
- The **aggregator** path states 0.60 and is ~87% accurate. Underconfident, so good answers get
  hidden behind a low threshold.

A single global accuracy number would have surfaced neither. Calibration has to be read per
resolution path.

## Finding 3 — v2 improves the average but introduces a regression

The v1→v2 diff (see `regression_v1_to_v2.json`) shows 18 merchant improvements and **1 regression**:
`PYPL *STEAMGAMES` was correctly resolved to Steam (Entertainment / Video Games) in v1, but v2's new
aggregator rule sees the `PYPL` prefix and labels it PayPal (General Merchandise). The rule that
fixed many DoorDash/Uber-Eats rows over-applies here and masks a real merchant.

This is the entire reason a quality eval runs on every change: a net-positive release can still break
a specific, customer-visible case. A release gate keyed on per-row regressions catches it; a gate
keyed only on average accuracy ships it. (The expanded recurring-cue list in v2 caused a second,
smaller regression of the same kind — see Finding 4.)

## Finding 4 — recurring detection isn't a meaningful single-transaction metric

Recurrence is a property of a *series* of transactions, not a single string, so a system — or an
eval — that sees one line at a time cannot honestly measure it. That is why recurring is kept out of
the headline table: any F1 I quoted would mostly reflect how many cue-less cases I chose to put in the
seed (recall is roughly *easy positives / all positives* by construction), not real performance. It is
reported here as a failure-mode demonstration, not a score. The seed includes adversarial cases that
expose the ceiling:

- `EQUINOX FITNESS CLUB` and `NYTIMES NYTIMES.COM` are genuine subscriptions with no cue word and no
  KB entry, so the cue-based detector **misses** them (false negatives).
- `MONTHLY MARKET SF` is a one-off grocery run at a store named "Monthly Market"; the word *monthly*
  **wrongly trips** the recurring flag (false positive). This is also the v2 cue-list regression noted
  above: v1 didn't know the `MONTHLY` cue and got it right.

An earlier version of this eval reported recurring F1 = 1.0, which was a small-n artifact: the labels
and the detector were built from the same cue list. Adding cases the heuristic cannot solve replaced
a misleading perfect score with an honest one. The real fix is transaction history, not a cleverer
string rule.

## Finding 5 — "correct" needs a judge, and the judge needs validation

Exact-match alone would wrongly fail semantically-equal predictions (`Blue Bottle` vs
`Blue Bottle Coffee`). The merchant-equivalence judge was validated against 24 human-labeled pairs
before being allowed to relabel anything: **92% agreement, Cohen's κ = 0.83**. Its two residual blind
spots are honest and instructive: parent-vs-consumer brand (`Comcast`/`Xfinity`) and acronym
expansion (`BART`/`Bay Area Rapid Transit`), both of which need a brand-alias knowledge base or an
LLM judge. That κ is the bar any future judge has to clear.

## Recommended roadmap order

1. **Close the bills/services/travel coverage gap** (Finding 1) — biggest single block of errors.
2. **Suppress or review keyword-fallback answers** (Finding 2) — they are confidently wrong today.
3. **Add a regression gate on per-row flips** (Finding 3) — before shipping the next enricher version.
4. **Promote the aggregator rule carefully** (Finding 3) — it helps in aggregate but needs a guard so
   it doesn't swallow merchants that happen to be billed through a processor.

## How this maps to the role

Every section here is one of the job's responsibilities made concrete: defining the quality metric
(the rubric + tiered merchant matching), turning a vague complaint into a structured investigation
(the hook), measuring AI effectiveness in a principled way (judge validation + calibration), building
eval that scales (the regression gate), and influencing the roadmap with data (this document).
