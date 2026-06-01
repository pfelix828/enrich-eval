"""
Merchant-equivalence judge + its validation.

Exact and normalized matching miss a real category of correct answers: the predicted merchant
means the same thing as the gold merchant but in a different surface form ("Blue Bottle" vs
"Blue Bottle Coffee"). A judge decides semantic equivalence for those near-misses.

The crucial discipline, and the reason this file exists, is that *you do not trust a judge you have
not measured*. data/judge_validation.csv holds human verdicts on 24 merchant pairs, including the
adversarial cases where surface overlap is misleading (Amazon vs Amazon Prime, Uber vs Uber Eats).
validate() reports the judge's agreement and Cohen's kappa against those human labels. A judge that
cannot beat that bar is not allowed to relabel the eval.

Default judge is deterministic (free, reproducible). ENRICH_JUDGE=claude swaps in a Claude judge;
the validation harness is identical either way.
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import normalize_merchant

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
REPORTS = os.path.join(HERE, "reports")

# Generic words that don't change merchant identity when added/removed.
_GENERIC = {"coffee", "cafe", "gas", "pharmacy", "store", "inc", "llc", "co", "the", "us", "mktp"}
# Modifiers that DO change identity: they name a distinct product/sub-brand, not the same merchant.
_DISTINGUISHING = {"prime", "eats", "video", "music", "plus", "pro", "one", "max", "go", "wallet"}
# A few brand aliases the token logic can't infer, stored in normalized form. Deliberately partial:
# Comcast/Xfinity and BART expansion are left out, so the judge keeps a realistic blind spot
# (knowledge-base gaps) that the validation exposes and that motivates an LLM judge.
_ALIASES = {("applecom", "apple")}


def _toks(s: str) -> set:
    return set(normalize_merchant(s).split())


def judge_equivalent_rules(pred: str, gold: str) -> bool:
    np_, ng = normalize_merchant(pred), normalize_merchant(gold)
    if np_ == ng:
        return True
    if (np_, ng) in _ALIASES or (ng, np_) in _ALIASES:
        return True
    tp, tg = _toks(pred), _toks(gold)
    if not tp or not tg:
        return False
    # the tokens that differ between the two names
    diff = tp.symmetric_difference(tg)
    # a distinguishing modifier in the difference means they are NOT the same entity
    if diff & _DISTINGUISHING:
        return False
    # strip generic words, then check subset (one name is the other plus only generic words)
    cp, cg = tp - _GENERIC, tg - _GENERIC
    if cp and cg and (cp <= cg or cg <= cp):
        return True
    return False


class ClaudeJudge:
    PROMPT = (
        "Do these two strings refer to the SAME consumer-facing merchant brand? Answer only 'yes' "
        "or 'no'. A specific product or sub-brand (Amazon Prime, Uber Eats, Apple Music) is NOT the "
        "same as its parent. A payment aggregator is NOT the same as the merchant it masks.\n"
        "A: {a}\nB: {b}"
    )

    def __init__(self, model: str = "claude-sonnet-4-6"):
        from anthropic import Anthropic
        self.client = Anthropic()
        self.model = model

    def __call__(self, pred: str, gold: str) -> bool:
        msg = self.client.messages.create(
            model=self.model, max_tokens=5,
            messages=[{"role": "user", "content": self.PROMPT.format(a=pred, b=gold)}])
        return msg.content[0].text.strip().lower().startswith("y")


def get_judge():
    if os.environ.get("ENRICH_JUDGE", "rules").lower() == "claude":
        return ClaudeJudge()
    return judge_equivalent_rules


def validate(judge=None) -> dict:
    judge = judge or get_judge()
    df = pd.read_csv(os.path.join(DATA, "judge_validation.csv"))
    human = df["human_equivalent"].astype(bool).tolist()
    pred = [judge(r.pred_merchant, r.gold_merchant) for r in df.itertuples()]
    agree = sum(int(h == p) for h, p in zip(human, pred)) / len(human)
    kappa = cohen_kappa_score(human, pred)
    disagreements = [
        {"pred_merchant": df.iloc[i].pred_merchant, "gold_merchant": df.iloc[i].gold_merchant,
         "human": human[i], "judge": pred[i], "note": df.iloc[i].note}
        for i in range(len(human)) if human[i] != pred[i]
    ]
    return {"n_pairs": len(human), "agreement": round(agree, 4), "cohen_kappa": round(float(kappa), 4),
            "disagreements": disagreements}


def apply_to_predictions(version: int, judge=None) -> int:
    """Upgrade merchant_correct for rows that exact/normalized matching missed but the judge accepts.
    Returns the number of rows the judge flipped. Honest by construction: only flips False->True when
    the judge says the near-miss is semantically equivalent."""
    judge = judge or get_judge()
    path = os.path.join(REPORTS, f"predictions_v{version}.csv")
    df = pd.read_csv(path)
    flipped = 0
    for i, r in df.iterrows():
        if not r["merchant_correct"] and r["pred_merchant"] != "Unknown":
            if judge(r["pred_merchant"], r["gold_merchant"]):
                df.at[i, "merchant_correct"] = True
                df.at[i, "judge_used"] = True
                flipped += 1
    df.to_csv(path, index=False)
    return flipped


if __name__ == "__main__":
    os.makedirs(REPORTS, exist_ok=True)
    res = validate()
    with open(os.path.join(REPORTS, "judge_validation.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(f"judge validation: n={res['n_pairs']} agreement={res['agreement']:.2f} "
          f"kappa={res['cohen_kappa']:.2f}")
    for d in res["disagreements"]:
        print(f"  MISS: {d['pred_merchant']} ~ {d['gold_merchant']} | human={d['human']} "
              f"judge={d['judge']} ({d['note']})")
    for v in (1, 2):
        if os.path.exists(os.path.join(REPORTS, f"predictions_v{v}.csv")):
            n = apply_to_predictions(v)
            print(f"  v{v}: judge upgraded {n} near-miss merchant rows")
