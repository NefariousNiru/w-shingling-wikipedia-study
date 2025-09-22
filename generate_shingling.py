"""
Generate shingles for a single city, window w, and λ, writing to the unified layout:

  shingles/<City_State>/<w>/lam-<lambda_label>/C-<version>.txt

Input
- dumps/<City_State>/<City_State>_C-<version>.txt (plain text)

Output
- One line per shingle (MD5 hex), integer-sorted ascending.
- λ = 'inf' writes all shingles; finite λ writes the first k lines (top-k).

Usage
- python generate_shingling.py 25 dumps/New-York-City_NY --lambda inf
- python generate_shingling.py 50 dumps/Miami_FL --lambda 32

Notes
- Tokenization: lower().split() (whitespace), no punctuation stripping.
- If len(tokens) < w, writes an empty file.
"""

import argparse
import math
from pathlib import Path
import hashlib
from collections import deque
import struct
import re
from typing import Iterable, List

FNAME_RE = re.compile(r"^(.+?)_(\w{2})_C-(\d+)\.txt$")


def _md5_of_bytes_seq(seq: Iterable[bytes]) -> str:
    """MD5 of a sequence of byte strings using length-prefixing."""
    h = hashlib.md5()
    for b in seq:
        h.update(struct.pack(">I", len(b)))  # 4-byte length
        h.update(b)  # payload
    return h.hexdigest()


def sliding_window(tokens: List[str], w: int) -> List[str]:
    """Return MD5 for each contiguous window of size w; sorted by integer value."""
    if w <= 0:
        raise ValueError("w must be positive")
    if len(tokens) < w:
        return []

    queue: deque[bytes] = deque(maxlen=w)
    out: List[str] = []
    for token in tokens:
        queue.append(token.encode("utf-8"))
        if len(queue) == w:
            out.append(_md5_of_bytes_seq(queue))

    # Sort in ascending order by numeric magnitude (not lexicographic)
    out.sort(key=lambda x: int(x, 16))
    return out


def process_file(
    infile: Path, w: int, lam_label: str, lam_k: int | float, outroot: Path
) -> None:
    """Read dumps/<City_State>/<City_State>_C-<version>.txt and write shingles to layout."""
    m = FNAME_RE.match(infile.name)
    if not m:
        print(f"[WARN] Skipping {infile.name}, filename does not match schema")
        return

    city, state, version = m.groups()
    city_state = f"{city}_{state}"

    text = infile.read_text(encoding="utf-8").lower()
    tokens = text.split()
    shingles = sliding_window(tokens, w)

    # Select top-k or all
    if lam_k is math.inf:
        selected = shingles
    else:
        k = int(lam_k)
        selected = shingles[:k] if k > 0 else []

    outdir = outroot / city_state / str(w) / f"lam-{lam_label}"
    outdir.mkdir(parents=True, exist_ok=True)

    outfile = outdir / f"C-{version}.txt"
    with outfile.open("w", encoding="utf-8") as out:
        for sh in selected:
            out.write(sh + "\n")

    print(f"[INFO] Wrote {len(selected):6d} shingles -> {outfile}")


def _parse_cli() -> tuple[int, Path, str, int | float, Path]:
    parser = argparse.ArgumentParser(
        description="Generate word-level shingles for a given w and λ into lam-* folders."
    )
    parser.add_argument("w", type=int, help="Window size, e.g., 25 or 50")
    parser.add_argument(
        "indir", help="City directory with text files (e.g., dumps/Detroit_MI)"
    )
    parser.add_argument(
        "--lambda",
        dest="lam",
        required=True,
        help="λ as positive int or 'inf' to store all shingles",
    )
    parser.add_argument(
        "--outroot", default="shingles", help="Root of output directory"
    )
    args = parser.parse_args()

    # Parse λ
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
    return args.w, indir, lam_label, lam_k, outroot


def main() -> None:
    w, indir, lam_label, lam_k, outroot = _parse_cli()

    # Process each dump file for this city
    for f in sorted(p for p in indir.iterdir() if p.is_file() and p.suffix == ".txt"):
        process_file(f, w, lam_label, lam_k, outroot)


if __name__ == "__main__":
    main()
