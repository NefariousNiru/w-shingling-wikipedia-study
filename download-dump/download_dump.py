# download_dump.py
import argparse
import time
import re
from pathlib import Path
from typing import List, Dict, Tuple
import requests
from bs4 import BeautifulSoup, Tag

API_FMT = "https://{lang}.wikipedia.org/w/api.php"
UA = "Every3TextDump/1.0 (contact: your-email@example.com)"
TIMEOUT = 30


def session(lang: str) -> Tuple[requests.Session, str]:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s, API_FMT.format(lang=lang)


def fetch_revisions(
    sess: requests.Session, api: str, title: str, max_count: int
) -> List[Dict]:
    """Newest->older. Fields: revid, timestamp, user, size, comment."""
    out: List[Dict] = []
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "revisions",
        "titles": title,
        "rvprop": "ids|timestamp|user|size|comment",
        "rvslots": "main",
        "rvlimit": "50",  # non-bot cap
        "rvdir": "older",  # start at current and go back
        "maxlag": "5",
    }
    cont = None
    while len(out) < max_count:
        if cont:
            params["rvcontinue"] = cont
        r = sess.get(api, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", [])
        if pages:
            revs = pages[0].get("revisions", [])
            if not revs:
                break
            out.extend(revs)
        cont = data.get("continue", {}).get("rvcontinue")
        if not cont:
            break
    return out[:max_count]


def fetch_html_for_oldid(sess: requests.Session, api: str, oldid: int) -> str:
    """Rendered HTML for a specific historical revision."""
    params = {
        "action": "parse",
        "format": "json",
        "formatversion": "2",
        "prop": "text",
        "oldid": str(oldid),
        "maxlag": "5",
    }
    r = sess.get(api, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if "parse" not in data or "text" not in data["parse"]:
        raise RuntimeError(f"No HTML returned for oldid={oldid}")
    return data["parse"]["text"]


def html_to_pure_text(html: str) -> str:
    """
    Strip Wikipedia article HTML to clean text:
    - keep headings, paragraphs, lists
    - drop infoboxes, references, navboxes, math, tables, editlinks, images
    - collapse whitespace; add blank lines between blocks
    """
    soup = BeautifulSoup(html, "html.parser")

    # Work only inside article body if present
    body = soup.select_one(".mw-parser-output") or soup

    # Remove noise
    for sel in [
        ".mw-editsection",
        ".reference",
        ".refbegin",
        ".refend",
        ".reflist",
        "#toc",
        ".toc",
        ".hatnote",
        ".ambox",
        ".navbox",
        ".vertical-navbox",
        ".metadata",
        ".infobox",
        ".thumb",
        ".mwe-math-element",
        ".gallery",
        ".sistersitebox",
        ".sidebar",
        ".box-RelArticle",
        ".box-More",
        ".mw-empty-elt",
        ".shortdescription",
        ".infobox_v2",
    ]:
        for n in body.select(sel):
            n.decompose()

    # Remove tables entirely (keeps text-only output aligned with your example)
    for tbl in body.find_all("table"):
        tbl.decompose()

    # Replace <br> with newline
    for br in body.find_all("br"):
        br.replace_with("\n")

    # Flatten images/figures
    for fig in body.find_all(["figure", "figcaption", "img", "map", "svg", "noscript"]):
        fig.decompose()

    blocks = []

    def push(text: str):
        t = re.sub(r"[ \t]+\n", "\n", text.strip())
        t = re.sub(r"\n{3,}", "\n\n", t)
        if t:
            blocks.append(t)

    # Walk only top-level blocks to keep order
    for el in body.children:
        if not isinstance(el, Tag):
            continue
        name = el.name.lower()

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            txt = el.get_text(" ", strip=True)
            if txt:
                push(txt)

        elif name == "p":
            txt = el.get_text(" ", strip=True)
            if txt:
                push(txt)

        elif name in {"ul", "ol"}:
            lines = []
            for li in el.find_all("li", recursive=False):
                item = li.get_text(" ", strip=True)
                if item:
                    lines.append("- " + item)
            if lines:
                push("\n".join(lines))

        elif name in {"div", "section"}:
            # Some articles wrap paragraphs in divs; collect p/ul/ol inside
            buf = []
            for child in el.find_all(
                ["p", "ul", "ol", "h2", "h3", "h4", "h5", "h6"], recursive=False
            ):
                if child.name == "p":
                    t = child.get_text(" ", strip=True)
                    if t:
                        buf.append(t)
                elif child.name in {"ul", "ol"}:
                    sub = []
                    for li in child.find_all("li", recursive=False):
                        it = li.get_text(" ", strip=True)
                        if it:
                            sub.append("- " + it)
                    if sub:
                        buf.append("\n".join(sub))
                else:
                    t = child.get_text(" ", strip=True)
                    if t:
                        buf.append(t)
            if buf:
                push("\n".join(buf))

        # Other tags are ignored for text-only output

    text = "\n\n".join(blocks)
    # Final cleanup: collapse excessive spaces, trim multiple spaces before punctuation
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", s)


def main():
    ap = argparse.ArgumentParser(
        description="Dump every 3rd Wikipedia revision as pure text."
    )
    ap.add_argument("title", help="Page title, e.g., 'Atlanta'")
    ap.add_argument("outdir", help="Output directory")
    ap.add_argument("--lang", default="en", help="Language subdomain, default en")
    ap.add_argument(
        "--max-back",
        type=int,
        default=147,
        help="Farthest offset to include (default 147)",
    )
    ap.add_argument(
        "--sleep", type=float, default=1, help="Seconds to sleep between API calls"
    )
    ap.add_argument(
        "--concat",
        action="store_true",
        help="Write one concatenated file instead of many",
    )
    args = ap.parse_args()

    sess, api = session(args.lang)
    Path(args.outdir).mkdir(parents=True, exist_ok=True)

    needed = args.max_back + 1  # Vt .. Vt-max_back inclusive
    city, state = args.title.split("_")
    print(city, state)
    revs = fetch_revisions(sess, api, city, needed)
    if not revs:
        raise SystemExit(f"No revisions found for {city}_{state}")

    chosen = []
    for i in range(0, len(revs), 3):
        if i > args.max_back:
            break
        chosen.append((i, revs[i]))  # (offset, revision dict)

    base = safe_name(city)
    concat_parts = []

    for offset, rev in chosen:
        oldid = rev["revid"]

        html = fetch_html_for_oldid(sess, api, oldid)
        text = html_to_pure_text(html)

        # Include headers to check manually if it got right and append to text
        # ts = rev.get("timestamp", "")
        # user = rev.get("user", "")
        # size = rev.get("size", "")
        # header = f"Title: {args.title}\nVt-{offset}\noldid: {oldid}\ntimestamp: {ts}\nuser: {user}\nsize: {size}\n"

        if args.concat:
            sep = "\n" + ("=" * 80) + "\n\n"
            concat_parts.append(text + sep)
        else:
            fname = f"{base}_{state}_C-{offset}.txt"
            (Path(args.outdir) / fname).write_text(text, encoding="utf-8")
            print(f"Wrote {fname}")

        time.sleep(args.sleep)

    if args.concat:
        fname = f"{base}_every3_Vt_to_Vt-{args.max_back}.txt"
        (Path(args.outdir) / fname).write_text(
            "".join(concat_parts).rstrip() + "\n", encoding="utf-8"
        )
        print(f"Wrote {fname}")


if __name__ == "__main__":
    main()
