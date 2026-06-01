"""
EnrichEval — Streamlit demo for the transaction-enrichment quality lab.

Run:  ./.venv/bin/streamlit run app.py
Reads precomputed artifacts from reports/. Run `python src/run_all.py` first to (re)build them.
"""

import json
import os
import sys

import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")
FIGS = os.path.join(REPORTS, "figures")
sys.path.insert(0, os.path.join(HERE, "src"))

from enrich import Enricher          # noqa: E402
from investigate import investigate, to_markdown  # noqa: E402

st.set_page_config(page_title="EnrichEval", layout="wide")

CAVEAT = ("Data note: descriptors are synthetic strings for real merchants, formatted like real bank "
          "descriptors. They are not real cardholder data. This is a methodology demo, not production "
          "metrics.")


def load(name):
    p = os.path.join(REPORTS, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def fig(name):
    p = os.path.join(FIGS, name)
    if os.path.exists(p):
        st.image(p, use_container_width=True)
    else:
        st.info(f"Missing figure {name}. Run `python src/run_all.py`.")


st.sidebar.title("EnrichEval")
st.sidebar.caption("A quality lab for transaction enrichment")
page = st.sidebar.radio("View", ["Overview", "Investigate (the hook)", "Segments",
                                 "Calibration", "Regression", "Judge"])
st.sidebar.warning(CAVEAT)

# ---------------------------------------------------------------------------------------------------
if page == "Overview":
    st.title("Measuring whether an AI enrichment system is actually good")
    st.write("Enrichment turns a raw bank string like `SQ *BLUE BOTTLE COFFEE OAKLAND CA` into a clean "
             "merchant, a category, and a recurring flag. This project does not try to build the best "
             "enricher. It builds the harness that tells you, in a principled way, where an enricher "
             "is wrong and what to fix first.")
    m1, m2 = load("metrics_v1.json"), load("metrics_v2.json")
    if m2:
        o1, o2 = m1["overall"], m2["overall"]
        c = st.columns(4)
        c[0].metric("Merchant accuracy", f"{o2['merchant_correct_acc']:.0%}", f"{o2['merchant_correct_acc']-o1['merchant_correct_acc']:+.0%} vs v1")
        c[1].metric("Detailed category", f"{o2['detailed_acc']:.0%}", f"{o2['detailed_acc']-o1['detailed_acc']:+.0%} vs v1")
        c[2].metric("Recurring F1", f"{o2['recurring']['f1']:.2f}")
        c[3].metric("Merchant ECE", f"{o2['ece_merchant']:.3f}", help="Expected calibration error; lower is better")
    fig("accuracy_v1_v2.png")
    st.subheader("Try the enricher live")
    d = st.text_input("Raw descriptor", "DD *DOORDASH SUSHIYA")
    if d:
        p = Enricher(version=2).enrich(d)
        st.json({"merchant": p.merchant, "primary": p.primary, "detailed": p.detailed,
                 "is_recurring": p.is_recurring, "confidence": p.confidence, "match_type": p.match_type})

# ---------------------------------------------------------------------------------------------------
elif page == "Investigate (the hook)":
    st.title("Complaint → structured root-cause")
    st.write("A customer says something vague. The harness routes it to the right error type, clusters "
             "the failures by root cause, and ranks what to fix first by volume and how confidently the "
             "system was wrong.")
    complaint = st.text_area("Customer complaint",
                             "categorization is wrong for a lot of my users", height=80)
    col = st.columns(3)
    version = col[0].selectbox("Enricher version", [2, 1])
    use_filter = col[1].checkbox("Filter the transaction slice")
    filt = col[2].text_input("pandas filter", "amount < 50") if use_filter else None
    if st.button("Investigate", type="primary"):
        rep = investigate(complaint, version=version, filter_expr=filt)
        st.markdown(to_markdown(rep))

# ---------------------------------------------------------------------------------------------------
elif page == "Segments":
    st.title("Quality by segment")
    st.caption("Averages lie. Enrichment quality is wildly uneven across descriptor patterns.")
    fig("by_pattern_tag.png")
    m = load("metrics_v2.json")
    if m:
        which = st.selectbox("Slice by", ["by_pattern_tag", "by_primary", "by_difficulty",
                                          "by_amount_bucket", "by_match_type"])
        rows = [{"segment": k, "n": v["n"], "merchant_acc": v["merchant_correct_acc"],
                 "primary_acc": v["primary_acc"], "detailed_acc": v["detailed_acc"],
                 "recurring_f1": v["recurring"]["f1"]} for k, v in m[which].items()]
        st.dataframe(pd.DataFrame(rows).sort_values("detailed_acc"), use_container_width=True)

# ---------------------------------------------------------------------------------------------------
elif page == "Calibration":
    st.title("Does the system know when it's wrong?")
    st.write("A confidence score is only useful if it tracks reality. Two views: the reliability "
             "diagram, and confidence vs actual accuracy along each resolution path.")
    c = st.columns(2)
    with c[0]:
        fig("calibration.png")
    with c[1]:
        fig("confidence_by_matchtype.png")
    st.info("Finding: the `keyword` fallback path is badly overconfident, and `aggregator` is "
            "underconfident. A single global accuracy number hides both.")

# ---------------------------------------------------------------------------------------------------
elif page == "Regression":
    st.title("CI for model quality: v1 → v2")
    d = load("regression_v1_to_v2.json")
    if d:
        rows = [{"field": f, "v1": s["acc_old"], "v2": s["acc_new"], "delta": s["delta"],
                 "improved": s["improved"], "regressed": s["regressed"]}
                for f, s in d["fields"].items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.subheader("Regressed rows — right in v1, wrong in v2")
        if d["regressions"]:
            st.dataframe(pd.DataFrame(d["regressions"]), use_container_width=True)
            st.warning("v2 improves every average yet breaks `PYPL *STEAMGAMES`: the new aggregator "
                       "rule over-applies and masks Steam as PayPal. A release gate should flag this.")
        else:
            st.success("No regressions.")

# ---------------------------------------------------------------------------------------------------
elif page == "Judge":
    st.title("You don't trust a judge you haven't measured")
    st.write("Exact and normalized matching miss semantically-equal near-misses (`Blue Bottle` vs "
             "`Blue Bottle Coffee`). A judge decides equivalence — but only after it's validated "
             "against human labels on adversarial pairs.")
    j = load("judge_validation.json")
    if j:
        c = st.columns(3)
        c[0].metric("Validation pairs", j["n_pairs"])
        c[1].metric("Agreement w/ human", f"{j['agreement']:.0%}")
        c[2].metric("Cohen's κ", f"{j['cohen_kappa']:.2f}")
        st.subheader("Where the deterministic judge still fails")
        st.dataframe(pd.DataFrame(j["disagreements"]), use_container_width=True)
        st.caption("These need a brand-alias knowledge base or an LLM judge (ENRICH_JUDGE=claude). "
                   "The kappa bar is what a stronger judge has to beat before it's allowed to relabel "
                   "the eval.")
