"use client";

/** Slice the v1/v2 comparison by difficulty, category, amount, or resolution
 *  path. Sorted by improvement so the biggest movers read top-down. */

import { useState } from "react";
import clsx from "clsx";
import { scorecard } from "@/lib/data";
import { humanize, pct } from "@/lib/format";
import { Delta } from "@/components/ui";

const SLICES: { id: string; label: string }[] = [
  { id: "by_difficulty", label: "Difficulty" },
  { id: "by_primary", label: "Category" },
  { id: "by_amount_bucket", label: "Amount" },
  { id: "by_match_type", label: "Resolution path" },
];

export function SliceExplorer() {
  const [sliceId, setSliceId] = useState("by_difficulty");
  const slice = scorecard.slices[sliceId];
  const v1ByKey = new Map(slice.v1.map((r) => [r.key, r]));
  const rows = [...slice.v2]
    .map((r) => {
      const prev = v1ByKey.get(r.key);
      return { ...r, v1_detailed: prev?.detailed_acc ?? null, delta: prev ? r.detailed_acc - prev.detailed_acc : null };
    })
    .sort((a, b) => (b.delta ?? -2) - (a.delta ?? -2));

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {SLICES.map((s) => (
          <button
            key={s.id}
            onClick={() => setSliceId(s.id)}
            className={clsx(
              "rounded-md px-2.5 py-1.5 text-xs font-medium",
              s.id === sliceId ? "bg-accent-soft text-accent" : "bg-zinc-100 text-foreground/70 hover:text-foreground",
            )}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-xs text-muted">
              <th className="py-2 pr-3 font-medium">Slice</th>
              <th className="py-2 pr-3 font-medium">n</th>
              <th className="py-2 pr-3 font-medium">v1 detailed acc</th>
              <th className="py-2 pr-3 font-medium">v2 detailed acc</th>
              <th className="py-2 font-medium">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-b border-border-subtle/60">
                <td className="py-2 pr-3 font-medium">{humanize(r.key)}</td>
                <td className="py-2 pr-3 tabular-nums text-muted">{r.n}</td>
                <td className="py-2 pr-3 tabular-nums">{r.v1_detailed === null ? "—" : pct(r.v1_detailed)}</td>
                <td className="py-2 pr-3 tabular-nums font-medium">{pct(r.detailed_acc)}</td>
                <td className="py-2">
                  {r.delta === null ? (
                    <span className="text-xs text-muted">new path in v2</span>
                  ) : (
                    <Delta value={r.delta} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">
        Accuracy here is detailed-category accuracy, the strictest of the three headline metrics. Rows are
        sorted by improvement. Small n per slice is expected — this is a 55-row methodology seed, so read
        direction, not significance.
      </p>
    </div>
  );
}
