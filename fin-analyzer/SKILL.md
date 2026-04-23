---
name: fin-analyzer
description: "Analyze bank and credit card CSV statements to find repeated payments, subscriptions, and spending categories. Produces a standalone interactive HTML report with tables and Chart.js doughnut charts. Use this skill whenever the user mentions analyzing bank statements, credit card bills, transaction CSVs, monthly spending, recurring charges, subscription tracking, expense categorization, or wants to understand where their money goes. Also trigger when the user uploads or references CSV files that look like financial transactions (columns like date, merchant/payee/description, amount). Works with any CSV format - Japanese bank statements, US credit card exports, European bank downloads."
---

# Financial Transaction Analyzer

Analyze bank/credit card CSV statements and produce a standalone HTML report with interactive charts.

## Architecture

The key design principle: **Python handles all math, Claude handles all judgment.**

- Counting, summing, grouping, subscription detection → Python scripts (100% accurate at any scale)
- Column identification, income detection, categorization → Claude (judgment calls that benefit from language understanding)

A 500-row bank statement might have only 50-80 unique merchants. Claude categorizes those 50-80 items — well within reliable range.

## Scripts

```
scripts/
├── parse_csv.py       # Encoding detection, CSV reading, column extraction
├── analyze.py         # Merchant aggregation, subscription detection, category finalization
└── generate_report.py # Standalone HTML report with Chart.js
```

## Workflow

### Step 1: Identify the CSV files

Ask the user which CSV files to analyze if not already clear. They might provide file paths, a directory to scan, or pasted content.

### Step 2: Preview and identify columns

Run the preview command to see the first 10 lines of each file:

```bash
python <skill-path>/scripts/parse_csv.py <file1.csv> [file2.csv ...] --preview
```

This outputs the encoding, row count, and first 10 rows with column indices. Read the output yourself and determine:

1. **Which column is date, merchant, and amount** — look at the headers and sample data
2. **Whether there's a header row** — if the first row looks like data (has dates/amounts), use `--no-header`
3. **The amount sign convention** — are expenses positive or negative? (CC statements are usually all positive; bank statements vary)
4. **Whether there's a direction column** (入出金区分 etc.) that marks income vs expense

Do NOT ask the user about any of the above — figure it out yourself from the data.

### Step 3: Parse and normalize

Extract the relevant columns:

```bash
python <skill-path>/scripts/parse_csv.py <file.csv> --date-col "利用日" --merchant-col "利用先" --amount-col "金額" --output /tmp/fin_normalized.csv
```

If you identified a direction column (入出金区分 etc.) in Step 2, include it:

```bash
python <skill-path>/scripts/parse_csv.py <file.csv> --date-col "日付" --merchant-col "摘要" --amount-col "金額" --direction-col "入出金区分" --output /tmp/fin_normalized.csv
```

This preserves the direction column in the output CSV, which you'll use in Step 4 to filter income rows.

For multiple files with different column layouts, run separately and merge:

```bash
python <skill-path>/scripts/parse_csv.py card.csv --date-col "利用日" --merchant-col "利用先" --amount-col "利用金額" --output /tmp/fin_card.csv
python <skill-path>/scripts/parse_csv.py bank.csv --date-col "日付" --merchant-col "摘要" --amount-col "出金" --output /tmp/fin_bank.csv
```

Then concatenate (skip header of second file):
```bash
cat /tmp/fin_card.csv > /tmp/fin_normalized.csv && tail -n +2 /tmp/fin_bank.csv >> /tmp/fin_normalized.csv
```

### Step 4: Clean the data

Read the normalized CSV. Before running analysis, remove rows that shouldn't be in the spending analysis. Edit the CSV or filter programmatically:

**Cross-file dedup (do first):**
When multiple CSV files from the same bank/card cover overlapping date ranges (e.g., `bank_202401.csv` and `bank_202402.csv` both contain 2/01 transactions), the boundary dates will have duplicate entries. Dedup logic:
1. Group rows by (date, merchant, amount)
2. For each group, count how many times it appears in EACH source file separately
3. The real count = max(count_per_file) — not the sum, because the same transactions appear in both files
4. Keep only max(count_per_file) rows for each group

Example: 2/01 コンビニ ¥500 appears 2 times in `bank_202401.csv` and 2 times in `bank_202402.csv` → real count = max(2, 2) = 2, not 4.

**Remove silently (don't ask):**
- Income rows — if a `direction` column is present, use it to identify income entries (入金). Otherwise infer from amount sign convention (determined in Step 2) and merchant name patterns (給与, 振込入金, 賞与, 利息). Note: 返金 and 還付 are refunds, NOT income — they are handled by the refund rule below.
- Zero-amount rows
- Credit card settlement entries from bank statements — ANY entry where the merchant name contains 振替 + a card company name (カード, ｶ-ﾄﾞ, クレジット). These are the bank paying off credit card bills — the individual charges are already in the credit card CSV. Remove ALL of them regardless of amount, not just the large ones.
- Digital wallet top-ups from bank statements — entries like ﾊﾞﾝｸPOS + wallet name, nanaco/Suica/PayPay charge entries. These are transfers from bank to a digital wallet — the actual spending happens inside the wallet app and isn't in the bank CSV. Remove them to avoid counting money that's just moving between accounts. If the user also provides wallet spending CSVs, those will capture the actual purchases.

**Handle refunds automatically (don't ask):**
Credit card CSVs often contain refund entries as negative amounts. These should offset the original charges, not be silently dropped.

1. Find all negative-amount rows in the data
2. For each refund, find the matching positive charge — same merchant name, same or similar amount (absolute value)
3. If a match is found: subtract the refund amount from the original merchant's total. Concretely:
   - If the refund exactly equals one charge → remove both the refund row and the original charge row
   - If the refund is a partial amount (e.g., charge ¥36,000 then refund ¥6,000) → keep the charge row but reduce its amount by the refund (¥36,000 → ¥30,000)
4. If no obvious match is found for a refund → remove the refund row and note it to the user
5. After processing, all remaining amounts should be positive

**Pre-flight questions (ask in one batch):**

Only ask questions that genuinely require human judgment. Combine all applicable questions into one message.

**Q1. File roles** (only if both CC and bank files exist and it's ambiguous):
> "`card_202401.csv`（85行）和 `bank_202401.csv`（12行）分别是信用卡还是银行账户？"

Skip if: only one file, or filenames are obvious.

**Q2. Ambiguous large entries** (only if they exist):
Bank entries over ¥30,000 that don't match settlement patterns and aren't obviously categorizable:
> **这几笔大额想确认一下，算支出吗？**
> - 1/15 振込 ヤマダタロウ ¥100,000

If no questions apply, skip straight to Step 5.

After the user responds, apply their decisions and ensure all remaining amounts are positive (absolute value). Save the cleaned CSV.

**Save excluded items:**
During all the cleaning above, collect every removed/modified row into a JSON file at `/tmp/fin_analysis/excluded.json`. Each entry should have:
```json
{"date": "2025/01/25", "merchant": "給与 サンプル株式会社", "amount": "300000", "source": "bank_202501.csv", "reason": "収入"}
```
Use these reason categories:
- `收入` — income rows (入金, 給与, 利息 etc.)
- `信用卡结算` — credit card settlement entries (振替)
- `电子钱包充值` — digital wallet top-ups (ﾊﾞﾝｸPOS, nanaco, Suica etc.)
- `跨文件重复` — cross-file duplicate rows
- `退款抵消` — refund rows and their matching charges that were removed
- `零金额` — zero-amount rows

This file is passed to `generate_report.py --excluded` in Step 8 so the user can verify nothing important was removed.

### Step 5: Aggregate (Python)

Run the aggregation script — this does all the math:

```bash
python <skill-path>/scripts/analyze.py aggregate /tmp/fin_normalized.csv --output-dir /tmp/fin_analysis
```

This produces:
- `merchant_summary.json` — one entry per unique merchant with count, total, average, months seen, `category: null`
- `subscription_candidates.json` — algorithmically detected subscriptions (regular intervals + consistent amounts)
- `overall_stats.json` — total spending, monthly breakdowns, transaction count

### Step 6: Categorize (Claude)

Read `merchant_summary.json`. It has ~50-80 unique merchants with `"category": null`. Your job: assign a category to each merchant.

Categories to use (Chinese names — create new ones if needed):
- 食品/生鲜, 餐饮, 购物, 交通, 旅行, 水电通信, 娱乐, 医疗, 网购, 便利店, 药妆店, 加油, 订阅服务, 家政服务, 税费, 住房贷款, 电子钱包, 自动贩卖机, 儿童, 投资, 其他

For each merchant, set the `"category"` field. Keep merchant names exactly as they appear — do not translate or modify Japanese names.

Also review `subscription_candidates.json` — confirm or remove false positives.

Write the updated `merchant_summary.json` back to disk.

**Critical rule: Do NOT recompute any totals or counts. The numbers in merchant_summary.json are authoritative. Your only job is filling in the `category` field.**

### Step 7: Finalize (Python)

Run finalization to compute category totals from your assignments:

```bash
python <skill-path>/scripts/analyze.py finalize \
  --merchant-summary /tmp/fin_analysis/merchant_summary.json \
  --subscription-candidates /tmp/fin_analysis/subscription_candidates.json \
  --output-dir /tmp/fin_analysis
```

This produces: `repeated.json`, `subscriptions.json`, `categories.json`, `monthly_categories.json`.

### Step 8: Generate report

```bash
python <skill-path>/scripts/generate_report.py \
  --repeated /tmp/fin_analysis/repeated.json \
  --subscriptions /tmp/fin_analysis/subscriptions.json \
  --categories /tmp/fin_analysis/categories.json \
  --monthly-categories /tmp/fin_analysis/monthly_categories.json \
  --excluded /tmp/fin_analysis/excluded.json \
  --output /tmp/fin_report.html
```

Then open it:
```bash
open /tmp/fin_report.html
```

Tell the user the report is ready. Report features: month tab filtering, category doughnut chart (clickable), repeated payments, subscriptions, monthly comparison bar chart, excluded items list. Dark/light theme toggle available.

### Step 9: Offer follow-up

After the report is open, ask if they want to:
- Drill into a specific category
- Compare months
- Export data to a spreadsheet
- Look at trends over time

## Edge Cases

- **Single file type only**: Skip settlement dedup if only CC or only bank files.
- **Multiple files with different column layouts**: Preview each, determine columns separately, parse each with its own column flags, then merge the output CSVs.
- **Multiple currencies**: Note the currency mix but don't attempt conversion.
- **Very large files (10,000+ rows)**: The architecture handles this — `analyze.py` aggregates efficiently regardless of row count. Claude only sees the unique merchant list.
