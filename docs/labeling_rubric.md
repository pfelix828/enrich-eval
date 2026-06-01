# Labeling Rubric — Transaction Enrichment Gold Set

This rubric defines what "correct" means for the enrichment system under test. It is the
reference an annotator uses to assign ground-truth labels, and it is itself a deliverable:
defining quality precisely is half the job of measuring it.

Each transaction is labeled on four fields: `merchant_name`, `primary` category,
`detailed` category, and `is_recurring`. Categories use Plaid's public Personal Finance
Category (PFC) taxonomy, stored at `data/plaid_pfc_taxonomy.csv` (16 primary, 103 detailed).

## 1. merchant_name

The consumer-recognizable brand, in the brand's canonical casing (e.g. `Blue Bottle Coffee`,
not `BLUE BOTTLE` or `blue bottle`).

Normalization rules, applied in order:
1. **Strip processor / gateway prefixes:** `SQ *`, `TST*`, `PYPL *`, `PAYPAL *`, `SP `,
   `CKE*`, `POS `, `DBT `. These identify the payment processor, not the merchant.
2. **Strip location and store-ID noise:** trailing city/state (`OAKLAND CA`), store numbers
   (`#1234`, `STORE 04471`), phone numbers, and reference IDs.
3. **Canonicalize the brand:** map to the brand's normal spelling and casing. `AMZN MKTP`,
   `AMAZON.COM`, and `Amazon Mktp US` all resolve to `Amazon`.

**Aggregator-masked case:** when the true underlying merchant cannot be recovered from the
string because a platform sits in front of it (`DD *DOORDASH`, `UBER EATS`, `PAYPAL *JOHNSDELI`),
label `merchant_name` as the **aggregator** (`DoorDash`, `Uber Eats`) and tag the row
`aggregator_masked`. This is a known ceiling on enrichment quality, and isolating it is one of
the eval's jobs, not something to paper over with a guess.

## 2. Category (primary + detailed)

Assign both the PFC `primary` and `detailed` value. The detailed value must be a child of the
chosen primary in the taxonomy file.

Documented tie-break rules for recurring ambiguities:
- **Starbucks / Blue Bottle / Peet's** → `FOOD_AND_DRINK_COFFEE` (not `RESTAURANT` or `FAST_FOOD`).
- **Amazon (general)** → `GENERAL_MERCHANDISE_ONLINE_MARKETPLACES`. Amazon is not a superstore.
- **Target / Walmart** → `GENERAL_MERCHANDISE_SUPERSTORES` (they sell groceries + general goods).
- **Costco** → `GENERAL_MERCHANDISE_SUPERSTORES`.
- **Uber / Lyft rides** → `TRANSPORTATION_TAXIS_AND_RIDE_SHARES`; **Uber Eats** → `FOOD_AND_DRINK`.
- **Netflix / Hulu / Disney+** → `ENTERTAINMENT_TV_AND_MOVIES`; **Spotify / Apple Music** →
  `ENTERTAINMENT_MUSIC_AND_AUDIO`.
- **Gas stations (Shell, Chevron)** → `TRANSPORTATION_GAS` even when a convenience store is attached,
  unless the string clearly indicates the in-store purchase.
- When genuinely ambiguous, prefer the primary category's `_OTHER_` detailed bucket and tag the row
  `ambiguous_category` rather than forcing a specific child.

## 3. is_recurring

`TRUE` only when the merchant and pattern indicate a subscription or regularly scheduled charge:
streaming, music, SaaS, gym memberships, insurance, rent, loan payments, utilities.

`FALSE` for one-off purchases, **including at merchants that are capable of recurring** — a single
Amazon order or one Uber ride is not recurring.

Known limitation, stated honestly: recurrence is a property of a *series* of transactions, not a
single string. The seed set labels recurrence from the merchant archetype plus descriptor cues
(e.g. `RECUR`, `AUTOPAY`, `MONTHLY`). A production-grade recurring signal needs the account's
transaction history, which is out of scope for the string-level eval. This limitation is reported,
not hidden.

## 4. Confidence is not labeled

Annotators do **not** assign a confidence score. Confidence is the model's output, and the eval
measures whether the model's confidence is *calibrated* against the correctness the rubric defines.
Coverage (does the model return a confident answer at all) is likewise a model property.

## 5. Process notes for the full gold set

The seed set (`data/gold_set_seed.csv`) is single-author. For the planned 300–500 row gold set:
- Double-label a 20% sample with a second annotator and report Cohen's kappa per field.
- Adjudicate disagreements and fold the resolution back into this rubric as a new tie-break rule.
- Every rule added here is traceable to a real disagreement, so the rubric grows from evidence.

## 6. Data provenance (read before trusting any number)

Seed descriptors are **synthetically formatted strings for real merchants**, written to mimic common
US bank-descriptor patterns. They are **not** drawn from real cardholder data, which is proprietary
and contains PII. The contribution of this project is the eval methodology; a gold set built on real
descriptors is the prerequisite for quoting any of these metrics as production quality. This caveat
is repeated on every chart and in the README so no synthetic number is ever read as real.
