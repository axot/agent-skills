#!/usr/bin/env python3
"""
Aggregate normalized transactions and prepare data for LLM categorization.

Input: normalized CSV from parse_csv.py (date, merchant, amount, source)
Output: merchant_summary.json, subscription_candidates.json, overall_stats.json

The LLM only needs to categorize ~50-80 unique merchants instead of scanning 500+ rows.
"""

import csv
import json
import sys
import argparse
import os
import re
from collections import defaultdict
from datetime import datetime
import statistics


def normalize_merchant_name(name):
    """
    Normalize for grouping purposes — collapse trivial variants of the same merchant.
    Targets: full-width ASCII, corporate prefixes, trailing IDs, whitespace.
    Does NOT touch katakana (アマゾン stays as-is, won't merge with AMAZON).
    """
    s = name
    result = []
    for ch in s:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            result.append(chr(cp - 0xFEE0))
        elif cp == 0x3000:
            result.append(' ')
        else:
            result.append(ch)
    s = ''.join(result)

    s = re.sub(r'^[（(]?カ[）)]', '', s)
    s = re.sub(r'^[（(]?株[）)]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'[\s/／]+$', '', s)

    return s


def parse_date_to_month(date_str):
    formats = [
        '%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S', '%Y.%m.%d', '%Y%m%d',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m'), dt
        except ValueError:
            continue
    ymd = re.match(r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})', date_str.strip())
    if ymd:
        return f"{ymd.group(1)}-{int(ymd.group(2)):02d}", datetime(int(ymd.group(1)), int(ymd.group(2)), int(ymd.group(3)))
    return None, None


def infer_frequency(avg_days):
    if avg_days <= 0:
        return 'unknown'
    if avg_days <= 10:
        return 'weekly'
    if avg_days <= 21:
        return 'biweekly'
    if avg_days <= 45:
        return 'monthly'
    if avg_days <= 100:
        return 'quarterly'
    return 'yearly'


def analyze(input_csv, output_dir):
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("Error: No data in input CSV", file=sys.stderr)
        sys.exit(1)

    merchant_data = defaultdict(lambda: {
        'variants': set(),
        'amounts': [],
        'dates': [],
        'parsed_dates': [],
        'months': set(),
        'sources': set(),
        'monthly_breakdown': defaultdict(lambda: {'total': 0, 'count': 0}),
    })

    monthly_totals = defaultdict(float)
    monthly_counts = defaultdict(int)
    all_parsed_dates = []

    for row in rows:
        merchant_raw = row['merchant']
        amount = float(row['amount'])
        date_str = row['date']
        source = row.get('source', '')

        normalized = normalize_merchant_name(merchant_raw)
        month, parsed_dt = parse_date_to_month(date_str)

        entry = merchant_data[normalized]
        entry['variants'].add(merchant_raw)
        entry['amounts'].append(abs(amount))
        entry['dates'].append(date_str)
        entry['sources'].add(source)
        if parsed_dt:
            entry['parsed_dates'].append(parsed_dt)
            all_parsed_dates.append(parsed_dt)
        if month:
            entry['months'].add(month)
            entry['monthly_breakdown'][month]['total'] += abs(amount)
            entry['monthly_breakdown'][month]['count'] += 1
            monthly_totals[month] += abs(amount)
            monthly_counts[month] += 1

    merchant_summary = []
    subscription_candidates = []

    for normalized_name, data in sorted(merchant_data.items(), key=lambda x: -sum(x[1]['amounts'])):
        total = sum(data['amounts'])
        count = len(data['amounts'])
        avg = total / count if count > 0 else 0
        amount_std = statistics.stdev(data['amounts']) if count > 1 else 0
        amount_variance_pct = (amount_std / avg * 100) if avg > 0 else 0

        interval_stats = {}
        if len(data['parsed_dates']) >= 3:
            sorted_dates = sorted(data['parsed_dates'])
            intervals = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
            intervals = [d for d in intervals if d > 0]
            if len(intervals) >= 2:
                interval_stats = {
                    'avg_days': statistics.mean(intervals),
                    'std_days': statistics.stdev(intervals),
                }

        is_subscription = False
        subscription_confidence = None
        if count >= 3 and len(data['months']) >= 2 and len(data['parsed_dates']) >= 3:
            low_variance = amount_variance_pct < 15
            has_interval = bool(interval_stats)
            if low_variance and has_interval:
                regular_interval = interval_stats['std_days'] < 5 and 25 <= interval_stats['avg_days'] <= 35
                if regular_interval:
                    is_subscription = True
                    subscription_confidence = 'high'
                elif interval_stats['std_days'] < 15:
                    is_subscription = True
                    subscription_confidence = 'medium'

        monthly_bkdn = {
            month: {'total': round(vals['total']), 'count': vals['count']}
            for month, vals in sorted(data['monthly_breakdown'].items())
        }

        entry = {
            'normalized_name': normalized_name,
            'variants': sorted(data['variants']),
            'count': count,
            'total': round(total),
            'average': round(avg),
            'months_seen': sorted(data['months']),
            'monthly_breakdown': monthly_bkdn,
            'sources': sorted(data['sources']),
            'category': None,
        }
        merchant_summary.append(entry)

        if is_subscription:
            subscription_candidates.append({
                'merchant': normalized_name,
                'variants': sorted(data['variants']),
                'amount_avg': round(avg),
                'amount_variance_pct': round(amount_variance_pct, 1),
                'occurrences': count,
                'months_seen': sorted(data['months']),
                'interval_avg_days': round(interval_stats.get('avg_days', 0), 1),
                'interval_std_days': round(interval_stats.get('std_days', 0), 1),
                'frequency': infer_frequency(interval_stats.get('avg_days', 0)),
                'confidence': subscription_confidence,
            })

    date_range_min = min(all_parsed_dates).strftime('%Y-%m-%d') if all_parsed_dates else rows[0]['date']
    date_range_max = max(all_parsed_dates).strftime('%Y-%m-%d') if all_parsed_dates else rows[-1]['date']

    overall_stats = {
        'total_spending': round(sum(monthly_totals.values())),
        'transaction_count': len(rows),
        'unique_merchants': len(merchant_summary),
        'date_range': [date_range_min, date_range_max],
        'monthly_totals': {k: round(v) for k, v in sorted(monthly_totals.items())},
        'monthly_counts': dict(sorted(monthly_counts.items())),
    }

    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'merchant_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(merchant_summary, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'subscription_candidates.json'), 'w', encoding='utf-8') as f:
        json.dump(subscription_candidates, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'overall_stats.json'), 'w', encoding='utf-8') as f:
        json.dump(overall_stats, f, ensure_ascii=False, indent=2)

    print(f"Analyzed {len(rows)} transactions → {len(merchant_summary)} unique merchants, {len(subscription_candidates)} subscription candidates", file=sys.stderr)
    print(json.dumps({
        'merchants': len(merchant_summary),
        'subscriptions': len(subscription_candidates),
        'total_spending': overall_stats['total_spending'],
        'output_dir': output_dir,
    }))


def finalize(merchant_summary_path, subscription_candidates_path, output_dir):
    """
    After Claude assigns categories to merchant_summary.json, compute category totals
    and produce the 3 JSON files that generate_report.py expects.
    """
    with open(merchant_summary_path, 'r', encoding='utf-8') as f:
        merchants = json.load(f)

    with open(subscription_candidates_path, 'r', encoding='utf-8') as f:
        subscriptions_raw = json.load(f)

    category_map = defaultdict(lambda: {'total': 0, 'merchants': []})
    monthly_category_map = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'merchants': []}))
    repeated = []
    all_months = set()

    for m in merchants:
        cat = m.get('category') or '其他'
        display_name = m['variants'][0] if m['variants'] else m['normalized_name']
        category_map[cat]['total'] += m['total']
        category_map[cat]['merchants'].append({
            'merchant': display_name,
            'total': m['total'],
        })

        monthly = m.get('monthly_breakdown', {})
        for month, stats in monthly.items():
            all_months.add(month)
            monthly_category_map[month][cat]['total'] += stats['total']
            monthly_category_map[month][cat]['merchants'].append({
                'merchant': display_name,
                'total': stats['total'],
            })
            if stats['count'] >= 2:
                repeated.append({
                    'month': month,
                    'merchant': display_name,
                    'amount': stats['total'],
                    'count': stats['count'],
                })

    def build_categories(cat_map):
        return sorted([
            {'name': name, 'total': data['total'], 'merchants': sorted(data['merchants'], key=lambda x: -x['total'])}
            for name, data in cat_map.items()
        ], key=lambda x: -x['total'])

    categories = build_categories(category_map)

    monthly_categories = {}
    for month in sorted(all_months):
        monthly_categories[month] = build_categories(monthly_category_map[month])

    subscriptions = [{
        'merchant': s['variants'][0] if s.get('variants') else s['merchant'],
        'amount': s['amount_avg'],
        'frequency': s.get('frequency', 'monthly'),
        'months_seen': len(s.get('months_seen', [])),
    } for s in subscriptions_raw]

    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'repeated.json'), 'w', encoding='utf-8') as f:
        json.dump(repeated, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'subscriptions.json'), 'w', encoding='utf-8') as f:
        json.dump(subscriptions, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'categories.json'), 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'monthly_categories.json'), 'w', encoding='utf-8') as f:
        json.dump(monthly_categories, f, ensure_ascii=False, indent=2)

    print(f"Finalized: {len(categories)} categories, {len(subscriptions)} subscriptions, {len(repeated)} repeated, {len(all_months)} months", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Aggregate and analyze financial transactions')
    sub = parser.add_subparsers(dest='command')

    p_analyze = sub.add_parser('aggregate', help='Aggregate normalized CSV into merchant summary')
    p_analyze.add_argument('input_csv', help='Normalized CSV from parse_csv.py')
    p_analyze.add_argument('--output-dir', '-o', default='/tmp/fin_analysis')

    p_finalize = sub.add_parser('finalize', help='Compute category totals after LLM categorization')
    p_finalize.add_argument('--merchant-summary', required=True)
    p_finalize.add_argument('--subscription-candidates', required=True)
    p_finalize.add_argument('--output-dir', '-o', default='/tmp/fin_analysis')

    args = parser.parse_args()

    if args.command == 'aggregate':
        analyze(args.input_csv, args.output_dir)
    elif args.command == 'finalize':
        finalize(args.merchant_summary, args.subscription_candidates, args.output_dir)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
