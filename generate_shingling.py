# generate_shingling.py
"""
Generate shingles for a single city, window w, and λ, writing to the unified layout:

  shingles/<City_State>/<w>/lam-<λ_label>/C-<version>.txt

- Input: dumps/<City_State>/<City_State>_C-<version>.txt (plain text)
- Output: One line per shingle, MD5 hex, integer-sorted ascending.
- λ='inf' writes all shingles; finite λ keeps the first k lines (top-k).

Usage:
  python generate_shingling.py 25 dumps/New-York-City_NY --lambda inf
  python generate_shingling.py 50 dumps/Miami_FL --lambda 32

Notes:
  - Tokenization: lower().split() (whitespace), no punctuation stripping.
  - If the page yields zero shingles (len(tokens) < w), an empty file is written.
"""

import argparse
import math
from pathlib import Path
import hashlib
from collections import deque
import struct
import re


FNAME_RE = re.compile(r"^(.+?)_(\w{2})_C-(\d+)\.txt$")


def _md5_of_bytes_seq(seq) -> str:
    """MD5 of a sequence of byte strings using length-prefixing."""
    h = hashlib.md5()
    for b in seq:
        h.update(struct.pack(">I", len(b)))  # 4-byte length
        h.update(b)  # payload
    return h.hexdigest()


def sliding_window(tokens, w):
    """
    Create a set of window size tokens
    tokens: list of strings
    w: window size (int)
    return: MD5 Hash of each window
    """
    if w <= 0:
        raise ValueError("w must be positive")
    if len(tokens) < w:
        return []

    queue = deque(maxlen=w)
    out = []
    for token in tokens:
        token = token.encode("utf-8")
        queue.append(token)
        if len(queue) == w:
            out.append(_md5_of_bytes_seq(queue))

    # Sort in asc order by magnitude not lexicographically
    out.sort(key=lambda x: int(x, 16))
    return out


def process_file(
    infile: Path, w: int, lam_label: str, lam_k: int | float, outroot: Path
):
    """
    Read dumps/<City_State>/<City_State>_C-<version>.txt and write shingles to:
      shingles/<City_State>/<w>/lam-<lam_label>/C-<version>.txt
    """
    m = FNAME_RE.match(infile.name)
    if not m:
        print(f"[WARN] Skipping {infile.name}, filename does not match schema")
        return

    city, state, version = m.groups()
    city_state = f"{city}_{state}"

    text = infile.read_text(encoding="utf-8").lower()
    tokens = text.split()
    shingles = sliding_window(tokens, w)

    # take top-k or all
    if lam_k is math.inf:
        selected = shingles
    else:
        k = int(lam_k)
        if k <= 0:
            selected = []
        else:
            selected = shingles[:k]

    outdir = outroot / city_state / str(w) / f"lam-{lam_label}"
    outdir.mkdir(parents=True, exist_ok=True)

    outfile = outdir / f"C-{version}.txt"
    with outfile.open("w", encoding="utf-8") as out:
        for sh in selected:
            out.write(sh + "\n")

    print(f"[INFO] Wrote {len(selected):6d} shingles -> {outfile}")


def main():
    ap = argparse.ArgumentParser(
        description="Generate word-level shingles for a given w and λ into lam-* folders."
    )
    ap.add_argument("w", type=int, help="Window size, e.g., 25 or 50")
    ap.add_argument(
        "indir", help="City directory containing text files (e.g., dumps/Detroit_MI)"
    )
    ap.add_argument(
        "--lambda",
        dest="lam",
        required=True,
        help="λ as positive int or 'inf' to store all shingles",
    )
    ap.add_argument("--outroot", default="shingles", help="Root of output directory")
    args = ap.parse_args()

    # parse λ
    if str(args.lam).lower() in ("inf", "infty", "infinite"):
        lam_k = math.inf
        lam_label = "inf"
    else:
        lam_k = int(args.lam)
        if lam_k <= 0:
            raise ValueError("λ must be a positive integer or 'inf'")
        lam_label = str(lam_k)

    indir = Path(args.indir)
    if not indir.exists() or not indir.is_dir():
        raise NotADirectoryError(
            f"Input directory {indir} does not exist or is not a directory"
        )

    outroot = Path(args.outroot)

    # Process each dump file for this city
    for f in sorted(p for p in indir.iterdir() if p.is_file() and p.suffix == ".txt"):
        process_file(f, args.w, lam_label, lam_k, outroot)


if __name__ == "__main__":
    main()
