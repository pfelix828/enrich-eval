import Link from "next/link";
import { investigations, scorecard } from "@/lib/data";
import { pct } from "@/lib/format";
import { Card, CardTitle, Delta, PageHeader, Stat, SyntheticDataNote } from "@/components/ui";
import { InvestigationExplorer } from "@/components/investigation-explorer";

export default function InvestigatePage() {
  const { v1, v2 } = scorecard.overall;
  return (
    <div className="space-y-6">
      <PageHeader
        title="A vague complaint goes in. A ranked roadmap comes out."
        subtitle={
          <>
            EnrichEval measures the systems that turn a raw bank-statement string like{" "}
            <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-xs">SQ *BLUE BOTTLE COFFEE OAKLAND CA</code>{" "}
            into a clean merchant, category, and recurring flag. Most evals stop at an accuracy number. This one
            starts where real quality work starts: a customer says “your data looks wrong,” and someone has to turn
            that into specific, prioritized engineering work.
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardTitle sub="Three real complaints, each run through the investigation engine. Pick one.">
            Watch a complaint become a roadmap
          </CardTitle>
          <InvestigationExplorer />
        </Card>

        <div className="space-y-4">
          <Card>
            <CardTitle>The system under test</CardTitle>
            <div className="space-y-4">
              <Stat
                label="Merchant accuracy, v2"
                value={pct(v2.merchant_correct_acc)}
                delta={<Delta value={v2.merchant_correct_acc - v1.merchant_correct_acc} />}
                hint="Share of the 55-row seed where the predicted merchant matches the gold label, after the validated equivalence judge."
              />
              <Stat
                label="Category accuracy, v2"
                value={pct(v2.detailed_acc)}
                delta={<Delta value={v2.detailed_acc - v1.detailed_acc} />}
                hint="Detailed-category accuracy — the strictest of the category metrics."
              />
              <p className="text-xs leading-relaxed text-muted">
                Deltas compare v2 against the v1 baseline. The full comparison, sliced by descriptor pattern,
                difficulty, and amount, is on the{" "}
                <Link href="/scorecard" className="underline decoration-dotted underline-offset-2 hover:text-foreground">
                  Scorecard
                </Link>
                .
              </p>
            </div>
          </Card>

          <Card>
            <CardTitle>How to read this</CardTitle>
            <ul className="space-y-2 text-xs leading-relaxed text-muted">
              <li>
                <strong className="text-foreground">Routing</strong> — keywords map the complaint to merchant,
                category, or recurring errors. Deterministic, so the same complaint always produces the same report.
              </li>
              <li>
                <strong className="text-foreground">One cause per error</strong> — each failing transaction gets a
                single root cause from a fixed priority list; an unresolved merchant is always a coverage gap, no
                matter what else is going on in the string.
              </li>
              <li>
                <strong className="text-foreground">Impact, not just volume</strong> — clusters are ranked by errors
                × (0.5 + mean confidence). A confidently-wrong answer reaches customers looking trustworthy, so it
                outranks an equally common but hesitant one.
              </li>
            </ul>
          </Card>

          <Card>
            <CardTitle>Why this matters</CardTitle>
            <p className="text-xs leading-relaxed text-muted">
              “Your categorization is bad” is unactionable. “{investigations[0].clusters[0]?.n_errors ?? 9} of the{" "}
              {investigations[0].errors} merchant errors are knowledge-base coverage gaps, and the system averaged{" "}
              {investigations[0].clusters[0]?.mean_confidence.toFixed(2)} confidence while being wrong — close the
              coverage gap first” is a sprint plan. The translation between those two sentences is the job.
            </p>
          </Card>
        </div>
      </div>

      <SyntheticDataNote />
    </div>
  );
}
