
# W-Shingling for Wikipedia Document Evolution Study  
CSCI 8790 - Class Project

> ℹ️ **Info**  
> Some of the data in the corpus was not collected or named correctly. To align with the project guidelines, the data was cleaned and renamed. Running the system with the uncorrected data could cause failures, as it expects inputs to follow the specified format.

## Overview
This project studies the **evolution of Wikipedia pages** using the **W-Shingling technique**.  
Given multiple versions of Wikipedia city pages, we:

1. Generate shingles (hashed substrings of length *W*) from the text.
2. Select the top-λ shingles to approximate the page content.
3. Compute **Jaccard similarity** between the current version (C-0) and past versions (C-3, C-6, …, C-147).
4. Run experiments to evaluate:
   - How λ approximates the ∞ (all shingles) case.
   - How similarity curves evolve over time.
   - How runtime scales with different (W, λ) pairs.

This pipeline provides both **quantitative measures** (Jaccard scores, timing data) and **visual insight** (plots of similarity across versions and parameter settings).


---
## Dependencies

- Python 3.12
- Matplotlib
- beautifulsoup4 is web scraping
- [Get Dataset Here](https://drive.google.com/file/d/175NWyhgpCd-pHcyo3nbieTFzO1P8dO6a/view?usp=sharing)

```bash
  pip install matplotlib  
```
---
## Repository Structure

```

.
├── dumps/                 # Input text dumps of city pages (by version)
│   ├── Detroit_MI/Detroit_MI_C-0.txt, C-3.txt, ...
│   └── ...
├── shingles/              # Auto-generated shingles (by city, W, λ)
│   └── Detroit_MI/<w>/lam-<val>/C-0.txt ...
├── jaccard/               # Auto-generated Jaccard CSVs
│   └── 25/w-25_lam-8.csv ...
├── results/               # Final experiment results (plots, CSVs)
│   ├── experiment1_summary.csv
│   ├── experiment1_detailed.csv
│   ├── exp3_time_plot.png
│   ├── exp3_run_log.txt
│   ├── exp3_run_data.csv
│   └── ...
├── Experiment1.py                 # Experiment 1: λ vs ∞ comparison
├── Experiment2.py                 # Experiment 2: Similarity curves
├── Experiment3.py                 # Experiment 3: Timing analysis
├── generate_shingling.py          # Core shingle generator
├── generate_jaccard_similarity.py # Core Jaccard generator
├── README.md
└── generate_plot_pdf.py           # Generate a pdf of all the plots
```

---

## Data Preparation

- Stored in `dumps/<City>_<State>/`  
- Files named `<City>_<State>_C-<version>.txt`, e.g.:
```

dumps/Detroit_MI/Detroit_MI_C-0.txt
dumps/Detroit_MI/Detroit_MI_C-3.txt
...
dumps/Detroit_MI/Detroit_MI_C-147.txt

````

The project assumes this naming convention. **If not followed, the code will warn or skip files.**

---

## Core Components

### 1. `generate_shingling.py`
- **Input:** `dumps/<City_State>/...`
- **Output:** `shingles/<City_State>/<W>/lam-<λ>/C-<version>.txt`
- **Description:**  
- Splits text into tokens.  
- Applies W-shingling with MD5 hashing.  
- Sorts shingles numerically.  
- Stores either top-λ shingles or all (λ=∞).  

**Usage example:**
```bash
python generate_shingling.py 25 dumps/Detroit_MI --lambda 16
python generate_shingling.py 25 dumps/Detroit_MI --lambda inf
````

---

### 2. `generate_jaccard_similarity.py`

* **Input:** shingles from step 1
* **Output:** CSVs in `jaccard/<W>/w-<W>_lam-<λ>.csv`
* **Description:**
  Computes Jaccard(C-0, C-v) for v=3,6,…,147 across all cities.

**Usage example:**

```bash
python generate_jaccard_similarity.py --w 25 --lambda inf
```

---

### 3. `Experiment1.py`

* **Goal:** Identify which λ best approximates ∞ Jaccard similarity.

* **Modes:**

  * `--generate`: Precomputes all Jaccard CSVs for the full parameter grid so Experiment 2 can plot directly.
  * Default (no flag): Ensures CSVs exist, computes MAE of |Jλ − J∞| aggregated over all cities/versions, reports the best λ per W, and writes outputs.

* **Process:**

  1. For each (W, λ), loads the Jaccard CSV from `jaccard/<W>/w-<W>_lam-<λ>.csv`.
  2. If a file is missing, invokes `generate_jaccard_similarity.py` to create it.
  3. Compares each finite λ to λ=∞ baseline and computes mean absolute error (MAE).
  4. Logs the best λ per W.
  5. Writes outputs:

     * `results/experiment1_summary.csv` — per-W MAE table
     * `results/experiment1_detailed.csv` — merged per-city, per-version Jaccard results

* **Jaccard CSV format:**

  * **Path:** `jaccard/<W>/w-<W>_lam-<λ>.csv`
  * **Columns:** `city, w, lambda, version, jaccard`

* **Example messages:**

  ```
  [INFO] Generating Jaccard CSV for w=25, λ=8 -> jaccard/25/w-25_lam-8.csv
  [RESULT] w=25: best λ = 64 with mean |Jλ−J∞| = 0.047740
  [INFO] Wrote summary  -> results/experiment1_summary.csv
  [INFO] Wrote detailed -> results/experiment1_detailed.csv
  ```

* **Usage:**

```bash
# Precompute all Jaccard CSVs (no MAE computation)
python Experiment1.py --generate

# Compute Experiment 1 outputs (auto-creates any missing CSVs, runs MAE analysis)
python Experiment1.py
```

---

### 4. `Experiment2.py`

* **Goal:** Plot similarity curves over time for each city.

* **Assumptions:**

  * Shingles have already been generated (Experiment 3).
  * Jaccard CSVs have already been generated (Experiment 1).
    Expected paths: `jaccard/<w>/w-<w>_lam-<λ>.csv` with `w ∈ {25, 50}` and `λ ∈ {8, 16, 32, 64, inf}`.

* **Operation:**

  * For each city and each `w`, plot `Jaccard(C-0, C-v)` vs version `v`.
  * One line per λ: 8, 16, 32, 64, and ∞ (∞ rendered last as the baseline).
  * Sorted x-axis by version for monotone curves.
  * Legend shows λ values. Grid and labels included.

* **Outputs:**

  * One PNG per city per `w`:
    `results/exp2/<City>/w-<w>.png`
    Example: `results/exp2/Los_Angeles_CA/w-25.png`, `results/exp2/Los_Angeles_CA/w-50.png`

* **Failure behavior:**

  * If any required Jaccard CSVs are missing for a given `w`, the script exits with an error and guidance to generate them first using Experiment 1.
    Example message:

    ```
    [ERROR] Missing Jaccard CSV(s) for w=25: ['8', '16', ...]
    Generate Jaccard CSVs first, e.g.:
      python Experiment1.py --generate
    ```

* **Usage:**

  ```bash
  python Experiment2.py
  ```

* **Notes:**

  * λ series are plotted in a fixed order with ∞ last for visual comparison.
  * Figure size and export DPI are chosen for readability in reports; adjust if needed in the script.
  * Output directory structure is created automatically.


---

### 5. `Experiment3.py`

* **Goal:** Measure wall-clock time to generate shingles across the full parameter grid and optionally pre-generate all shingles without timing.

* **Parameter grid:**
  `(W, λ) ∈ {(25, 8), (25, 16), (25, 32), (25, 64), (25, ∞), (50, 8), (50, 16), (50, 32), (50, 64), (50, ∞)}`

* **Inputs:**

  * `dumps/` directory with per-city text dumps named `<City>_<State>_C-<version>.txt`
  * Example: `dumps/Los_Angeles_CA/Los_Angeles_CA_C-0.txt`, `..._C-3.txt`, ..., `..._C-147.txt`

* **Outputs:**

  * `shingles/<City>/<W>/lam-<λ>/C-<version>.txt`

    * `lam-inf` contains the full MD5-shingle set sorted by integer value
    * finite `lam-8/16/32/64` contain the first k lines of `lam-inf`
  * `results/exp3_run_data.csv` with per-configuration timing stats
  * `results/exp3_time_plot.png` with mean time vs λ for each W

* **Modes:**

  1. **Timed runs** for all `(W, λ)`

     ```bash
     python Experiment3.py dumps/
     ```

     * Performs 4 executions per pair: 1 warmup + 3 measured
     * Aggregates mean, std, min, max for the 3 measured runs
     * Writes CSV and plot under `results/`
  2. **Optimized generation only**

     ```bash
     python Experiment3.py dumps/ --generate
     ```

     * Builds `lam-inf` once per `(city, W)` by calling `generate_shingling.py`
     * Derives `lam-8/16/32/64` by truncating the first k lines of `lam-inf`
     * No timing and no plots in this mode

* **Behavior details:**

  * Invokes `generate_shingling.py` for each city, W, λ to create shingle files under `shingles/`
  * In `--generate` mode, finite λ outputs are always derived from `lam-inf` to avoid recomputation
  * Timed mode repeats the full per-pair generation with 1 warmup run then 3 measured runs
  * The time plot shows mean wall-clock seconds vs λ with separate lines for `w=25` and `w=50`

* **CLI reference:**

  ```bash
  # Timed runs for all (W, λ), produces CSV + plot
  python Experiment3.py dumps/

  # Pre-generate shingles efficiently, no timing, no plot
  python Experiment3.py dumps/ --generate
  ```

* **Output file formats:**

  * `results/exp3_run_data.csv`

    ```
    w,lambda,run1,run2,run3,mean,std,min,max
    25,8, ...three measured times..., mean, std, min, max
    ...
    50,∞, ...
    ```
  * `results/exp3_time_plot.png`

    * X axis: λ values including ∞
    * Y axis: mean time in seconds
    * One line per W
    * Each point labeled with its mean for readability

* **Log examples:**

  ```
  [RUN] Starting timed run for w=25, λ=32
  [INFO] Run 1/4 (warmup)...
  [INFO] City Los_Angeles_CA
  ...
  [DONE] Run 4/4 -> 299.84 s
  [RESULT] w=25, λ=32 -> mean=299.79s (std=0.20, min=299.52, max=300.01)
  [INFO] Wrote results/exp3_run_data.csv
  [INFO] Wrote results/exp3_time_plot.png
  ```

* **Notes and expectations:**

  * `lam-inf` is the baseline reference used by Experiment 1 and is required to derive finite λ efficiently
  * The measured time is dominated by tokenization, shingle construction, hashing, and I/O
  * Larger W will increase total shingles and generally increase runtime
  * Finite λ runs are comparable in time because generation dominates and truncation is cheap
---

## Flow of Running the Project

1. **Prepare dumps**
   Place city dumps into `dumps/` with correct schema.

2. **Generate shingles (Exp3 with `--generate`)**

   ```bash
   python Experiment3.py dumps/ --generate
   ```

   This ensures all shingles (including λ=∞) are available.

3. **Generate Jaccard CSVs (Exp1 with `--generate`)**

   ```bash
   python Experiment1.py --generate
   ```

   Produces `jaccard/<W>/w-<W>_lam-<λ>.csv`.

4. **Run Experiment 1 (analysis)**

   ```bash
   python Experiment1.py
   ```

   Writes detailed + summary CSVs in `results/`.

5. **Run Experiment 2 (plots)**

   ```bash
   python Experiment2.py
   ```

   Produces per-city plots in `results/`.

6. **Run Experiment 3 (timing)**

   ```bash
   python Experiment3.py dumps/
   ```

   Produces timing CSV + plots in `results/`.

---

## Testing Single Instances

To check one city/version pair:

* Generate shingles manually:

  ```bash
  python generate_shingling.py 25 dumps/Detroit_MI --lambda 16
  ```
* Generate its Jaccard manually:

  ```bash
  python generate_jaccard_similarity.py --w 25 --lambda 16
  ```
---

## Key Messages & What They Mean

* `[INFO] Wrote ...`
  → A file has been created (shingles, Jaccard CSV, or plot).
* `[RESULT] w=25: best λ=64 ...`
  → Summary from Exp1: λ=64 approximates ∞ best.
* `[WARN] Missing C-0. Skipping city.`
  → Your dump for that city does not have a baseline current version.
* `[ERROR] Missing Jaccard CSV(s)...`
  → Run Experiment1 with `--generate` to create them.

---

## Summary

* **Experiment 1:** Quantifies λ vs ∞ difference.
* **Experiment 2:** Visualizes similarity curves (city-wise).
* **Experiment 3:** Analyzes runtime cost.