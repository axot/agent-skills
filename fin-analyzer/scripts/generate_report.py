#!/usr/bin/env python3
"""
Generate a standalone HTML financial report from analysis JSON files.

Takes repeated payments, subscriptions, and categories JSON data and produces
an interactive HTML file with tables, Chart.js doughnut chart, and theme toggle.
"""

import json
import sys
import argparse
import os


CHART_COLORS = [
    '#ff6384', '#00d4aa', '#ffce56', '#4bc0c0', '#9966ff', '#ff9f40',
    '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c',
    '#e67e22', '#34495e', '#16a085', '#c0392b',
]

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>收支分析报告</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0f0f0f;
  --surface: #1a1a1a;
  --surface-2: #252525;
  --text: #e8e8e8;
  --text-muted: #888;
  --border: rgba(255,255,255,0.08);
  --accent: #00d4aa;
  --accent-dim: rgba(0,212,170,0.15);
  --shadow: rgba(0,0,0,0.3);
  --font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
[data-theme="light"] {
  --bg: #f5f5f5;
  --surface: #ffffff;
  --surface-2: #f0f0f0;
  --text: #1a1a1a;
  --text-muted: #666;
  --border: rgba(0,0,0,0.08);
  --accent: #0891b2;
  --accent-dim: rgba(8,145,178,0.1);
  --shadow: rgba(0,0,0,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}
header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 1.25rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
header h1 {
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}
#themeToggle {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0.4rem 0.6rem;
  border-radius: 8px;
  transition: background 0.2s;
}
#themeToggle:hover { background: var(--accent-dim); }
main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px var(--shadow);
}
.card h2 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th {
  text-align: left;
  padding: 0.6rem 0.8rem;
  border-bottom: 2px solid var(--border);
  color: var(--text-muted);
  font-weight: 500;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  user-select: none;
}
th:hover { color: var(--accent); }
th.sorted-asc::after { content: ' \u25B2'; font-size: 0.7rem; }
th.sorted-desc::after { content: ' \u25BC'; font-size: 0.7rem; }
td {
  padding: 0.5rem 0.8rem;
  border-bottom: 1px solid var(--border);
}
tr:hover td { background: var(--accent-dim); }
.amount { text-align: right; font-variant-numeric: tabular-nums; }
.count { text-align: center; }
.category-group { margin-bottom: 1.5rem; }
.category-group h3 {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.category-total {
  font-size: 0.8rem;
  color: var(--text-muted);
  font-weight: 400;
}
.chart-container {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
}
.chart-container canvas { cursor: pointer; }
.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.stat-card {
  background: var(--surface-2);
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}
.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent);
}
.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}
.empty-state {
  color: var(--text-muted);
  text-align: center;
  padding: 2rem;
  font-style: italic;
}
.month-tab-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0.6rem 2rem;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}
.month-tab-bar .tab-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-right: 0.25rem;
  font-weight: 500;
}
.month-tab {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 0.8rem;
  font-weight: 500;
  padding: 0.3rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
}
.month-tab:hover {
  color: var(--text);
  border-color: var(--accent);
}
.month-tab.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
[data-theme="light"] .month-tab.active {
  color: #fff;
}
@media (max-width: 768px) {
  header { padding: 1rem; }
  main { padding: 1rem; }
  .card { padding: 1rem; }
  table { font-size: 0.8rem; }
  th, td { padding: 0.4rem; }
  .month-tab-bar { padding: 0.5rem 1rem; }
}
</style>
</head>
<body data-theme="dark">
<header>
  <h1>收支分析报告</h1>
  <button id="themeToggle">&#x1F319;</button>
</header>
<nav class="month-tab-bar" id="monthTabBar"></nav>
<main>
  <div class="card">
    <div class="summary-stats" id="summaryStats"></div>
  </div>
  <div class="card">
    <h2>重复支出</h2>
    <div id="repeatedPayments"></div>
  </div>
  <div class="card">
    <h2>订阅服务</h2>
    <div id="subscriptions"></div>
  </div>
  <div class="card">
    <h2>分类分析</h2>
    <div class="chart-container"><canvas id="categoryChart" width="500" height="500"></canvas></div>
    <div id="categories"></div>
  </div>
  <div class="card" id="monthlyComparisonCard" style="display:none;">
    <h2>月度对比</h2>
    <div class="chart-container" style="width:100%;"><canvas id="monthlyComparisonChart"></canvas></div>
  </div>
  <div class="card" id="excludedCard" style="display:none;">
    <h2>排除项目</h2>
    <p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:1rem;">以下条目已从分析中排除。如有误排，请告知。</p>
    <div id="excludedItems"></div>
  </div>
</main>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const DATA = __DATA_PLACEHOLDER__;
const COLORS = __COLORS_PLACEHOLDER__;
let doughnutChart = null;
let currentMonth = null;

function formatAmount(n) {
  return n.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0});
}

function sortTable(table, colIdx, type) {
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const th = table.querySelectorAll('th')[colIdx];
  const asc = !th.classList.contains('sorted-asc');
  table.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc','sorted-desc'));
  th.classList.add(asc ? 'sorted-asc' : 'sorted-desc');
  rows.sort((a,b) => {
    let va = a.children[colIdx].textContent.trim();
    let vb = b.children[colIdx].textContent.trim();
    if (type === 'number') { va = parseFloat(va.replace(/,/g,'')) || 0; vb = parseFloat(vb.replace(/,/g,'')) || 0; }
    return asc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });
  rows.forEach(r => tbody.appendChild(r));
}

function renderSummary(cats) {
  const el = document.getElementById('summaryStats');
  const totalSpend = (cats || []).reduce((s,c) => s + c.total, 0);
  const subCount = (DATA.subscriptions || []).length;
  const catCount = (cats || []).length;
  el.innerHTML = `
    <div class="stat-card"><div class="stat-value">${formatAmount(totalSpend)}</div><div class="stat-label">总支出</div></div>
    <div class="stat-card"><div class="stat-value">${subCount}</div><div class="stat-label">订阅服务</div></div>
    <div class="stat-card"><div class="stat-value">${catCount}</div><div class="stat-label">消费分类</div></div>
  `;
}

function renderRepeated(month) {
  const el = document.getElementById('repeatedPayments');
  el.innerHTML = '';
  const all = DATA.repeatedPayments || DATA.repeated_payments || [];
  const items = month ? all.filter(i => i.month === month) : all;
  if (!items.length) { el.innerHTML = '<div class="empty-state">未检测到重复支出</div>'; return; }
  const table = document.createElement('table');
  table.innerHTML = '<thead><tr><th>月份</th><th>商户</th><th class="amount">月合计</th><th class="count">次数</th><th class="amount">平均每次</th></tr></thead><tbody></tbody>';
  items.forEach(item => {
    const row = document.createElement('tr');
    const avg = item.count > 0 ? Math.round(item.amount / item.count) : 0;
    row.innerHTML = `<td>${esc(item.month)}</td><td>${esc(item.merchant)}</td><td class="amount">${formatAmount(item.amount)}</td><td class="count">${item.count}</td><td class="amount">${formatAmount(avg)}</td>`;
    table.querySelector('tbody').appendChild(row);
  });
  el.appendChild(table);
  table.querySelectorAll('th').forEach((th, i) => {
    const type = (i >= 2) ? 'number' : 'string';
    th.addEventListener('click', () => sortTable(table, i, type));
  });
}

function renderSubscriptions() {
  const el = document.getElementById('subscriptions');
  const items = DATA.subscriptions || [];
  if (!items.length) { el.innerHTML = '<div class="empty-state">未检测到订阅服务</div>'; return; }
  const table = document.createElement('table');
  table.innerHTML = '<thead><tr><th>商户</th><th class="amount">金额</th><th>频率</th><th class="count">持续月数</th></tr></thead><tbody></tbody>';
  items.forEach(item => {
    const row = document.createElement('tr');
    const months = item.months_seen || item.month || '';
    row.innerHTML = `<td>${esc(item.merchant)}</td><td class="amount">${formatAmount(item.amount)}</td><td>${esc(item.frequency)}</td><td class="count">${months}</td>`;
    table.querySelector('tbody').appendChild(row);
  });
  el.appendChild(table);
  table.querySelectorAll('th').forEach((th, i) => {
    const type = (i === 1 || i === 3) ? 'number' : 'string';
    th.addEventListener('click', () => sortTable(table, i, type));
  });
}

function renderCategories(cats) {
  const el = document.getElementById('categories');
  el.innerHTML = '';
  if (!cats || !cats.length) { el.innerHTML = '<div class="empty-state">未检测到消费分类</div>'; return; }
  cats.forEach((cat, idx) => {
    const group = document.createElement('div');
    group.className = 'category-group';
    group.id = 'cat-' + idx;
    group.innerHTML = `<h3>${esc(cat.name)} <span class="category-total">${formatAmount(cat.total)}</span></h3>`;
    if (cat.merchants && cat.merchants.length) {
      const table = document.createElement('table');
      table.innerHTML = '<thead><tr><th>商户</th><th class="amount">合计</th></tr></thead><tbody></tbody>';
      cat.merchants.forEach(m => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${esc(m.merchant)}</td><td class="amount">${formatAmount(m.total)}</td>`;
        table.querySelector('tbody').appendChild(row);
      });
      group.appendChild(table);
      table.querySelectorAll('th').forEach((th, i) => {
        const type = (i === 1) ? 'number' : 'string';
        th.addEventListener('click', () => sortTable(table, i, type));
      });
    }
    el.appendChild(group);
  });
}

function renderChart(cats) {
  if (!cats || !cats.length) return;
  const canvas = document.getElementById('categoryChart');
  if (doughnutChart) { doughnutChart.destroy(); doughnutChart = null; }
  doughnutChart = new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: cats.map(c => c.name),
      datasets: [{ data: cats.map(c => c.total), backgroundColor: COLORS.slice(0, cats.length), borderColor: 'transparent', borderWidth: 0, hoverOffset: 10 }]
    },
    options: {
      responsive: false,
      cutout: '55%',
      animation: { animateScale: true, animateRotate: true },
      onClick: (evt, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          const target = document.getElementById('cat-' + idx);
          if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); target.style.transition = 'background 0.3s'; target.style.background = 'var(--accent-dim)'; setTimeout(() => target.style.background = '', 1500); }
        }
      },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16, color: getComputedStyle(document.body).getPropertyValue('--text').trim(), font: { family: "'Inter', sans-serif" } } },
        tooltip: { callbacks: { label: ctx => { const pct = ((ctx.parsed / ctx.dataset.data.reduce((a,b) => a+b, 0)) * 100).toFixed(1); return `${ctx.label}: ${formatAmount(ctx.parsed)} (${pct}%)`; } } }
      }
    }
  });
}

function buildMonthTabs() {
  const bar = document.getElementById('monthTabBar');
  const mc = DATA.monthlyCategories || {};
  const months = Object.keys(mc).sort();
  if (!months.length) { bar.style.display = 'none'; return; }
  bar.innerHTML = '<span class="tab-label">月份筛选</span>';
  const allBtn = document.createElement('button');
  allBtn.className = 'month-tab active';
  allBtn.textContent = '全部';
  allBtn.addEventListener('click', () => switchMonth(null));
  bar.appendChild(allBtn);
  months.forEach(m => {
    const btn = document.createElement('button');
    btn.className = 'month-tab';
    btn.textContent = m;
    btn.addEventListener('click', () => switchMonth(m));
    bar.appendChild(btn);
  });
}

function switchMonth(month) {
  currentMonth = month;
  const cats = month ? (DATA.monthlyCategories || {})[month] || [] : DATA.categories || [];
  document.querySelectorAll('.month-tab').forEach(btn => {
    btn.classList.toggle('active', month === null ? btn.textContent === '全部' : btn.textContent === month);
  });
  renderSummary(cats);
  renderRepeated(month);
  renderCategories(cats);
  renderChart(cats);
}

function renderMonthlyComparison() {
  const mc = DATA.monthlyCategories || {};
  const months = Object.keys(mc).sort();
  if (months.length < 1) return;
  document.getElementById('monthlyComparisonCard').style.display = '';
  const catNames = [];
  const catSet = new Set();
  months.forEach(m => (mc[m] || []).forEach(c => { if (!catSet.has(c.name)) { catSet.add(c.name); catNames.push(c.name); } }));
  const monthColors = ['#00d4aa', '#ff6384', '#ffce56', '#4bc0c0', '#9966ff', '#ff9f40', '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'];
  const datasets = months.map((m, idx) => {
    const lookup = {};
    (mc[m] || []).forEach(c => { lookup[c.name] = c.total; });
    return {
      label: m,
      data: catNames.map(n => lookup[n] || 0),
      backgroundColor: monthColors[idx % monthColors.length],
      borderRadius: 3,
      barPercentage: 0.7,
      categoryPercentage: 0.8,
    };
  });
  const canvas = document.getElementById('monthlyComparisonChart');
  const barHeight = Math.max(catNames.length * months.length * 18, 300);
  canvas.style.height = barHeight + 'px';
  new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: { labels: catNames, datasets: datasets },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: {
            color: getComputedStyle(document.body).getPropertyValue('--text-muted').trim(),
            font: { family: "'Inter', sans-serif" },
            callback: v => '¥' + formatAmount(v)
          }
        },
        y: {
          grid: { display: false },
          ticks: {
            color: getComputedStyle(document.body).getPropertyValue('--text').trim(),
            font: { family: "'Inter', sans-serif", size: 12 }
          }
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 16,
            color: getComputedStyle(document.body).getPropertyValue('--text').trim(),
            font: { family: "'Inter', sans-serif" }
          }
        },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ¥${formatAmount(ctx.parsed.x)}`
          }
        }
      }
    }
  });
}

function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

const toggle = document.getElementById('themeToggle');
toggle.addEventListener('click', () => {
  const current = document.body.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.body.setAttribute('data-theme', next);
  toggle.innerHTML = next === 'dark' ? '&#x1F319;' : '&#x2600;&#xFE0F;';
});

function renderExcluded() {
  const items = DATA.excluded || [];
  const card = document.getElementById('excludedCard');
  const el = document.getElementById('excludedItems');
  if (!items.length) return;
  card.style.display = '';
  const groups = {};
  items.forEach(item => {
    const r = item.reason || '其他';
    if (!groups[r]) groups[r] = [];
    groups[r].push(item);
  });
  Object.keys(groups).forEach(reason => {
    const section = document.createElement('div');
    section.className = 'category-group';
    const total = groups[reason].reduce((s, i) => s + Math.abs(parseFloat(i.amount) || 0), 0);
    section.innerHTML = '<h3>' + esc(reason) + ' <span class="category-total">' + groups[reason].length + '笔 / ' + formatAmount(total) + '</span></h3>';
    const table = document.createElement('table');
    table.innerHTML = '<thead><tr><th>日期</th><th>商户</th><th class="amount">金额</th><th>来源</th></tr></thead><tbody></tbody>';
    groups[reason].forEach(item => {
      const row = document.createElement('tr');
      row.innerHTML = '<td>' + esc(item.date) + '</td><td>' + esc(item.merchant) + '</td><td class="amount">' + formatAmount(Math.abs(parseFloat(item.amount) || 0)) + '</td><td>' + esc(item.source || '') + '</td>';
      table.querySelector('tbody').appendChild(row);
    });
    section.appendChild(table);
    table.querySelectorAll('th').forEach((th, i) => {
      const type = (i === 2) ? 'number' : 'string';
      th.addEventListener('click', () => sortTable(table, i, type));
    });
    el.appendChild(section);
  });
}

buildMonthTabs();
renderSummary(DATA.categories || []);
renderRepeated(null);
renderSubscriptions();
renderCategories(DATA.categories || []);
renderChart(DATA.categories || []);
renderMonthlyComparison();
renderExcluded();
</script>
</body>
</html>"""


def escape_json_for_html(obj):
    return json.dumps(obj, ensure_ascii=False).replace('</script>', '<\\/script>')


def main():
    parser = argparse.ArgumentParser(description='Generate financial HTML report')
    parser.add_argument('--repeated', help='Path to repeated payments JSON')
    parser.add_argument('--subscriptions', help='Path to subscriptions JSON')
    parser.add_argument('--categories', help='Path to categories JSON')
    parser.add_argument('--monthly-categories', help='Path to monthly categories JSON (per-month breakdown)')
    parser.add_argument('--excluded', help='Path to excluded items JSON')
    parser.add_argument('--output', '-o', default='/tmp/fin_report.html', help='Output HTML path')

    args = parser.parse_args()

    data = {}

    json_files = [
        ('repeatedPayments', args.repeated, 'repeated', []),
        ('subscriptions', args.subscriptions, 'subscriptions', []),
        ('categories', args.categories, 'categories', []),
        ('monthlyCategories', getattr(args, 'monthly_categories', None), 'monthly-categories', {}),
        ('excluded', getattr(args, 'excluded', None), 'excluded', []),
    ]

    for key, path, label, default in json_files:
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data[key] = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in {label} file ({path}): {e}", file=sys.stderr)
                data[key] = default

    report_html = HTML_TEMPLATE.replace(
        '__DATA_PLACEHOLDER__',
        escape_json_for_html(data)
    ).replace(
        '__COLORS_PLACEHOLDER__',
        json.dumps(CHART_COLORS)
    )

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report_html)

    print(f"Report generated: {args.output}")


if __name__ == '__main__':
    main()
