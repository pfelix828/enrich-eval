import { regression } from "@/lib/data";
import { humanize, pct } from "@/lib/format";
import { Card, CardTitle, Delta, Descriptor, PageHeader, SyntheticDataNote } from "@/components/ui";

const FIELD_LABELS: Record<string, string> = {
  merchant_correct: "Merchant",
  primary_correct: "Primary category",
  detailed_correct: "Detailed category",
  recurring_correct: "Recurring flag",
};

export default function RegressionPage() {
  const fields = Object.entries(regression.fields);
  const star = regression.regressions.find((r) => r.raw_descriptor.includes("STEAMGAMES"));
  const others = regression.regressions.filter((r) => r !== star);

  return (
    <div className="space-y-6">
      <PageHeader
        title="A net-positive release still broke a customer-visible case"
        subtitle={
          <>
            v2 beats v1 on every average. Ship it? The per-row diff says: almost. Averages can&apos;t see a release
            that fixes eighteen rows and silently breaks one a customer will notice. That&apos;s what a regression
            gate is for, and this page is the gate&apos;s output for v1 → v2.
          </>
        }
      />

      <Card>
        <CardTitle sub="Accuracy by field, v1 → v2, with the per-row improvement and regression counts a release review actually needs.">
          The release diff at a glance
        </CardTitle>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {fields.map(([key, f]) => (
            <div key={key} className="rounded-lg border border-border-subtle p-4">
              <div className="text-xs font-medium text-muted">{FIELD_LABELS[key] ?? humanize(key)}</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-lg font-bold tabular-nums tracking-tight">
                  {pct(f.acc_old)} → {pct(f.acc_new)}
                </span>
                <Delta value={f.delta} />
              </div>
              <div className="mt-2 text-xs text-muted">
                <span className="font-medium text-emerald-700">{f.improved} rows improved</span>
                {" · "}
                <span className={f.regressed > 0 ? "font-medium text-red-700" : ""}>{f.regressed} regressed</span>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted">
          The recurring row is shown for completeness but is excluded from headline quality metrics — see
          Methodology for why a single-transaction recurring score is not meaningful.
        </p>
      </Card>

      {star ? (
        <Card className="border-red-200">
          <CardTitle sub="The regression the averages would have shipped.">
            Featured regression: <Descriptor>{star.raw_descriptor}</Descriptor>
          </CardTitle>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-emerald-50/60 p-4">
              <div className="text-xs font-semibold text-emerald-800">v1 — correct</div>
              <div className="mt-1 text-sm font-medium">{star.v1_pred_merchant}</div>
              <div className="text-xs text-muted">{star.v1_pred_category}</div>
            </div>
            <div className="rounded-lg bg-red-50/60 p-4">
              <div className="text-xs font-semibold text-red-800">v2 — regressed</div>
              <div className="mt-1 text-sm font-medium">{star.v2_pred_merchant}</div>
              <div className="text-xs text-muted">{star.v2_pred_category}</div>
            </div>
            <div className="rounded-lg bg-zinc-50 p-4">
              <div className="text-xs font-semibold text-zinc-600">Gold label</div>
              <div className="mt-1 text-sm font-medium">{star.gold_merchant}</div>
              <div className="text-xs text-muted">{star.gold_category}</div>
            </div>
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted">
            v2&apos;s new aggregator rule — the same rule that fixed the DoorDash and Uber Eats rows — sees the{" "}
            <Descriptor>PYPL</Descriptor> prefix and stops at the platform, labeling this PayPal instead of the real
            merchant behind it, Steam. A rule that helps in aggregate over-applies to a specific case. The roadmap
            consequence: promote the aggregator rule with a guard, so it doesn&apos;t swallow merchants that merely
            bill through a processor.
          </p>
        </Card>
      ) : null}

      {others.length > 0 ? (
        <Card>
          <CardTitle sub="Every other row that flipped from correct to incorrect in v2.">Remaining regressions</CardTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border-subtle text-muted">
                  <th className="py-1.5 pr-3 font-medium">Descriptor</th>
                  <th className="py-1.5 pr-3 font-medium">Field</th>
                  <th className="py-1.5 pr-3 font-medium">v1 said</th>
                  <th className="py-1.5 pr-3 font-medium">v2 says</th>
                  <th className="py-1.5 font-medium">Gold</th>
                </tr>
              </thead>
              <tbody>
                {others.map((r) => {
                  const recurring = r.field === "recurring_correct";
                  return (
                    <tr key={`${r.id}-${r.field}`} className="border-b border-border-subtle/60">
                      <td className="py-1.5 pr-3"><Descriptor>{r.raw_descriptor}</Descriptor></td>
                      <td className="py-1.5 pr-3">{FIELD_LABELS[r.field] ?? r.field}</td>
                      <td className="py-1.5 pr-3">{recurring ? (r.v1_recurring ? "recurring" : "not recurring") : r.v1_pred_merchant}</td>
                      <td className="py-1.5 pr-3 text-red-700">{recurring ? (r.v2_recurring ? "recurring" : "not recurring") : r.v2_pred_merchant}</td>
                      <td className="py-1.5">{recurring ? (r.gold_recurring ? "recurring" : "not recurring") : r.gold_merchant}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      <Card>
        <CardTitle>Why gate on rows, not averages</CardTitle>
        <p className="max-w-3xl text-sm leading-relaxed text-muted">
          A release gate keyed on average accuracy ships this regression; a gate keyed on per-row flips catches it
          and forces a decision — fix the rule, guard it, or accept the trade-off knowingly. On a 55-row seed the
          gate is a demonstration; on a production system diffing millions of rows per release, it is the difference
          between finding out from your eval and finding out from a customer.
        </p>
      </Card>

      <SyntheticDataNote />
    </div>
  );
}
