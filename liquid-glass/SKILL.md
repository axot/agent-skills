---
name: liquid-glass
description: Build Apple Liquid Glass (iOS 26 / macOS Tahoe) UI in pure HTML/CSS/SVG — real edge refraction that bends background content, chromatic dispersion rim, specular highlights. Use whenever the user asks for liquid glass, 液态玻璃, Apple-style glassmorphism, "transparent like the Apple icon", refractive glass cards/icons/navbars, or wants an existing page redone in Liquid Glass style. Far beyond plain backdrop-filter blur — covers the displacement-map technique that makes glass actually refract. Full effect Chrome/Edge; auto-degrades to frosted glass elsewhere.
---

# Apple Liquid Glass in HTML/CSS

Recreates Apple's Liquid Glass material (WWDC 2025, iOS 26 / macOS Tahoe) in a browser. The signature look: a transparent slab whose **edges visibly bend the content behind it** (refraction), with a faint **rainbow fringe** at the rim (chromatic dispersion) and a bright **specular highlight**. Plain `backdrop-filter: blur()` gives frosted glass; the refraction is what reads as "liquid".

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

`x/y/width/height` MUST be `0%/0%/100%/100%` — default `-10%` filter region offsets the feImage map and breaks edge alignment. `preserveAspectRatio="none"` stretches one square map onto any aspect ratio (slight distortion on extreme ratios is invisible in practice).

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

Refraction is invisible against flat color. The backdrop needs **high-frequency detail near glass edges**: large text, thin stripes, grid patterns, photos. Recipe that works: vivid multi-radial gradient base + 2–3 drifting blurred color blobs (`mix-blend-mode:screen`) + big bold text/outlined text/stripe+grid patterns scattered behind glass. If user's page has a plain background, add a detail layer or the effect dies.

## Critical gotchas

- **Chrome/Edge only for the lens.** Safari & Firefox ignore `backdrop-filter:url()` — feature-detect and warn or degrade:
  ```js
  if(!CSS.supports('backdrop-filter','url(#x)')&&!CSS.supports('-webkit-backdrop-filter','url(#x)'))/* fallback */
  ```
  Degraded mode = drop `url(#lens)`, keep `blur(4px) saturate(1.55)` — still decent frosted glass. `::after` specular works everywhere; the `::before` dispersion rim relies on `mask-composite:exclude` which Safari handles inconsistently — verify there, or drop ::before too in degraded mode.
- **One filter per geometry family is fine** — same `#lens` reused by navbar, cards, dock. Only build separate maps for radically different shapes (circle vs long pill) if edge zone looks off.
- **Don't put `filter:` on the element itself** — must be `backdrop-filter`, else you displace the content, not the backdrop.
- **`isolation:isolate`** on glass element prevents blend-mode leakage of ::before/::after.
- **Performance**: each glass element re-filters its backdrop on repaint. Keep animated things *in front of* glass, not behind it; static background = filter result cached. Avoid >10 large glass panels animating simultaneously.
- **Hidden tab / headless screenshot**: rAF and IntersectionObserver freeze — if page uses entrance animations, add `if(document.hidden)` fallback to reveal content immediately.
- **Small viewports**: the edge zone scales with element size — a near-fullscreen glass panel on mobile has huge soft edges and little clear center. Cap glass panel size or reduce edge exponent/scale under `@media (max-width:768px)`.
- **Class naming**: demo.html uses `.glass`; the snippets here use `.lqg`. Same layer structure — pick one name per project.

## Composing a full page redesign

When redoing an existing doc/dashboard in Liquid Glass:

1. Keep semantic structure + copy; swap visual shell.
2. Dark vivid gradient background + detail layer (big ghost text of key stats works double duty as decoration).
3. Every card/panel/nav → `.lqg` with `border-radius` 16–28px (squircle feel).
4. Text on glass → white/near-white with subtle `text-shadow`; accent colors keep hue but lift lightness (works on dark glass).
5. SVG diagrams: recolor fills to `rgba(255,255,255,.06–.12)` boxes + white strokes/text; keep accent strokes.
6. Inner sub-cards: lighter treatment — `rgba(255,255,255,.08)` + 1px white border, no second lens (nested lens = visual mud + perf cost).
7. Interactive flourish (optional): drag-able glass icon, pointer-following specular via CSS vars.

Full working reference with tuning sliders: `assets/demo.html` (open in Chrome).
