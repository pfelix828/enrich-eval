"""Export web-ready JSON for the Next.js app in web/.

Everything is derived from the same artifacts the Streamlit app reads
(reports/*.json, reports/predictions_v{1,2}.csv) plus three precomputed
investigations run through the real engine in investigate.py. No number in
the web app exists that this script did not compute from those sources.

Usage: .venv/bin/python src/export_web.py
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

from investigate import FOCI, investigate, primary_cause  # noqa: E402

REPORTS = os.path.join(HERE, "reports")
OUT = os.path.join(HERE, "web", "src", "data")

CANNED_COMPLAINTS = [
    "The merchant names my users see are messy",
    "Your categorization is wrong for a lot of my users",
    "Subscriptions aren't being flagged as recurring",
]

MAX_ROWS_PER_CLUSTER = 8


def load(name: str):
    with open(os.path.join(REPORTS, name)) as f:
        return json.load(f)


def slice_rows(slice_dict: dict) -> list[dict]:
    """Flatten a metrics slice ({key: {n, ...metrics}}) into chart-ready rows."""
    rows = []
    for key, m in slice_dict.items():
        rows.append({
            "key": key,
            "n": m["n"],
            "merchant_acc": m["merchant_correct_acc"],
            "primary_acc": m["primary_acc"],
            "detailed_acc": m["detailed_acc"],
            "coverage": m["merchant_coverage"],
        })
    return rows


def cluster_rows(version: int, focus: str, cause: str) -> list[dict]:
    """Full error rows behind one investigation cluster, for the detail table."""
    df = pd.read_csv(os.path.join(REPORTS, f"predictions_v{version}.csv"))
    df["category_correct"] = df["primary_correct"] & df["detailed_correct"]
    col = FOCI[focus]["col"]
    errors = df[~df[col]].copy()
    errors["cause"] = errors.apply(
        lambda r: primary_cause(r["pattern_tags"], r["pred_merchant"]), axis=1
    )
    rows = errors[errors["cause"] == cause]
    out = []
    for _, r in rows.head(MAX_ROWS_PER_CLUSTER).iterrows():
        out.append({
            "descriptor": r["raw_descriptor"],
            "gold_merchant": r["gold_merchant"],
            "pred_merchant": r["pred_merchant"],
            "gold_category": f'{r["gold_primary"]} / {r["gold_detailed"]}',
            "pred_category": f'{r["pred_primary"]} / {r["pred_detailed"]}',
            "gold_recurring": bool(r["gold_is_recurring"]),
            "pred_recurring": bool(r["pred_is_recurring"]),
            "confidence": round(float(r["confidence"]), 2),
        })
    return out


def match_type_profile(version: int) -> list[dict]:
    df = pd.read_csv(os.path.join(REPORTS, f"predictions_v{version}.csv"))
    out = []
    for mt, grp in df.groupby("match_type"):
        out.append({
            "match_type": mt,
            "n": int(len(grp)),
            "mean_confidence": round(float(grp["confidence"].mean()), 3),
            "accuracy": round(float(grp["merchant_correct"].mean()), 3),
        })
    out.sort(key=lambda r: r["n"], reverse=True)
    return out


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    v1, v2 = load("metrics_v1.json"), load("metrics_v2.json")

    # --- scorecard.json ---
    scorecard = {
        "overall": {
            "v1": {k: v1["overall"][k] for k in
                   ["n", "merchant_correct_acc", "primary_acc", "detailed_acc", "merchant_coverage"]},
            "v2": {k: v2["overall"][k] for k in
                   ["n", "merchant_correct_acc", "primary_acc", "detailed_acc", "merchant_coverage"]},
        },
        "by_pattern_tag": {
            "v1": slice_rows(v1["by_pattern_tag"]),
            "v2": slice_rows(v2["by_pattern_tag"]),
        },
        "slices": {
            name: {"v1": slice_rows(v1[name]), "v2": slice_rows(v2[name])}
            for name in ["by_difficulty", "by_primary", "by_amount_bucket", "by_match_type"]
        },
    }

    # --- calibration.json ---
    calibration = {
        "ece_v2": v2["overall"]["ece_merchant"],
        "reliability_v2": [b for b in v2["overall"]["reliability"] if b["n"] > 0],
        "match_type_profile_v2": match_type_profile(2),
        "match_type_profile_v1": match_type_profile(1),
    }

    # --- regression.json (enrich each regression with before/after rows) ---
    reg = load("regression_v1_to_v2.json")
    p1 = pd.read_csv(os.path.join(REPORTS, "predictions_v1.csv")).set_index("id")
    p2 = pd.read_csv(os.path.join(REPORTS, "predictions_v2.csv")).set_index("id")
    detailed_regressions = []
    for r in reg["regressions"]:
        rid = r["id"]
        detailed_regressions.append({
            **r,
            "gold_merchant": p2.loc[rid, "gold_merchant"],
            "v1_pred_merchant": p1.loc[rid, "pred_merchant"],
            "v2_pred_merchant": p2.loc[rid, "pred_merchant"],
            "gold_category": f'{p2.loc[rid, "gold_primary"]} / {p2.loc[rid, "gold_detailed"]}',
            "v1_pred_category": f'{p1.loc[rid, "pred_primary"]} / {p1.loc[rid, "pred_detailed"]}',
            "v2_pred_category": f'{p2.loc[rid, "pred_primary"]} / {p2.loc[rid, "pred_detailed"]}',
            "v1_recurring": bool(p1.loc[rid, "pred_is_recurring"]),
            "v2_recurring": bool(p2.loc[rid, "pred_is_recurring"]),
            "gold_recurring": bool(p2.loc[rid, "gold_is_recurring"]),
        })
    regression = {"fields": reg["fields"], "regressions": detailed_regressions}

    # --- judge.json ---
    judge = load("judge_validation.json")

    # --- investigations.json (run the real engine for 3 canned complaints) ---
    investigations = []
    for complaint in CANNED_COMPLAINTS:
        rep = investigate(complaint, version=2)
        for cluster in rep["clusters"]:
            cluster["rows"] = cluster_rows(2, rep["routed_focus"], cluster["cause"])
        investigations.append(rep)

    # --- meta.json ---
    meta = {
        "seed_n": v2["overall"]["n"],
        "dataNote": ("All numbers come from a 55-row seed of synthetic transaction descriptors for "
                     "real merchants, scored by a deterministic rules enricher. This is a methodology "
                     "demonstration, not production metrics — the point is the method, not the magnitude."),
        "versions": {"v1": "baseline rules enricher", "v2": "v1 + aggregator awareness, fuller "
                     "merchant knowledge base, more processor prefixes, richer recurring cues"},
    }

    for name, obj in [
        ("scorecard.json", scorecard), ("calibration.json", calibration),
        ("regression.json", regression), ("judge.json", judge),
        ("investigations.json", investigations), ("meta.json", meta),
    ]:
        path = os.path.join(OUT, name)
        with open(path, "w") as f:
            json.dump(obj, f, indent=1)
        print(f"{name}: {os.path.getsize(path) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
