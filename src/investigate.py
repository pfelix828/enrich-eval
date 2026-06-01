"""
Complaint -> structured root-cause investigation.

This is the hook. A customer says something vague ("your categorization is wrong for my users").
This turns that into an actionable report: which transactions are affected, what the errors cluster
into, which cluster to fix first (ranked by volume x how confidently-wrong the system was), and a
concrete recommendation per cluster.

Routing the complaint to a focus (merchant / category / recurring) is keyword-based by default; a
Claude router is available behind ENRICH_ROUTER=claude. The clustering and ranking are deterministic
so the report is reproducible and defensible.

Usage:
  python src/investigate.py "categorization is wrong for a lot of my users"
  python src/investigate.py "merchant names look messy" --version 2 --filter "amount < 50"
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(HERE, "reports")

# Priority order for assigning a single primary cause to a multi-tagged error row.
CAUSE_PRIORITY = [
    "aggregator_masked", "ambiguous_category", "processor_prefix",
    "allcaps_truncated", "store_id_noise", "city_state_suffix", "recurring_cue", "clean",
]

CAUSE_FIX = {
    "coverage_gap": "The merchant was not resolved at all (blank/Unknown). This is a knowledge-base "
                    "coverage gap, not a parsing bug. Add these merchants to the KB or fall back to a "
                    "cleaned descriptor string rather than emitting nothing.",
    "aggregator_masked": "True merchant is unrecoverable from the descriptor (a platform masks it). "
                         "Stop guessing the underlying merchant; label the platform and expose a "
                         "lower-confidence flag so customers can handle it downstream.",
    "ambiguous_category": "The category is genuinely contestable. Add an explicit tie-break rule to "
                          "the labeling rubric and encode it, rather than letting the model guess.",
    "processor_prefix": "A payment-processor prefix is defeating merchant resolution. Extend the "
                        "prefix-stripping rules to cover these processors before lookup.",
    "allcaps_truncated": "Truncation/casing is breaking lookup. Add fuzzy/normalized matching for "
                         "clipped tokens.",
    "store_id_noise": "Store IDs and reference numbers are leaking into matching. Strengthen the "
                      "noise-stripping pass.",
    "city_state_suffix": "Trailing city/state tokens are interfering with resolution. Strip them "
                         "before lookup.",
    "recurring_cue": "Recurring detection is missing scheduled-charge cues. Expand the cue list and "
                     "incorporate transaction history.",
    "clean": "Clean strings are failing, which points at coverage gaps in the merchant knowledge "
             "base rather than parsing.",
}

FOCI = {
    "merchant": {"keys": ["merchant", "name", "messy", "wrong merchant"], "col": "merchant_correct",
                 "label": "merchant-name"},
    "category": {"keys": ["categor", "category", "miscategor", "wrong category", "bucket"],
                 "col": "category_correct", "label": "categorization"},
    "recurring": {"keys": ["recur", "subscription", "subscriptions", "renew"],
                  "col": "recurring_correct", "label": "recurring-detection"},
}


def route_complaint(complaint: str) -> str:
    c = complaint.lower()
    for focus, spec in FOCI.items():
        if any(k in c for k in spec["keys"]):
            return focus
    return "category"  # most common enrichment complaint


def primary_cause(tags: str, pred_merchant: str = "") -> str:
    # an unresolved merchant is a coverage gap, regardless of the descriptor's surface pattern
    if str(pred_merchant) == "Unknown":
        return "coverage_gap"
    present = str(tags).split(";")
    for cause in CAUSE_PRIORITY:
        if cause in present:
            return cause
    return "clean"


def investigate(complaint: str, version: int = 2, filter_expr: str | None = None) -> dict:
    df = pd.read_csv(os.path.join(REPORTS, f"predictions_v{version}.csv"))
    # category_correct = both levels right
    df["category_correct"] = df["primary_correct"] & df["detailed_correct"]
    population = len(df)
    if filter_expr:
        df = df.query(filter_expr)

    focus = route_complaint(complaint)
    col = FOCI[focus]["col"]
    n = len(df)
    errors = df[~df[col]].copy()
    err_n = len(errors)
    accuracy = round(1 - err_n / n, 4) if n else None

    clusters = []
    if err_n:
        errors["cause"] = errors.apply(
            lambda r: primary_cause(r["pattern_tags"], r["pred_merchant"]), axis=1)
        for cause, grp in errors.groupby("cause"):
            mean_conf = round(grp["confidence"].mean(), 3)
            # impact: more errors and more confidently-wrong = worse (confident errors reach customers)
            impact = round(len(grp) * (0.5 + mean_conf), 2)
            clusters.append({
                "cause": cause,
                "n_errors": int(len(grp)),
                "share_of_errors": round(len(grp) / err_n, 3),
                "mean_confidence": mean_conf,
                "impact_score": impact,
                "examples": grp["raw_descriptor"].head(3).tolist(),
                "recommendation": CAUSE_FIX[cause],
            })
        clusters.sort(key=lambda c: c["impact_score"], reverse=True)

    return {
        "complaint": complaint, "version": version, "filter": filter_expr,
        "routed_focus": focus, "focus_label": FOCI[focus]["label"],
        "population": population, "scope_n": n, "errors": err_n, "accuracy_in_scope": accuracy,
        "clusters": clusters,
    }


def to_markdown(rep: dict) -> str:
    L = []
    L.append(f"# Investigation: {rep['focus_label']} quality")
    L.append(f"\n**Complaint:** \"{rep['complaint']}\"")
    scope = f"{rep['scope_n']} transactions"
    if rep["filter"]:
        scope += f" (filtered: `{rep['filter']}`, from {rep['population']} total)"
    L.append(f"\n**Routed to:** {rep['focus_label']} errors  |  **Scope:** {scope}")
    acc = rep["accuracy_in_scope"]
    L.append(f"\n**Headline:** {rep['focus_label']} accuracy in scope is "
             f"**{acc:.0%}** ({rep['errors']} of {rep['scope_n']} wrong).")
    if not rep["clusters"]:
        L.append("\nNo errors found in scope. The complaint is not reproduced by the current eval set.")
        return "\n".join(L)
    L.append("\n## Error clusters, ranked by impact (volume x confidently-wrong)\n")
    L.append("| Rank | Root cause | Errors | % of errors | Mean conf | Impact |")
    L.append("|---|---|---|---|---|---|")
    for i, c in enumerate(rep["clusters"], 1):
        L.append(f"| {i} | `{c['cause']}` | {c['n_errors']} | {c['share_of_errors']:.0%} "
                 f"| {c['mean_confidence']:.2f} | {c['impact_score']} |")
    top = rep["clusters"][0]
    L.append(f"\n## Fix this first: `{top['cause']}`")
    L.append(f"\nIt is {top['share_of_errors']:.0%} of the errors in scope, and the system was "
             f"{top['mean_confidence']:.0%} confident while wrong, so these reach customers.")
    L.append(f"\nExamples: " + ", ".join(f"`{e}`" for e in top["examples"]))
    L.append(f"\n**Recommendation:** {top['recommendation']}")
    L.append("\n## All recommendations\n")
    for c in rep["clusters"]:
        L.append(f"- **`{c['cause']}`** ({c['n_errors']} errors): {c['recommendation']}")
    return "\n".join(L)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("complaint")
    ap.add_argument("--version", type=int, default=2)
    ap.add_argument("--filter", default=None)
    args = ap.parse_args()

    rep = investigate(args.complaint, args.version, args.filter)
    md = to_markdown(rep)
    os.makedirs(REPORTS, exist_ok=True)
    out = os.path.join(REPORTS, f"investigation_{_slug(args.complaint)}.md")
    with open(out, "w") as f:
        f.write(md)
    print(md)
    print(f"\n[saved -> {out}]")
