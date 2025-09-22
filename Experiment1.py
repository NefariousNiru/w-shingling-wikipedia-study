# Experiment1.py
"""
Experiment 1 runner

Modes
- With --generate: precomputes Jaccard CSVs for all (w, λ) pairs so Experiment 2 can plot directly.
- Without --generate: verifies required Jaccard CSVs (generates any missing), computes MAE of |J_λ − J_∞| aggregated over all cities/versions for each w, prints the best λ per w, and writes:
  - results/experiment1_summary.csv
  - results/experiment1_detailed.csv

Jaccard CSV layout
- Path: jaccard/<w>/w-{w}_lam-{λ}.csv
- Columns: city, w, lambda, version, jaccard

Parameter grid (hardcoded)
- W ∈ {25, 50}
- λ ∈ {8, 16, 32, 64, inf} (inf used as baseline)

Shingles requirement
- Expects shingles under shingles/<City>/<w>/lam-*/C-*.txt.
- If missing, execution stops with a clear instruction to populate via:
    python Experiment3.py dumps --generate

Usage
- Pre-generate all Jaccard CSVs (no MAE computation):
    python Experiment1.py --generate

- Compute Experiment 1 outputs (auto-creates any missing Jaccard CSVs):
    python Experiment1.py
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# ---- Constants ----
WS: List[int] = [25, 50]
LAMBDAS: List[str] = ["8", "16", "32", "64", "inf"]  # 'inf' is the baseline

# ---- Fixed paths ----
DUMPS_ROOT = Path("dumps")
SHINGLES_ROOT = Path("shingles")
RESULTS_ROOT = Path("results")
GENERATOR = "generate_jaccard_similarity.py"  # System Dev 2 script
JACCARD_ROOT = Path("jaccard")

# ---- Utilities ----


def jaccard_csv_path(w: int, lam: str) -> Path:
    """Return jaccard/<w>/w-{w}_lam-{lam}.csv."""
    outdir = JACCARD_ROOT / str(w)
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir / f"w-{w}_lam-{lam}.csv"


def call_generator_or_fail(w: int, lam_label: str) -> Path:
    """
    Materializes the expected CSV if absent by invoking generate_jaccard_similarity.py.
    Terminates with guidance if shingles are missing.
    """
    out_csv = jaccard_csv_path(w, lam_label)
    if out_csv.exists():
        return out_csv

    cmd = [
        sys.executable,
        GENERATOR,
        "--w",
        str(w),
        "--lambda",
        lam_label,
        "--dumps_root",
        str(DUMPS_ROOT),
        "--shingles_root",
        str(SHINGLES_ROOT),
        "--out",
        str(out_csv),
    ]
    print(f"[INFO] Generating Jaccard CSV for w={w}, λ={lam_label} -> {out_csv}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("\n[ERROR] Failed to compute Jaccard similarities.")
        print("Likely cause: shingles are missing for some (city, w, λ, version).")
        print("Populate shingles with the optimized generator:")
        print("  python Experiment3.py dumps --generate")
        sys.exit(2)

    if not out_csv.exists():
        print(f"[ERROR] Generator reported success but CSV not found: {out_csv}")
        sys.exit(3)
    return out_csv


def read_jaccard_csv(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append(
                {
                    "city": r["city"],
                    "w": int(r["w"]),
                    "lambda": r["lambda"],
                    "version": int(r["version"]),
                    "jaccard": float(r["jaccard"]),
                }
            )
    return rows


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(rows)


# ---- Operations ----


def generate_all_jaccard_csvs() -> None:
    """Precompute Jaccard CSVs for all (w, λ) pairs."""
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    for w in WS:
        for lam in LAMBDAS:
            call_generator_or_fail(w, lam)
    print("[DONE] Generated all Jaccard CSVs for (w, λ).")


def compute_experiment1() -> None:
    """
    Ensures required CSVs exist, computes MAE of |J_λ − J_∞| per w,
    logs winners, and writes summary + merged detailed CSVs.
    """
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)

    summary_rows: List[Dict] = []
    merged_detailed: List[Dict] = []

    for w in WS:
        # Load baseline λ = inf
        base_csv = call_generator_or_fail(w, "inf")
        base_rows = read_jaccard_csv(base_csv)
        merged_detailed.extend(base_rows)

        base_map = {(r["city"], r["version"]): r["jaccard"] for r in base_rows}

        # Compare each finite λ with baseline and compute MAE
        best_lambda = None
        best_mae = float("inf")

        for lam in LAMBDAS:
            if lam == "inf":
                continue
            cur_csv = call_generator_or_fail(w, lam)
            cur_rows = read_jaccard_csv(cur_csv)
            merged_detailed.extend(cur_rows)

            errs = []
            for r in cur_rows:
                key = (r["city"], r["version"])
                if key in base_map:
                    errs.append(abs(r["jaccard"] - base_map[key]))
            mae = (sum(errs) / len(errs)) if errs else float("nan")

            summary_rows.append({"w": w, "lambda": lam, "mae_vs_infty": mae})

            if mae == mae and mae < best_mae:  # NaN-safe comparison
                best_mae = mae
                best_lambda = lam

        if best_lambda is None:
            print(f"[WARN] w={w}: unable to determine best λ (no comparable rows).")
        else:
            print(
                f"[RESULT] w={w}: best λ = {best_lambda} with mean |J_λ−J_∞| = {best_mae:.6f}"
            )

    # Emit outputs
    write_csv(
        RESULTS_ROOT / "experiment1_summary.csv",
        ["w", "lambda", "mae_vs_infty"],
        summary_rows,
    )
    write_csv(
        RESULTS_ROOT / "experiment1_detailed.csv",
        ["city", "w", "lambda", "version", "jaccard"],
        merged_detailed,
    )
    print(f"[INFO] Wrote summary  -> {RESULTS_ROOT / 'experiment1_summary.csv'}")
    print(f"[INFO] Wrote detailed -> {RESULTS_ROOT / 'experiment1_detailed.csv'}")


# ---- CLI ----


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Experiment 1 runner: generate CSVs or compute MAE vs ∞."
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Only generate all Jaccard CSVs for (w, λ) and exit (no MAE computation).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.generate:
        generate_all_jaccard_csvs()
    else:
        compute_experiment1()


if __name__ == "__main__":
    main()
