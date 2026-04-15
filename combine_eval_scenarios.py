#!/usr/bin/env python3
"""
Ghép 2 file eval (corrupted + clean) thành 1 file với cột scenario.
Tạo artifacts/eval/eval_combined_scenarios.csv
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVAL_DIR = ROOT / "artifacts" / "eval"


def combine(before_csv: Path, after_csv: Path, out_csv: Path) -> None:
    rows = []
    for path, scenario in [(before_csv, "corrupted"), (after_csv, "clean")]:
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                r["scenario"] = scenario
                rows.append(r)

    if not rows:
        print("No rows to combine.")
        return

    fieldnames = ["scenario"] + [k for k in rows[0] if k != "scenario"]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {out_csv}  ({len(rows)} rows)")


if __name__ == "__main__":
    combine(
        before_csv=EVAL_DIR / "eval_corrupted.csv",
        after_csv=EVAL_DIR / "eval_clean.csv",
        out_csv=EVAL_DIR / "eval_combined_scenarios.csv",
    )
