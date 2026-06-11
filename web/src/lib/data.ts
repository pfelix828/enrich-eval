/** Typed loaders for the JSON exported by src/export_web.py (repo root).
 *  Every number in the app comes from these files — nothing is computed
 *  or invented client-side beyond display formatting. */

import metaJson from "@/data/meta.json";
import scorecardJson from "@/data/scorecard.json";
import calibrationJson from "@/data/calibration.json";
import regressionJson from "@/data/regression.json";
import judgeJson from "@/data/judge.json";
import investigationsJson from "@/data/investigations.json";

export interface OverallMetrics {
  n: number;
  merchant_correct_acc: number;
  primary_acc: number;
  detailed_acc: number;
  merchant_coverage: number;
}

export interface SliceRow {
  key: string;
  n: number;
  merchant_acc: number;
  primary_acc: number;
  detailed_acc: number;
  coverage: number;
}

export interface Scorecard {
  overall: { v1: OverallMetrics; v2: OverallMetrics };
  by_pattern_tag: { v1: SliceRow[]; v2: SliceRow[] };
  slices: Record<string, { v1: SliceRow[]; v2: SliceRow[] }>;
}

export interface ReliabilityBin {
  bin: number;
  lo: number;
  hi: number;
  n: number;
  avg_conf: number | null;
  accuracy: number | null;
}

export interface MatchTypeProfile {
  match_type: string;
  n: number;
  mean_confidence: number;
  accuracy: number;
}

export interface Calibration {
  ece_v2: number;
  reliability_v2: ReliabilityBin[];
  match_type_profile_v2: MatchTypeProfile[];
  match_type_profile_v1: MatchTypeProfile[];
}

export interface RegressionField {
  acc_old: number;
  acc_new: number;
  delta: number;
  improved: number;
  regressed: number;
}

export interface RegressionRow {
  id: string | number;
  field: string;
  raw_descriptor: string;
  pattern_tags: string;
  gold_merchant: string;
  v1_pred_merchant: string;
  v2_pred_merchant: string;
  gold_category: string;
  v1_pred_category: string;
  v2_pred_category: string;
  v1_recurring: boolean;
  v2_recurring: boolean;
  gold_recurring: boolean;
}

export interface Regression {
  fields: Record<string, RegressionField>;
  regressions: RegressionRow[];
}

export interface Judge {
  n_pairs: number;
  agreement: number;
  cohen_kappa: number;
  disagreements: { pred_merchant: string; gold_merchant: string; human: boolean; judge: boolean; note: string }[];
}

export interface ClusterRowDetail {
  descriptor: string;
  gold_merchant: string;
  pred_merchant: string;
  gold_category: string;
  pred_category: string;
  gold_recurring: boolean;
  pred_recurring: boolean;
  confidence: number;
}

export interface Cluster {
  cause: string;
  n_errors: number;
  share_of_errors: number;
  mean_confidence: number;
  impact_score: number;
  examples: string[];
  recommendation: string;
  rows: ClusterRowDetail[];
}

export interface Investigation {
  complaint: string;
  version: number;
  filter: string | null;
  routed_focus: string;
  focus_label: string;
  population: number;
  scope_n: number;
  errors: number;
  accuracy_in_scope: number;
  clusters: Cluster[];
}

export interface Meta {
  seed_n: number;
  dataNote: string;
  versions: { v1: string; v2: string };
}

export const meta = metaJson as Meta;
export const scorecard = scorecardJson as Scorecard;
export const calibration = calibrationJson as Calibration;
export const regression = regressionJson as unknown as Regression;
export const judge = judgeJson as Judge;
export const investigations = investigationsJson as Investigation[];

/** Human labels for cause/tag keys. */
export const CAUSE_LABELS: Record<string, string> = {
  coverage_gap: "Knowledge-base coverage gap",
  aggregator_masked: "Masked by a payment platform",
  ambiguous_category: "Genuinely ambiguous category",
  processor_prefix: "Processor prefix defeats lookup",
  allcaps_truncated: "Truncated / all-caps descriptor",
  store_id_noise: "Store-ID noise in string",
  city_state_suffix: "Trailing city/state tokens",
  recurring_cue: "Recurring-cue handling",
  hidden_recurring: "Subscription without a cue word",
  false_cue: "Cue word on a non-subscription",
  clean: "Clean string still failed",
};
