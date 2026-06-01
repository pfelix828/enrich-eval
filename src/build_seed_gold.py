"""
Build the seed gold set for the enrichment eval harness.

Each row is a synthetically formatted bank-descriptor string for a REAL merchant, hand-curated
to cover the descriptor patterns the eval needs to slice on. Labels follow docs/labeling_rubric.md
and use Plaid's public PFC taxonomy (data/plaid_pfc_taxonomy.csv).

Provenance: descriptors are NOT real cardholder data. See the rubric, section 6. This script is the
reproducible source of the seed; edit here, never hand-edit the CSV.

Run:  python src/build_seed_gold.py
Out:  data/gold_set_seed.csv
"""

import csv
import os

# pattern_tags vocabulary (the segment-slice dimensions for the metrics layer):
#   clean              - tidy, recognizable string
#   processor_prefix   - SQ*/TST*/PYPL* etc. in front of the merchant
#   allcaps_truncated  - upper-cased and/or cut off mid-word
#   city_state_suffix  - trailing CITY ST
#   store_id_noise     - store numbers, reference ids, phone numbers
#   aggregator_masked  - true merchant hidden behind a platform (ceiling on quality)
#   ambiguous_category - reasonable people could disagree on the detailed category
#   recurring_cue      - descriptor hints at a subscription/scheduled charge

# columns: raw_descriptor, amount, merchant, primary, detailed, is_recurring, difficulty, tags, notes
ROWS = [
    # --- clean / easy baseline ---
    ("Netflix", 15.49, "Netflix", "ENTERTAINMENT", "ENTERTAINMENT_TV_AND_MOVIES", True, "easy", "clean;recurring_cue", "canonical subscription"),
    ("SPOTIFY USA", 11.99, "Spotify", "ENTERTAINMENT", "ENTERTAINMENT_MUSIC_AND_AUDIO", True, "easy", "allcaps_truncated;recurring_cue", ""),
    ("CHEVRON 0094213", 52.10, "Chevron", "TRANSPORTATION", "TRANSPORTATION_GAS", False, "easy", "store_id_noise", "gas pump"),
    ("TRADER JOE'S #182 SAN RAFAEL CA", 84.27, "Trader Joe's", "FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES", False, "easy", "store_id_noise;city_state_suffix", ""),
    ("SHELL OIL 5742 BERKELEY CA", 41.88, "Shell", "TRANSPORTATION", "TRANSPORTATION_GAS", False, "easy", "store_id_noise;city_state_suffix", ""),

    # --- processor prefixes (Square, Toast, PayPal, Stripe) ---
    ("SQ *BLUE BOTTLE COFFEE OAKLAND CA", 6.75, "Blue Bottle Coffee", "FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE", False, "medium", "processor_prefix;city_state_suffix", "Square in front of coffee"),
    ("TST* TARTINE BAKERY SAN FRANCISC", 18.40, "Tartine Bakery", "FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT", False, "medium", "processor_prefix;allcaps_truncated", "Toast prefix, truncated city"),
    ("SQ *RAINBOW NAILS & SPA", 45.00, "Rainbow Nails & Spa", "PERSONAL_CARE", "PERSONAL_CARE_HAIR_AND_BEAUTY", False, "medium", "processor_prefix", ""),
    ("PYPL *STEAMGAMES 4029357733", 29.99, "Steam", "ENTERTAINMENT", "ENTERTAINMENT_VIDEO_GAMES", False, "hard", "processor_prefix;store_id_noise", "PayPal wraps Steam; phone-like ref id"),
    ("SP CHECKOUT* ALLBIRDS", 98.00, "Allbirds", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_CLOTHING_AND_ACCESSORIES", False, "medium", "processor_prefix", "Stripe checkout"),

    # --- aggregator-masked (the ceiling) ---
    ("DD *DOORDASH SUSHIYA", 37.62, "DoorDash", "FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT", False, "hard", "aggregator_masked;processor_prefix", "true merchant Sushiya unrecoverable as brand"),
    ("UBER EATS", 24.10, "Uber Eats", "FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT", False, "hard", "aggregator_masked", ""),
    ("PAYPAL *JOHNSDELI 4029357733", 13.25, "PayPal", "FOOD_AND_DRINK", "FOOD_AND_DRINK_OTHER_FOOD_AND_DRINK", False, "hard", "aggregator_masked;processor_prefix;store_id_noise", "small unknown merchant behind PayPal"),
    ("SQ *SQ *FARMERS MARKET", 22.00, "Square", "FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES", False, "hard", "aggregator_masked;processor_prefix", "generic Square seller, no brand"),
    ("GRUBHUB*HALAL GUYS", 28.90, "Grubhub", "FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT", False, "hard", "aggregator_masked;processor_prefix", ""),

    # --- Amazon family (canonicalization + category ambiguity) ---
    ("AMZN MKTP US*RT4G88H13", 41.99, "Amazon", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES", False, "medium", "allcaps_truncated;store_id_noise", "marketplace, not superstore"),
    ("AMAZON.COM*2K9X10 AMZN.COM/BILL WA", 12.34, "Amazon", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES", False, "medium", "store_id_noise;city_state_suffix", ""),
    ("Amazon Prime*9G2K1", 14.99, "Amazon Prime", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES", True, "hard", "store_id_noise;recurring_cue;ambiguous_category", "Prime membership is recurring; some label entertainment"),
    ("PRIME VIDEO*8H2L4", 8.99, "Amazon Prime Video", "ENTERTAINMENT", "ENTERTAINMENT_TV_AND_MOVIES", True, "hard", "store_id_noise;recurring_cue;ambiguous_category", "Prime Video vs Prime membership boundary"),

    # --- superstore vs marketplace vs grocery ---
    ("TARGET 00027841 NOVATO CA", 119.46, "Target", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_SUPERSTORES", False, "medium", "store_id_noise;city_state_suffix", "superstore, not grocery"),
    ("WAL-MART #5260", 63.20, "Walmart", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_SUPERSTORES", False, "medium", "store_id_noise", ""),
    ("COSTCO WHSE #0476", 210.55, "Costco", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_SUPERSTORES", False, "medium", "store_id_noise;ambiguous_category", "warehouse club; some expect groceries"),
    ("SAFEWAY #1199 MILL VALLEY CA", 77.31, "Safeway", "FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES", False, "easy", "store_id_noise;city_state_suffix", ""),

    # --- coffee vs fast food vs restaurant tie-breaks ---
    ("STARBUCKS STORE 04471", 5.65, "Starbucks", "FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE", False, "medium", "store_id_noise;ambiguous_category", "coffee, not fast food"),
    ("MCDONALD'S F12345 SAN JOSE CA", 9.41, "McDonald's", "FOOD_AND_DRINK", "FOOD_AND_DRINK_FAST_FOOD", False, "easy", "store_id_noise;city_state_suffix", ""),
    ("CHIPOTLE 2487", 13.85, "Chipotle", "FOOD_AND_DRINK", "FOOD_AND_DRINK_FAST_FOOD", False, "medium", "store_id_noise;ambiguous_category", "fast-casual sits between fast food and restaurant"),
    ("PEET'S COFFEE #03311", 4.95, "Peet's Coffee", "FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE", False, "easy", "store_id_noise", ""),

    # --- ride share vs eats vs gas (same parent brand, different category) ---
    ("UBER TRIP HELP.UBER.COM", 18.73, "Uber", "TRANSPORTATION", "TRANSPORTATION_TAXIS_AND_RIDE_SHARES", False, "medium", "ambiguous_category", "Uber rides vs Uber Eats split"),
    ("LYFT *RIDE WED 2PM", 12.40, "Lyft", "TRANSPORTATION", "TRANSPORTATION_TAXIS_AND_RIDE_SHARES", False, "easy", "processor_prefix", ""),
    ("LIME*RIDE SAN FRANCISCO CA", 4.50, "Lime", "TRANSPORTATION", "TRANSPORTATION_BIKES_AND_SCOOTERS", False, "medium", "processor_prefix;city_state_suffix", ""),
    ("BART-POWELL ST FARE", 4.95, "BART", "TRANSPORTATION", "TRANSPORTATION_PUBLIC_TRANSIT", False, "medium", "allcaps_truncated", "regional transit, lesser-known brand"),

    # --- subscriptions where category is genuinely ambiguous ---
    ("DROPBOX*9X8K2L", 11.99, "Dropbox", "GENERAL_SERVICES", "GENERAL_SERVICES_OTHER_GENERAL_SERVICES", True, "hard", "store_id_noise;recurring_cue;ambiguous_category", "cloud storage lands in services-other"),
    ("APPLE.COM/BILL 866-712-7753", 2.99, "Apple", "GENERAL_SERVICES", "GENERAL_SERVICES_OTHER_GENERAL_SERVICES", True, "hard", "store_id_noise;recurring_cue;ambiguous_category", "iCloud/app sub; could be many detailed buckets"),
    ("CLAUDE.AI SUBSCRIPTION", 20.00, "Anthropic", "GENERAL_SERVICES", "GENERAL_SERVICES_OTHER_GENERAL_SERVICES", True, "hard", "recurring_cue;ambiguous_category", "AI SaaS; brand vs product name gap"),
    ("PLANET FIT CLUB FEES 8005551212", 24.99, "Planet Fitness", "PERSONAL_CARE", "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS", True, "medium", "allcaps_truncated;store_id_noise;recurring_cue", ""),

    # --- bills / utilities / loans (recurring, less brand-forward) ---
    ("PG&E WEB ONLINE PMT", 142.07, "PG&E", "RENT_AND_UTILITIES", "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY", True, "medium", "allcaps_truncated;recurring_cue", ""),
    ("COMCAST / XFINITY", 89.00, "Xfinity", "RENT_AND_UTILITIES", "RENT_AND_UTILITIES_INTERNET_AND_CABLE", True, "medium", "ambiguous_category;recurring_cue", "Comcast vs Xfinity brand naming"),
    ("VERIZON WIRELESS PMT RECUR", 95.43, "Verizon", "RENT_AND_UTILITIES", "RENT_AND_UTILITIES_TELEPHONE", True, "easy", "allcaps_truncated;recurring_cue", ""),
    ("TOYOTA FIN SVC AUTOPAY", 412.00, "Toyota Financial Services", "LOAN_PAYMENTS", "LOAN_PAYMENTS_CAR_PAYMENT", True, "medium", "allcaps_truncated;recurring_cue", ""),
    ("NELNET STUDENT LOAN", 268.00, "Nelnet", "LOAN_PAYMENTS", "LOAN_PAYMENTS_STUDENT_LOAN_PAYMENT", True, "medium", "recurring_cue", ""),
    ("RENT CAFE EPAY PROPERTYMGMT", 2850.00, "RentCafe", "RENT_AND_UTILITIES", "RENT_AND_UTILITIES_RENT", True, "hard", "allcaps_truncated;recurring_cue;ambiguous_category", "payment portal, not the landlord brand"),

    # --- medical / services / travel ---
    ("CVS/PHARMACY #04412 SAN RAFAEL", 23.18, "CVS Pharmacy", "MEDICAL", "MEDICAL_PHARMACIES_AND_SUPPLEMENTS", False, "easy", "store_id_noise;city_state_suffix", ""),
    ("MARIN DENTAL CARE LLC", 180.00, "Marin Dental Care", "MEDICAL", "MEDICAL_DENTAL_CARE", False, "medium", "clean", "local provider, no national brand"),
    ("GEICO *AUTO 8006861234", 121.50, "GEICO", "GENERAL_SERVICES", "GENERAL_SERVICES_INSURANCE", True, "medium", "processor_prefix;store_id_noise;recurring_cue", ""),
    ("UNITED 0162334451288 UNITED.COM", 412.20, "United Airlines", "TRAVEL", "TRAVEL_FLIGHTS", False, "medium", "store_id_noise", "ticket number noise"),
    ("MARRIOTT SAN FRANCISCO", 289.00, "Marriott", "TRAVEL", "TRAVEL_LODGING", False, "easy", "city_state_suffix", ""),
    ("AIRBNB * HMXYZ123", 540.00, "Airbnb", "TRAVEL", "TRAVEL_LODGING", False, "medium", "processor_prefix;store_id_noise", ""),

    # --- noisy / low-signal hard cases ---
    ("POS DEBIT 0471 9TH ST", 7.25, "Unknown", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE", False, "hard", "aggregator_masked;store_id_noise;ambiguous_category", "no merchant recoverable; address only"),
    ("SQ *", 3.00, "Square", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE", False, "hard", "aggregator_masked;processor_prefix", "empty Square descriptor"),
    ("CASH APP*CASH OUT", 50.00, "Cash App", "TRANSFER_OUT", "TRANSFER_OUT_OTHER_TRANSFER_OUT", False, "hard", "processor_prefix;ambiguous_category", "P2P transfer, not a purchase"),
    ("ZELLE TO J SMITH", 75.00, "Zelle", "TRANSFER_OUT", "TRANSFER_OUT_OTHER_TRANSFER_OUT", False, "hard", "ambiguous_category", "person-to-person transfer"),
    ("VENMO PAYMENT 8885551212", 30.00, "Venmo", "TRANSFER_OUT", "TRANSFER_OUT_OTHER_TRANSFER_OUT", False, "medium", "store_id_noise;ambiguous_category", ""),
]

FIELDNAMES = [
    "id", "raw_descriptor", "amount", "gold_merchant", "gold_primary",
    "gold_detailed", "gold_is_recurring", "difficulty", "pattern_tags",
    "provenance", "notes",
]


def load_valid_detailed(taxonomy_path):
    valid = set()
    with open(taxonomy_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            valid.add(row["DETAILED"])
    return valid


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(here, "data")
    taxonomy_path = os.path.join(data_dir, "plaid_pfc_taxonomy.csv")
    out_path = os.path.join(data_dir, "gold_set_seed.csv")

    valid_detailed = load_valid_detailed(taxonomy_path)

    # Fail loudly if any label drifts off the real taxonomy.
    bad = [(r[0], r[4]) for r in ROWS if r[4] not in valid_detailed]
    if bad:
        raise ValueError(f"{len(bad)} rows use detailed codes not in the taxonomy: {bad}")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for i, r in enumerate(ROWS, start=1):
            writer.writerow({
                "id": f"seed_{i:03d}",
                "raw_descriptor": r[0],
                "amount": f"{r[1]:.2f}",
                "gold_merchant": r[2],
                "gold_primary": r[3],
                "gold_detailed": r[4],
                "gold_is_recurring": str(r[5]).lower(),
                "difficulty": r[6],
                "pattern_tags": r[7],
                "provenance": "synthetic_descriptor_real_merchant",
                "notes": r[8],
            })

    print(f"wrote {len(ROWS)} rows -> {out_path}")
    # quick coverage summary
    from collections import Counter
    prim = Counter(r[3] for r in ROWS)
    diff = Counter(r[6] for r in ROWS)
    tags = Counter(t for r in ROWS for t in r[7].split(";") if t)
    print("primary categories covered:", dict(prim))
    print("difficulty mix:", dict(diff))
    print("pattern tags:", dict(tags))


if __name__ == "__main__":
    main()
