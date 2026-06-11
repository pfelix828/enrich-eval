import { scorecard } from "@/lib/data";
import { pct } from "@/lib/format";
import { Card, CardTitle, Delta, PageHeader, Stat, SyntheticDataNote, Term } from "@/components/ui";
import { PatternTagBars } from "@/components/charts";
import { SliceExplorer } from "@/components/slice-explorer";

export default function ScorecardPage() {
  const { v1, v2 } = scorecard.overall;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Two enricher versions, compared the way a release review would"
        subtitle={
          <>
            v2 adds aggregator awareness, a fuller merchant knowledge base, more processor-prefix handling, and
            richer recurring cues. Every headline metric improved — and the interesting part is{" "}
            <em>why</em>, which the averages alone don&apos;t say.
          </>
        }
      />

      <Card>
        <div className="grid gap-6 sm:grid-cols-3">
          <Stat
            label={<Term def="Predicted merchant matches the gold label, judged by the validated equivalence judge (so 'Blue Bottle' = 'Blue Bottle Coffee').">Merchant accuracy</Term>}
            value={pct(v2.merchant_correct_acc)}
            delta={<Delta value={v2.merchant_correct_acc - v1.merchant_correct_acc} />}
            hint={`v1: ${pct(v1.merchant_correct_acc)}`}
          />
          <Stat
            label={<Term def="Top-level Plaid Personal Finance Category (16 primaries).">Primary category</Term>}
            value={pct(v2.primary_acc)}
            delta={<Delta value={v2.primary_acc - v1.primary_acc} />}
            hint={`v1: ${pct(v1.primary_acc)}`}
          />
          <Stat
            label={<Term def="Full detailed Plaid category (103 detailed labels) — the strictest headline metric.">Detailed category</Term>}
            value={pct(v2.detailed_acc)}
            delta={<Delta value={v2.detailed_acc - v1.detailed_acc} />}
            hint={`v1: ${pct(v1.detailed_acc)}`}
          />
        </div>
        <p className="mt-4 text-xs text-muted">
          Recurring detection is deliberately excluded from this table: recurrence is a property of a series of
          transactions, not one string, so any single-transaction score would be misleading. The Methodology page
          shows the adversarial cases that prove the point.
        </p>
      </Card>

      <Card className="border-accent/40 bg-accent-soft/30">
        <CardTitle>The finding the averages hide</CardTitle>
        <p className="max-w-3xl text-sm leading-relaxed">
          <strong>v1&apos;s merchant problem was coverage, not parsing.</strong> Every one of v1&apos;s merchant
          errors was an unresolved <em>Unknown</em>, not a wrong guess — knowledge-base gaps concentrated in bills,
          loans, services, and travel. That single observation redirects the work: the fix was adding coverage
          (which v2 did), not building smarter string normalization. Slicing errors by cause is what surfaced it.
        </p>
      </Card>

      <Card>
        <CardTitle sub="Detailed-category accuracy per descriptor pattern, v1 (gray) vs v2 (green), sorted hardest-first. Hover for sample sizes.">
          Which kinds of messy strings got fixed?
        </CardTitle>
        <PatternTagBars v1={scorecard.by_pattern_tag.v1} v2={scorecard.by_pattern_tag.v2} />
        <p className="mt-2 text-xs text-muted">
          Aggregator-masked descriptors (DoorDash, Uber Eats hiding the real merchant) and processor prefixes moved
          most — exactly what v2&apos;s new rules target. Patterns still short of the bar are the next roadmap items.
        </p>
      </Card>

      <Card>
        <CardTitle sub="The same v1-to-v2 comparison, cut four different ways.">Slice it yourself</CardTitle>
        <SliceExplorer />
      </Card>

      <SyntheticDataNote />
    </div>
  );
}
