// Amazon search-results extractor (verified on amazon.co.jp with ?language=ja_JP).
// Usage:
//   agent-browser --session shop open "https://www.amazon.co.jp/s?k=<q>&page=<n>&language=ja_JP"
//   agent-browser --session shop wait --load networkidle
//   agent-browser --session shop eval --stdin < amazon_search_extract.js > raw.json
// raw.json holds a JSON-encoded STRING: json.load() it, then json.loads() again if the
// result is a str, before writing the list for `product_db.py insert --json-file`.
(() => {
  const out = [];
  document.querySelectorAll('div[data-asin][data-component-type="s-search-result"]').forEach((it, idx) => {
    const asin = it.dataset.asin; if (!asin || asin.length < 5) return;
    const name = ((it.querySelector('h2') || {}).textContent || '').trim();
    // JA rating text is "5つ星のうち4.2": take the number AFTER のうち, never the leading 5.
    let rating = null; const ra = it.querySelector('span.a-icon-alt');
    if (ra) { const m = ra.textContent.match(/のうち\s*([0-9.]+)/) || ra.textContent.match(/([0-9.]+) out of/); if (m) rating = parseFloat(m[1]); }
    // Review count: multi-fallback chain (layouts vary between rows and A/B variants).
    let reviews = null;
    const c = it.querySelector('[aria-label*="件の評価"],[aria-label*="個の評価"],[aria-label*="レーティング"],[aria-label*="ratings"]');
    if (c) { const m = (c.getAttribute('aria-label') || '').replace(/[,，]/g, '').match(/([0-9]+)/); if (m) reviews = +m[1]; }
    if (reviews === null) { const u = it.querySelector('a span.s-underline-text, span.s-underline-text'); if (u) { const m = u.textContent.replace(/[,，]/g, '').match(/([0-9]+)/); if (m) reviews = +m[1]; } }
    if (reviews === null) { for (const l of it.querySelectorAll('a[aria-label]')) { const lab = l.getAttribute('aria-label').replace(/[,，]/g, ''); const m = lab.match(/^([0-9]+)$/) || lab.match(/([0-9]+)\s*(ratings|件)/); if (m) { reviews = +m[1]; break; } } }
    let price = null, price_raw = null; const p = it.querySelector('span.a-price span.a-offscreen');
    if (p) { price_raw = p.textContent.trim(); const m = price_raw.replace(/[,，]/g, '').match(/([0-9]+)/); if (m) price = +m[1]; }
    const sponsored = !!it.querySelector('.puis-sponsored-label-text, [aria-label*="スポンサー"]');
    out.push({ product_id: asin, name, rating, review_count: reviews, price, price_raw, currency: 'JPY',
               search_rank: idx + 1, url: 'https://www.amazon.co.jp/dp/' + asin, sponsored });
  });
  return JSON.stringify(out);
})()
