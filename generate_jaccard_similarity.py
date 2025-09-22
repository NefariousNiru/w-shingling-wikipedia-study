"""
Compute Jaccard(C-0, C-v) for v in {3, 6, ..., 147} using precomputed shingles

Reads
- shingles/<City_State>/<w>/lam-<lambda_label>/C-<version>.txt

Writes
- results/jaccard_w-{w}_lam-{lambda_label}.csv
  columns: city, w, lambda, version, jaccard

Usage
- python generate_jaccard_similarity.py --w 25 --lambda inf
- python generate_jaccard_similarity.py --w 50 --lambda 32

Behavior
- If a required shingles file is missing, raises RuntimeError with guidance to run Experiment 3.
- Empty shingles files are treated as empty sets; Jaccard is defined accordingly.
"""

import argparse
from pathlib import Path
import re
from typing import Dict, List, Set
import csv

DUMPS_DIR = "dumps"
SHINGLES_DIR = "shingles"
RESULTS_DIR = "results"

CITY_DIR_NAME_RE = re.compile(r"^(.+?)_(\w{2})$")
DUMP_FILE_RE = re.compile(r"^(.+?)_(\w{2})_C-(\d+)\.txt$")


def _runtime_missing(city: str, w: int, lam_label: str, version: int) -> None:
    raise RuntimeError(
        (
            f"Shingles not generated for {city}, w={w}, λ={lam_label}, version C-{version}. "
            f"Generate them first using Experiment3.py."
        )
    )


def _list_city_versions(dumps_root: Path) -> Dict[str, List[int]]:
    cities: Dict[str, List[int]] = {}
    if not dumps_root.exists():
        raise FileNotFoundError(f"Missing dumps directory: {dumps_root}")

    for cdir in sorted(p for p in dumps_root.iterdir() if p.is_dir()):
        name = cdir.name
        if not CITY_DIR_NAME_RE.match(name):
            continue
        versions: List[int] = []
        for f in cdir.iterdir():
            if not f.is_file():
                continue
            m = DUMP_FILE_RE.match(f.name)
            if not m:
                continue
            _, _, ver = m.groups()
            versions.append(int(ver))
        if versions:
            cities[name] = sorted(set(versions))

    if not cities:
        raise RuntimeError(f"No city/version files found under {dumps_root}")
    return cities


def _load_shingles(
    shingles_root: Path, city: str, w: int, lam_label: str, version: int
) -> List[str]:
    fpath = shingles_root / city / str(w) / f"lam-{lam_label}" / f"C-{version}.txt"
    if not fpath.exists():
        _runtime_missing(city, w, lam_label, version)

    # Treat empty files as empty sets; preserve sort by MD5 integer value
    lines = [
        ln.strip()
        for ln in fpath.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if lines:
        lines.sort(key=lambda h: int(h, 16))
    return lines


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Compute Jaccard(C-0, C-v) for v in {3,6,...,147} using shingles in lam-* folders."
        )
    )
    ap.add_argument("--w", type=int, required=True, help="Window size (e.g., 25 or 50)")
    ap.add_argument(
        "--lambda",
        dest="lam",
        required=True,
        help="Lambda value: positive integer or 'inf' for all shingles",
    )
    ap.add_argument("--dumps_root", default=DUMPS_DIR, help="Root directory of dumps/")
    ap.add_argument(
        "--shingles_root", default=SHINGLES_DIR, help="Root directory of shingles/"
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Output CSV path. Default results/jaccard_w-{w}_lam-{lambda_label}.csv",
    )
    args = ap.parse_args()

    lam_label = (
        "inf"
        if str(args.lam).lower() in ("inf", "infty", "infinite")
        else str(int(args.lam))
    )
    w = int(args.w)

    dumps_root = Path(args.dumps_root)
    shingles_root = Path(args.shingles_root)

    out_path = (
        Path(args.out)
        if args.out
        else Path(RESULTS_DIR) / f"jaccard_w-{w}_lam-{lam_label}.csv"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    city_versions = _list_city_versions(dumps_root)

    rows: List[Dict[str, str]] = []
    for city, versions in city_versions.items():
        if 0 not in versions:
            print(f"[WARN] {city}: missing C-0. Skipping city.")
            continue

        targets = [v for v in versions if v % 3 == 0 and v != 0 and v <= 147]
        if not targets:
            print(f"[WARN] {city}: no target versions (3..147 step 3). Skipping.")
            continue

        cur = set(_load_shingles(shingles_root, city, w, lam_label, 0))
        for v in targets:
            past = set(_load_shingles(shingles_root, city, w, lam_label, v))
            j = _jaccard(cur, past)
            rows.append(
                {
                    "city": city,
                    "w": str(w),
                    "lambda": lam_label,
                    "version": str(v),
                    "jaccard": f"{j:.6f}",
                }
            )

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["city", "w", "lambda", "version", "jaccard"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[INFO] Wrote Jaccard rows -> {out_path}")


if __name__ == "__main__":
    main()
