// Amazon search-results extractor (verified on amazon.co.jp with ?language=ja_JP).
// Usage:
//   agent-browser --session shop open "https://www.amazon.co.jp/s?k=<q>&page=<n>&language=ja_JP"
//   agent-browser --session shop eval --stdin < amazon_search_extract.js > /tmp/search_p<n>.json
//   python3 product_db.py insert --db <DB> --json-file /tmp/search_p<n>.json --platform amazon.co.jp
// Output: {blocked, url, page, query, products}. `insert` reads the saved file as-is and
// exits with code 2 when the page was a CAPTCHA/robot check. Every product carries
// search_query (the `k` parameter) and search_rank (position across pages, empty for
// sponsored rows).
(() => {
  const plain = s => (s || '').replace(/[,，]/g, '');
  const integerIn = s => { const m = plain(s).match(/[0-9]+/); return m ? +m[0] : null; };
  const numberIn = s => { const m = plain(s).match(/[0-9]+(?:\.[0-9]+)?/); return m ? +m[0] : null; };

  const ratingOf = it => {
    const alt = it.querySelector('span.a-icon-alt');
    if (!alt) return null;
    // JA rating text is "5つ星のうち4.2": take the number AFTER のうち, never the leading 5.
    const m = alt.textContent.match(/のうち\s*([0-9.]+)/) || alt.textContent.match(/([0-9.]+) out of/);
    return m ? parseFloat(m[1]) : null;
  };

  // Layouts vary between rows and A/B variants, so try several places in turn.
  const reviewCountOf = it => {
    const label = it.querySelector('[aria-label*="件の評価"],[aria-label*="個の評価"],[aria-label*="レーティング"],[aria-label*="ratings"]');
    if (label) {
      const n = integerIn(label.getAttribute('aria-label'));
      if (n !== null) return n;
    }
    const link = it.querySelector('a span.s-underline-text, span.s-underline-text');
    if (link) {
      const n = integerIn(link.textContent);
      if (n !== null) return n;
    }
    for (const a of it.querySelectorAll('a[aria-label]')) {
      const text = plain(a.getAttribute('aria-label'));
      const m = text.match(/^([0-9]+)$/) || text.match(/([0-9]+)\s*(ratings|件)/);
      if (m) return +m[1];
    }
    return null;
  };

  const params = new URLSearchParams(location.search);
  const query = params.get('k') || '';
  const page = parseInt(params.get('page') || '1', 10) || 1;
  const blocked = !!document.querySelector('form[action*="validateCaptcha"], #captchacharacters');
  const isSponsored = it => !!it.querySelector('.puis-sponsored-label-text, [aria-label*="スポンサー"], [aria-label*="Sponsored"]');
  const results = Array.from(document.querySelectorAll('div[data-asin][data-component-type="s-search-result"]'))
    .filter(it => (it.dataset.asin || '').length >= 5);
  const organic = results.filter(it => !isSponsored(it));
  const sponsored = results.filter(isSponsored);

  // The info bar prints this page's range ("検索結果 685 のうち 49-96件", "49-96 of over
  // 1,000 results"). Read only the bar: the page header also shows the delivery postcode (NNN-NNNN).
  const barText = Array.from(document.querySelectorAll('[data-component-type="s-result-info-bar"]'))
    .map(e => e.textContent).join(' ');
  const range = plain(barText).match(/(\d+)\s*[-–~〜]\s*\d+/);
  const offset = range ? +range[1] - 1 : (page - 1) * organic.length;

  const products = [];
  const seen = new Set();
  const add = (it, rank) => {
    const asin = it.dataset.asin;
    if (seen.has(asin)) return;
    seen.add(asin);
    const priceEl = it.querySelector('span.a-price span.a-offscreen');
    const price_raw = priceEl ? priceEl.textContent.trim() : null;
    products.push({
      product_id: asin,
      name: ((it.querySelector('h2') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
      rating: ratingOf(it),
      review_count: reviewCountOf(it),
      price: numberIn(price_raw),
      price_raw,
      currency: 'JPY',
      search_rank: rank,
      search_query: query,
      url: location.origin + '/dp/' + asin,
    });
  };
  organic.forEach((it, i) => add(it, offset + i + 1));
  sponsored.forEach(it => add(it, null));
  return JSON.stringify({ blocked, url: location.href, page, query, products });
})()
