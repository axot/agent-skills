# Marketing-Spec Traps: when a keyword filters in products that aren't the thing

A class of search problem on Amazon (and most marketplaces): a desirable feature
keyword is used loosely across the listings, so a keyword search returns a mix of
products that all *claim* the feature but implement fundamentally different
mechanisms. Ranking by rating without classifying first hands the user the wrong
product. Always classify by real mechanism → filter → then rank.

---

## Worked example: サーキュレーター "360° 首振り" (circulator fans, Amazon.co.jp)

**The trap:** searching `360° サーキュレーター 首振り` returns ~300 listings whose
titles nearly all say "360°首振り" — but there are TWO distinct mechanisms:

| Marketing phrase | What it actually does | Is it real 360°? |
|---|---|---|
| **真水平360° 回転** (true horizontal rotation) | Head rotates a full circle, like a rotating security cam; usually a round turntable base; many let you stop/lock at any angle | ✅ YES |
| **3D送風 / 立体首振り** = 上下100° + 左右90° | Oscillates up-down ~100° AND left-right ~90°, called "360° 立体" for marketing — but the head never sweeps a full horizontal circle | ❌ NO |

The cheaper/high-volume models overwhelmingly use the second (3D) meaning while
still printing "360°" in the title. The genuinely-rotating models cluster in a few
brands (this session: **zonzon** had two qualifying SKUs).

**How to tell them apart (don't trust the title):**
- Read the **feature bullets** and the **spec table**. Real 360° says things like
  "水平/横 360度回転" or a review says "360度回転するので…自分の好きな位置に固定できる".
  Fake says "上下100°＋左右90°の3D首振り" or "上下左右 自動首振り" with explicit angles < 360.
- The Japanese 山善 AAS-KW15 (huge review count, tempting) is "左右首振り＋上下角度調節"
  → NOT true 360°. High review count ≠ matches the requirement.

**Mutually-exclusive criteria seen here:** "底盘小 (small base)" vs "高さ調節可能
(telescoping height)". Telescoping floor units need a wide base (~31×31 cm) to stay
upright; small-base units (~21×22 cm) are fixed-height tabletop. You usually cannot
get both — surface the tradeoff and give one pick per side (see SKILL.md
"Mutually-Exclusive Criteria"). Verified this session:
- zonzon B0GMPVMGYF / B0GMPWS8PX — matte white, telescoping 43–100 cm, true 360°, base ~31.8 cm (NOT small)
- Dolado B0GT4CLCF9 — white, true 360°, small base 21.6×22.5 cm, but FIXED 31.6 cm height (its "高さ調節" is only up/down tilt)

---

## Worked example: "USB-C" PC speakers for a Mac (Amazon.co.jp)

**The trap:** `USB-C スピーカー PC` returns listings that all print "USB-C" in the title,
but the port does one of two different jobs:

| Listing says | What it actually does | Cables to the Mac |
|---|---|---|
| **USBオーディオ / USBケーブル1本で給電と音声 / オーディオと電源の両方** | USB audio device: Mac lists it as a sound output; power + digital audio on one cable | 1 |
| **USB-C給電 + 3.5mmピン音声接続 / AUX入力** | USB is power only; sound must come from the headphone jack | 2 (USB + 3.5mm) |

The best-selling listing in a family is often the power-only one (e.g. the Pebble V2
sold under two ASINs, both power + 3.5mm, at different prices), while the single-cable
USB-audio variant is a different model (Pebble V3 / Pro, EDIFIER R20BT, clip-on USB
bars). Classify from the feature bullets: phrases like `USBオーディオ`, `1本で…音声`,
`3.5mm AUXジャックは不要` mean USB audio; `給電` + `3.5mmピン` / `AUX入力` as the only
audio input means power-only. "No power cord" = USB bus-powered; a listing whose spec
table says `入力電圧 110V (AC)` or reviews mentioning `コンセント` needs a mains outlet.

For movie use, tell the user to watch over the wired USB connection: several of these
listings state their Bluetooth is SBC only, which adds visible lip-sync delay.

## The general recipe (applies to any feature keyword)

1. Pull the result set into the DB as usual.
2. Before ranking, **classify each candidate by real mechanism**, using spec table +
   feature bullets + A+ images — NOT the title.
3. Filter to the variant that actually matches the user's intent.
4. Rank within that variant.
5. In the final answer, explicitly call out the look-alikes you excluded and why
   ("X has 6653 reviews but is only left-right oscillation, not true 360°").

Other likely instances of this trap: "USB-C" audio gear (USB audio vs USB power + 3.5mm),
"noise-cancelling" (ANC vs passive),
"waterproof" (IPX rating vs "water-resistant"), "fast charge" (PD/QC vs 5W),
"4K" (native vs upscaled), "leather" (genuine vs PU/合皮), "blackout" (遮光1級 vs 2級/3級).
