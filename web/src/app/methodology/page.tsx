import { judge, meta } from "@/lib/data";
import { pct } from "@/lib/format";
import { Card, CardTitle, Descriptor, PageHeader, Stat, Term } from "@/components/ui";

export default function MethodologyPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Methodology"
        subtitle="What was measured, how correctness was defined, what was validated before being trusted, and where the honest limits are."
      />

      <Card>
        <CardTitle>The seed gold set</CardTitle>
        <div className="max-w-3xl space-y-3 text-sm leading-relaxed text-muted">
          <p>
            {meta.seed_n} hand-curated transaction descriptors with gold labels for merchant, category, and
            recurring flag, reproducible from a seeded build script. Categories follow Plaid&apos;s public Personal
            Finance Category taxonomy (16 primary, 103 detailed); the seed covers 11 primaries and is deliberately
            weighted toward patterns that break naive enrichment: processor prefixes (<Descriptor>SQ *</Descriptor>,{" "}
            <Descriptor>TST*</Descriptor>), aggregator-masked merchants (<Descriptor>DD *DOORDASH SUSHIYA</Descriptor>),
            all-caps truncation, store-ID noise, ambiguous categories, and recurring cues both real and misleading.
          </p>
          <p>
            Two enricher versions run against it: <strong className="text-foreground">v1</strong>,{" "}
            {meta.versions.v1}; <strong className="text-foreground">v2</strong>, {meta.versions.v2}. Both are
            deliberately simple rules systems — the deliverable is the measurement around them, and every layer
            (metrics, investigation, regression gate) works unchanged against a model-based enricher; the backends
            are swappable behind environment flags.
          </p>
        </div>
      </Card>

      <Card>
        <CardTitle>What counts as “correct” — and validating the judge</CardTitle>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="md:col-span-2">
          <div className="max-w-2xl space-y-3 text-sm leading-relaxed text-muted">
            <p>
              Exact string match would wrongly fail <Descriptor>Blue Bottle</Descriptor> vs{" "}
              <Descriptor>Blue Bottle Coffee</Descriptor>, so merchant correctness is tiered: exact match, then
              normalized match, then a semantic-equivalence judge for the remainder. Because the judge relabels
              data, it had to earn that right: it was scored against {judge.n_pairs} human-labeled pairs before
              being allowed to touch anything.
            </p>
            <p>
              Its two residual blind spots are documented rather than hidden: parent-versus-consumer brand
              (<Descriptor>Comcast</Descriptor> vs <Descriptor>Xfinity</Descriptor>) and acronym expansion
              (<Descriptor>BART</Descriptor> vs <Descriptor>Bay Area Rapid Transit</Descriptor>). Both need a
              brand-alias knowledge base or an LLM judge — and any future judge has to beat this one&apos;s κ on
              the same 24 pairs to replace it.
            </p>
          </div>
          </div>
          <div className="space-y-4">
            <Stat label="Human agreement" value={pct(judge.agreement)} hint="Share of 24 human-labeled pairs where the judge gave the same verdict." />
            <Stat
              label={<Term def="Agreement corrected for chance. 0.83 is 'almost perfect' on the standard Landis-Koch scale.">Cohen&apos;s κ</Term>}
              value={judge.cohen_kappa.toFixed(2)}
            />
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>Why recurring detection is excluded from headline metrics</CardTitle>
        <div className="max-w-3xl space-y-3 text-sm leading-relaxed text-muted">
          <p>
            Recurrence is a property of a <em>series</em> of transactions, not one string. A system — or an eval —
            that sees one line at a time cannot honestly measure it, and any F1 quoted from this seed would mostly
            reflect how many cue-less cases were put in it, not real performance. An earlier version of this eval
            reported recurring F1 = 1.0; that was a small-n artifact (the labels and the detector shared a cue
            list), and it was replaced with adversarial cases that expose the ceiling:
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <Descriptor>EQUINOX FITNESS CLUB</Descriptor> and <Descriptor>NYTIMES NYTIMES.COM</Descriptor> are real
              subscriptions with no cue word — the cue-based detector misses both.
            </li>
            <li>
              <Descriptor>MONTHLY MARKET SF</Descriptor> is a one-off grocery run at a store with “Monthly” in its
              name — the cue wrongly fires. v1, which didn&apos;t know the cue, got it right; v2&apos;s richer cue
              list regressed it.
            </li>
          </ul>
          <p>The honest fix is transaction history, not a cleverer string rule.</p>
        </div>
      </Card>

      <Card>
        <CardTitle>Limitations, stated plainly</CardTitle>
        <ul className="max-w-3xl list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-muted">
          <li>Synthetic descriptors for real merchants; no real cardholder data anywhere. Magnitudes are demonstrations, not production quality.</li>
          <li>{meta.seed_n} rows is enough to exercise every metric and failure mode, not enough for statistically tight slice estimates — read direction, not significance.</li>
          <li>The enrichers under test are rules systems; absolute accuracies say nothing about any production system&apos;s.</li>
          <li>Complaint routing is keyword-based by default (a Claude-based router exists behind a flag); the demo investigations here use the deterministic router so results are exactly reproducible.</li>
          <li>The judge is itself a rules system validated on 24 pairs — small by design, with its blind spots named above.</li>
        </ul>
      </Card>

      <Card>
        <CardTitle>Run it yourself</CardTitle>
        <div className="max-w-3xl space-y-2 text-sm leading-relaxed text-muted">
          <p>
            Everything on this site is reproducible offline from the{" "}
            <a href="https://github.com/pfelix828/enrich-eval" className="underline decoration-dotted underline-offset-2 hover:text-foreground">
              repo
            </a>
            : <Descriptor>python src/run_all.py</Descriptor> rebuilds every artifact, and{" "}
            <Descriptor>python src/investigate.py &quot;your complaint here&quot;</Descriptor> runs a fresh
            investigation against any complaint, not just the three precomputed on the home page. A local Streamlit
            dashboard (<Descriptor>streamlit run app.py</Descriptor>) is included for interactive exploration.
          </p>
        </div>
      </Card>
    </div>
  );
}
