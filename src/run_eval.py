"""
Eval driver: run an enricher version across the gold set, score every row, and write
  reports/predictions_v{n}.csv   (per-transaction predictions + correctness flags)
  reports/metrics_v{n}.json      (overall metrics + every segment slice)

Usage:
  python src/run_eval.py            # runs v1 and v2
  python src/run_eval.py 2          # runs v2 only
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enrich import Enricher
import metrics as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
REPORTS = os.path.join(HERE, "reports")


def score_rows(version: int) -> pd.DataFrame:
    gold = pd.read_csv(os.path.join(DATA, "gold_set_seed.csv"))
    enr = Enricher(version=version)
    recs = []
    for _, g in gold.iterrows():
        p = enr.enrich(g["raw_descriptor"], g["amount"])
        m_exact = M.exact_match(p.merchant, g["gold_merchant"])
        m_norm = M.normalized_match(p.merchant, g["gold_merchant"])
        recs.append({
            "id": g["id"],
            "raw_descriptor": g["raw_descriptor"],
            "amount": g["amount"],
            "difficulty": g["difficulty"],
            "pattern_tags": g["pattern_tags"],
            "amount_bucket": M.amount_bucket(g["amount"]),
            "gold_merchant": g["gold_merchant"],
            "pred_merchant": p.merchant,
            "gold_primary": g["gold_primary"],
            "pred_primary": p.primary,
            "gold_detailed": g["gold_detailed"],
            "pred_detailed": p.detailed,
            "gold_is_recurring": bool(g["gold_is_recurring"]),
            "pred_is_recurring": p.is_recurring,
            "confidence": p.confidence,
            "match_type": p.match_type,
            "merchant_exact": m_exact,
            "merchant_normalized": m_norm,
            # judge fills this later for near-misses; until then it equals normalized
            "merchant_correct": bool(m_exact or m_norm),
            "judge_used": False,
            "primary_correct": p.primary == g["gold_primary"],
            "detailed_correct": p.detailed == g["gold_detailed"],
            "recurring_correct": p.is_recurring == bool(g["gold_is_recurring"]),
        })
    return pd.DataFrame(recs)


def bundle(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "merchant_exact_acc": round(df["merchant_exact"].mean(), 4),
        "merchant_correct_acc": round(df["merchant_correct"].mean(), 4),
        "primary_acc": round(df["primary_correct"].mean(), 4),
        "detailed_acc": round(df["detailed_correct"].mean(), 4),
        "merchant_coverage": round((df["pred_merchant"] != "Unknown").mean(), 4),
        "recurring": M.binary_prf(list(df["gold_is_recurring"]), list(df["pred_is_recurring"])),
    }


def segment(df: pd.DataFrame, col: str) -> dict:
    return {str(v): bundle(df[df[col] == v]) for v in sorted(df[col].unique())}


def segment_tags(df: pd.DataFrame) -> dict:
    out = {}
    all_tags = sorted({t for tags in df["pattern_tags"] for t in str(tags).split(";") if t})
    for tag in all_tags:
        mask = df["pattern_tags"].apply(lambda s: tag in str(s).split(";"))
        out[tag] = bundle(df[mask])
    return out


def compute_metrics(df: pd.DataFrame) -> dict:
    overall = bundle(df)
    overall["ece_merchant"], overall["reliability"] = M.expected_calibration_error(
        list(df["confidence"]), list(df["merchant_correct"]))
    return {
        "overall": overall,
        "by_difficulty": segment(df, "difficulty"),
        "by_pattern_tag": segment_tags(df),
        "by_primary": segment(df, "gold_primary"),
        "by_amount_bucket": segment(df, "amount_bucket"),
        "by_match_type": segment(df, "match_type"),
    }


def run(version: int):
    os.makedirs(REPORTS, exist_ok=True)
    df = score_rows(version)
    df.to_csv(os.path.join(REPORTS, f"predictions_v{version}.csv"), index=False)
    mtr = compute_metrics(df)
    with open(os.path.join(REPORTS, f"metrics_v{version}.json"), "w") as f:
        json.dump(mtr, f, indent=2)
    o = mtr["overall"]
    print(f"[v{version}] n={o['n']}  merchant(exact/correct)={o['merchant_exact_acc']:.2f}/"
          f"{o['merchant_correct_acc']:.2f}  primary={o['primary_acc']:.2f}  detailed={o['detailed_acc']:.2f}"
          f"  recurring_F1={o['recurring']['f1']:.2f}  ECE={o['ece_merchant']:.3f}")
    return df, mtr


if __name__ == "__main__":
    versions = [int(sys.argv[1])] if len(sys.argv) > 1 else [1, 2]
    for v in versions:
        run(v)
