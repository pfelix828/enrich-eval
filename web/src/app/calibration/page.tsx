import { calibration } from "@/lib/data";
import { pct, score3 } from "@/lib/format";
import { Card, CardTitle, PageHeader, SeverityBadge, Stat, SyntheticDataNote, Term } from "@/components/ui";
import { MatchTypeProfileChart, ReliabilityChart } from "@/components/charts";

export default function CalibrationPage() {
  const keyword = calibration.match_type_profile_v2.find((p) => p.match_type === "keyword");
  const aggregator = calibration.match_type_profile_v2.find((p) => p.match_type === "aggregator");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Does the confidence score mean anything?"
        subtitle={
          <>
            Every enriched transaction ships with a confidence value, and downstream products threshold on it: show
            the answer, hide it, or send it to review. A confidence score that doesn&apos;t track accuracy quietly
            breaks all three decisions. This page measures that — overall, and then where it actually matters, per
            resolution path.
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardTitle sub="Each dot is a confidence bin; dot size is how many transactions landed in it. On the dashed line, stated confidence equals measured accuracy.">
            Reliability, all paths pooled
          </CardTitle>
          <ReliabilityChart bins={calibration.reliability_v2} />
        </Card>
        <Card className="lg:col-span-2">
          <CardTitle>The one number — and why it&apos;s not enough</CardTitle>
          <Stat
            label={<Term def="Expected Calibration Error: the average gap between stated confidence and measured accuracy, weighted by how many transactions sit in each confidence bin. 0 = perfectly calibrated.">ECE, merchant confidence</Term>}
            value={score3(calibration.ece_v2)}
          />
          <p className="mt-3 text-sm leading-relaxed text-muted">
            An aggregate ECE of {score3(calibration.ece_v2)} sounds like a moderate, uniform problem. It isn&apos;t.
            The miscalibration is concentrated in specific resolution paths, and they fail in opposite directions —
            which a single pooled number can never show.
          </p>
        </Card>
      </div>

      <Card>
        <CardTitle sub="For each way the system resolves a merchant: the confidence it states (gray) next to the accuracy it actually achieves (green, or red when confidence overshoots accuracy by more than 15 points).">
          The real story is per resolution path
        </CardTitle>
        <MatchTypeProfileChart profile={calibration.match_type_profile_v2} />
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <div className="mb-2 flex items-center gap-2">
            <SeverityBadge severity="risk" />
            <h3 className="text-sm font-semibold tracking-tight">Keyword fallback: confidently wrong</h3>
          </div>
          <p className="text-sm leading-relaxed text-muted">
            The keyword path states {keyword ? pct(keyword.mean_confidence) : "~40%"} confidence and measures{" "}
            <strong className="text-foreground">{keyword ? pct(keyword.accuracy) : "0%"} accuracy</strong> on its{" "}
            {keyword?.n} transactions. These answers look trustworthy to any downstream threshold and are wrong —
            exactly the kind that reach customers. The fix is operational, not model work: suppress or route
            keyword-path answers to review until the path improves.
          </p>
        </Card>
        <Card>
          <div className="mb-2 flex items-center gap-2">
            <SeverityBadge severity="opportunity" />
            <h3 className="text-sm font-semibold tracking-tight">Aggregator path: underconfident</h3>
          </div>
          <p className="text-sm leading-relaxed text-muted">
            The new aggregator path states {aggregator ? pct(aggregator.mean_confidence) : "60%"} but measures{" "}
            <strong className="text-foreground">{aggregator ? pct(aggregator.accuracy) : "~87%"} accuracy</strong> on{" "}
            {aggregator?.n} transactions — good answers hiding below a typical display threshold. Raising its stated
            confidence surfaces correct enrichments customers currently never see.
          </p>
        </Card>
      </div>

      <Card>
        <CardTitle>Why read calibration this way</CardTitle>
        <p className="max-w-3xl text-sm leading-relaxed text-muted">
          A model can be accurate and still unusable if its confidence lies. Pooled metrics average a
          confidently-wrong path against an underconfident one and call the result “moderately miscalibrated” —
          when the right reading is two specific, opposite fixes. Per-path calibration turns a vague model-quality
          concern into two lines of a sprint plan.
        </p>
      </Card>

      <SyntheticDataNote />
    </div>
  );
}
