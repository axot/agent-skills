#!/usr/bin/env python3
import argparse
import csv
import glob
import io
import json
import os
import re
import secrets
import sqlite3
import sys
from datetime import datetime, timezone, timedelta


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    product_id TEXT NOT NULL,
    name TEXT,
    price REAL,
    price_raw TEXT,
    currency TEXT DEFAULT 'JPY',
    rating REAL,
    review_count INTEGER,
    search_rank INTEGER,
    url TEXT,
    search_query TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    specs_json TEXT,
    verified INTEGER DEFAULT 0,
    UNIQUE(platform, product_id)
);

CREATE TABLE IF NOT EXISTS product_pages (
    product_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    page_text TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (platform, product_id),
    FOREIGN KEY (platform, product_id) REFERENCES products(platform, product_id)
);

CREATE TABLE IF NOT EXISTS _meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_rating ON products(rating);
CREATE INDEX IF NOT EXISTS idx_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_platform ON products(platform);
CREATE INDEX IF NOT EXISTS idx_verified ON products(verified);
"""

CACHE_DIR = os.path.expanduser("~/.cache/smart-shopper")

EXPORT_COLUMNS = [
    "platform",
    "product_id",
    "name",
    "price",
    "currency",
    "rating",
    "review_count",
    "url",
    "verified",
    "specs_json",
]


def _now_utc():
    return datetime.now(timezone.utc).isoformat()


def _get_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _sanitize_slug(text, max_len=40):
    slug = re.sub(r"[^a-z0-9\u3040-\u9fff]+", "-", text.lower())
    return re.sub(r"-+", "-", slug).strip("-")[:max_len]


def _init_meta(conn, topic=""):
    now = _now_utc()
    for key, value in [
        ("created_at", now),
        ("last_accessed", now),
        ("description", topic),
        ("search_queries", "[]"),
    ]:
        conn.execute("INSERT OR REPLACE INTO _meta VALUES (?, ?)", (key, value))


def _touch_accessed(conn):
    conn.execute(
        "INSERT OR REPLACE INTO _meta VALUES ('last_accessed', ?)", (_now_utc(),)
    )


def _output(data):
    print(json.dumps(data, ensure_ascii=False, default=str))


def _read_meta(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT key, value FROM _meta").fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


def _db_product_count(db_path):
    try:
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def cmd_create(args):
    cache_dir = args.cache_dir or CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    slug = _sanitize_slug(args.topic) if args.topic else "unnamed"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{date_str}-{slug}-{secrets.token_hex(2)}.db"
    db_path = os.path.join(cache_dir, filename)

    conn = _get_db(db_path)
    conn.executescript(SCHEMA)
    _init_meta(conn, args.topic or "")
    conn.commit()
    conn.close()
    _output({"status": "ok", "db": db_path})


def cmd_init(args):
    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    conn = _get_db(args.db)
    conn.executescript(SCHEMA)
    _init_meta(conn, args.topic or "")
    conn.commit()
    conn.close()
    _output({"status": "ok", "db": args.db})


def cmd_insert(args):
    if not args.json and not args.json_file:
        _output({"error": "must provide --json or --json-file"})
        return

    conn = _get_db(args.db)
    conn.executescript(SCHEMA)

    raw_json = args.json
    if args.json_file:
        with open(args.json_file, "r", encoding="utf-8") as f:
            raw_json = f.read()

    products = json.loads(raw_json)
    if isinstance(products, dict):
        products = [products]

    received = len(products)
    inserted = 0
    skipped = 0
    skipped_ids = []
    for p in products:
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO products
                (platform, product_id, name, price, price_raw, currency,
                 rating, review_count, search_rank, url, search_query)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p.get("platform", args.platform or "unknown"),
                    p.get("product_id", ""),
                    p.get("name", ""),
                    p.get("price"),
                    p.get("price_raw", ""),
                    p.get("currency", "JPY"),
                    p.get("rating"),
                    p.get("review_count"),
                    p.get("search_rank"),
                    p.get("url", ""),
                    p.get("search_query", ""),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
                skipped_ids.append(p.get("product_id", "?"))
        except sqlite3.IntegrityError:
            skipped += 1
            skipped_ids.append(p.get("product_id", "?"))

    conn.commit()
    _touch_accessed(conn)

    new_terms = {p.get("search_query", "") for p in products} - {""}
    if new_terms:
        try:
            existing = json.loads(
                conn.execute(
                    "SELECT value FROM _meta WHERE key='search_queries'"
                ).fetchone()[0]
                or "[]"
            )
        except (TypeError, json.JSONDecodeError):
            existing = []
        conn.execute(
            "INSERT OR REPLACE INTO _meta VALUES ('search_queries', ?)",
            (json.dumps(list(set(existing) | new_terms), ensure_ascii=False),),
        )
        conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    result = {
        "received": received,
        "inserted": inserted,
        "skipped": skipped,
        "total_in_db": total,
    }
    if skipped_ids:
        result["skipped_ids"] = skipped_ids
    _output(result)


def cmd_query(args):
    conn = _get_db(args.db)

    conditions = []
    params = []

    if args.min_rating is not None:
        conditions.append("rating >= ?")
        params.append(args.min_rating)
    if args.max_price is not None:
        conditions.append("price <= ?")
        params.append(args.max_price)
    if args.min_reviews is not None:
        conditions.append("review_count >= ?")
        params.append(args.min_reviews)
    if args.platform:
        conditions.append("platform = ?")
        params.append(args.platform)
    if args.search:
        conditions.append("""(p.name LIKE ? OR EXISTS (
            SELECT 1 FROM product_pages pp
            WHERE pp.product_id = p.product_id AND pp.platform = p.platform
            AND pp.page_text LIKE ?))""")
        params.extend([f"%{args.search}%", f"%{args.search}%"])
    if args.verified_only:
        conditions.append("verified = 1")
    if args.spec_filter:
        for sf in args.spec_filter:
            for op in (">=", "<="):
                if op in sf:
                    key, val = sf.split(op, 1)
                    key = key.strip()
                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
                        continue
                    conditions.append(
                        f"CAST(json_extract(specs_json, '$.{key}') AS REAL) {op} ?"
                    )
                    params.append(float(val))
                    break
    if args.spec_match:
        for sm in args.spec_match:
            if "=" in sm:
                key, pattern = sm.split("=", 1)
                key = key.strip()
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
                    continue
                conditions.append(f"json_extract(specs_json, '$.{key}') LIKE ?")
                params.append(f"%{pattern.strip()}%")

    where = " AND ".join(conditions) if conditions else "1=1"
    sql = f"""SELECT id, platform, product_id, name, price, currency, rating,
                     review_count, url, search_query, verified, specs_json, created_at
              FROM products p WHERE {where}
              ORDER BY rating DESC, review_count DESC LIMIT ?"""
    params.append(args.limit or 50)

    rows = conn.execute(sql, params).fetchall()
    count_params = params[:-1]
    total_match = conn.execute(
        f"SELECT COUNT(*) FROM products p WHERE {where}", count_params
    ).fetchone()[0]
    total_all = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    conn.close()
    _output(
        {
            "results": [dict(r) for r in rows],
            "match_count": total_match,
            "total_in_db": total_all,
            "query_conditions": conditions,
        }
    )


def cmd_update_detail(args):
    conn = _get_db(args.db)
    platform = args.platform or "%"

    row = conn.execute(
        "SELECT platform FROM products WHERE product_id = ? AND platform LIKE ?",
        (args.product_id, platform),
    ).fetchone()
    if row is None:
        conn.close()
        _output({"error": "product not found", "product_id": args.product_id})
        return
    resolved_platform = args.platform or row[0]

    set_clauses = []
    params = []
    if args.verified:
        set_clauses.append("verified = 1")
    if args.specs:
        set_clauses.append("specs_json = ?")
        params.append(args.specs)
    if set_clauses:
        params.extend([args.product_id, resolved_platform])
        conn.execute(
            f"UPDATE products SET {', '.join(set_clauses)} WHERE product_id = ? AND platform = ?",
            params,
        )

    page_text = args.page_text
    if args.page_text_file:
        with open(args.page_text_file, "r", encoding="utf-8") as f:
            page_text = f.read()

    if page_text:
        conn.execute(
            "INSERT OR REPLACE INTO product_pages (product_id, platform, page_text, fetched_at) VALUES (?, ?, ?, ?)",
            (args.product_id, resolved_platform, page_text, _now_utc()),
        )

    conn.commit()
    changes = conn.total_changes
    conn.close()
    _output({"updated": changes, "product_id": args.product_id})


def cmd_stats(args):
    conn = _get_db(args.db)

    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    verified = conn.execute(
        "SELECT COUNT(*) FROM products WHERE verified = 1"
    ).fetchone()[0]
    by_platform = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT platform, COUNT(*) FROM products GROUP BY platform"
        ).fetchall()
    }
    rating_dist = {
        f"{r[0]:.1f}+": r[1]
        for r in conn.execute(
            "SELECT ROUND(rating, 0) as r, COUNT(*) FROM products WHERE rating IS NOT NULL GROUP BY r ORDER BY r DESC"
        ).fetchall()
    }
    price_row = conn.execute(
        "SELECT MIN(price), MAX(price) FROM products WHERE price IS NOT NULL"
    ).fetchone()

    conn.close()
    _output(
        {
            "total": total,
            "verified": verified,
            "by_platform": by_platform,
            "rating_distribution": rating_dist,
            "price_range": dict(price_row) if price_row else {},
        }
    )


def cmd_export(args):
    conn = _get_db(args.db)
    rows = conn.execute(
        f"SELECT {', '.join(EXPORT_COLUMNS)} FROM products ORDER BY rating DESC"
    ).fetchall()
    conn.close()

    if args.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(EXPORT_COLUMNS)
        for r in rows:
            writer.writerow(list(r))
        print(output.getvalue())
    else:
        _output([dict(r) for r in rows])


def cmd_discover(args):
    cache_dir = args.cache_dir or CACHE_DIR
    max_age = timedelta(days=args.max_age_days or 30)
    now = datetime.now(timezone.utc)

    db_files = sorted(
        glob.glob(os.path.join(cache_dir, "*.db")), key=os.path.getmtime, reverse=True
    )

    results = []
    pruned = []
    corrupt = []

    for db_path in db_files:
        meta = _read_meta(db_path)
        if not meta and os.path.getsize(db_path) > 0:
            corrupt.append(db_path)
            continue

        last_accessed = meta.get("last_accessed", "")
        try:
            accessed_dt = datetime.fromisoformat(last_accessed)
            if accessed_dt.tzinfo is None:
                accessed_dt = accessed_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            accessed_dt = datetime.fromtimestamp(
                os.path.getmtime(db_path), tz=timezone.utc
            )

        age = now - accessed_dt
        if age > max_age:
            if args.auto_cleanup:
                try:
                    os.remove(db_path)
                    pruned.append(db_path)
                except OSError:
                    pass
            continue

        search_queries = []
        try:
            search_queries = json.loads(meta.get("search_queries", "[]"))
        except json.JSONDecodeError:
            pass

        score = 0
        if args.query:
            query_lower = args.query.lower()
            for sq in search_queries:
                if query_lower in sq.lower() or sq.lower() in query_lower:
                    score += 10
            desc = meta.get("description", "").lower()
            if query_lower in desc or desc in query_lower:
                score += 5

        results.append(
            {
                "db_path": db_path,
                "description": meta.get("description", ""),
                "created_at": meta.get("created_at", ""),
                "last_accessed": last_accessed,
                "age_days": round(age.total_seconds() / 86400, 1),
                "search_queries": search_queries,
                "product_count": _db_product_count(db_path),
                "match_score": score,
            }
        )

    results.sort(key=lambda x: (-x["match_score"], x["age_days"]))
    _output(
        {
            "databases": results,
            "pruned": pruned,
            "corrupt": corrupt,
            "total_found": len(results),
            "total_pruned": len(pruned),
            "total_corrupt": len(corrupt),
        }
    )


COMMANDS = {
    "create": cmd_create,
    "init": cmd_init,
    "insert": cmd_insert,
    "query": cmd_query,
    "update-detail": cmd_update_detail,
    "stats": cmd_stats,
    "export": cmd_export,
    "discover": cmd_discover,
}


def main():
    parser = argparse.ArgumentParser(description="Smart Shopper product DB helper")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init")
    p_init.add_argument("--db", required=True)
    p_init.add_argument("--topic", default=None)

    p_create = sub.add_parser("create")
    p_create.add_argument("--topic", required=True)
    p_create.add_argument("--cache-dir", default=CACHE_DIR)

    p_insert = sub.add_parser("insert")
    p_insert.add_argument("--db", required=True)
    p_insert.add_argument("--json", default=None)
    p_insert.add_argument("--json-file", default=None)
    p_insert.add_argument("--platform", default=None)

    p_query = sub.add_parser("query")
    p_query.add_argument("--db", required=True)
    p_query.add_argument("--min-rating", type=float, default=None)
    p_query.add_argument("--max-price", type=float, default=None)
    p_query.add_argument("--min-reviews", type=int, default=None)
    p_query.add_argument("--platform", default=None)
    p_query.add_argument("--search", default=None)
    p_query.add_argument("--verified-only", action="store_true")
    p_query.add_argument("--spec-filter", nargs="*", default=[])
    p_query.add_argument("--spec-match", nargs="*", default=[])
    p_query.add_argument("--limit", type=int, default=50)

    p_detail = sub.add_parser("update-detail")
    p_detail.add_argument("--db", required=True)
    p_detail.add_argument("--product-id", required=True)
    p_detail.add_argument("--platform", default=None)
    p_detail.add_argument("--page-text", default=None)
    p_detail.add_argument("--page-text-file", default=None)
    p_detail.add_argument("--specs", default=None)
    p_detail.add_argument("--verified", action="store_true")

    p_stats = sub.add_parser("stats")
    p_stats.add_argument("--db", required=True)

    p_export = sub.add_parser("export")
    p_export.add_argument("--db", required=True)
    p_export.add_argument("--format", choices=["json", "csv"], default="json")

    p_discover = sub.add_parser("discover")
    p_discover.add_argument("--cache-dir", default=CACHE_DIR)
    p_discover.add_argument("--query", default=None)
    p_discover.add_argument("--max-age-days", type=int, default=30)
    p_discover.add_argument("--auto-cleanup", action="store_true")

    args = parser.parse_args()
    handler = COMMANDS.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
