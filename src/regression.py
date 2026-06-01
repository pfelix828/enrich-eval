"""
Regression diff between two enricher versions: the "CI for model quality" piece.

A new model version that improves the average can still silently break a segment. This joins the
per-row predictions of v1 and v2 and reports, for every quality field:
  - net change in accuracy
  - rows that improved (was wrong, now right)
  - rows that REGRESSED (was right, now wrong)  <- the ones a release gate should block on
plus per-pattern-tag accuracy deltas so a localized regression can't hide inside a global gain.

Usage:  python src/regression.py            # compares v1 -> v2
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(HERE, "reports")

FIELDS = ["merchant_correct", "primary_correct", "detailed_correct", "recurring_correct"]


def diff(old: int = 1, new: int = 2) -> dict:
    a = pd.read_csv(os.path.join(REPORTS, f"predictions_v{old}.csv")).set_index("id")
    b = pd.read_csv(os.path.join(REPORTS, f"predictions_v{new}.csv")).set_index("id")
    j = a.join(b, lsuffix="_old", rsuffix="_new")

    field_summary = {}
    regressions = []
    for f in FIELDS:
        fo, fn = f"{f}_old", f"{f}_new"
        improved = j[~j[fo] & j[fn]]
        regressed = j[j[fo] & ~j[fn]]
        field_summary[f] = {
            "acc_old": round(j[fo].mean(), 4),
            "acc_new": round(j[fn].mean(), 4),
            "delta": round(j[fn].mean() - j[fo].mean(), 4),
            "improved": int(len(improved)),
            "regressed": int(len(regressed)),
        }
        for rid, r in regressed.iterrows():
            regressions.append({
                "id": rid, "field": f, "raw_descriptor": r["raw_descriptor_old"],
                "pattern_tags": r["pattern_tags_old"],
                "old": f"{r['pred_merchant_old']} / {r['pred_primary_old']}",
                "new": f"{r['pred_merchant_new']} / {r['pred_primary_new']}",
            })

    # per-pattern-tag detailed-accuracy deltas
    tag_delta = {}
    all_tags = sorted({t for tags in j["pattern_tags_old"] for t in str(tags).split(";") if t})
    for tag in all_tags:
        mask = j["pattern_tags_old"].apply(lambda s: tag in str(s).split(";"))
        sub = j[mask]
        if len(sub):
            tag_delta[tag] = {
                "n": int(len(sub)),
                "detailed_old": round(sub["detailed_correct_old"].mean(), 3),
                "detailed_new": round(sub["detailed_correct_new"].mean(), 3),
                "delta": round(sub["detailed_correct_new"].mean() - sub["detailed_correct_old"].mean(), 3),
            }

    return {"old": old, "new": new, "fields": field_summary,
            "regressions": regressions, "by_pattern_tag_detailed": tag_delta}


def print_summary(d: dict):
    print(f"=== regression diff: v{d['old']} -> v{d['new']} ===")
    for f, s in d["fields"].items():
        print(f"  {f:20} {s['acc_old']:.2f} -> {s['acc_new']:.2f} ({s['delta']:+.2f})"
              f"  improved={s['improved']} regressed={s['regressed']}")
    if d["regressions"]:
        print("  --- REGRESSED ROWS (was right in old, wrong in new) ---")
        for r in d["regressions"]:
            print(f"    [{r['field']}] {r['raw_descriptor']}  ({r['old']}  ->  {r['new']})")
    neg = {t: v for t, v in d["by_pattern_tag_detailed"].items() if v["delta"] < 0}
    if neg:
        print("  --- pattern tags where detailed accuracy DROPPED ---")
        for t, v in neg.items():
            print(f"    {t}: {v['detailed_old']:.2f} -> {v['detailed_new']:.2f} (n={v['n']})")


if __name__ == "__main__":
    os.makedirs(REPORTS, exist_ok=True)
    d = diff(1, 2)
    with open(os.path.join(REPORTS, "regression_v1_to_v2.json"), "w") as f:
        json.dump(d, f, indent=2)
    print_summary(d)
