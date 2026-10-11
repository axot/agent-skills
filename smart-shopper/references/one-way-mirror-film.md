# Category Trap: One-Way Mirror Window Film (Amazon.co.jp 窓 目隠しフィルム)

A reusable worked example of the "one keyword, several physically distinct product types, and the
highest-rated cluster is the WRONG one" pattern. Generalize the method; the specifics are JA window film.

## The user's actual need
"From inside you can see out, but from outside you can't see in." This is **one-way mirror film**
(マジックミラー / ミラーフィルム / 反射フィルム / ミラー効果). Japanese keywords:
`窓 シール 目隠し マジックミラー`, `マジックミラーフィルム 窓 外から見えない`.

## Why it's a trap — three sub-types share the same search
A search on those keywords returns a MIX:
1. **マジックミラー / ミラーフィルム (true one-way mirror)** — reflective metallic coating. Works by
   **light differential**: daytime, outside is brighter → outside sees a mirror, inside sees out.
   **At night, with interior lights on, it REVERSES — outside can see in.** This is physics, not a
   product defect, and applies to every product in this sub-type without exception.
2. **すりガラス調 / 曇りガラス / 磨りガラス (frosted)** — diffuses light. Blocks the view **both
   directions** — you can't see out clearly either. NOT one-way.
3. **ステンドグラス / 花柄 / 砂柄 / 虹色 (stained/patterned)** — decorative, also blocks both ways.

The frosted & patterned sub-types **rate higher** (often 4.3–4.6★) than the mirror sub-type
(typically capped ~4.0★) precisely BECAUSE the mirror type carries the nighttime-reversal failure
mode that frustrates some buyers into leaving low reviews. So "sort by rating, take the top" hands the
user a frosted film that does not do what they asked. The rating ceiling is a **category property**,
not a per-product quality signal.

## Classification heuristic (filter BEFORE ranking)
- Mirror sub-type if name contains: `マジックミラー`, `ミラーフィルム`, `ミラー効果`, `鏡面`,
  `反射フィルム`, `窓用ミラー`, `両面シルバー`.
- Exclude even if "マジックミラー" appears, when the name ALSO contains a frosted/decorative marker:
  `すりガラス`, `曇りガラス`, `ステンドグラス`, `磨りガラス` (these are frosted products that merely
  mention mirror in keyword stuffing).
- Within the mirror sub-type, THEN apply the user's rating/review thresholds and rank.

## Verification on the product page
Confirm the mechanism in `#feature-bullets`, not the title. Genuine one-way mirror film says things like:
- 「昼間は外側が鏡のようになり…室内からは外の景色を楽しめます」(daytime outside=mirror, inside sees out)
- 「表:アルミで UVカット ミラー効果 / 裏:黒で 中から外が見える」(front mirror / back see-through)

## How to present (always include the physics caveat)
- Lead by separating the sub-types and stating plainly that the highest-rated results are usually the
  frosted type that does NOT meet the "see out only" need.
- Give the strict-criteria pick AND a "relax to 4.0★" set, explaining that 4.0★ is the realistic
  ceiling for this sub-type and a 4.0★ item with 30k reviews is more trustworthy than a 4.2★ with 20.
- Surface caveats every buyer needs: (1) needs a day/night light differential to work, reverses at
  night with lights on → recommend curtains for bedrooms; (2) do not apply to wire-reinforced
  (網入り) or double-pane (複層) glass — thermal-crack (熱割れ) risk.

## Transmittance (透光率/可視光透過率) lives in the A+ images, not the text

When asked for transmittance per product, a text + spec-table scan of four films
(テクノエイム/ZEROSHEET, Coavas, DUOFIRE, DARUITE) found **no transmittance number** — the spec
tables list only brand/size/material/UV, and the bullets mention at most UV% and IR%. Reporting
"transmittance not published" at that point was wrong: the user knew it was printed in the
description images. Reading the A+ infographics with the vision tool surfaced a full per-color
comparison table on the **DUOFIRE** page (ASIN B0CRHH1B16):

| Variant | 可視光透過率 (VLT) | UVカット | IR/赤外線カット | privacy |
|---|---|---|---|---|
| ブラックシルバー (black-silver) | **15%** | 99% | 88% | daytime only |
| シルバーシルバー (silver) | **20%** | 99% | 83% | daytime only |
| グレーシルバー (grey-silver) | **25%** | 99% | 78% | daytime only |
| S001 frosted (not mirror) | 70% | 95% | 25% | 24h |
| (no film, reference) | 90% | <10% | 0% | — |

Read this as a rule of thumb for the whole sub-type: **mirror films run ~15–25% VLT** (darker color =
lower VLT = darker room but stronger one-way effect); a 70%+ VLT product is almost certainly a frosted
type, which fails the "see out clearly" need. テクノエイム's mesh type is an outlier at roughly ~40%
VLT (its image prints "約6℃ temperature-rise reduction" rather than a VLT number) — that higher
transmittance is exactly why it can hit 4.2★ where pure-mirror films cap near 4.0★.

**Method takeaway:** for window film (and any category where the buyer cares about a percentage),
go straight to the A+ images for VLT/UV/IR before claiming the number is absent. See SKILL.md
Step 4c-bis for the URL-collection + `._AC_SL1500_.jpg` suffix procedure.
