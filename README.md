
# W-Shingling for Wikipedia Document Evolution Study  
CSCI 8790 - Class Project

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
│   ├── exp2_city-Detroit_MI_w-25.png
│   ├── exp3_time_plot.png
│   └── ...
├── Experiment1.py                 # Experiment 1: λ vs ∞ comparison
├── Experiment2.py                 # Experiment 2: Similarity curves
├── Experiment3.py                 # Experiment 3: Timing analysis
├── generate_shingling.py          # Core shingle generator
├── generate_jaccard_similarity.py # Core Jaccard generator
└── README.md

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

* **Goal:** Identify λ that best approximates ∞ Jaccard.
* **Process:**

  * Reads all per-λ Jaccard CSVs.
  * Computes **MAE (mean absolute error)** between Jλ and J∞ across cities/versions.
  * Produces:

    * `results/experiment1_detailed.csv` — raw per-city, per-version results.
    * `results/experiment1_summary.csv` — MAE table and “best λ” per W.
* **Messages:**

  * `[RESULT] w=25: best λ=64 with mean |Jλ−J∞|=0.0383`
    → For W=25, λ=64 shingles is closest to using all shingles.

**Run:**

```bash
python Experiment1.py

# To run only jaccard similiarity generation, no MAE no stats
python Experiment1.py --generate 
```

---

### 4. `Experiment2.py`

* **Goal:** Plot similarity curves over time.
* **Process:**

  * Reads Jaccard CSVs (`jaccard/<W>/...`).
  * For each city, plots **version vs Jaccard** with one line per λ.
  * Saves plots in `results/exp2_city-<City>_w-<W>.png`.
* **Interpretation:**
  Shows how quickly λ-curves approximate ∞.
  Example: If λ=16 overlaps λ=∞, it means 16 shingles are enough.

**Run:**

```bash
python Experiment2.py
```

---

### 5. `Experiment3.py`

* **Goal:** Measure runtime cost.
* **Process:**

  * Times shingle generation for each (W, λ) pair.
  * Produces CSV of run stats and a timing plot.
* **Outputs:**

  * `results/exp3_run_data.csv` — all runs with mean/std/min/max.
  * `results/exp3_time_plot.png` — runtime vs λ, one line per W.
* **Interpretation:**
  Confirms that larger λ means more time. Helps explain efficiency tradeoffs.

**Run (generate only):**

```bash
python Experiment3.py dumps/ --generate
```

**Run (with timing):**

```bash
python Experiment3.py dumps/
```

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

Together, these experiments validate whether **top-λ shingling** can approximate the full set of shingles (∞) while saving computation.