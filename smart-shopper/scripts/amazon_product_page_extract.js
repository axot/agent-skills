// Amazon product-page extractor (verified on amazon.co.jp/dp/<ASIN>?language=ja_JP).
// Usage (open, scroll so lazy blocks load, then eval):
//   agent-browser --session shop open "https://www.amazon.co.jp/dp/<ASIN>?language=ja_JP"
//   agent-browser --session shop scroll down 3000 && agent-browser --session shop wait 1200
//   agent-browser --session shop eval --stdin < amazon_product_page_extract.js > /tmp/<ASIN>.json
//   python3 product_db.py update-detail --db <DB> --product-id <ASIN> --extract-file /tmp/<ASIN>.json
// update-detail stores `body` as the page text and prints the other fields. Copy the values
// the user's criteria need into flat ASCII keys for `update-detail --specs` (e.g.
// {"weight_kg": 1.2}); do not store this record as specs_json. Read mechanism claims from
// `bullets` and `specs`: `body` also contains sponsored carousels for OTHER products.
(() => {
  const clean = s => (s || '').replace(/[\u200e\u200f]/g, '').replace(/\s+/g, ' ').trim();
  const q = sel => document.querySelector(sel);
  const textOf = sel => clean((q(sel) || {}).textContent);
  const numberIn = s => { const m = (s || '').replace(/[,，]/g, '').match(/[0-9]+(?:\.[0-9]+)?/); return m ? +m[0] : null; };
  const hires = u => (u || '').replace(/\._[^/]*_\.(jpe?g|png|webp)$/i, '._AC_SL1500_.$1');

  const specsOf = () => {
    const specs = {};
    document.querySelectorAll('#productOverview_feature_div tr, #prodDetails tr, #technicalSpecifications_section_1 tr, table.a-keyvalue tr, #poExpander tr').forEach(r => {
      const k = clean((r.querySelector('th, td.a-span3, td:first-child') || {}).textContent);
      const v = clean((r.querySelector('td:last-child') || {}).textContent);
      if (k && v && k !== v && k.length < 40) specs[k] = v.slice(0, 200);
    });
    document.querySelectorAll('#detailBullets_feature_div li').forEach(li => {
      const s = clean(li.textContent);
      const i = s.indexOf(':');
      if (i > 0) specs[clean(s.slice(0, i))] = clean(s.slice(i + 1)).slice(0, 200);
    });
    return specs;
  };

  const mainImage = () => {
    const img = q('#landingImage, #imgBlkFront');
    if (!img) return '';
    if (img.getAttribute('data-old-hires')) return img.getAttribute('data-old-hires');
    try {
      const first = Object.keys(JSON.parse(img.getAttribute('data-a-dynamic-image') || '{}'))[0];
      if (first) return first;
    } catch (e) { /* malformed attribute: fall back to src */ }
    return img.currentSrc || img.src || '';
  };

  const unique = list => [...new Set(list)];
  const gallery_images = unique(Array.from(document.querySelectorAll('#altImages img'))
    .map(i => i.getAttribute('src') || '')
    .filter(u => u.includes('/images/I/'))
    .map(hires));
  const aplus_images = unique(Array.from(document.querySelectorAll('#aplus img, #aplus_feature_div img, .aplus-v2 img, #productDescription img'))
    .map(i => i.getAttribute('data-src') || i.currentSrc || i.getAttribute('src') || '')
    .filter(u => /^https?:/.test(u) && !/pixel|transparent|\.gif(\?|$)/i.test(u)));

  const title = textOf('#productTitle');
  const rating_raw = clean((q('#acrPopover') || {}).title || '');
  const ratingMatch = rating_raw.match(/のうち\s*([0-9.]+)/) || rating_raw.match(/([0-9.]+) out of/);
  // Only the buy box: elsewhere on the page `.a-price` belongs to other products.
  const price_raw = textOf('#corePrice_feature_div .a-price .a-offscreen, #corePriceDisplay_desktop_feature_div .a-price .a-offscreen, #apex_desktop .a-price .a-offscreen');
  const bodyText = document.body.innerText;
  const blocked = !!q('form[action*="validateCaptcha"], #captchacharacters') ||
    (!title && /ロボット|robot/i.test(bodyText.slice(0, 3000)));
  const asin = (location.pathname.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})/) || [])[1] || (q('#ASIN') || {}).value || '';

  return JSON.stringify({
    asin,
    url: location.href,
    blocked,
    title,
    rating: ratingMatch ? parseFloat(ratingMatch[1]) : null,
    rating_raw,
    review_count: numberIn(textOf('#acrCustomerReviewText')),
    price: numberIn(price_raw),
    price_raw,
    bullets: Array.from(document.querySelectorAll('#feature-bullets li span.a-list-item'))
      .map(e => clean(e.textContent)).filter(Boolean).join(' | '),
    specs: specsOf(),
    desc: textOf('#productDescription').slice(0, 1500),
    main_image: mainImage(),
    gallery_images,
    aplus_images,
    body: bodyText.slice(0, 60000),
  });
})()
