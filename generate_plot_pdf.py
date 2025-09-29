# generate_plot_pdf
"""
Build A4 contact sheets for Experiment 2 plots.

- Working dir: project root (parent of 'results/')
- Input: results/exp2/<City>/{w-25.png,w-50.png}
- Order: cities alphabetical
- Layout per page: 4 rows x 2 cols = 4 cities per page
  Each row: [w-25.png | w-50.png] for the same city
- Output: results/exp2/exp2_contact_sheets.pdf
"""

import math
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw

# Config
BASE = Path("results") / "exp2"
OUT_PDF = Path("results") / "exp2_contact_sheets.pdf"

# A4 portrait at 300 DPI in pixels
A4_W, A4_H = 2480, 3508

# Grid: 4 rows, 2 columns -> each row is one city pair (25 left, 50 right)
ROWS = 4
COLS = 2
CITIES_PER_PAGE = ROWS  # one city per row
IMAGES_PER_PAGE = ROWS * COLS  # 8

# Margins and paddings (pixels)
PAGE_MARGIN_X = 80
PAGE_MARGIN_Y = 80
CELL_PADDING = 24  # inner padding within each cell

# Background color
BG = (255, 255, 255)


def collect_city_pairs(base: Path) -> List[Tuple[str, Path, Path]]:
    """
    Return list of (city_name, path_25, path_50), sorted by city_name.
    Skip cities missing either image.
    """
    if not base.exists():
        raise SystemExit(f"Folder not found: {base}")

    cities = sorted([p for p in base.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    pairs: List[Tuple[str, Path, Path]] = []
    for city_dir in cities:
        p25 = city_dir / "w-25.png"
        p50 = city_dir / "w-50.png"
        if p25.exists() and p50.exists():
            pairs.append((city_dir.name, p25, p50))
    if not pairs:
        raise SystemExit(f"No complete city pairs found under {base}")
    return pairs


def fit_within(src_w: int, src_h: int, max_w: int, max_h: int) -> Tuple[int, int]:
    """Keep aspect ratio, fit within max_w x max_h."""
    scale = min(max_w / src_w, max_h / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    return new_w, new_h


def paste_centered(page: Image.Image, img: Image.Image, box_x: int, box_y: int, box_w: int, box_h: int) -> None:
    """Paste img centered inside a box at (box_x, box_y, box_w, box_h)."""
    new_w, new_h = fit_within(img.width, img.height, box_w, box_h)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)
    x = box_x + (box_w - new_w) // 2
    y = box_y + (box_h - new_h) // 2
    page.paste(img_resized, (x, y))


def make_pages(pairs: List[Tuple[str, Path, Path]]) -> List[Image.Image]:
    """
    Build PIL images (A4 pages) laying out up to 4 city pairs per page.
    No captions, just images.
    """
    pages: List[Image.Image] = []

    # Compute grid cell size
    grid_w = A4_W - 2 * PAGE_MARGIN_X
    grid_h = A4_H - 2 * PAGE_MARGIN_Y
    cell_w = grid_w // COLS
    cell_h = grid_h // ROWS

    # Drawable area inside a cell (padding on all sides)
    draw_w = cell_w - 2 * CELL_PADDING
    draw_h = cell_h - 2 * CELL_PADDING

    num_pages = math.ceil(len(pairs) / CITIES_PER_PAGE)
    # Pad with blanks if needed
    padded = pairs + [("", None, None)] * (num_pages * CITIES_PER_PAGE - len(pairs))

    for page_idx in range(num_pages):
        page = Image.new("RGB", (A4_W, A4_H), color=BG)
        draw = ImageDraw.Draw(page)

        chunk = padded[page_idx * CITIES_PER_PAGE:(page_idx + 1) * CITIES_PER_PAGE]

        for r, (city, p25, p50) in enumerate(chunk):
            # Left cell for w-25
            left_x = PAGE_MARGIN_X + 0 * cell_w + CELL_PADDING
            left_y = PAGE_MARGIN_Y + r * cell_h + CELL_PADDING

            # Right cell for w-50
            right_x = PAGE_MARGIN_X + 1 * cell_w + CELL_PADDING
            right_y = PAGE_MARGIN_Y + r * cell_h + CELL_PADDING

            if p25 and p25.exists():
                with Image.open(p25) as im25:
                    im25 = im25.convert("RGB")
                    paste_centered(page, im25, left_x, left_y, draw_w, draw_h)
            else:
                # Optional light gray frame to show missing
                draw.rectangle([left_x, left_y, left_x + draw_w, left_y + draw_h],
                               outline=(200, 200, 200), width=2)

            if p50 and p50.exists():
                with Image.open(p50) as im50:
                    im50 = im50.convert("RGB")
                    paste_centered(page, im50, right_x, right_y, draw_w, draw_h)
            else:
                draw.rectangle([right_x, right_y, right_x + draw_w, right_y + draw_h],
                               outline=(200, 200, 200), width=2)

        pages.append(page)

    return pages


def save_pdf(pages: List[Image.Image], out_pdf: Path) -> None:
    if not pages:
        print("No pages to save.")
        return
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    first, rest = pages[0], pages[1:]
    first.save(out_pdf, "PDF", save_all=True, append_images=rest, resolution=300)
    print(f"Wrote PDF: {out_pdf}")


def main():
    pairs = collect_city_pairs(BASE)
    pages = make_pages(pairs)
    save_pdf(pages, OUT_PDF)


if __name__ == "__main__":
    main()
