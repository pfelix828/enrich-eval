"""
Scoring primitives for the enrichment eval.

Merchant correctness is tiered, because "correct" is fuzzy:
  - exact_match:      strings equal after lowercasing/trimming
  - normalized_match: equal after stripping punctuation, casing, and corporate suffixes
  - (judge_match comes later, in judge.py, for semantic near-misses these two miss)

Category is scored on primary and detailed separately. Recurring is a binary classifier scored with
precision/recall/F1 on the positive class, because the classes are imbalanced and accuracy alone
would hide the failure mode that matters (missing a real subscription).
"""

from __future__ import annotations

import re

_SUFFIXES = {"inc", "llc", "co", "corp", "ltd", "the"}


def normalize_merchant(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9 ]", "", s)            # drop punctuation/apostrophes
    toks = [t for t in s.split() if t not in _SUFFIXES]
    return " ".join(toks)


def exact_match(pred: str, gold: str) -> bool:
    return pred.strip().lower() == gold.strip().lower()


def normalized_match(pred: str, gold: str) -> bool:
    return normalize_merchant(pred) == normalize_merchant(gold)


def binary_prf(y_true, y_pred, positive=True):
    """Precision/recall/F1 for the positive class, computed by hand so there are no surprises and
    no dependency on sklearn's label inference for a tiny, imbalanced set."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if p == positive and t == positive)
    fp = sum(1 for t, p in zip(y_true, y_pred) if p == positive and t != positive)
    fn = sum(1 for t, p in zip(y_true, y_pred) if p != positive and t == positive)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn, "support": tp + fn}


def expected_calibration_error(confidences, correct, n_bins=10):
    """ECE: average gap between confidence and accuracy, weighted by bin population."""
    bins = [[] for _ in range(n_bins)]
    for c, ok in zip(confidences, correct):
        idx = min(int(c * n_bins), n_bins - 1)
        bins[idx].append((c, 1 if ok else 0))
    n = len(confidences)
    ece, rows = 0.0, []
    for i, b in enumerate(bins):
        if not b:
            rows.append({"bin": i, "lo": i / n_bins, "hi": (i + 1) / n_bins, "n": 0,
                         "avg_conf": None, "accuracy": None})
            continue
        avg_conf = sum(c for c, _ in b) / len(b)
        acc = sum(o for _, o in b) / len(b)
        ece += (len(b) / n) * abs(avg_conf - acc)
        rows.append({"bin": i, "lo": i / n_bins, "hi": (i + 1) / n_bins, "n": len(b),
                     "avg_conf": round(avg_conf, 4), "accuracy": round(acc, 4)})
    return round(ece, 4), rows


def amount_bucket(amount: float) -> str:
    if amount < 10:
        return "<$10"
    if amount < 50:
        return "$10-50"
    if amount < 200:
        return "$50-200"
    return ">$200"
