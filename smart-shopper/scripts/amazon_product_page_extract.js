// Amazon product-page extractor (verified on amazon.co.jp/dp/<ASIN>?language=ja_JP).
// Usage (open, wait, scroll so lazy blocks load, then eval):
//   agent-browser --session shop open "https://www.amazon.co.jp/dp/<ASIN>?language=ja_JP"
//   agent-browser --session shop wait --load networkidle
//   agent-browser --session shop scroll down 3000 && agent-browser --session shop wait 1200
//   agent-browser --session shop eval --stdin < amazon_product_page_extract.js > pg_raw.json
// Output is a JSON-encoded string (decode twice). Save `body` to a .txt for
// `product_db.py update-detail --page-text-file`, keep the rest as the spec record.
// Read mechanism claims from `bullets` and `specs`; `body` also contains sponsored
// carousels for OTHER products, so never scan it for this product's claims.
(() => {
  const t = s => (s || '').replace(/\s+/g, ' ').trim();
  const title = t((document.querySelector('#productTitle') || {}).textContent);
  const rating = t((document.querySelector('#acrPopover') || {}).title || '');
  const rc = t((document.querySelector('#acrCustomerReviewText') || {}).textContent);
  const price = t((document.querySelector('.a-price .a-offscreen') || {}).textContent);
  const bullets = Array.from(document.querySelectorAll('#feature-bullets li span.a-list-item'))
    .map(e => t(e.textContent)).join(' | ');
  const specs = {};
  document.querySelectorAll('#productOverview_feature_div tr, #prodDetails tr, #technicalSpecifications_section_1 tr, table.a-keyvalue tr, #poExpander tr').forEach(r => {
    const k = t((r.querySelector('th, td.a-span3, td:first-child') || {}).textContent);
    const v = t((r.querySelector('td:last-child') || {}).textContent);
    if (k && v && k !== v && k.length < 40) specs[k] = v.slice(0, 200);
  });
  document.querySelectorAll('#detailBullets_feature_div li').forEach(li => {
    const s = t(li.textContent); const i = s.indexOf(':');
    if (i > 0) specs[t(s.slice(0, i)).replace(/[\u200f\u200e]/g, '')] = t(s.slice(i + 1)).replace(/[\u200f\u200e]/g, '').slice(0, 200);
  });
  const desc = t((document.querySelector('#productDescription') || {}).textContent).slice(0, 1500);
  const blocked = /captcha|ロボットではありません/i.test(document.body.innerText.slice(0, 2000));
  return JSON.stringify({ title, rating, rc, price, bullets, specs, desc, blocked,
                          body: document.body.innerText.slice(0, 60000) });
})()
