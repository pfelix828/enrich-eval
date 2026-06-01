"""
Render the eval figures into reports/figures/. All numbers come from the computed artifacts; every
figure carries the synthetic-data caveat so no chart can be mistaken for production quality.

Usage:  python src/make_figures.py
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(HERE, "reports")
FIGS = os.path.join(REPORTS, "figures")

CAVEAT = "Synthetic descriptors for real merchants; methodology demo, not production metrics."


def _caption(fig):
    fig.text(0.5, 0.005, CAVEAT, ha="center", fontsize=7, color="gray")


def _load(name):
    with open(os.path.join(REPORTS, name)) as f:
        return json.load(f)


def fig_accuracy():
    # Recurring is deliberately excluded here: it's a property of a transaction SERIES, not a single
    # string, so its score is not a meaningful single-transaction metric. It lives in findings.md as a
    # failure-mode demonstration, not a headline number.
    m1, m2 = _load("metrics_v1.json")["overall"], _load("metrics_v2.json")["overall"]
    fields = ["merchant_correct_acc", "primary_acc", "detailed_acc"]
    labels = ["Merchant", "Primary cat", "Detailed cat"]
    v1 = [m1[f] for f in fields]
    v2 = [m2[f] for f in fields]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([i - 0.2 for i in x], v1, width=0.4, label="v1 (baseline)", color="#bbbbbb")
    ax.bar([i + 0.2 for i in x], v2, width=0.4, label="v2 (improved)", color="#2a7ae2")
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05); ax.set_ylabel("Accuracy")
    ax.set_title("Merchant & category quality: v1 vs v2")
    for i, (a, b) in enumerate(zip(v1, v2)):
        ax.text(i - 0.2, a + 0.02, f"{a:.2f}", ha="center", fontsize=8)
        ax.text(i + 0.2, b + 0.02, f"{b:.2f}", ha="center", fontsize=8)
    ax.legend()
    fig.tight_layout(rect=[0, 0.03, 1, 1]); _caption(fig)
    fig.savefig(os.path.join(FIGS, "accuracy_v1_v2.png"), dpi=130); plt.close(fig)


def fig_by_pattern_tag():
    m = _load("metrics_v2.json")["by_pattern_tag"]
    tags = sorted(m, key=lambda t: m[t]["detailed_acc"])
    accs = [m[t]["detailed_acc"] for t in tags]
    ns = [m[t]["n"] for t in tags]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["#d9534f" if a < 0.8 else "#5cb85c" for a in accs]
    ax.barh(range(len(tags)), accs, color=colors)
    ax.set_yticks(range(len(tags)))
    ax.set_yticklabels([f"{t} (n={n})" for t, n in zip(tags, ns)])
    ax.set_xlim(0, 1.05); ax.set_xlabel("Detailed-category accuracy (v2)")
    ax.set_title("Where v2 breaks: detailed accuracy by descriptor pattern")
    for i, a in enumerate(accs):
        ax.text(a + 0.01, i, f"{a:.2f}", va="center", fontsize=8)
    fig.tight_layout(rect=[0, 0.03, 1, 1]); _caption(fig)
    fig.savefig(os.path.join(FIGS, "by_pattern_tag.png"), dpi=130); plt.close(fig)


def fig_calibration():
    rel = _load("metrics_v2.json")["overall"]["reliability"]
    ece = _load("metrics_v2.json")["overall"]["ece_merchant"]
    pts = [(r["avg_conf"], r["accuracy"], r["n"]) for r in rel if r["n"] > 0]
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect calibration")
    if pts:
        xs, ys, ns = zip(*pts)
        ax.scatter(xs, ys, s=[n * 40 for n in ns], color="#2a7ae2", alpha=0.7, label="conf bin (size=n)")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("Mean confidence"); ax.set_ylabel("Actual accuracy")
    ax.set_title(f"Calibration of merchant confidence (ECE={ece:.3f})")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout(rect=[0, 0.03, 1, 1]); _caption(fig)
    fig.savefig(os.path.join(FIGS, "calibration.png"), dpi=130); plt.close(fig)


def fig_confidence_by_matchtype():
    df = pd.read_csv(os.path.join(REPORTS, "predictions_v2.csv"))
    g = df.groupby("match_type").agg(
        mean_conf=("confidence", "mean"), accuracy=("merchant_correct", "mean"), n=("id", "count")
    ).reset_index().sort_values("mean_conf")
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(g))
    ax.bar([i - 0.2 for i in x], g["mean_conf"], width=0.4, label="stated confidence", color="#f0ad4e")
    ax.bar([i + 0.2 for i in x], g["accuracy"], width=0.4, label="actual accuracy", color="#2a7ae2")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{t}\n(n={n})" for t, n in zip(g['match_type'], g['n'])])
    ax.set_ylim(0, 1.05); ax.set_ylabel("Confidence / accuracy")
    ax.set_title("Confidence vs reality by resolution path (gaps = mis-calibration)")
    ax.legend()
    fig.tight_layout(rect=[0, 0.03, 1, 1]); _caption(fig)
    fig.savefig(os.path.join(FIGS, "confidence_by_matchtype.png"), dpi=130); plt.close(fig)


def main():
    os.makedirs(FIGS, exist_ok=True)
    fig_accuracy()
    fig_by_pattern_tag()
    fig_calibration()
    fig_confidence_by_matchtype()
    print(f"wrote 4 figures -> {FIGS}")


if __name__ == "__main__":
    main()
