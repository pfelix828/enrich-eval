"""
The enrichment system under test.

Takes a raw bank-descriptor string and returns structured fields:
    {merchant, primary, detailed, is_recurring, confidence}

This is deliberately a *baseline* enricher built from normalization + a merchant knowledge base,
not a large model. Two reasons:
  1. The deliverable of this project is the eval harness, not the model. A transparent, deterministic
     baseline makes the eval reproducible and makes its failure modes legible.
  2. It is honest about cost. The whole pipeline runs offline for free. A real Claude backend is
     wired in (ClaudeEnricher) but gated behind ENRICH_BACKEND=claude so it never runs by surprise.

Two rule versions (v1, v2) exist so the regression harness has two real systems to diff. v2 adds
aggregator awareness, more merchants, and better recurring cues. Whether v2 strictly dominates v1 is
an empirical question the eval answers, not an assumption baked in here.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

# --- knowledge base -------------------------------------------------------------------------------
# Each merchant: aliases (substrings searched in the cleaned, upper-cased descriptor), the canonical
# display name, PFC primary + detailed, and a default recurring flag (None = decide from cues).
# The KB is intentionally NOT exhaustive. The gaps are what the eval is meant to find.

MERCHANT_KB = [
    # streaming / subscriptions
    {"aliases": ["NETFLIX"], "name": "Netflix", "primary": "ENTERTAINMENT", "detailed": "ENTERTAINMENT_TV_AND_MOVIES", "recurring": True},
    {"aliases": ["SPOTIFY"], "name": "Spotify", "primary": "ENTERTAINMENT", "detailed": "ENTERTAINMENT_MUSIC_AND_AUDIO", "recurring": True},
    {"aliases": ["PRIME VIDEO"], "name": "Amazon Prime Video", "primary": "ENTERTAINMENT", "detailed": "ENTERTAINMENT_TV_AND_MOVIES", "recurring": True},
    {"aliases": ["AMAZON PRIME", "AMZN PRIME"], "name": "Amazon Prime", "primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES", "recurring": True},
    {"aliases": ["STEAMGAMES", "STEAM GAMES", "STEAM"], "name": "Steam", "primary": "ENTERTAINMENT", "detailed": "ENTERTAINMENT_VIDEO_GAMES", "recurring": None},
    # coffee / food
    {"aliases": ["BLUE BOTTLE"], "name": "Blue Bottle Coffee", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_COFFEE", "recurring": False},
    {"aliases": ["STARBUCKS"], "name": "Starbucks", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_COFFEE", "recurring": False},
    {"aliases": ["PEET'S", "PEETS"], "name": "Peet's Coffee", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_COFFEE", "recurring": False},
    {"aliases": ["TARTINE"], "name": "Tartine Bakery", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_RESTAURANT", "recurring": False},
    {"aliases": ["MCDONALD"], "name": "McDonald's", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_FAST_FOOD", "recurring": False},
    {"aliases": ["CHIPOTLE"], "name": "Chipotle", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_FAST_FOOD", "recurring": False},
    {"aliases": ["TRADER JOE"], "name": "Trader Joe's", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_GROCERIES", "recurring": False},
    {"aliases": ["SAFEWAY"], "name": "Safeway", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_GROCERIES", "recurring": False},
    # retail / superstore
    {"aliases": ["AMZN MKTP", "AMAZON.COM", "AMAZON MKTP", "AMZN.COM"], "name": "Amazon", "primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES", "recurring": False},
    {"aliases": ["TARGET"], "name": "Target", "primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_SUPERSTORES", "recurring": False},
    {"aliases": ["WAL-MART", "WALMART"], "name": "Walmart", "primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_SUPERSTORES", "recurring": False},
    {"aliases": ["COSTCO"], "name": "Costco", "primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_SUPERSTORES", "recurring": False},
    {"aliases": ["ALLBIRDS"], "name": "Allbirds", "primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_CLOTHING_AND_ACCESSORIES", "recurring": False},
    # transport
    {"aliases": ["CHEVRON"], "name": "Chevron", "primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_GAS", "recurring": False},
    {"aliases": ["SHELL"], "name": "Shell", "primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_GAS", "recurring": False},
    {"aliases": ["LYFT"], "name": "Lyft", "primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_TAXIS_AND_RIDE_SHARES", "recurring": False},
    {"aliases": ["UBER TRIP", "UBER *TRIP", "UBER TRI"], "name": "Uber", "primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_TAXIS_AND_RIDE_SHARES", "recurring": False},
    {"aliases": ["LIME"], "name": "Lime", "primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_BIKES_AND_SCOOTERS", "recurring": False},
    {"aliases": ["BART"], "name": "BART", "primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_PUBLIC_TRANSIT", "recurring": False},
    # personal care / medical
    {"aliases": ["PLANET FIT"], "name": "Planet Fitness", "primary": "PERSONAL_CARE", "detailed": "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS", "recurring": True},
    {"aliases": ["CVS"], "name": "CVS Pharmacy", "primary": "MEDICAL", "detailed": "MEDICAL_PHARMACIES_AND_SUPPLEMENTS", "recurring": False},
    # utilities / bills / loans (v2 mostly)
    {"aliases": ["PG&E", "PGANDE", "PG AND E"], "name": "PG&E", "primary": "RENT_AND_UTILITIES", "detailed": "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY", "recurring": True},
    {"aliases": ["XFINITY", "COMCAST"], "name": "Xfinity", "primary": "RENT_AND_UTILITIES", "detailed": "RENT_AND_UTILITIES_INTERNET_AND_CABLE", "recurring": True},
    {"aliases": ["VERIZON"], "name": "Verizon", "primary": "RENT_AND_UTILITIES", "detailed": "RENT_AND_UTILITIES_TELEPHONE", "recurring": True},
    {"aliases": ["TOYOTA FIN"], "name": "Toyota Financial Services", "primary": "LOAN_PAYMENTS", "detailed": "LOAN_PAYMENTS_CAR_PAYMENT", "recurring": True},
    {"aliases": ["NELNET"], "name": "Nelnet", "primary": "LOAN_PAYMENTS", "detailed": "LOAN_PAYMENTS_STUDENT_LOAN_PAYMENT", "recurring": True},
    {"aliases": ["GEICO"], "name": "GEICO", "primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_INSURANCE", "recurring": True},
    {"aliases": ["DROPBOX"], "name": "Dropbox", "primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_OTHER_GENERAL_SERVICES", "recurring": True},
    {"aliases": ["APPLE.COM"], "name": "Apple", "primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_OTHER_GENERAL_SERVICES", "recurring": True},
    # travel
    {"aliases": ["UNITED"], "name": "United Airlines", "primary": "TRAVEL", "detailed": "TRAVEL_FLIGHTS", "recurring": False},
    {"aliases": ["MARRIOTT"], "name": "Marriott", "primary": "TRAVEL", "detailed": "TRAVEL_LODGING", "recurring": False},
    {"aliases": ["AIRBNB"], "name": "Airbnb", "primary": "TRAVEL", "detailed": "TRAVEL_LODGING", "recurring": False},
]

# v1 sees only a subset of the KB (no utilities/loans/services/travel). This is the realistic state
# of a young enrichment system: good coverage of consumer brands, thin on bills.
V1_PRIMARIES = {"ENTERTAINMENT", "FOOD_AND_DRINK", "GENERAL_MERCHANDISE", "TRANSPORTATION", "PERSONAL_CARE", "MEDICAL"}

# Aggregators: the true merchant is masked behind a platform. v2 recognizes these and labels the
# platform (per the rubric); v1 does not, so it mis-parses the trailing token.
AGGREGATORS = [
    {"aliases": ["DOORDASH", "DD *"], "name": "DoorDash", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_RESTAURANT"},
    {"aliases": ["UBER EATS"], "name": "Uber Eats", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_RESTAURANT"},
    {"aliases": ["GRUBHUB"], "name": "Grubhub", "primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_RESTAURANT"},
    {"aliases": ["CASH APP", "CASH OUT"], "name": "Cash App", "primary": "TRANSFER_OUT", "detailed": "TRANSFER_OUT_OTHER_TRANSFER_OUT"},
    {"aliases": ["ZELLE"], "name": "Zelle", "primary": "TRANSFER_OUT", "detailed": "TRANSFER_OUT_OTHER_TRANSFER_OUT"},
    {"aliases": ["VENMO"], "name": "Venmo", "primary": "TRANSFER_OUT", "detailed": "TRANSFER_OUT_OTHER_TRANSFER_OUT"},
    {"aliases": ["PAYPAL", "PYPL"], "name": "PayPal", "primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE"},
]

# Keyword fallback when no merchant matches: at least guess a category from a content word.
KEYWORD_CATEGORY = [
    (["COFFEE", "CAFE"], "FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE"),
    (["NAIL", "SPA", "SALON", "BEAUTY"], "PERSONAL_CARE", "PERSONAL_CARE_HAIR_AND_BEAUTY"),
    (["DENTAL"], "MEDICAL", "MEDICAL_DENTAL_CARE"),
    (["PHARMACY"], "MEDICAL", "MEDICAL_PHARMACIES_AND_SUPPLEMENTS"),
    (["GAS", "FUEL", "OIL"], "TRANSPORTATION", "TRANSPORTATION_GAS"),
    (["RENT", "PROPERTYMGMT", "PROPERTY MGMT"], "RENT_AND_UTILITIES", "RENT_AND_UTILITIES_RENT"),
    (["MARKET", "GROCER"], "FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES"),
]

RECURRING_CUES = ["RECUR", "AUTOPAY", "MONTHLY", "SUBSCRIPTION", "CLUB FEES", "MEMBERSHIP", "EPAY"]

# noise-stripping patterns
PREFIX_PATTERNS_V2 = [r"^SQ \*", r"^TST\*\s*", r"^PYPL \*", r"^PAYPAL \*", r"^SP CHECKOUT\* ", r"^SP \*?", r"^POS DEBIT ", r"^POS ", r"^DD \*", r"^GRUBHUB\*", r"^CKE\*"]
PREFIX_PATTERNS_V1 = [r"^SQ \*"]  # v1 only knows the most common prefix

STORE_ID = re.compile(r"\b(?:#?\d{3,}|STORE \d+|F\d{4,})\b")
PHONE = re.compile(r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b|\b\d{10,}\b")
REF_ID = re.compile(r"\*[A-Z0-9]{4,}\b")
CITY_STATE = re.compile(r"\b[A-Z][A-Z ]+ (?:CA|NY|WA|TX|FL|IL|SAN FRANCISC[O]?)\b")
WEBSITE = re.compile(r"\b[A-Z0-9.]+\.(?:COM|ORG|NET)(?:/[A-Z]+)?\b")


@dataclass
class Prediction:
    merchant: str
    primary: str
    detailed: str
    is_recurring: bool
    confidence: float
    match_type: str  # how the merchant was resolved; drives confidence + is useful for slicing


def _clean(raw: str, prefixes) -> str:
    s = raw.upper()
    for pat in prefixes:
        s = re.sub(pat, "", s)
    s = WEBSITE.sub(" ", s)
    s = REF_ID.sub(" ", s)
    s = PHONE.sub(" ", s)
    s = STORE_ID.sub(" ", s)
    s = CITY_STATE.sub(" ", s)
    s = re.sub(r"[*#]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _detect_recurring(raw_upper: str, kb_default, version: int) -> bool:
    cues = RECURRING_CUES if version >= 2 else ["RECUR", "AUTOPAY"]  # v1 knows fewer cues
    if any(c in raw_upper for c in cues):
        return True
    return bool(kb_default)


class Enricher:
    """Rules enricher. version=1 is the thin baseline; version=2 adds aggregator awareness,
    full KB, more prefixes, and richer recurring cues."""

    def __init__(self, version: int = 2):
        self.version = version
        self.prefixes = PREFIX_PATTERNS_V2 if version >= 2 else PREFIX_PATTERNS_V1
        self.kb = MERCHANT_KB if version >= 2 else [m for m in MERCHANT_KB if m["primary"] in V1_PRIMARIES]

    def enrich(self, descriptor: str, amount: float | None = None) -> Prediction:
        raw_upper = descriptor.upper()

        # 1. aggregators first (v2 only). The merchant is the platform; category is the platform's guess.
        if self.version >= 2:
            for agg in AGGREGATORS:
                if any(a in raw_upper for a in agg["aliases"]):
                    rec = _detect_recurring(raw_upper, False, self.version)
                    return Prediction(agg["name"], agg["primary"], agg["detailed"], rec, 0.60, "aggregator")

        cleaned = _clean(descriptor, self.prefixes)

        # 2. merchant KB lookup
        for m in self.kb:
            for alias in m["aliases"]:
                if alias in raw_upper or alias in cleaned:
                    # confidence reflects how much noise we had to strip to find the merchant
                    if cleaned == m["aliases"][0] or raw_upper.strip() == m["name"].upper():
                        conf, mt = 0.95, "exact"
                    else:
                        conf, mt = 0.85, "normalized"
                    rec = _detect_recurring(raw_upper, m["recurring"], self.version)
                    return Prediction(m["name"], m["primary"], m["detailed"], rec, conf, mt)

        # 3. keyword category fallback: no merchant, but guess a category from a content word
        for words, primary, detailed in KEYWORD_CATEGORY:
            if any(w in cleaned for w in words):
                rec = _detect_recurring(raw_upper, False, self.version)
                return Prediction("Unknown", primary, detailed, rec, 0.40, "keyword")

        # 4. total miss
        rec = _detect_recurring(raw_upper, False, self.version)
        return Prediction("Unknown", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE", rec, 0.20, "fallback")


def get_enricher(version: int = 2):
    """Factory. Set ENRICH_BACKEND=claude to use the (metered) Claude backend instead of rules."""
    backend = os.environ.get("ENRICH_BACKEND", "rules").lower()
    if backend == "claude":
        return ClaudeEnricher()
    return Enricher(version=version)


class ClaudeEnricher:
    """Real Anthropic-backed enricher. Off by default (gated behind ENRICH_BACKEND=claude) so the
    pipeline stays free and reproducible. Included to show the harness is model-agnostic: swap the
    backend, the metrics/judge/investigation layers don't change."""

    PROMPT = (
        "You enrich raw US bank-transaction descriptors. Return STRICT JSON with keys "
        "merchant, primary, detailed, is_recurring, confidence. Use Plaid's Personal Finance "
        "Category taxonomy for primary/detailed. If a payment aggregator (DoorDash, Uber Eats, "
        "PayPal, Venmo) masks the merchant, return the aggregator as merchant. confidence is 0-1.\n"
        "Descriptor: {descriptor}\nAmount: {amount}"
    )

    def __init__(self, model: str = "claude-sonnet-4-6"):
        from anthropic import Anthropic  # imported lazily so rules-only runs need no API key
        self.client = Anthropic()
        self.model = model

    def enrich(self, descriptor: str, amount: float | None = None) -> Prediction:
        import json
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": self.PROMPT.format(descriptor=descriptor, amount=amount)}],
        )
        data = json.loads(msg.content[0].text)
        return Prediction(
            data["merchant"], data["primary"], data["detailed"],
            bool(data["is_recurring"]), float(data.get("confidence", 0.5)), "claude",
        )


if __name__ == "__main__":
    e = Enricher(version=2)
    for d in ["SQ *BLUE BOTTLE COFFEE OAKLAND CA", "DD *DOORDASH SUSHIYA", "AMZN MKTP US*RT4G88H13", "PG&E WEB ONLINE PMT"]:
        print(d, "->", e.enrich(d))
