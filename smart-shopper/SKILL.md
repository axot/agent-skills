---
name: smart-shopper
description: Product research and comparison shopping assistant. Use this skill whenever the user wants to find, compare, or filter products on any online shopping platform (Amazon, Rakuten, Yahoo Shopping, IKEA, Costco, Taobao, JD, etc.). Triggers include "find me a product", "search for X on Amazon", "help me buy Y", "compare products", "I need a [product]", "search [platform] for", "shop for", "looking for something to buy", any mention of shopping criteria like price range, star ratings, product specifications, or when the user names a product category and an online store. Also triggers when the user changes filtering criteria mid-search (e.g., "relax the rating to 3.9", "what if we increase the budget"). This skill caches all search results in a local SQLite database so criteria changes can be answered instantly without re-searching. Load it before the first shopping search, not after ad-hoc browsing. Also for owner-review research (which models owners recommend) and multi-product setups like desk cable management.
dependencies: agent-browser
---

# Smart Shopper — Product Research & Comparison Skill

## Prerequisites

This skill requires `agent-browser` for searching and visiting pages (Amazon.co.jp product pages can also be fetched without a browser, see Step 4). Before starting any search:

1. Check if the `agent-browser` skill is available in your skill list
2. If available, load it: use the `skill` tool to load `agent-browser`
3. If NOT available, install it:
   ```bash
   npx skills add agent-browser
   ```
   Then load the skill after installation.

Do NOT proceed with any search steps until `agent-browser` is confirmed working. Quick check:
```bash
agent-browser --version
```
If the CLI itself is missing, install it: `brew install agent-browser` or `npm i -g agent-browser`, then `agent-browser install` to download the browser.

## Why This Skill Exists

Online product research is tedious: you search, open dozens of tabs, compare specs, lose track of what you've already checked, and when criteria change, you start over. This skill solves that by:

1. **Caching everything** in SQLite — criteria changes trigger instant re-filtering, not re-searching
2. **Structured extraction** — prices, ratings, review counts go into queryable columns
3. **Full page preservation** — raw page text is stored so you can dig into specs later without re-visiting

## Workflow Overview

```
User request
    ↓
[1] Clarify requirements (platform, criteria, budget, language)
    ↓
[2] Search platform via agent-browser → extract product list
    ↓
[3] Cache basic info in SQLite → immediately filter by rating/price/review_count → candidate list
    ↓  more than 20 candidates? → ask user: change the filter, or investigate all
[4] Verify candidates only (parallel batch — visit product pages, extract specs, store page_text)
    ↓
[5] Present results (table + recommendation)
    ↓
[6] User changes criteria? → Re-query cached DB, only re-search if data insufficient
```

## Owner-review research mode ("which model do owners recommend?")

When the user asks which models owners recommend or how a model holds up, the deliverable is evidence from owner reviews, not a filtered shopping list. Skip the Step 1 questionnaire, the 100-product target and the price/store-rating requirements. Prioritize actual owner reviews on specialist retailers and owner forums over manufacturer positioning, cache the focused evidence, and link directly to the reviews. Read `references/owner-review-research.md` first: it covers establishing brand coverage before narrowing, matching evidence to the exact variant, and vehicle tyres.

## Solution-scheme mode ("find better products / a better setup for this problem")

When the user wants products that implement a solution (organize a desk, wire a room, mount a device) rather than one product with criteria, the deliverable is a set of components that work together, not a ranked list of one item.

1. Skip the Step 1 questionnaire, the 100-product target and the Step 3 "more than 20 candidates" question: this mode opens a sample on purpose. Take constraints from the conversation so far (e.g. "must stay easy to adjust", "don't replace my existing cables"). Re-asking for them, or proposing what the user already rejected, is a regression.
2. Split the solution into its component layers, e.g. where the hub goes, under-desk storage, mounting the power strip, quick-access clips. Run 1–2 queries per layer, 1 page each, into one DB. Add a device-specific query for the user's exact equipment (`<model> ハブ スタンド`). Purpose-built accessories often beat generic ones, and a generic search won't surface them.
3. Filter each layer at ≥4.2★ and ≥100 reviews (`query --search-query "<the layer's query>"`, repeated for each of its queries). Open the top 1–3 per layer and read the **fit constraints** from the bullets and spec table: board-thickness range, required clamp depth, port list and limits (bus-power, shared bandwidth), maximum cable diameter, width. Grep reviews for recurring defects such as port instability or stripped screws. In the answer, say for each layer how many products passed the filter and how many you opened.
4. Present the products layer by layer, each with a bare URL. Then give 2 bundles (premium / budget) with a total price. End with the measurements the user must take before ordering (desk thickness, gap to the wall, clamp depth). Label any fit requirement you could not read from a page as inference.

For desk and cable organization, the advice principles (don't make swapping cables the method; tier cables by how often they are touched instead of hiding everything under the desk) and the per-layer fit constraints are in `references/desk-cable-management.md`.

## Step 1: Clarify Requirements

Before searching, always ask the user:

| Question | Why it matters |
|---|---|
| **Platform** | Which site to search (Amazon.co.jp, Rakuten, etc.) |
| **Product type** | What they're looking for |
| **Budget** | Price ceiling |
| **Key physical/technical criteria** | Weight, size, material, features — whatever matters for this product |
| **Rating threshold** | Minimum star rating (default: suggest 4.0+) |
| **Review requirements** | e.g., "must have Japanese reviews", minimum review count |
| **Quantity needed** | How many candidates to present (default: 10) |
| **Site language** | What language should the site display in? (default: infer from platform — e.g., Amazon.co.jp → Japanese, Amazon.com → English). If unclear, ask the user. |

Use the user's language throughout. If they write in Chinese, respond in Chinese. If Japanese, respond in Japanese.

## Step 2: Search

Use `agent-browser` to search the target platform. Construct search queries using the user's product description + key criteria keywords in the platform's language.

### Set Site Language First

agent-browser starts with a clean browser (no cookies, no language preferences). Many sites default to English even for local domains (e.g., Amazon.co.jp shows English to new visitors). **Before any search, switch the site to the correct language.**

**Amazon language switch examples:**
- Japanese: navigate to `https://www.amazon.co.jp/-/ja/` or append `?language=ja_JP` to any URL
- Chinese: `https://www.amazon.co.jp/-/zh/` or `?language=zh_CN`
- English: `https://www.amazon.co.jp/-/en/` (usually the default)

**For other platforms:** look for a language/locale selector in the page header or footer, or set the `Accept-Language` header if supported.

**Why this matters:**
- Page text stored in `product_pages` will be in the site language — if English, Japanese keyword searches on cached data won't work
- Spec table field names differ by language ("Item Weight" vs "商品の重量")
- Review language detection is more reliable when the site matches the target language

**Search target: 100+ products.** Broad coverage here means better filtering in Step 3 and less re-searching when criteria change. Aim for 100 unique products before proceeding. Fallback rules:
- After 3 keyword variations with full pagination and still under 100 → proceed with what you have.
- Below 30 products → inform the user the market is narrow and ask whether to broaden the category.

**Search strategy:**
- Use 2-3 keyword combinations that cover the core need from different angles (e.g., synonyms, category terms, brand keywords). Keep all variations within the same product category to avoid polluting the DB with irrelevant products. Insert results from each query into the DB before moving to the next.
- For each query, paginate through at least 4-5 pages of results. Most platforms show 16-48 products per page, so 4-5 pages from 2-3 queries typically reaches 100+.
- After each page insertion, check the running total via the insert command's `total_in_db` output (`UNIQUE(platform, product_id)` deduplicates, so this count reflects unique products even when queries overlap). Stop paginating once you reach 100+.
- If results are sparse despite multiple queries, broaden keywords (e.g., drop adjectives, use the parent category) and search again.
- Extract data from search result pages using JavaScript eval (fast, no need to open each product)

**Extraction pattern:** on Amazon.co.jp, use the ready-made extractors below. On other platforms, write a script of the same shape: it runs in the page through `agent-browser eval` and returns `JSON.stringify(products)`, where each product carries `product_id`, `name`, `rating`, `price`, `review_count`, `url` and `search_query`:
```javascript
// Run via agent-browser eval to extract search results
JSON.stringify(Array.from(document.querySelectorAll('[data-asin]'))
  .filter(el => el.dataset.asin.length > 3)
  .map(el => ({
    product_id: el.dataset.asin,
    name: (el.querySelector('h2 span') || {}).textContent || '',
    rating: /* extract star rating */,
    price: /* extract price */,
    review_count: /* extract review count */,
    url: 'https://www.amazon.co.jp/dp/' + el.dataset.asin,
    search_query: new URLSearchParams(location.search).get('k') || ''  // Amazon's query parameter; other sites name it differently
  })))
```

Adapt the selectors for each platform. The goal: get product_id, name, rating, price, review_count, and URL from the search results page itself. `search_query` is what `discover` matches later sessions against, and `insert` only takes it from each product, so always include it.

**CRITICAL: Write extracted data to a JSON file, not to LLM context.** Large product lists (50+ items) will be truncated or corrupted if passed through the LLM. `agent-browser eval` runs inside the page, where `require` and `fs` don't exist, so the script can't write the file itself: redirect its output into a fresh directory instead of reading it, and insert from that file in the same command (shell variables such as `$OUT` don't survive between separate commands):

```bash
OUT=$(mktemp -d)
agent-browser --session shop eval --stdin < extract.js > "$OUT/page1.json"
python3 product_db.py insert --db <DB_PATH> --json-file "$OUT/page1.json" --platform amazon.co.jp
```

The insert command outputs `received`, `inserted`, `skipped` counts. If `received` is much less than what you extracted, the JSON file was corrupted. If `skipped` is high, products were duplicates from overlapping searches (expected). `insert` reads the saved eval output as-is (agent-browser prints a returned string JSON-encoded; insert decodes it).

**Ready-made Amazon.co.jp extractors** (prefer these to writing your own):
- `scripts/amazon_search_extract.js` — one search results page. Returns `{blocked, url, page, query, products}`; each product has `product_id`, `name`, `rating` (parsed after `のうち`), `review_count` (multi-fallback chain), `price`, `price_raw`, `url`, `search_query` (the `k` parameter) and `search_rank` (position across pages, empty for sponsored rows).
- `scripts/amazon_product_page_extract.js` — one product page. Returns `title`, `rating`, `review_count`, `price`, `bullets`, `specs` (spec tables plus detail bullets), `desc`, image URLs (`main_image`, `gallery_images`, `aplus_images`) and the page text (`body`).

Loop the pages in one shell command so product data never passes through the LLM. `insert` exits with code 2 when a page was a CAPTCHA or robot check, which ends the loop:

```bash
S=/path/to/smart-shopper/scripts; OUT=$(mktemp -d)
Q=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote_plus(sys.argv[1]))' "<query>")
for n in 1 2 3 4 5; do
  agent-browser --session shop open "https://www.amazon.co.jp/s?k=$Q&page=$n&language=ja_JP" || break
  agent-browser --session shop eval --stdin < "$S/amazon_search_extract.js" > "$OUT/p$n.json" || break
  python3 "$S/product_db.py" insert --db <DB_PATH> --json-file "$OUT/p$n.json" --platform amazon.co.jp || break
done
```

Don't add `agent-browser wait --load networkidle` before extracting. On an Amazon.co.jp product page it ran until its 25-second timeout, although every field the extractors read was already in the page when `open` returned.

## Step 3: Cache & Filter

Store basic info (name, price, rating, review_count, URL) for all extracted products in SQLite. This is cheap — just search result data, no page visits needed. Then **immediately filter** to identify candidates for detailed verification.

**Database directory:** `~/.cache/smart-shopper/`

**Filename format:** `{YYYY-MM-DD}-{topic-slug}-{4hex}.db`
Example: `2026-03-29-garden-table-set-a3f1.db`

### Database Discovery (automatic — don't ask the user unless ambiguous)

Every DB contains a `_meta` table with `created_at`, `last_accessed`, `description`, and `search_queries` (JSON array). Use this for auto-matching.

```
Start of skill invocation
  │
  ├─ Already have DB_PATH in this conversation?
  │   └─ YES → reuse it, skip discovery
  │
  ├─ Run: product_db.py discover --query "user's search terms" --auto-cleanup
  │
  ├─ 0 databases found → create new DB
  │
  ├─ Results with match_score > 0?
  │   ├─ Exactly 1 match → auto-select, tell user: "Continuing with [description]"
  │   └─ Multiple matches → show list, ask user to pick
  │
  ├─ All results have match_score = 0 (no keyword overlap)?
  │   ├─ Any DB accessed in last 24h → show it as option, ask if related
  │   └─ Otherwise → create new DB
  │
  └─ discover also prunes DBs not accessed in 30+ days
```

The key rule: **never auto-select a DB without query matching**. Recency alone is not enough — a "keyboard" search must not silently attach to yesterday's "chair" DB.

**Auto-discovery command (also prunes >30 day old DBs):**
```bash
python3 /path/to/smart-shopper/scripts/product_db.py discover --cache-dir ~/.cache/smart-shopper --query "user's search terms" --auto-cleanup
```
This returns matching DBs sorted by relevance score, and silently removes any DB not accessed in 30+ days.

### Creating a New DB

```bash
python3 /path/to/smart-shopper/scripts/product_db.py create --topic "garden table set"
```

This generates a safe filename internally (sanitized slug + UTC date + random hex) and returns the path in JSON:
```json
{"status": "ok", "db": "/Users/you/.cache/smart-shopper/2026-03-29-garden-table-set-a3f1.db"}
```

Never construct DB filenames in shell commands — always use the `create` command to avoid injection risks.

### Within a Conversation

Always reuse the same DB. Multiple product categories can coexist (tracked by `search_query` column); `query --search-query "<query>"` filters to one of them.

### Self-Cleanup

Cleanup is built into the `discover` command — when `--auto-cleanup` is passed, any DB with `last_accessed` older than 30 days is automatically removed. No separate cleanup step needed.

Use the helper script to manage the database:

```bash
python3 /path/to/smart-shopper/scripts/product_db.py create --topic "garden table set"
python3 /path/to/smart-shopper/scripts/product_db.py insert --db <DB_PATH> --json-file /tmp/products.json --platform amazon.co.jp
python3 /path/to/smart-shopper/scripts/product_db.py query --db <DB_PATH> --min-rating 4.2 --max-price 100000
python3 /path/to/smart-shopper/scripts/product_db.py update-detail --db <DB_PATH> --product-id "B09T97Z57Y" --page-text-file /tmp/page.txt --specs '{"weight": "16.74kg", ...}'
python3 /path/to/smart-shopper/scripts/product_db.py update-detail --db <DB_PATH> --product-id "B09T97Z57Y" --extract-file /path/to/B09T97Z57Y.json
python3 /path/to/smart-shopper/scripts/product_db.py update-detail --db <DB_PATH> --product-id "B09T97Z57Y" --verified
python3 /path/to/smart-shopper/scripts/product_db.py query --db <DB_PATH> --spec-filter "table_weight_kg>=12" --spec-match "material=wood"
python3 /path/to/smart-shopper/scripts/product_db.py query --db <DB_PATH> --search-query "ガーデンテーブル セット" --min-rating 4.2
```

**Schema:**

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    product_id TEXT NOT NULL,
    name TEXT,
    price REAL,
    price_raw TEXT,                    -- original text e.g. "¥12,800" / "$128.00"
    currency TEXT DEFAULT 'JPY',
    rating REAL,
    review_count INTEGER,
    search_rank INTEGER,              -- position in search results (quality signal)
    url TEXT,
    search_query TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    specs_json TEXT,
    verified INTEGER DEFAULT 0,
    UNIQUE(platform, product_id)
);

CREATE TABLE product_pages (          -- separate table to keep products lean
    product_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    page_text TEXT,                    -- full innerText for later extraction
    fetched_at TIMESTAMP,
    PRIMARY KEY (platform, product_id)
);

CREATE TABLE product_queries (        -- every query that found a product
    platform TEXT NOT NULL,
    product_id TEXT NOT NULL,
    search_query TEXT NOT NULL,
    PRIMARY KEY (platform, product_id, search_query)
);

CREATE TABLE _meta (key TEXT PRIMARY KEY, value TEXT);
```

**Key design decisions:**
- `product_pages` is a separate table so filter queries on `products` stay fast (no 100KB blobs scanned).
- `price_raw` preserves the original display text; `price` is the parsed numeric value for SQL comparison.
- `search_rank` captures result position — a free quality signal.
- `specs_json` stores extracted specifications as a JSON object (e.g., `{"table_weight_kg": 16.74, "chair_weight_kg": 7.64, "material": "PS wood"}`).
- `UNIQUE(platform, product_id)` prevents duplicates when searches overlap. `products.search_query` keeps the first query that found a product; `product_queries` records all of them, and `query --search-query` checks both.
- `verified` flag tracks which products have been individually checked.

### Immediate Filtering

Right after inserting products, filter using the data already available from search results. **Do NOT visit any product pages yet** — this filter uses only what's in the `products` table.

```sql
SELECT * FROM products
WHERE rating >= 4.2          -- replace with user's threshold
  AND price <= 100000         -- replace with user's budget
  AND review_count >= 10      -- default minimum; replace with user's if specified
ORDER BY rating DESC, review_count DESC;
```

**Default minimum review count is 10** unless the user specifies otherwise. Products with fewer than 10 reviews have unreliable ratings and waste page visits.

Respect strict wording: "大于 / more than 4.2" excludes exactly 4.2. Query inclusively (`>=`) so the boundary items stay in hand, then report exact-boundary products separately as the first relaxation option instead of mixing them into the qualifying list.

This produces the **candidate list** — only these products proceed to Step 4 (page visits + detailed verification). The remaining products stay in the DB for potential re-query if the user relaxes criteria later, but their pages are never visited.

Note: criteria that can't be expressed in SQL (e.g., "Japanese reviews exist", "chair weight per component") require visiting the product page — these are checked in Step 4, not here.

If insufficient products match, tell the user how many matched and suggest criteria relaxation. Show the distribution: "Found 3 products at ≥4.2★. Relaxing to ≥3.9★ would add 4 more."

**More than 20 candidates → ask the user before visiting any page.** Report the candidate count and offer two choices:
1. **Change the filter** — show how many candidates tighter thresholds would leave (run the counts in SQL on the cached DB), e.g., "61 candidates. ≥4.4★ → 23, ≤¥50,000 → 18, ≥100 reviews → 15."
2. **Investigate all** — check every candidate's page. On Amazon.co.jp the fetch script in Step 4 handles about 60 pages a minute; browser visits take about 5 seconds each (61 candidates ≈ 5 minutes).

Wait for the answer. Every product that passes the user's thresholds is in scope. Do not pick a subset yourself — not the first few by Candidate ordering, not the top-rated few, not one per brand, not the famous brands or the largest review counts (the omitted items can include the category's best seller). If the changed filter still leaves more than 20, ask again. Skip the question only when the user has already explicitly asked to investigate all candidates.

## Step 4: Detailed Verification

Step 3 filtered using basic search-result data (rating, price, review count). But many user criteria — weight, material, dimensions, review language — are only available on the product page. Step 4 has three phases:

1. **Batch extract**: Visit candidate pages in parallel, extract specs → store in DB
2. **Detailed filter**: SQL filter again using the newly extracted specs → much smaller final set
3. **Verify**: Cross-verify and checklist only the final few products

Example flow:
> 61 candidates (from Step 3) → more than 20, user chose "Investigate all" → batch page visits → extract specs → detailed filter (weight≥12kg, chair≥7kg) → **5 finalists** → cross-verify + checklist

### Page Extraction Strategy

Visiting product pages is the biggest time bottleneck (about 5 seconds per page in the browser; on Amazon.co.jp the fetch script below is much faster). Two approaches available — choose based on candidate count and environment stability.

#### Default: Sequential Extraction with Smart Ordering (Recommended)

Visit candidate pages **sequentially in the parent agent**. This is simpler, more reliable, and often faster than parallel sub-agents because:
- No sub-agent initialization overhead (~30s each)
- No browser session conflicts
- Early termination: stop once enough qualifying products are found
- Resumable: specs persist in DB after each product, so interruptions don't lose progress

**Candidate ordering** (visit most-likely-qualifying products first):
1. Known heavy brands first (e.g., Yamazen Garden Master, THREE STONE, aks for furniture)
2. Higher price (correlates with heavier construction)
3. Higher review count (more data available for verification)

This ordering only sets which page to open first; it is not a cutoff. Visit every candidate in the list — stop early only via the early termination check (step 5 below) or an Error Recovery case.

**Resume check** — before visiting any pages, skip products already extracted:
```sql
SELECT product_id, url FROM products
WHERE specs_json IS NULL
  AND rating >= ?    -- Step 3 filter criteria
  AND price <= ?
ORDER BY price DESC, rating DESC;
```
This makes the workflow resumable after network interruptions — just re-run and it picks up where it left off.

**Fast path for Amazon.co.jp product pages (no browser):** `scripts/amazon_fetch_pages.py` fetches product pages over plain HTTP and extracts the same fields as `amazon_product_page_extract.js`, using only the Python standard library. Pipe the candidate list into it:

```bash
python3 /path/to/smart-shopper/scripts/product_db.py query --db <DB_PATH> --min-rating 4.2 --max-price 100000 --min-reviews 10 --limit 500 \
  | python3 /path/to/smart-shopper/scripts/amazon_fetch_pages.py --out-dir "$(mktemp -d)" --db <DB_PATH>
```

It handles about 60 pages a minute. For each product it writes `<id>.json` (the fields) and `<id>.txt` (the page text) into the output directory, stores the page text in `product_pages`, and prints a summary. It stops at the first CAPTCHA, robot check or unusual redirect, exits with code 2 and lists the IDs it did not fetch; then follow the CAPTCHA rule in Error Recovery. From each `<id>.json`, read only the fields the criteria need (usually `specs` and `bullets`; the image lists matter only for 4c-bis) and store the values with `update-detail --specs`. Use it whenever the candidate list exceeds about 8, so the cost of browser visits never tempts you to sample the candidates. Use the browser for pages it reports as `unparsed`, and for checks that need scrolling, clicking or screenshots (review language, visual checks).

**Batch size (browser visits):** a page costs about 5 seconds (open, scroll, extract), and a foreground command is time-capped. Size each call to that limit (20 pages take about 100 seconds), write each page's output to disk as it finishes so a timed-out batch loses nothing, and list what landed on disk before re-running the rest.

**For each candidate (browser):**
1. `agent-browser open {url}` (it returns once the page has loaded)
2. Scroll to load dynamic content (reviews, spec tables often lazy-load)
3. Extract full page text → write to temp file → `python3 {script} update-detail --db {db} --product-id {id} --page-text-file {tmpdir}/{id}_page.txt`. On Amazon.co.jp, run `scripts/amazon_product_page_extract.js` into `{tmpdir}/{id}.json` instead and store it with `update-detail --extract-file {tmpdir}/{id}.json`, which saves `body` as the page text and prints the other fields. (`{tmpdir}` is a directory made once with `mktemp -d`; write its literal path into each command, because shell variables don't carry over between commands.)
4. Extract specs from the structured spec table (not marketing copy) → `python3 {script} update-detail --db {db} --product-id {id} --specs '{...}'`
5. **Early termination check**: if the user requested N qualifying products and you've found N products that pass ALL spec criteria so far, you may stop visiting remaining candidates and proceed to Step 4a. Skip this check when the user wants all candidates investigated (chosen at the Step 3 question or asked for up front) — then visit every candidate.

#### Alternative: Parallel Sub-Agent Extraction

Use only when: (a) ≥ 20 candidates, (b) network is stable, (c) you've confirmed agent-browser supports parallel sessions.

**CRITICAL: Each sub-agent MUST use a unique `--session` flag** to avoid browser daemon conflicts:
```bash
agent-browser --session batch-1 open {url}
agent-browser --session batch-1 eval "..."
```

**Batch strategy:**
- Split into batches of ~10, spawn one sub-agent per batch
- Maximum 3 concurrent sub-agents (more risks resource exhaustion)

**Sub-agent delegation template:**

```
task(
  category="unspecified-low",
  load_skills=["agent-browser"],
  run_in_background=true,
  description="Extract product details batch N/M",
  prompt="
    TASK: Visit product pages and extract detailed specs. Data extraction only — do NOT make pass/fail judgments.

    BROWSER SESSION: Use --session batch-{N} for ALL agent-browser commands to avoid conflicts with other agents.
    Example: agent-browser --session batch-{N} open {url}

    DB: {db_path}
    SCRIPT: python3 {path/to/product_db.py}

    PRODUCTS (batch N of M):
    1. {product_id} | {url} | {name}
    2. ...

    SPECS TO EXTRACT (based on user criteria):
    - {spec 1, e.g., table weight in kg}
    - {spec 2, e.g., chair weight in kg}
    - {spec 3, e.g., material type}
    - ...

    FOR EACH PRODUCT:
    1. agent-browser --session batch-{N} open {url}
    2. Scroll to load dynamic content (reviews, spec tables often lazy-load)
    3. Extract full page text → write to a temp file, then store:
       python3 {script} update-detail --db {db} --product-id {id} --page-text-file /tmp/{id}_page.txt
    4. Extract ALL specs listed above from the structured spec table (not marketing copy)
    5. Store specs in specs_json:
       python3 {script} update-detail --db {db} --product-id {id} --specs '{...}'

    WHEN DONE: Close your browser session:
       agent-browser --session batch-{N} close

    MUST NOT:
    - Set verified=1 (that happens later, after detailed filtering)
    - Skip storing data for any product — even if specs look bad (data is valuable for later criteria changes)
    - Retry more than once if agent-browser fails on a product — skip and move on
    - Use agent-browser WITHOUT --session batch-{N} (will conflict with other agents)

    RETURN: For each product: product_id, extracted specs summary, any specs that were NOT found on the page.
  "
)
```

**After all sub-agents complete:**
1. Close any remaining browser sessions: `agent-browser --session batch-{N} close` for each batch
2. Collect results and note any products where specs could not be extracted
2. Proceed to Step 4a (detailed filtering)

### 4a: Detailed Filtering (second-round filter)

Now that `specs_json` is populated from page visits, filter again using the detailed specs. This is the **second filter** — it uses product page data that wasn't available in Step 3.

```sql
SELECT p.*, pp.page_text FROM products p
LEFT JOIN product_pages pp ON p.product_id = pp.product_id AND p.platform = pp.platform
WHERE (json_extract(p.specs_json, '$.table_weight_kg') >= 12
       OR json_extract(p.specs_json, '$.table_weight_kg') IS NULL)
  AND (json_extract(p.specs_json, '$.chair_weight_kg') >= 7
       OR json_extract(p.specs_json, '$.chair_weight_kg') IS NULL)
  AND (json_extract(p.specs_json, '$.material') NOT LIKE '%cedar%'
       OR json_extract(p.specs_json, '$.material') IS NULL)
ORDER BY p.rating DESC, p.review_count DESC;
```

The `IS NULL` clauses are critical — without them, products where the sub-agent couldn't extract a spec are silently dropped. These are exactly the products that need cross-verification in Step 4b.

This typically reduces the candidate set dramatically (e.g., 61 → 5). Only these **finalists** proceed to cross-verification and the full checklist.

If a spec couldn't be extracted (sub-agent reported it missing), don't discard the product — include it in the finalists for manual cross-verification in Step 4b.

Report the funnel to the user:
> "61 candidates → page visits complete → detailed filter (weight, material) → **5 finalists**"

### 4b: Cross-Verification (only for finalists with missing/ambiguous specs)

Only for the small set of finalists from Step 4a, and only when a critical spec is missing or ambiguous.

**When to cross-verify:**
- A spec the user explicitly cares about is **not directly stated** on the product page (this includes cases where you could calculate it from other values — calculation is not verification)
- The product page shows a total weight but not per-component breakdown
- A claim seems inconsistent (e.g., "Item Weight 14kg" but individual parts sum to 28kg)
- Values are **ambiguous**: two or more conflicting values for the same spec on the page, OR a value that differs significantly from similar products, OR a value only in marketing copy but missing from the specs table

**How to cross-verify safely:**
1. Extract the **exact model number** from the product page (e.g., "MFC-259D", "HMTS-50", "KPT-1470")
2. Search the model number using whatever search tools you have available (web search, DDG, webfetch, etc.) — simply search for `"manufacturer name" + "model number" + "specs"` or the equivalent in the relevant language
3. **Match identity strictly**: the model number, dimensions, and manufacturer must ALL match. A similar-looking product from the same brand is NOT the same product.
4. If the cross-verified spec is found, update `specs_json` in the DB and note the source

Do NOT hardcode any specific verification site (e.g., Kakaku.com is Japan-only). Use whatever search capability the agent currently has. The model number is the key — it's globally unique and searchable on any search engine.

**Identity matching rules:**
- ✅ Same manufacturer + same model number + same dimensions → confirmed match
- ❌ Same manufacturer + different model suffix (e.g., MFC-259D vs MFC-259DN) → treat as different unless specs page covers both
- ❌ Same appearance + different brand → NOT the same product
- ❌ Similar name but no model number match → NOT verified

**Do NOT cross-verify when:**
- The product page directly states the exact value your criterion needs (not a derived or related value — the actual number)
- The product has no identifiable model number (generic no-brand items)
- You're just curious — only cross-verify for specs the user's criteria depend on

### 4c: Screenshot Verification

Only if the user's criteria involve something that can't be verified from text alone (e.g., "can this chair really lie flat?" or "what does the design look like?"). Don't screenshot by default — it's slow. If you do screenshot, use `agent-browser screenshot` + `look_at` tool to analyze the image.

### 4c-bis: A+ description images carry specs the text does NOT — READ THE IMAGES

A hard-won lesson: for many product categories, the **most important numeric specs are printed inside the A+ marketing/description images, NOT in the page text or the structured spec table.** Examples seen in the wild: window-film **可視光透過率/透光率 (visible-light transmittance), UVカット%, 赤外線/IRカット%** appear only as a comparison-table graphic in the `#aplus` block; the spec table lists only brand/size/material and the text bullets list only one or two of the percentages.

**Failure mode to avoid:** scanning `document.body.innerText` + the spec table, finding nothing, and telling the user "this parameter is not published / doesn't exist." That is **confidently-wrong** — the user can see the number in the image and will (rightly) push back. When a user asks for a spec that text-scan can't find, the next step is to READ THE IMAGES before concluding it's absent.

**Procedure when a requested spec isn't in text/spec-table:**
1. Collect A+ / description image URLs. On Amazon.co.jp both product-page scripts return them (`main_image`, `gallery_images`, `aplus_images`). Elsewhere they live in `#aplus img, .aplus-v2 img, #aplus_feature_div img, #productDescription img` plus the main gallery (`#altImages img`, `[data-a-dynamic-image]`): read `data-old-hires` / `data-src` / `currentSrc`, and parse `data-a-dynamic-image` JSON keys for hi-res URLs.
2. **Amazon image-URL gotcha:** the bare base URL (e.g. `https://m.media-amazon.com/images/I/71G4Au+gCtL`) often returns **HTTP 400** to a vision fetch. Append a size suffix to make it loadable: `...71G4Au+gCtL._AC_SL1500_.jpg`. Strip any existing `._...` segment first, then add `._AC_SL1500_.jpg`.
3. The biggest images (filename prefixes `61/71/81…`) are the A+ infographics where spec tables/percentages are printed. Feed those to the vision tool and ask it to read every number+label (透過率, 遮光率, UV, IR, 温度, etc.). Implementation specs are often a per-color / per-variant comparison table (e.g. ブラックシルバー 可視光15% / シルバー 20% / グレー 25%).
4. Only after reading the images may you state a spec is "not published." Report a number read from an image as the manufacturer's stated value. When it decides pass/fail, it is still marketing copy missing from the spec table, so cross-verify it as 4b requires.

### 4d: Criterion Verification Checklist

After all data is collected (page extraction, detailed filtering, cross-verification), go through EVERY user criterion one by one for each finalist before marking it as verified. For each criterion:

1. **State the criterion** (e.g., "Japanese reviews must exist")
2. **State how you verified it** (e.g., "Opened review section, found 3 reviews in Japanese")
3. **State the result** — pass or fail
4. **Tag the evidence type**: `[direct]` = read from page, `[cross-verified]` = from external source, `[estimated]` = derived/calculated (must resolve via 4b first), `[unverified]` = could not confirm

**Only set `verified = 1` when ALL user criteria show `[direct]` or `[cross-verified]`.** Products with any `[estimated]` or `[unverified]` criteria must NOT be marked verified — either resolve them via cross-verification or present them to the user with the tag visible.

**Criterion type → verification method:**

| Criterion Type | Examples | How to Verify |
|---|---|---|
| **Numeric spec** | weight ≥ 7kg, price ≤ ¥10k | Read the exact value from a structured spec table on the product page. If only a related value exists (e.g., total weight but not per-component), treat the specific value as missing → cross-verify (4b). |
| **Review quality** | "Japanese reviews exist", "≥10 reviews" | Open the review section of the product page (scroll/click to load it). Count reviews matching the requirement. A star rating or review count alone does NOT satisfy a review-language requirement. |
| **Visual/behavioral** | "fully flat recline", "fits 4 people" | Screenshot verification (4c), or find an explicit spec value (e.g., "recline angle: 180°"). Product title claims do not count. |
| **Material/durability** | "no cedar", "waterproof" | Read material from the spec table. Assess durability based on the material type identified. |
| **Spec printed only in A+ image** | 透過率/透光率, UV%, IR%, 遮光率, dB rating | Text-scan + spec table first; if absent, collect A+ image URLs and READ them with the vision tool (Step 4c-bis). Do NOT declare the spec "unpublished" until images are read. |
| **Availability** | "Prime eligible", "in stock" | Check the specific section on the product page. |

## Step 5: Present Results

Present the most relevant fields for this product search. Every product MUST carry:
- Product name (abbreviated if long)
- Price
- Rating + review count
- A clickable link (the `url` column)
- Key criteria columns (whatever the user specified — weight, material, size, etc.)

**Every product you show carries its link, next to the product.** That includes shortlists, quick summaries and recommendation picks. A link listed in a separate block or an earlier message doesn't count, and neither does holding links back until the user asks. When space is short, abbreviate the name, never the link. If a product genuinely has no URL, write `—` and say why.

**On chat platforms (Telegram, WhatsApp, Discord), use bare URLs, not Markdown links in table cells.** A `[text](url)` inside a table cell often shows as plain text with nothing to tap. Give each product a short block with the bare URL on its own line (chat clients turn bare URLs into links):

```
**1. Product name** — 4.3★ / 281 reviews / ¥4,430 — key spec
https://www.amazon.co.jp/dp/XXXXXXXXXX
```

A Markdown table is still fine for name/price/rating/spec columns there, as long as the links sit outside it as bare URLs.

After the product list, add a **brief recommendation section** organized by use case. Each pick repeats its link:

```markdown
| Priority | Pick | Reason |
|---|---|---|
| Value | Product A | Cheapest that meets all criteria |
| Quality | Product C | Highest rating + most reviews |

Product A: https://www.amazon.co.jp/dp/XXXXXXXXXX
Product C: https://www.amazon.co.jp/dp/YYYYYYYYYY
```

### Pre-delivery audit

Treat the answer as not ready until each check passes:
1. Every product shown has a clickable link (on chat platforms, a bare URL on its own line).
2. Every product in the recommended list passes the user's stated filters (rating / reviews / price / sub-type). Anything else you show (boundary items, relaxation options, the other side of a tradeoff) names the criterion it fails or couldn't confirm.
3. Off-target sub-types (Category Traps) are separated out, not silently mixed into the recommendation.

## Step 6: Iterate

When the user changes criteria:

1. **First, query the existing DB** — instant results
2. **Report what's available**: "Relaxing to ≥3.9★: found N additional products in cache"
3. **If newly qualifying products lack page data**, distinguish two cases:
   - **Never visited** (no row in `product_pages`): run Step 4 batch extraction for them — if more than 20, ask the user first, same as Step 3
   - **Visited but spec missing** (`product_pages` exists, `specs_json` is NULL): skip extraction, go directly to cross-verification (Step 4b)
4. **Only re-search if the DB doesn't have enough data** (e.g., user wants a completely different product type)

This is the key advantage of the caching design: what previously required 20 minutes of re-searching now takes 2 seconds.

### Common follow-ups after a shortlist

- **"哪个好看 / which looks best":** looks are subjective, so show the images instead of describing them. Take each product's `main_image` from the product-page script output and write a numbered HTML grid (image plus number and short name per cell) to `grid.html` in a fresh `mktemp -d` directory. Render it with agent-browser: `agent-browser set viewport 1200 900`, then `agent-browser open "file://<dir>/grid.html"`, then `agent-browser wait --fn "Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)"`, then `agent-browser screenshot --full <dir>/grid.png`. Look at the PNG before sending it to check that every row and caption is visible. Then group the products by style (retro, minimal, rugged, cute) and give one opinion.
- **"一次充电用多久 / runtime":** lead with the runtime at the highest brightness. The headline "最长 XX 時間" is almost always measured at the lowest mode. Mark every number as a manufacturer claim, say so in the user's language when the page gives no figure, and label any estimate you derive from mAh and lumens as your own. Finish with a practical takeaway, for example which models last a 4–5 h evening on medium and which last it on max.
- **User sends a product link that isn't in your answer:** resolve the short link with `curl -s -o /dev/null -w "%{redirect_url}" <amzn.asia link>` to get the ASIN, then check the DB for it first. If it is already cached and passes the filter, say plainly that you dropped it and why, verify its page, and give the user the number still unchecked.

## Important Principles

### Honesty Over Quantity
If the user asks for 10 products but only 6 genuinely meet all criteria, say so. Don't pad the list with products that don't qualify. Suggest criteria relaxation instead.

### Don't Trust Text — Verify Claims
Product titles and bullet points often exaggerate. "180° fully flat" might be 150°. "Lightweight" might be 11kg. When a specific claim matters to the user, verify it on the actual product page's structured specification table, not from marketing copy or search results summaries.

### Direct Observation, Not Derivation
When a specification determines whether a product meets user criteria, the value MUST come from direct reading on a product page spec table, manufacturer spec sheet, or cross-verified external source.

**Never derive a user-critical spec through calculation.** Example: if the page shows total weight (34kg) and table weight (18kg), do NOT calculate bench weight as (34-18)/2 = 8kg. Instead, treat bench weight as "not directly stated" and trigger cross-verification (Step 4b).

Why this matters: mathematical derivation introduces compounding errors (shipping weight vs. product weight, accessories included vs. excluded, rounding). A derived value that passes a threshold by a small margin (8kg vs. 7kg requirement) is especially unreliable.

An implausible spec-table value (a desktop speaker listed as 100 cm wide) is a listing error: say so, and if you fall back on a sibling model's stated value, label it as inference.

### Highest-Rated ≠ What The User Asked For (Category Traps)
A keyword search often returns several *physically distinct* product types under one label, and the **highest-rated cluster is frequently NOT the type the user wants**. Before ranking by rating, classify the result set by mechanism/sub-type and filter to the type that actually matches the stated need — then rank within it. Blindly returning the top-rated items hands the user the wrong product with a confident 4.5★.

A worked example (Amazon.co.jp window privacy film: true one-way *mirror* film vs. frosted/stained types that block both directions, where the frosted type rates higher precisely because it lacks the mirror type's nighttime-reversal failure mode) is in `references/one-way-mirror-film.md`. Treat it as the template for any "looks like one category, is actually three" search: name the sub-types, explain why ratings skew, filter before ranking, and surface the physics-driven caveat in the final answer.

A second worked example (Amazon.co.jp サーキュレーター / circulator fans: marketed "360°首振り" splits into **true horizontal 360° head rotation** vs. **fake "3D送風" = 上下100°+左右90°** that never rotates a full circle) is in `references/marketing-spec-traps.md`. Same drill: the keyword filters in lots of products whose titles all say "360°" but whose mechanism is different — read the spec table / feature bullets / A+ images to classify *real* vs *marketing* 360° before ranking. The same file covers "USB-C" speakers and audio gear, where single-cable USB-audio models and USB-power-plus-3.5mm models both print "USB-C" in the title.

A third worked example (Amazon.co.jp weed control: a casual "撒在地里防野草的东西" splits into THREE classes — 固まる砂/防草砂 (hardening sand) vs 防草シート/砂利 (barrier sheet/gravel) vs 除草剤粒剤 (granular herbicide = the "药/medicine"), and within herbicide again into 土壌処理型 vs 茎葉処理型 vs 芝生用 vs 水稲用) is in `references/weed-control-category-traps.md`, with the wording cues that tell the classes apart. Always ask whether plants nearby must be preserved before recommending a 土壌処理型 (long-residual) product — it suppresses wanted plants too.

### Mutually-Exclusive Criteria — Surface The Tradeoff, Don't Pick Silently
Sometimes two of the user's stated requirements **cannot physically coexist in one product**, and the catalog enforces it as a clean split. Example: a circulator that is BOTH "底盘小 (small base)" AND "高さ調節可能 (telescoping height)" barely exists — telescoping floor models need a wide (~31cm) base for stability, while small-base (~21cm) models are fixed-height tabletop units. When you detect this:
1. Name the tradeoff explicitly to the user (don't quietly optimize one side and drop the other).
2. Present a best pick for EACH side of the tradeoff (e.g. "if height-adjust matters most → X; if small base matters most → Y"), with the disqualifying attribute called out.
3. Ask which axis is the priority before finalizing.

This is far more useful than returning one product that silently fails a criterion the user explicitly asked for.

### Show Your Work on Filtering
When presenting results, briefly note how many total products were found, how many passed each filter, and how many survived to the final list. This helps the user understand the market and make informed decisions about relaxing criteria.

Example:
> Searched 3 keyword variations, paginated 4-5 pages each → 127 products cached.
> After filtering (★≥4.2, ¥≤100,000, reviews≥10): 31 remain.
> After weight verification (table≥12kg, chair≥7kg): 5 qualify.

### Category-Specific Notes
Read the file when the request falls in that category:
- High-end GPUs (live prices, multi-GPU build quotes): `references/gpu-price-research.md`
- Cables and chargers (USB-IF / Thunderbolt / MFi / PSE certification, construction and stiffness): `references/cable-certification.md`

### Platform-Specific Tips

**Amazon.co.jp / .com:**
- Extract ASINs from `[data-asin]` attributes; iterate `div[data-asin][data-component-type="s-search-result"]` for search results (the extractor leaves `search_rank` empty for sponsored rows)
- Product URL pattern: `https://www.amazon.co.jp/dp/{ASIN}`
- Rating and price need JavaScript extraction from specific selectors
- "Item Weight" on Amazon is unreliable — could be shipping weight, single component, or total
- **Search results paginate via `&page=N`** in the URL (results 1-48 on page 1, 49-96 on page 2, …). Re-navigate per page rather than clicking.

**Verified JA-layout selectors (search results page, `?language=ja_JP`):** the JA layout differs from EN and naive parsing silently corrupts data — capture the right field:
- **Rating**: `span.a-icon-alt` text is `"5つ星のうち4.2"`. Parse the number *after* `のうち`: `text.match(/のうち\s*([0-9.]+)/)`. A naive `match(/([0-9.]+)/)` grabs the leading **5** ("5つ星") and reports every product as 5.0★ — wrong.
- **Review count**: find the element whose `aria-label` matches `/レーティング|個の評価|件の評価/` (e.g. `"4,898 レーティング"`), strip commas, take the integer. The visible `(4898)` link text works as fallback.
- **Price**: `span.a-price span.a-offscreen` → `"￥980"`.

**Verified product-page selectors:** title `#productTitle`; rating `#acrPopover` `title` attr (`"5つ星のうち4.2"`); review count `#acrCustomerReviewText`; feature bullets `#feature-bullets li span.a-list-item`. The feature bullets are where directionality/mechanism claims live — read them, not just the title.

**Review-count extraction needs a multi-fallback chain — a single selector silently returns all-null.** Amazon serves several search-results layouts (A/B variants, JA vs EN, ad vs organic rows), and the element holding the review count moves between them; one selector alone (`span.a-size-base.s-underline-text`) once returned `reviews: null` for all 48 products on a page. `scripts/amazon_search_extract.js` tries an aria-label match, then the underline-text count link, then a bare-number aria-label, and takes the first hit. When a new layout appears, add its selector there.

**Sanity-check the yield before proceeding:** after extraction, check how many products got a non-null `review_count`. A healthy page looks like 38 of 48, where the nulls are new listings without reviews. If the non-null count is near zero, the selector chain missed the current layout — inspect one result element's HTML and add the layout's selector, don't push forward with an all-null filter.

**Claims about this product** (certifications, mechanism, materials): read them only from `#productTitle`, `#feature-bullets` and the spec table. The rest of the page text includes sponsored carousels for other products, for example other brands' "USB-IF認証取得" on almost every cable page, so a page-wide scan attributes their claims to this product.

**Rakuten:**
- Product IDs from URL patterns
- Rating system differs (may need normalization)

**Other platforms:**
- Adapt selectors and URL patterns as needed
- The core workflow (search → extract → cache → filter → verify → present) is the same

## Error Recovery

Searching shopping sites involves many things that can go wrong. Handle them gracefully instead of retrying blindly.

### CAPTCHA / Anti-Bot Detection
Shopping platforms aggressively block automation. If you encounter a CAPTCHA, access-denied page, or unusual redirect:
1. **Stop immediately** — do NOT retry in a loop (this wastes tokens and may trigger harder blocks)
2. Inform the user: "Amazon is showing a CAPTCHA. I can't proceed automatically."
3. Suggest alternatives: user can solve the CAPTCHA manually, or try a different search keyword, or try again later

### Search Returns 0 Results
1. Try 2 alternative keyword combinations (broader terms, different language, different word order)
2. If still 0 results, report to user with the keywords tried — the product category may not exist on this platform

### Database Errors
- **SQLITE_BUSY** (another process is using the DB): the script includes a 5-second built-in wait (`busy_timeout`). If you still see this error during Step 4 parallel extraction, do NOT create a new DB — retry once after 5 seconds. Only create a new DB if the error persists outside of parallel extraction (e.g., during initial setup).
- **Corrupt DB**: if any DB operation throws `sqlite3.DatabaseError`, skip that DB in discovery and inform the user. Don't crash the entire workflow.

### agent-browser Failures
- If `agent-browser` crashes or times out, try once more. If it fails again, close the browser (`agent-browser close`) and inform the user.
- If the platform page doesn't load (timeout, network error), skip that product and move to the next candidate. Don't block the entire search on one product.
