"use client";

/** Bespoke Recharts views. Each chart answers one question, stated in its
 *  card title; axes and tooltips are formatted so the answer is readable
 *  without cross-referencing. */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { humanize, pct } from "@/lib/format";
import type { MatchTypeProfile, ReliabilityBin, SliceRow } from "@/lib/data";

const ACCENT = "#0f766e";
const GRAY = "#9ca3af";
const RED = "#b91c1c";

/** Per-pattern accuracy, v1 vs v2 — which descriptor patterns got fixed? */
export function PatternTagBars({ v1, v2 }: { v1: SliceRow[]; v2: SliceRow[] }) {
  const v1ByKey = new Map(v1.map((r) => [r.key, r]));
  const rows = [...v2]
    .sort((a, b) => a.detailed_acc - b.detailed_acc)
    .map((r) => ({
      tag: humanize(r.key),
      n: r.n,
      v1: v1ByKey.get(r.key)?.detailed_acc ?? 0,
      v2: r.detailed_acc,
    }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(280, rows.length * 34)}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 36, bottom: 0, left: 8 }} barGap={2}>
        <CartesianGrid stroke="#eee" horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => pct(v)} tick={{ fontSize: 11, fill: "#6b7280" }} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="tag" width={170} tick={{ fontSize: 11.5, fill: "#374151" }} tickLine={false} axisLine={false} />
        <Tooltip
          formatter={(value, name) => [pct(Number(value)), name === "v1" ? "v1 accuracy" : "v2 accuracy"]}
          labelFormatter={(label, payload) => {
            const n = payload?.[0]?.payload?.n;
            return `${label}${n ? ` · ${n} transactions` : ""}`;
          }}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e4e4e7" }}
        />
        <Bar dataKey="v1" name="v1" fill={GRAY} radius={[0, 3, 3, 0]} barSize={9} />
        <Bar dataKey="v2" name="v2" fill={ACCENT} radius={[0, 3, 3, 0]} barSize={9}>
          <LabelList dataKey="v2" position="right" formatter={(v) => pct(Number(v))} style={{ fontSize: 10.5, fill: "#374151" }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Stated confidence vs measured accuracy per resolution path — where is the
 *  system confidently wrong? */
export function MatchTypeProfileChart({ profile }: { profile: MatchTypeProfile[] }) {
  const rows = [...profile]
    .sort((a, b) => b.n - a.n)
    .map((r) => ({
      path: `${humanize(r.match_type)} (n=${r.n})`,
      confidence: r.mean_confidence,
      accuracy: r.accuracy,
      gap: r.mean_confidence - r.accuracy,
    }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={rows} margin={{ top: 16, right: 8, bottom: 0, left: -16 }} barGap={3}>
        <CartesianGrid stroke="#eee" vertical={false} />
        <XAxis dataKey="path" tick={{ fontSize: 11, fill: "#374151" }} tickLine={false} axisLine={{ stroke: "#e4e4e7" }} interval={0} />
        <YAxis domain={[0, 1]} tickFormatter={(v) => pct(v)} tick={{ fontSize: 11, fill: "#6b7280" }} tickLine={false} axisLine={false} />
        <Tooltip
          formatter={(value, name) => [pct(Number(value)), name === "confidence" ? "Stated confidence" : "Measured accuracy"]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e4e4e7" }}
        />
        <Bar dataKey="confidence" name="confidence" fill={GRAY} radius={[3, 3, 0, 0]} barSize={22} />
        <Bar dataKey="accuracy" name="accuracy" radius={[3, 3, 0, 0]} barSize={22}>
          {rows.map((r) => (
            <Cell key={r.path} fill={r.gap > 0.15 ? RED : ACCENT} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Reliability: where the dots sit against the diagonal is the whole story. */
export function ReliabilityChart({ bins, height = 280 }: { bins: ReliabilityBin[]; height?: number }) {
  const pts = bins
    .filter((b) => b.n > 0 && b.avg_conf !== null && b.accuracy !== null)
    .map((b) => ({ conf: b.avg_conf as number, acc: b.accuracy as number, n: b.n }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: -16 }}>
        <CartesianGrid stroke="#eee" />
        <XAxis
          type="number"
          dataKey="conf"
          name="Stated confidence"
          domain={[0, 1]}
          tickFormatter={(v) => pct(v)}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#e4e4e7" }}
          label={{ value: "Stated confidence", position: "insideBottom", offset: -4, fontSize: 11, fill: "#6b7280" }}
        />
        <YAxis
          type="number"
          dataKey="acc"
          name="Measured accuracy"
          domain={[0, 1]}
          tickFormatter={(v) => pct(v)}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
        />
        <ZAxis type="number" dataKey="n" range={[60, 320]} name="transactions" />
        <ReferenceLine
          segment={[
            { x: 0, y: 0 },
            { x: 1, y: 1 },
          ]}
          stroke="#9ca3af"
          strokeDasharray="5 4"
          label={{ value: "perfectly calibrated", position: "insideTopLeft", fontSize: 10, fill: "#9ca3af" }}
        />
        <Tooltip
          formatter={(value, name) =>
            name === "transactions" ? [value, "transactions in bin"] : [pct(Number(value), 1), name]
          }
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e4e4e7" }}
        />
        <Scatter data={pts} fill={ACCENT} fillOpacity={0.85} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
