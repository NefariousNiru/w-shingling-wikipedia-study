# Experiment2.py
"""
Experiment 2 - Plot similarity curves (version on X, Jaccard on Y)

Assumptions
- Shingles already generated (Experiment 3).
- Jaccard CSVs already generated (Experiment 1).
  Expected files:
    jaccard/<w>/w-<w>_lam-<λ>.csv
  with w ∈ {25, 50} and λ ∈ {8, 16, 32, 64, inf}.

Operation
- For each city and each w, plot Jaccard(C-0, C-v) vs version v.
- One line per λ (8, 16, 32, 64, ∞ baseline).
- Output files:
    results/exp2_city-<City>_w-<w>.png

Missing inputs
- If required Jaccard CSVs are absent, terminate with guidance to first generate them using Experiment 1.

Usage
- python Experiment2.py
"""

import csv
from pathlib import Path
from typing import Dict, List, Tuple
import sys
import matplotlib.pyplot as plt

# Parameter grid (aligned with Exp 1 and Exp 3)
WS = [25, 50]
LAMBDAS = ["8", "16", "32", "64", "inf"]

# Locations
JACCARD_ROOT = Path("jaccard")
RESULTS_DIR = Path("results")


def _csv_path(w: int, lam: str) -> Path:
    return JACCARD_ROOT / str(w) / f"w-{w}_lam-{lam}.csv"


def _read_jaccard_csv(path: Path) -> List[Dict]:
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


def _collect_city_series_for_w(w: int) -> Dict[str, Dict[str, List[Tuple[int, float]]]]:
    """
    Build per-city, per-λ series for a given w.

    Returns
    -------
    Dict[str, Dict[str, List[Tuple[int, float]]]]
        Structure: {city: {lam_label: [(version, jaccard), ...]}, ...}

    Notes
    -----
    Expects all λ CSVs for this w to exist; if any are missing, exit with an Experiment 1 instruction.
    """
    # Validate required CSV presence for this w
    missing = [lam for lam in LAMBDAS if not _csv_path(w, lam).exists()]
    if missing:
        print(f"[ERROR] Missing Jaccard CSV(s) for w={w}: {missing}")
        print("Generate Jaccard CSVs first, e.g.:\n  python Experiment1.py --generate")
        sys.exit(2)

    # Load rows grouped by city and λ
    by_city: Dict[str, Dict[str, List[Tuple[int, float]]]] = {}
    for lam in LAMBDAS:
        rows = _read_jaccard_csv(_csv_path(w, lam))
        for r in rows:
            city = r["city"]
            by_city.setdefault(city, {})
            by_city[city].setdefault(lam, [])
            by_city[city][lam].append((r["version"], r["jaccard"]))

    # Sort by version for monotone X
    for city, lam_map in by_city.items():
        for lam, pts in lam_map.items():
            lam_map[lam] = sorted(pts, key=lambda t: t[0])

    return by_city


def _safe_name(s: str) -> str:
    """Filesystem-safe token for output artifact names."""
    return s.replace("/", "-").replace("\\", "-").replace(" ", "_")


def _plot_city_w(
    city: str, w: int, lam_series: Dict[str, List[Tuple[int, float]]]
) -> None:
    """
    Plot a single figure: versions on X, Jaccard on Y; one line per λ (including inf).
    Saves to results/exp2_city-<City>_w-<w>.png.
    """
    plt.figure(figsize=(9, 6))

    # Consistent λ order; baseline (inf) rendered last
    lam_order = [l for l in LAMBDAS if l != "inf"] + ["inf"]
    for lam in lam_order:
        if lam not in lam_series:
            # Skip quietly if some λ has no series for this city
            continue
        pts = lam_series[lam]
        if not pts:
            continue
        xs = [v for (v, _) in pts]
        ys = [j for (_, j) in pts]
        label = "∞" if lam == "inf" else f"λ={lam}"
        plt.plot(xs, ys, marker="o", linewidth=2, label=label)

    plt.title(f"Experiment 2: Jaccard vs Version  (city={city}, w={w})")
    plt.xlabel("Version (C-v)")
    plt.ylabel("Jaccard similarity with C-0")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(title="λ", frameon=True)
    plt.tight_layout()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    outpath = RESULTS_DIR / f"exp2_city-{_safe_name(city)}_w-{w}.png"
    plt.savefig(outpath, dpi=150)
    plt.close()
    print(f"[INFO] Wrote plot -> {outpath}")


def main() -> None:
    for w in WS:
        city_series = _collect_city_series_for_w(w)
        # One plot per city for this w
        for city, lam_series in sorted(city_series.items()):
            _plot_city_w(city, w, lam_series)


if __name__ == "__main__":
    main()
