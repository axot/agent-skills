#!/usr/bin/env python3
"""Fetch Amazon.co.jp product pages over plain HTTP, without a browser.

Extracts the same fields as amazon_product_page_extract.js using only the
Python standard library. For each product it writes <id>.json (the fields)
and <id>.txt (the page text); with --db it also stores the page text through
`product_db.py update-detail`. It stops at the first CAPTCHA, robot check or
unusual redirect and exits with code 2.

    python3 amazon_fetch_pages.py --out-dir /tmp/pages B0XXXXXXXX B0YYYYYYYY
    python3 product_db.py query --db DB --min-rating 4.2 --limit 500 \\
        | python3 amazon_fetch_pages.py --out-dir /tmp/pages --db DB
"""
import argparse
import gzip
import http.client
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
NO_TEXT_TAGS = {"script", "style", "noscript", "template"}
PRICE_BOXES = ("corePrice_feature_div", "corePriceDisplay_desktop_feature_div", "apex_desktop")
SPEC_BOXES = (
    "productOverview_feature_div",
    "prodDetails",
    "technicalSpecifications_section_1",
    "poExpander",
)
APLUS_BOXES = ("aplus", "aplus_feature_div", "productDescription")
DIRECTION_MARKS = re.compile("[\u200e\u200f]")
SKIP_IMAGE = re.compile(r"pixel|transparent|\.gif(\?|$)", re.I)
DB_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_db.py")


def clean(text):
    return " ".join(DIRECTION_MARKS.sub("", text or "").split())


def number(text):
    m = re.search(r"[0-9]+(?:\.[0-9]+)?", (text or "").replace(",", "").replace("，", ""))
    if not m:
        return None
    return float(m.group(0)) if "." in m.group(0) else int(m.group(0))


def hires(url):
    return re.sub(r"\._[^/]*_\.(jpe?g|png|webp)$", r"._AC_SL1500_.\1", url or "", flags=re.I)


def unique(items):
    out = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.parent = parent

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()

    def descendants(self):
        stack = list(reversed(self.children))
        while stack:
            node = stack.pop()
            if isinstance(node, Node):
                yield node
                stack.extend(reversed(node.children))

    def find_all(self, match):
        return [n for n in self.descendants() if match(n)]

    def find(self, match):
        return next((n for n in self.descendants() if match(n)), None)

    def text(self, sep=""):
        parts = []
        stack = list(reversed(self.children))
        while stack:
            node = stack.pop()
            if isinstance(node, str):
                parts.append(node)
            elif node.tag not in NO_TEXT_TAGS:
                stack.extend(reversed(node.children))
        return clean(sep.join(parts))


def has_ancestor(node, match, stop):
    node = node.parent
    while node is not None and node is not stop:
        if match(node):
            return True
        node = node.parent
    return False


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None)
        self.current = self.root
        self.by_id = {}

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: v or "" for k, v in attrs}, self.current)
        self.current.children.append(node)
        node_id = node.attrs.get("id")
        if node_id and node_id not in self.by_id:
            self.by_id[node_id] = node
        if tag not in VOID_TAGS:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.current = self.current.parent

    def handle_endtag(self, tag):
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.current = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


def extract_price(by_id):
    for box_id in PRICE_BOXES:
        box = by_id.get(box_id)
        if box is None:
            continue
        offscreen = box.find(
            lambda n: n.has_class("a-offscreen")
            and has_ancestor(n, lambda a: a.has_class("a-price"), box)
        )
        if offscreen is not None:
            return offscreen.text()
    return ""


def extract_bullets(by_id):
    box = by_id.get("feature-bullets")
    if box is None:
        return ""
    bullets = []
    for span in box.find_all(lambda n: n.tag == "span" and n.has_class("a-list-item")):
        text = span.text()
        if text and has_ancestor(span, lambda a: a.tag == "li", box):
            bullets.append(text)
    return " | ".join(bullets)


def extract_specs(root, by_id):
    specs = {}
    boxes = [by_id[i] for i in SPEC_BOXES if i in by_id]
    boxes += root.find_all(lambda n: n.tag == "table" and n.has_class("a-keyvalue"))
    seen_rows = set()
    for box in boxes:
        for row in box.find_all(lambda n: n.tag == "tr"):
            if row in seen_rows:
                continue
            seen_rows.add(row)
            cells = [c for c in row.children if isinstance(c, Node) and c.tag in ("th", "td")]
            if not cells:
                continue
            key_cell = next((c for c in cells if c.tag == "th" or c.has_class("a-span3")), cells[0])
            key = key_cell.text()
            value = cells[-1].text() if cells[-1].tag == "td" else ""
            if key and value and key != value and len(key) < 40:
                specs[key] = value[:200]
    detail = by_id.get("detailBullets_feature_div")
    if detail is not None:
        for li in detail.find_all(lambda n: n.tag == "li"):
            line = li.text()
            i = line.find(":")
            if i > 0:
                specs[clean(line[:i])] = clean(line[i + 1:])[:200]
    return specs


def extract_main_image(by_id):
    img = by_id.get("landingImage") or by_id.get("imgBlkFront")
    if img is None:
        return ""
    if img.attrs.get("data-old-hires"):
        return img.attrs["data-old-hires"]
    try:
        first = next(iter(json.loads(img.attrs.get("data-a-dynamic-image") or "{}")), "")
    except ValueError:
        first = ""
    return first or img.attrs.get("src", "")


def extract_gallery_images(by_id):
    alt = by_id.get("altImages")
    if alt is None:
        return []
    return unique(
        hires(img.attrs.get("src", ""))
        for img in alt.find_all(lambda n: n.tag == "img")
        if "/images/I/" in img.attrs.get("src", "")
    )


def extract_aplus_images(root, by_id):
    boxes = [by_id[i] for i in APLUS_BOXES if i in by_id]
    boxes += root.find_all(lambda n: n.has_class("aplus-v2"))
    urls = []
    for box in boxes:
        for img in box.find_all(lambda n: n.tag == "img"):
            url = img.attrs.get("data-src") or img.attrs.get("src", "")
            if url.startswith("http") and not SKIP_IMAGE.search(url):
                urls.append(url)
    return unique(urls)


def is_blocked(root, by_id, title, page_text):
    if "captchacharacters" in by_id:
        return True
    if root.find(lambda n: n.tag == "form" and "validateCaptcha" in n.attrs.get("action", "")):
        return True
    return not title and bool(re.search(r"ロボット|robot", page_text[:3000], re.I))


def parse_product_page(html):
    builder = TreeBuilder()
    builder.feed(html)
    builder.close()
    root, by_id = builder.root, builder.by_id

    def text_of(node_id):
        node = by_id.get(node_id)
        return node.text() if node is not None else ""

    title = text_of("productTitle")
    popover = by_id.get("acrPopover")
    rating_raw = clean(popover.attrs.get("title", "")) if popover is not None else ""
    rating = re.search(r"のうち\s*([0-9.]+)", rating_raw) or re.search(r"([0-9.]+) out of", rating_raw)
    price_raw = extract_price(by_id)
    body = root.find(lambda n: n.tag == "body") or root
    page_text = body.text(sep=" ")
    asin_input = by_id.get("ASIN")
    record = {
        "asin": asin_input.attrs.get("value", "") if asin_input is not None else "",
        "blocked": is_blocked(root, by_id, title, page_text),
        "title": title,
        "rating": float(rating.group(1)) if rating else None,
        "rating_raw": rating_raw,
        "review_count": number(text_of("acrCustomerReviewText")),
        "price": number(price_raw),
        "price_raw": price_raw,
        "bullets": extract_bullets(by_id),
        "specs": extract_specs(root, by_id),
        "desc": text_of("productDescription")[:1500],
        "main_image": extract_main_image(by_id),
        "gallery_images": extract_gallery_images(by_id),
        "aplus_images": extract_aplus_images(root, by_id),
    }
    return record, page_text


def fetch(url, timeout):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip",
        },
    )
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        status = response.getcode()
        final_url = response.geturl()
        raw = response.read()
        if response.headers.get("Content-Encoding", "") == "gzip":
            raw = gzip.decompress(raw)
        charset = response.headers.get_content_charset() or "utf-8"
    return status, final_url, raw.decode(charset, errors="replace")


def classify(record, status, final_url):
    if record["blocked"] or status in (429, 503) or not ASIN_RE.search(final_url):
        return "blocked"
    if status == 404:
        return "not_found"
    if status != 200 or not record["title"]:
        return "unparsed"
    return "ok"


def process(target, args):
    product_id, url = target
    try:
        status, final_url, html = fetch(url, args.timeout)
    except (OSError, ValueError, EOFError, LookupError, http.client.HTTPException):
        return product_id, "failed"
    record, page_text = parse_product_page(html)
    outcome = classify(record, status, final_url)
    record.update({"product_id": product_id, "url": url, "final_url": final_url,
                   "status": status, "outcome": outcome})
    base = os.path.join(args.out_dir, product_id)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    if outcome == "ok":
        with open(base + ".txt", "w", encoding="utf-8") as f:
            f.write(page_text)
    return product_id, outcome


def store_page_text(db, product_id, path):
    result = subprocess.run(
        [sys.executable, DB_SCRIPT, "update-detail", "--db", db,
         "--product-id", product_id, "--page-text-file", path],
        capture_output=True,
        text=True,
    )
    try:
        reply = json.loads(result.stdout)
    except ValueError:
        return False
    return result.returncode == 0 and "error" not in reply


def read_items(items):
    if items or sys.stdin.isatty():
        return items
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except ValueError:
        return raw.split()
    rows = data.get("results", []) if isinstance(data, dict) else data
    return [
        (row.get("product_id") or row.get("url") or "") if isinstance(row, dict) else str(row)
        for row in rows
    ]


def asin_of(item):
    if re.fullmatch(r"[A-Z0-9]{10}", item):
        return item
    m = ASIN_RE.search(item)
    return m.group(1) if m else None


def product_url(item, asin):
    m = re.match(r"https?://[^/]+", item)
    origin = m.group(0) if m else "https://www.amazon.co.jp"
    suffix = "?language=ja_JP" if origin.endswith(".co.jp") else ""
    return f"{origin}/dp/{asin}{suffix}"


def read_targets(items):
    targets, invalid, seen = [], [], set()
    for item in read_items(items):
        item = item.strip()
        asin = asin_of(item)
        if asin is None:
            invalid.append(item)
        elif asin not in seen:
            seen.add(asin)
            targets.append((asin, product_url(item, asin)))
    return targets, invalid


def main():
    parser = argparse.ArgumentParser(description="Fetch Amazon.co.jp product pages without a browser")
    parser.add_argument(
        "items", nargs="*",
        help="ASINs or product URLs; default: stdin, which may be `product_db.py query` output",
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--db", default=None, help="store each page's text with product_db.py update-detail")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--delay", type=float, default=1.0, help="seconds to wait between batches")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    targets, invalid = read_targets(args.items)
    os.makedirs(args.out_dir, exist_ok=True)
    workers = max(1, args.workers)
    summary = {"ok": [], "stored": 0, "not_found": [], "unparsed": [], "failed": [],
               "blocked": [], "not_fetched": [], "invalid": invalid}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0, len(targets), workers):
            batch = targets[start:start + workers]
            for product_id, outcome in pool.map(lambda target: process(target, args), batch):
                summary[outcome].append(product_id)
                if outcome == "ok" and args.db:
                    path = os.path.join(args.out_dir, product_id + ".txt")
                    if store_page_text(args.db, product_id, path):
                        summary["stored"] += 1
            if summary["blocked"]:
                summary["not_fetched"] = [pid for pid, _ in targets[start + len(batch):]]
                break
            if start + len(batch) < len(targets):
                time.sleep(args.delay)
    summary["out_dir"] = args.out_dir
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(2 if summary["blocked"] else 0)


if __name__ == "__main__":
    main()
