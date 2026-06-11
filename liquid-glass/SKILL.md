---
name: liquid-glass
description: Build Apple Liquid Glass (iOS 26 / macOS Tahoe) UI in pure HTML/CSS/SVG — real edge refraction that bends background content, chromatic dispersion rim, specular highlights. Use whenever the user asks for liquid glass, 液态玻璃, Apple-style glassmorphism, "transparent like the Apple icon", refractive glass cards/icons/navbars, or wants an existing page redone in Liquid Glass style. Far beyond plain backdrop-filter blur — covers the displacement-map technique that makes glass actually refract. Full effect Chrome/Edge; auto-degrades to frosted glass elsewhere.
---

# Apple Liquid Glass in HTML/CSS

Recreates Apple's Liquid Glass material (WWDC 2025, iOS 26 / macOS Tahoe) in a browser. The signature look: a transparent slab whose **edges visibly bend the content behind it** (refraction), with a faint **rainbow fringe** at the rim (chromatic dispersion) and a bright **specular highlight**. Plain `backdrop-filter: blur()` gives frosted glass; the refraction is what reads as "liquid".

The material is only half the look. The other half — learned from real redesign sessions — is the **background** (refraction is invisible without it) and the **typography** (heavy opaque type kills the glass feel faster than any wrong filter param). Those get their own sections.

## The stack (4 layers)

A glass element = base element + SVG lens filter + 2 pseudo-elements:

1. **Lens** — `backdrop-filter: url(#lens) blur() saturate() brightness()` where `#lens` is an SVG `feDisplacementMap` driven by a canvas-generated displacement map. Bends backdrop at edges, leaves center clear.
2. **Dispersion rim** (`::before`) — conic rainbow gradient masked to a thin border ring, blurred, `mix-blend-mode:screen`.
3. **Specular** (`::after`) — top-left linear sheen + bottom soft glow, `mix-blend-mode:screen`.
4. **Depth** — outer drop shadows + inset 1px white rim highlights (top bright, sides faint).

## Verified parameters

User-tuned on real renders (this is the "looks right" zone — start here):

| Param | Value | Meaning |
|---|---|---|
| `feDisplacementMap scale` | **-300** | Negative = concave lens look; ±120–300 usable, -300 = dramatic |
| Edge falloff exponent | **5** | `pow(t, 5)` — how sharply displacement ramps toward rim. 4–8 usable |
| `blur()` in backdrop chain | **4px** | 2px = crisp glass, 8px+ = frosted |
| Dispersion opacity | **0.50** | rainbow rim subtlety |
| `saturate()` | 1.5–1.9 | makes backdrop colors pop through glass |

## Core implementation

### SVG filter (once per page)

```html
<svg width="0" height="0" style="position:absolute"><defs>
  <filter id="lens" x="0%" y="0%" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feImage id="lensMap" result="map" preserveAspectRatio="none"/>
    <feDisplacementMap in="SourceGraphic" in2="map" scale="-300" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
</defs></svg>
```

Filter region and `feImage` must cover the SAME box or the map mis-aligns. Two working configs:

- **Tight (original): `0% / 100%`** on both. Simple, but the displacement samples outside the element resolve to **transparent black** — under hover/scroll repaints this surfaces as dark smears at card edges (bug found in production: "黒い物が出てくる").
- **Padded (recommended): `-20% / 140%`** on BOTH the `<filter>` and the `<feImage>`, plus a displacement map with a **20% neutral margin**: canvas = `SZ + 2*PAD` (PAD = SZ*0.2), fill all `rgb(128,128,128)` first, then draw the SDF map into the center SZ×SZ. Edge pixels still displace, but sampling now lands on real backdrop — transparent-black bleed is impossible.

`preserveAspectRatio="none"` stretches one square map onto any aspect ratio (slight distortion on extreme ratios is invisible in practice).

### Displacement map (JS, runs once)

Neutral gray (128,128) = no displacement. R channel displaces X, G displaces Y. Squircle (superellipse n=4) falloff matches Apple's corner geometry:

```js
const SZ=255,c=document.createElement('canvas');c.width=c.height=SZ;
const x2=c.getContext('2d'),im=x2.createImageData(SZ,SZ),d=im.data;
for(let y=0;y<SZ;y++)for(let x=0;x<SZ;x++){
  const i=(y*SZ+x)*4,nx=x/(SZ-1)*2-1,ny=y/(SZ-1)*2-1;
  const t=Math.min(Math.pow(Math.pow(Math.abs(nx),4)+Math.pow(Math.abs(ny),4),.25),1);
  const e=Math.pow(t,5);                       // edge exponent 5
  d[i]=128+nx*e*127;d[i+1]=128+ny*e*127;d[i+2]=128;d[i+3]=255;}
x2.putImageData(im,0,0);const url=c.toDataURL();
const fi=document.getElementById('lensMap');
fi.setAttribute('href',url);
fi.setAttributeNS('http://www.w3.org/1999/xlink','xlink:href',url);  // Safari needs xlink
```

### Glass class

```css
.lqg{position:relative;isolation:isolate;
  backdrop-filter:url(#lens) blur(4px) saturate(1.55) brightness(1.06);
  -webkit-backdrop-filter:url(#lens) blur(4px) saturate(1.55) brightness(1.06);
  background:rgba(255,255,255,.045);
  box-shadow:0 24px 60px -12px rgba(0,0,0,.45),0 4px 14px rgba(0,0,0,.18),
    inset 0 1.5px 1px rgba(255,255,255,.65),inset 0 -1px 1px rgba(255,255,255,.25),
    inset 1.5px 0 1px -.5px rgba(255,255,255,.35),inset -1.5px 0 1px -.5px rgba(255,255,255,.35);}
.lqg::before{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  padding:clamp(3px,2.5%,7px);
  background:conic-gradient(from 210deg,rgba(255,60,60,0) 0deg,rgba(255,80,80,.55) 40deg,
    rgba(255,200,60,.5) 80deg,rgba(80,255,140,.45) 130deg,rgba(70,180,255,.55) 190deg,
    rgba(160,90,255,.5) 250deg,rgba(255,80,160,.5) 310deg,rgba(255,60,60,0) 360deg);
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;
  filter:blur(4px);mix-blend-mode:screen;opacity:var(--disp,.5);}  /* dispersion 0–1 tunable */
.lqg::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  mix-blend-mode:screen;opacity:.85;
  background:linear-gradient(135deg,rgba(255,255,255,.5),rgba(255,255,255,.12) 28%,transparent 46%),
    radial-gradient(120% 60% at 50% 118%,rgba(255,255,255,.22),transparent 55%);}
.lqg>*{position:relative;z-index:2;}   /* content above pseudo layers */
```

## The background matters as much as the glass

Refraction is invisible against flat color. The backdrop needs **detail near glass edges** — but the kind of detail matters:

- **Best (field-tested): GlassPulse-style gradient mesh** — 4–6 large vivid radial color fields whose soft boundaries cross under glass edges, like Apple's iOS 26 wallpapers. The *color transitions* carry the refraction. No line patterns needed.
- Ghost outline numbers/text (`-webkit-text-stroke`, fill transparent) at low opacity — doubles as decoration, refracts beautifully.
- Photos also work.
- **Avoid line patterns as the primary detail** (grids, stripes, contour lines, node webs). A user verdict from a real redesign: "too many lines in the background." Lines under glass read as noise, not refraction. A faint hairline grid is acceptable as a tertiary layer at ≤0.05 alpha; never the main event.
- Keep the background layer **STATIC** (`position:fixed`, no animation). Anything moving behind glass forces every panel to re-filter per frame — the single biggest CPU cost in a glass-heavy page. Put motion *in front of* the glass instead (see flourishes in the redesign section).

## Typography on glass (the part everyone gets wrong)

Heavy opaque type on a delicate glass panel reads as "ink slapped on top" — it fights the material. Verdict from a real redesign session: the page only started feeling Apple-like after the type system changed, not the glass. Rules:

- **Weights: 700 max.** Never 900 on glass. Use size for hierarchy, not blackness. Body 400, headings 700.
- **Translucent ink, not opaque.** All text colors carry alpha so the backdrop breathes through: primary `rgba(22,30,48,.82–.92)`, secondary `.62`, tertiary `.42` (light theme; invert lightness for dark). Opaque pure `#000`/`#fff` looks pasted on — on dark glass use white *with alpha* (`rgba(255,255,255,.85–.92)`), which is what "white/near-white text" means anywhere in this skill.
- **Etched (engraved) effect** on labels/headings: `text-shadow: 0 1px 0 rgba(255,255,255,.5)` (light theme) makes glyphs read as pressed into the glass.
- **Numerals get a rounded face** — SF Rounded vibe. `M PLUS Rounded 1c` (700) is a good free stand-in for stats/prices/badges. Terminal monospace (JetBrains Mono etc.) for *all* numbers reads as a dev dashboard, not Apple; demote mono to an annotation voice only (eyebrow chips, timestamps, footnotes, tiny uppercase labels).
- **Body = system font stack** (`-apple-system, "Hiragino Sans", …`) for the native-OS feel; airy metrics: `line-height 1.8–1.85`, `letter-spacing .02em`.
- **Gradient-glass digits** for hero numbers: vertical 2-stop gradient via `background-clip:text` + `-webkit-text-fill-color:transparent`, plus `filter:drop-shadow(0 1px 0 rgba(255,255,255,.55))`. GOTCHA: a parent's `text-shadow` shows **through** clipped-transparent glyphs — always set `text-shadow:none` on the clipped element.

## Light theme variant

The defaults above are dark-tuned; light works and was user-preferred in one real project. Deltas:

- Tint `rgba(255,255,255,.10)` (vs `.045` dark); shadows tinted with ink not black: `0 24px 60px -16px rgba(28,34,48,.30)`; inset rims brighter (`.95` top). The `.lqg` CSS block above shows dark values — apply these three substitutions for light.
- Background: light gradient mesh (sky/teal/periwinkle/mint family, or warm pastels — ask the user; one user rejected pink-heavy as 太粉, cool palette won).
- Ghost detail text: dark strokes `rgba(28,34,48,.10–.14)` instead of white.
- Dispersion rim and specular layers work unchanged.

## Composing a full page redesign

When redoing an existing doc/dashboard in Liquid Glass:

1. Keep semantic structure + copy; swap visual shell.
2. Pick dark or light (sections above), build the gradient-mesh background + ghost-stat detail layer.
3. Every card/panel/nav → `.lqg` with `border-radius` 16–28px (squircle feel).
4. Apply the typography system (weights, translucent ink, rounded numerals, etched labels).
5. SVG diagrams: recolor fills to `rgba(255,255,255,.06–.12)` boxes + white strokes/text on dark, or `rgba(255,255,255,.55)` boxes + ink strokes on light; keep accent strokes. Replace emoji glyphs with proper vector icons (official brand/service icons where they exist — emoji in a polished glass UI reads as a prototype). **Audit every `<text>` against its containing box** (`getBBox()` width vs rect width) — overflowing labels are the #1 defect when porting existing diagrams; fix by widening the box, shortening copy, or splitting lines.
6. Inner sub-cards: lighter treatment — `rgba(255,255,255,.08)` + 1px white border, no second lens (nested lens = visual mud + perf cost).
7. Interactive flourishes (all compositor-only). NOTE: `::before`/`::after` are already taken by dispersion + specular, so flourishes must be **child elements** at `z-index:1` (above the lens, below content at `z-index:2`). Perf-final implementations (measured to hold 60fps p99 <19ms on Retina):
   - **Pointer glow = pre-painted disc moved by transform.** Do NOT re-paint a radial-gradient at `var(--mx)/var(--my)` per pointer event — that's a repaint per move and shows up as frame spikes. Instead: one fixed-size disc (e.g. 400×400, gradient painted once), positioned `left:-200px; top:-200px`, then `transform: translate(lxpx, lypx)` from a single rAF-throttled pointermove listener. Transform-only = zero repaints.
   - **Ripple rings = POOLED nodes, not createElement.** Pre-create ~6 `.wave` spans per glass card; spawn = round-robin pick, reset `animation:none`, set left/top, force reflow (`void el.offsetWidth`), re-enable animation. No DOM insert/remove during interaction → no layer churn under the lens.
   - **Pre-warm pools on `requestIdleCallback`**: build pools + run one invisible wave cycle + flash glow at opacity 0.001 — forces keyframe compilation and compositor layer allocation while idle, so the first real hover has no spike.
   - a periodic "sun sweep" — soft-light gradient band translating across hero panels every ~9s; cheap and consistently praised. Requires `overflow:hidden` on the panel.
   - **Hover lift on lens cards: use box-shadow, not transform.** `:hover { translateY(-4px) }` moves the element relative to its backdrop → full lens re-filter every hover. A box-shadow swap reads as lift without touching the backdrop.

## Critical gotchas

- **Chrome/Edge only for the lens.** Safari & Firefox ignore `backdrop-filter:url()` — feature-detect and degrade:
  ```js
  if(!CSS.supports('backdrop-filter','url(#x)')&&!CSS.supports('-webkit-backdrop-filter','url(#x)'))/* fallback */
  ```
  Degraded mode = drop `url(#lens)`, keep `blur(4px) saturate(1.55)` — still decent frosted glass. `::after` specular works everywhere; the `::before` dispersion rim relies on `mask-composite:exclude` which Safari handles inconsistently — verify there, or drop ::before too in degraded mode.
- **One filter per geometry family is fine** — same `#lens` reused by navbar, cards, dock. Only build separate maps for radically different shapes (circle vs long pill) if edge zone looks off.
- **Don't put `filter:` on the element itself** — must be `backdrop-filter`, else you displace the content, not the backdrop.
- **`isolation:isolate`** on glass element prevents blend-mode leakage of ::before/::after.
- **`overflow:hidden` + `contain:layout style paint` on every glass card.** Without the clip, ripple rings scaling past the card edge become "moving content behind the sibling card below" and smear darkness through ITS lens. Containment also stops internal flourish churn from invalidating anything outside the card.
- **Ghost/decoration layers and document flow.** If the ghost-stat layer is `position:absolute` (document-anchored), re-audit its coordinates after ANY change that moves section heights (`content-visibility`, added sections, font swaps) — a 150px outline numeral drifting under a frosted card renders as a giant gray smudge. Park ghosts at page edges (negative left/right), not under the card band, and keep strokes ≤0.06 alpha under 9–13px blur tiers.
- **Don't make `body` a scroll container.** `body { overflow-x:hidden }` can silently turn body into the scroller (window.scrollY stuck at 0, breaks scroll-driven JS and some browsers' scroll behavior). Put `overflow-x:hidden` on `html` instead.
- **Performance**: each glass element re-filters its backdrop on repaint; static background = cached result (see background section). The ">10 panels" caution applies to panels whose backdrop *changes* (animated or scrolling content behind them) — 20+ static-backdrop panels on one page is fine in practice. Flourish layers (`.glow`, ripples, sweeps) sit *in front of* the glass, so they don't trigger re-filtering.
- **Tier the glass.** Full stack (lens + dispersion rim) on hero panels only (~8–10); list rows / footers get a `.lite` variant: plain `blur(9px) saturate(1.4)`, `::before` rim hidden, no ripples. Visually near-identical on small rows, cuts the heavy filters by half or more. Measured result on a 23-panel page: hover-storm went 47fps → 60fps.
- **`content-visibility:auto` is a trap on glass pages.** Section re-activation during scroll re-runs the lens filters and shows up as scroll hitches; on a fixed-background page it also shifts measured section heights (breaking absolute-positioned decorations). Measure before keeping it — on the reference page removing it was the win.
- **Hidden tab / headless screenshot**: rAF and IntersectionObserver freeze — if page uses entrance animations, add `if(document.hidden)` fallback to reveal content immediately. Headless preview renderers may also not repaint after `window.scrollTo()` — to screenshot below the fold, hide earlier sections or translate `.page` (NOT `body` — that moves the `position:fixed` background away and you get a blank shot).
- **Small viewports**: the edge zone scales with element size — a near-fullscreen glass panel on mobile has huge soft edges and little clear center. Cap glass panel size or reduce edge exponent/scale under `@media (max-width:768px)`.
- **Class naming**: demo.html uses `.glass`; the snippets here use `.lqg`. Same layer structure — pick one name per project.

Full working reference with tuning sliders: `assets/demo.html` (open in Chrome).
