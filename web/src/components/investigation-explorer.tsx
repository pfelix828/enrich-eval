"use client";

/**
 * The hook: pick a vague complaint, see the precomputed investigation —
 * routed focus, headline accuracy in scope, and error clusters ranked by
 * impact (volume x confidently-wrong), each with example rows and a fix.
 *
 * Results were computed by the real engine (src/investigate.py) at export
 * time; this component only renders them.
 */

import { useState } from "react";
import clsx from "clsx";
import { investigations, CAUSE_LABELS, type Cluster } from "@/lib/data";
import { pct } from "@/lib/format";
import { Card, CardTitle, Descriptor, Pill, Term } from "@/components/ui";

const FOCUS_BADGE: Record<string, string> = {
  merchant: "merchant-name errors",
  category: "categorization errors",
  recurring: "recurring-detection errors",
};

export function InvestigationExplorer() {
  const [idx, setIdx] = useState(0);
  const inv = investigations[idx];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {investigations.map((it, i) => (
          <button
            key={it.complaint}
            onClick={() => setIdx(i)}
            className={clsx(
              "rounded-lg border px-3 py-2 text-left text-sm transition-colors",
              i === idx
                ? "border-accent bg-accent-soft font-medium text-accent"
                : "border-border-subtle bg-white text-foreground/80 hover:border-zinc-300",
            )}
          >
            “{it.complaint}”
          </button>
        ))}
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          <span className="text-muted">Routed to:</span>
          <Pill className="border-accent/40 bg-accent-soft text-accent">{FOCUS_BADGE[inv.routed_focus]}</Pill>
          <span className="text-muted">Scope:</span>
          <span className="font-medium">{inv.scope_n} transactions</span>
          <span className="text-muted">In-scope accuracy:</span>
          <span className="font-medium">
            {pct(inv.accuracy_in_scope)} <span className="text-muted">({inv.errors} wrong)</span>
          </span>
        </div>
        <p className="mt-3 text-sm text-muted">
          The complaint is keyword-routed to an error type, every failing transaction is assigned a
          single root cause, and causes are ranked by{" "}
          <Term def="impact = errors x (0.5 + mean confidence). An error the system was confident about reaches customers looking trustworthy, so confident clusters rank higher than raw counts suggest.">
            impact
          </Term>
          , not just count.
        </p>
      </Card>

      <div className="space-y-3">
        {inv.clusters.map((c, rank) => (
          <ClusterCard key={c.cause} cluster={c} rank={rank + 1} />
        ))}
      </div>
    </div>
  );
}

function ClusterCard({ cluster, rank }: { cluster: Cluster; rank: number }) {
  const [open, setOpen] = useState(rank === 1);
  return (
    <Card className={clsx(rank === 1 && "border-accent/50")}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle
            sub={
              <>
                {cluster.n_errors} errors · {pct(cluster.share_of_errors)} of all errors in scope · mean
                confidence {cluster.mean_confidence.toFixed(2)} while wrong
              </>
            }
          >
            <span className="mr-2 inline-grid h-5 w-5 place-items-center rounded-full bg-accent text-[11px] font-bold text-white">
              {rank}
            </span>
            {CAUSE_LABELS[cluster.cause] ?? cluster.cause}
            {rank === 1 ? <span className="ml-2 text-xs font-semibold text-accent">fix this first</span> : null}
          </CardTitle>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted">impact score</div>
          <div className="text-xl font-bold tracking-tight">{cluster.impact_score}</div>
        </div>
      </div>

      <p className="text-sm leading-relaxed">{cluster.recommendation}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {cluster.examples.map((e) => (
          <Descriptor key={e}>{e}</Descriptor>
        ))}
      </div>

      <button
        onClick={() => setOpen(!open)}
        className="mt-3 text-xs font-medium text-accent underline-offset-2 hover:underline"
      >
        {open ? "Hide" : "Show"} the affected transactions
      </button>

      {open ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border-subtle text-muted">
                <th className="py-1.5 pr-3 font-medium">Descriptor</th>
                <th className="py-1.5 pr-3 font-medium">Expected</th>
                <th className="py-1.5 pr-3 font-medium">System said</th>
                <th className="py-1.5 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {cluster.rows.map((r) => (
                <tr key={r.descriptor} className="border-b border-border-subtle/60">
                  <td className="py-1.5 pr-3">
                    <Descriptor>{r.descriptor}</Descriptor>
                  </td>
                  <td className="py-1.5 pr-3">
                    <div className="font-medium">{r.gold_merchant}</div>
                    <div className="text-muted">{r.gold_category}</div>
                  </td>
                  <td className="py-1.5 pr-3">
                    <div className={clsx("font-medium", r.pred_merchant !== r.gold_merchant && "text-red-700")}>
                      {r.pred_merchant}
                    </div>
                    <div className="text-muted">{r.pred_category}</div>
                  </td>
                  <td className="py-1.5 tabular-nums">{r.confidence.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Card>
  );
}
