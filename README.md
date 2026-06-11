# EnrichEval — a quality lab for transaction enrichment

**Live demo: [enrich-eval.vercel.app](https://enrich-eval.vercel.app)**

Most "data science" portfolio projects build a model. This one measures whether a model is any
good, which is the harder and more under-served problem. It is an evaluation harness for a
**transaction-enrichment** system: the kind of system that turns a raw bank-statement string like
`SQ *BLUE BOTTLE COFFEE OAKLAND CA` into structured data — clean merchant name, category, and a
recurring flag.

The model under test is deliberately cheap. The deliverable is the way its quality is defined,
measured, sliced, and root-caused.

## The hook: complaint in, root-cause out

A customer says *"your categorization is bad for my users."* That is unstructured and unactionable.
EnrichEval turns it into a one-page investigation: it scores the affected transactions, clusters the
errors, ranks the clusters by volume × severity, and reports something a roadmap can act on — e.g.
*"68% of these errors are aggregator-masked food-delivery charges where the true merchant is
unrecoverable from the string; that single pattern accounts for X points of category accuracy."*

## Why this project

It mirrors the actual job of an evaluation-focused data scientist on a foundations/AI team: define
quality metrics, turn vague complaints into structured investigations, validate AI effectiveness in
a principled way, and build eval that scales. The categories come from
[Plaid's public Personal Finance Category taxonomy](https://plaid.com/docs/transactions/transactions-data/#personal-finance-category)
(16 primary, 103 detailed).

## Build phases — all complete

| Phase | What | Status |
|---|---|---|
| 0 | Gold set + taxonomy + labeling rubric | done |
| 1 | Enrichment system under test (rules v1/v2 + optional Claude backend) | done |
| 2 | Metrics + segment slices (by pattern, category, amount, difficulty) | done |
| 3 | LLM-as-judge for fuzzy correctness, validated against human labels (Cohen's κ = 0.83) | done |
| 4 | Complaint → root-cause investigation engine | done |
| 5 | Confidence calibration (reliability, ECE) + v1-vs-v2 regression diff | done |
| 6 | Streamlit demo + figures + findings writeup | done |

## Run it

```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python src/run_all.py          # rebuild every artifact in reports/, offline
./.venv/bin/streamlit run app.py           # interactive demo
```

Everything runs offline and deterministically on the rules backend (free, reproducible). The harness
is model-agnostic: set `ENRICH_BACKEND=claude` to swap in a Claude enricher and `ENRICH_JUDGE=claude`
for a Claude judge — the metrics, investigation, and regression layers don't change. The headline
results and what they mean are written up in [reports/findings.md](reports/findings.md).

## Repo layout

```
data/
  plaid_pfc_taxonomy.csv     real, downloaded from Plaid's public docs (16 primary, 103 detailed)
  gold_set_seed.csv          55-row seed, built by the generator (do not hand-edit)
  judge_validation.csv       24 human-labeled merchant-equivalence pairs for judge validation
docs/
  labeling_rubric.md         what "correct" means; the definition-of-quality artifact
src/
  build_seed_gold.py         reproducible source of the seed gold set
  enrich.py                  the system under test: rules v1/v2 + gated Claude backend
  metrics.py                 scoring primitives (tiered merchant match, PRF, ECE, buckets)
  run_eval.py                run a version across the gold set -> predictions + metrics json
  judge.py                   merchant-equivalence judge + Cohen's-kappa validation harness
  investigate.py             complaint -> routed, clustered, ranked root-cause report
  regression.py              per-row + per-segment v1->v2 diff ("CI for model quality")
  make_figures.py            renders the four figures
  run_all.py                 one-command, end-to-end reproducible rebuild
app.py                       Streamlit demo (Overview, Investigate, Segments, Calibration, Regression, Judge)
reports/                     generated: predictions, metrics, investigations, figures, findings.md
```

## What's in the seed (Phase 0)

55 hand-curated rows across 11 of the 16 PFC primary categories, weighted toward the patterns that
break naive enrichment so the metrics layer has something real to slice on:

- **processor prefixes** — `SQ *`, `TST*`, `PYPL *` masking the merchant
- **aggregator-masked** — `DoorDash`, `Uber Eats`, `PayPal`, where the true merchant is unrecoverable
  from the string (a genuine ceiling on quality, isolated rather than guessed at)
- **store-id / location noise**, **all-caps truncation**, **city/state suffixes**
- **ambiguous categories** — Amazon (marketplace vs Prime vs Prime Video), Costco, fast-casual,
  cloud-storage SaaS, P2P transfers
- **recurring vs one-off** at recurring-capable merchants

Run `python src/build_seed_gold.py` to regenerate. The generator fails loudly if any label drifts
off the real taxonomy.

## Honesty note on the data

The seed descriptors are **synthetically formatted strings for real merchants**, written to mimic
common US bank-descriptor patterns. They are **not** real cardholder data, which is proprietary and
contains PII. The contribution here is the eval methodology; quoting any of these numbers as
production-grade quality would require a gold set built on real descriptors. This caveat travels with
every chart. See `docs/labeling_rubric.md` §6.
