"""
Rebuild every artifact in reports/ from scratch, in order. One command, fully reproducible, offline.

  python src/run_all.py

Order: seed gold -> eval (v1, v2) -> judge validation + apply -> regression -> figures -> investigations.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def step(title, *args):
    print(f"\n=== {title} ===")
    subprocess.run([PY, *args], cwd=HERE, check=True)


def main():
    step("build seed gold set", "src/build_seed_gold.py")
    step("run eval (v1 + v2)", "src/run_eval.py")
    step("validate judge + apply to predictions", "src/judge.py")
    step("regression diff", "src/regression.py")
    step("render figures", "src/make_figures.py")
    step("investigation: categorization (v2)", "src/investigate.py",
         "categorization is wrong for a lot of my users", "--version", "2")
    step("investigation: merchant names (v1)", "src/investigate.py",
         "the merchant names my users see are messy and often blank", "--version", "1")
    print("\nAll artifacts rebuilt in reports/. Launch the demo with:\n"
          "  ./.venv/bin/streamlit run app.py")


if __name__ == "__main__":
    main()
