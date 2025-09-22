# Experiment3.py
"""
Experiment 3: Timing shingles generation

Purpose
- Measure wall-clock time to generate shingles across (w, λ) pairs.
- Optionally pre-generate all shingles without timing.

Output layout
- shingles/
  <City_State>/
    <w>/
      lam-8/
      lam-16/
      lam-32/
      lam-64/
      lam-inf/
        C-0.txt
        C-3.txt
        ...

Notes
- Each lam-* directory contains MD5-hash shingles sorted by integer value.
- lam-inf is the full set; finite λ outputs are the first k lines of lam-inf.

Usage
- Timed runs for all (w, λ):
    python Experiment3.py dumps/
  Performs 4 executions per (w, λ) (1 warmup + 3 measured) and reports mean, std, min, max.

- Optimized generation-only mode:
    python Experiment3.py dumps/ --generate
  Builds lam-inf once per (city, w), then derives lam-8/16/32/64 by truncation. No timing, no plots.

Inputs
- dumps/ directory with per-city text dumps named <City>_<State>_C-<version>.txt.

Outputs
- results/exp3_run_data.csv: timing stats per (w, λ)
- results/exp3_time_plot.png: mean time vs λ for each w
- shingles/<City>/<w>/lam-*/C-<version>.txt: shingle files for downstream experiments

Behavior
- --generate populates shingles quickly; run timed mode afterwards for measurements.
- Finite λ outputs are always derived as top-k shingles from lam-inf (MD5 integer order).
"""

import argparse
import csv
import statistics
import time
from pathlib import Path
import subprocess
import matplotlib.pyplot as plt

PAIRS = [
    (25, 8),
    (25, 16),
    (25, 32),
    (25, 64),
    (25, float("inf")),
    (50, 8),
    (50, 16),
    (50, 32),
    (50, 64),
    (50, float("inf")),
]  # Extend as needed

RESULT_DIR = Path("results")
SHINGLES_ROOT = Path("shingles")


def _lam_label(lam):
    return "inf" if lam == float("inf") else str(int(lam))


def _run_generate_for_city(w: int, lam, citydir: Path):
    lam_arg = _lam_label(lam)
    cmd = [
        "python",
        "generate_shingling.py",
        str(w),
        str(citydir),
        "--lambda",
        lam_arg,
        "--outroot",
        str(SHINGLES_ROOT),
    ]
    subprocess.run(cmd, check=True)


def _derive_lam_from_inf_for_city(w: int, lam_k: int, city_name: str):
    """Create lam-k files by truncating the first k lines from lam-inf outputs."""
    inf_dir = SHINGLES_ROOT / city_name / str(w) / "lam-inf"
    out_dir = SHINGLES_ROOT / city_name / str(w) / f"lam-{lam_k}"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not inf_dir.exists():
        raise RuntimeError(
            f"Missing lam-inf for {city_name}, w={w}. "
            f"Generate it first with: python generate_shingling.py {w} dumps/{city_name} --lambda inf"
        )

    for f in sorted(inf_dir.glob("C-*.txt")):
        out_f = out_dir / f.name
        wrote = 0
        with f.open("r", encoding="utf-8") as src, out_f.open(
            "w", encoding="utf-8"
        ) as dst:
            for i, line in enumerate(src):
                if i >= lam_k:
                    break
                dst.write(line)
                wrote += 1
        # Uncomment for per-file trace logging
        # print(f"[TRACE] {city_name} w={w} k={lam_k}: wrote {wrote} -> {out_f}")


def _write_results_csv(csv_path, results):
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["w", "lambda", "run1", "run2", "run3", "mean", "std", "min", "max"]
        )
        for row in results:
            writer.writerow(
                [
                    row["w"],
                    ("∞" if row["lam"] == float("inf") else row["lam"]),
                    *row["runs"],
                    row["mean"],
                    row["std"],
                    row["min"],
                    row["max"],
                ]
            )


def _plot_results(path, timings):
    plt.figure(figsize=(8, 6))
    for w, vals in timings.items():
        xs = [("∞" if lam == float("inf") else lam) for lam, _, _ in vals]
        ys = [mean for _, mean, _ in vals]
        plt.plot(xs, ys, marker="o", label=f"w={w}")
        for x, y in zip(xs, ys):
            plt.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=8)
    plt.xlabel("λ value")
    plt.ylabel("Time (s)")
    plt.title("Experiment 3: Shingling time vs λ")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    all_vals = [mean for vals in timings.values() for _, mean, _ in vals]
    if all_vals:
        ymin, ymax = min(all_vals), max(all_vals)
        margin = 0.15 * (ymax - ymin if ymax > ymin else max(1.0, ymin))
        plt.ylim(max(0, ymin - margin), ymax + margin)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _parse_cli() -> tuple[Path, bool]:
    parser = argparse.ArgumentParser(
        description="Experiment 3: timing shingles generation for (w, λ) pairs"
    )
    parser.add_argument(
        "indir",
        help="Input root directory (dumps/). Must contain city subfolders.",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help=(
            "Optimized generation only: build lam-inf once, then derive finite λ via truncation (no timing)."
        ),
    )
    args = parser.parse_args()
    indir = Path(args.indir)
    if not indir.exists():
        raise NotADirectoryError(f"{indir} does not exist")
    return indir, args.generate


def _ensure_dirs() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    SHINGLES_ROOT.mkdir(parents=True, exist_ok=True)


def _discover_cities(indir: Path) -> list[Path]:
    return sorted([p for p in indir.iterdir() if p.is_dir()])


def _run_generate_mode(cities: list[Path]) -> None:
    # lam-inf once per (city, w), then finite λ via truncation
    unique_ws = sorted({w for w, _ in PAIRS})
    finite_lams = sorted({int(lam) for _, lam in PAIRS if lam != float("inf")})

    for w in unique_ws:
        print(f"\n[GENERATE] w={w}: generating lam-inf for all cities...")
        for citydir in cities:
            print(f"[INFO] City {citydir.name} -> lam-inf")
            _run_generate_for_city(w, float("inf"), citydir)

        for k in finite_lams:
            print(f"[GENERATE] w={w}: deriving lam-{k} from lam-inf...")
            for citydir in cities:
                _derive_lam_from_inf_for_city(w, k, citydir.name)

    print("[DONE] Optimized generation completed.")


def _run_timed_mode(cities: list[Path]) -> None:
    timings: dict[int, list[tuple[float, float, float]]] = {}
    all_results: list[dict] = []

    for w, lam in PAIRS:
        label = _lam_label(lam)
        print(f"\n[RUN] Starting timed run for w={w}, λ={label}")
        run_times: list[float] = []
        num_runs = 4  # 1 warmup + 3 measured

        for run in range(num_runs):
            is_warmup = run == 0
            print(f"[INFO] Run {run+1}/{num_runs}{' (warmup)' if is_warmup else ''}...")
            start = time.perf_counter()

            # Generate shingles for each city using this (w, λ)
            for citydir in cities:
                print(f"[INFO] City {citydir.name}")
                _run_generate_for_city(w, lam, citydir)

            elapsed = time.perf_counter() - start
            if not is_warmup:
                run_times.append(elapsed)
            print(f"[DONE] Run {run+1}/{num_runs} -> {elapsed:.2f} s")

        mean_time = statistics.mean(run_times)
        std_time = statistics.pstdev(run_times) if len(run_times) > 1 else 0.0
        min_time = min(run_times)
        max_time = max(run_times)
        timings.setdefault(w, []).append((lam, mean_time, std_time))
        all_results.append(
            {
                "w": w,
                "lam": lam,
                "runs": run_times,
                "mean": mean_time,
                "std": std_time,
                "min": min_time,
                "max": max_time,
            }
        )
        print(
            f"[RESULT] w={w}, λ={label} -> mean={mean_time:.2f}s (std={std_time:.2f}, min={min_time:.2f}, max={max_time:.2f})"
        )

    _write_results_csv(RESULT_DIR / "exp3_run_data.csv", all_results)
    _plot_results(RESULT_DIR / "exp3_time_plot.png", timings)


def main() -> None:
    indir, generate_only = _parse_cli()
    _ensure_dirs()
    cities = _discover_cities(indir)
    if generate_only:
        _run_generate_mode(cities)
    else:
        _run_timed_mode(cities)


if __name__ == "__main__":
    main()
