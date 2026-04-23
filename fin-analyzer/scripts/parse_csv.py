#!/usr/bin/env python3
"""
Parse financial CSV files with explicit column mapping.

Handles encoding detection, full-width normalization, and amount parsing.
Column mapping is determined externally (by the LLM reading the first 10 lines).

Usage:
    python parse_csv.py file.csv --date-col 0 --merchant-col 2 --amount-col 3 --output normalized.csv
    python parse_csv.py file.csv --date-col "利用日" --merchant-col "利用先" --amount-col "金額" --output normalized.csv
    python parse_csv.py file.csv --preview   # show first 10 lines for column detection
"""

import csv
import sys
import argparse
import re
import os


def normalize_text(text):
    """Normalize full-width ASCII to half-width for comparison. Does NOT touch katakana."""
    if not text:
        return ''
    result = []
    for ch in text:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            result.append(chr(cp - 0xFEE0))
        elif cp == 0x3000:
            result.append(' ')
        else:
            result.append(ch)
    return ''.join(result)


def parse_amount(value):
    """Parse monetary amounts like '¥1,590', '-3400', '(500)', '１，５９０' → float."""
    value = normalize_text(str(value).strip())
    if not value:
        return 0.0
    negative = False
    if value.startswith('(') and value.endswith(')'):
        negative = True
        value = value[1:-1]
    if value.startswith('-') or value.startswith('\u2212'):
        negative = True
        value = value[1:]

    cleaned = re.sub(r'[¥$€£,\s円]', '', value)
    try:
        result = float(cleaned)
        return -result if negative else result
    except ValueError:
        return 0.0


def detect_encoding(filepath):
    encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp', 'iso-2022-jp', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'utf-8'


def read_csv_raw(filepath):
    encoding = detect_encoding(filepath)
    with open(filepath, 'r', encoding=encoding, errors='replace', newline='') as f:
        reader = csv.reader(f)
        return list(reader)


def preview_file(filepath):
    rows = read_csv_raw(filepath)
    print(f"=== {os.path.basename(filepath)} ({len(rows)} rows, encoding: {detect_encoding(filepath)}) ===")
    for i, row in enumerate(rows[:10]):
        print(f"  [{i}] {row}")
    print()


def resolve_col(col_spec, headers):
    if col_spec.isdigit():
        return int(col_spec)
    if headers:
        col_map = {normalize_text(h).strip(): i for i, h in enumerate(headers)}
        idx = col_map.get(normalize_text(col_spec).strip())
        if idx is not None:
            return idx
        for i, h in enumerate(headers):
            if col_spec.lower() in normalize_text(h).strip().lower():
                return i
    return None


def extract_columns(filepath, date_col, merchant_col, amount_col, direction_col=None, has_header=True):
    rows = read_csv_raw(filepath)
    if not rows:
        return []

    headers = rows[0] if has_header else None
    data_rows = rows[1:] if has_header else rows

    date_idx = resolve_col(date_col, headers)
    merchant_idx = resolve_col(merchant_col, headers)
    amount_idx = resolve_col(amount_col, headers)

    direction_idx = None
    if direction_col:
        direction_idx = resolve_col(direction_col, headers)
        if direction_idx is None:
            print(f"Warning: Could not resolve direction column '{direction_col}', ignoring", file=sys.stderr)

    required = {date_col: date_idx, merchant_col: merchant_idx, amount_col: amount_idx}
    if any(v is None for v in required.values()):
        print(f"Error: Could not resolve columns: {required}", file=sys.stderr)
        if headers:
            print(f"Available headers: {headers}", file=sys.stderr)
        return []

    max_idx = max(date_idx, merchant_idx, amount_idx)
    normalized = []

    for row in data_rows:
        if len(row) <= max_idx:
            continue
        date_val = str(row[date_idx]).strip()
        merchant_val = str(row[merchant_idx]).strip()
        amount_val = parse_amount(row[amount_idx])

        if not date_val or not merchant_val or amount_val == 0:
            continue

        entry = {
            'date': date_val,
            'merchant': merchant_val,
            'amount': amount_val,
        }

        if direction_idx is not None and direction_idx < len(row):
            entry['direction'] = str(row[direction_idx]).strip()

        normalized.append(entry)

    return normalized


def main():
    parser = argparse.ArgumentParser(description='Parse financial CSV files')
    parser.add_argument('files', nargs='+', help='CSV files to parse')
    parser.add_argument('--output', '-o', default='/tmp/fin_normalized.csv')
    parser.add_argument('--preview', action='store_true', help='Show first 10 lines of each file and exit')
    parser.add_argument('--date-col', help='Date column name or 0-based index')
    parser.add_argument('--merchant-col', help='Merchant column name or 0-based index')
    parser.add_argument('--amount-col', help='Amount column name or 0-based index')
    parser.add_argument('--direction-col', help='Optional income/expense direction column name or index')
    parser.add_argument('--no-header', action='store_true', help='CSV has no header row')

    args = parser.parse_args()

    if args.preview:
        for filepath in args.files:
            if os.path.exists(filepath):
                preview_file(filepath)
            else:
                print(f"Warning: File not found: {filepath}", file=sys.stderr)
        return

    if not args.date_col or not args.merchant_col or not args.amount_col:
        print("Error: --date-col, --merchant-col, and --amount-col are required (use --preview first to inspect the CSV)", file=sys.stderr)
        sys.exit(1)

    all_rows = []
    has_direction = False

    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"Warning: File not found: {filepath}", file=sys.stderr)
            continue
        rows = extract_columns(
            filepath, args.date_col, args.merchant_col, args.amount_col,
            direction_col=args.direction_col, has_header=not args.no_header,
        )
        source_label = os.path.basename(filepath)
        for row in rows:
            row['source'] = source_label
            if 'direction' in row:
                has_direction = True
        all_rows.extend(rows)
        print(f"Parsed {len(rows)} rows from {filepath}", file=sys.stderr)

    if not all_rows:
        print("Error: No data parsed from any file", file=sys.stderr)
        sys.exit(1)

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    fieldnames = ['date', 'merchant', 'amount', 'source']
    if has_direction:
        fieldnames.append('direction')

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} normalized rows to {output_path}", file=sys.stderr)
    print(f'{{"total_rows": {len(all_rows)}, "output": "{output_path}", "has_direction": {str(has_direction).lower()}}}')


if __name__ == '__main__':
    main()
