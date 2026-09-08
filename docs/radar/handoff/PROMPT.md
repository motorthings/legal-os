# Prompt for Claude Code — rebuild the "streams" visualization

Two files ship with this prompt:

- `handoff/streams-chart.js` — dependency-free reference implementation (layout math + render)
- `handoff/streams-chart.html` — standalone page that renders it; open it to see the target

Paste everything below the line into Claude Code, with those two files in context.

---

## Task

Replace the Sankey on the **Legal AI OS → Radar → "The streams"** page with the corroboration board in `handoff/streams-chart.js`. Port it into this codebase's idioms (component, styling, data layer) — don't just drop the file in and don't re-derive the layout math. Keep the existing Matrix view as the second tab; it stays as the exact/appendix view.

## Why this shape (don't lose the reasoning when you refactor)

The page must convey one thing: **four streams converge into ranked predictions, and more streams agreeing = a stronger call.** The old Sankey failed because right-side node order was dictated by crossing-minimisation, which fought the ranking — and rank is the answer the reader came for.

There's also a real unit mismatch: sources are counted in **items**, predictions scored on a **0–10 queue**. They cannot be chained through one flow honestly. The fix in the reference: items stay a flow on the left, queue becomes a ranked bar on the right, and **corroboration is carried by the bar's internal composition** — a four-colour bar vs. a solid one. Corroboration is then encoded three redundant ways: colour bands in the bar, lit pips, and ribbons landing on the row.

The ribbons **taper** on purpose: left edge sized in items (share of that stream's rail), right edge sized as share of that prediction. That taper is what lets the two units coexist without fudging either. Do not "fix" it into a constant-width ribbon.

## Requirements

1. **Rank is the y-axis.** Rows sorted by queue descending; verification reads as the headline. Never reorder rows to reduce crossings.
2. **Ribbon arrival order == bar segment order**, so nothing crosses at the join. The reference does this with a per-row cursor; preserve it.
3. **Progressive disclosure.** Hover/focus a stream rail or a prediction row: related ribbons go to 0.85, everything unrelated to 0.07, unrelated rows to 0.28. Resting ribbon opacity 0.5 — the 25 links are background texture, not something to decode. Escape and mouse-leave clear.
4. **Keyboard + touch.** Rails and rows are tabbable and respond to focus, not just hover (already in the reference). On touch, tap locks a trace, tap background clears.
5. **Native SVG `<text>` for every label.** No `foreignObject`, no HTML overlay — labels must survive print and image export.
6. **Data in one place.** A single exported `STREAMS` + `PREDICTIONS` structure that both this chart and the Matrix tab read. No duplicated numbers in markup. Don't change any number; if something looks wrong, leave `// TODO(data)`.
7. **Responsive.** The SVG scales via its 1160×780 viewBox. Below ~720px drop the ribbon field and the label column, and keep rank + colour bands + pips — the story survives without the flow.
8. **Motion once.** The reference fades the ribbon field in over 520ms on first render, gated on `prefers-reduced-motion`. Three rules make it fail safe: the resting opacity is painted **before** any animation; the reveal runs on a **mounted wrapper `<g>`** (never the same property, on the same element, that the hover state writes); and the first interaction **cancels** it. Anything that parks visibility on a callback or an animation origin — rAF, transition-end, per-path WAAPI with `fill:'none'` — silently ships an empty chart in a background tab, in print, or in image capture, and hover can't recover it. Never re-run on re-render or scroll-back. Nothing loops.
9. **Colour is meaning.** One hue per stream (rose/olive/sage/amber in the reference — swap to the site's stream colours, keep one hue per stream). Right-side text and numbers stay ink/graphite so the eye reads left→right causality.
10. **Tooltips (add — not in the reference).** On hovering a ribbon or a segment: `stream → prediction`, item count, and share of both ends, e.g. "13 of 25 rules items · 57% of verification".

## Page layout / feel

- The figure is the hero: full content width, generous vertical space, no card or widget framing.
- One-sentence deck above the chart, high contrast; the methodological caveat ("mass split, not a head-count") demoted to small muted text under the figure.
- Axis captions read as axis labels: small caps, muted, `white-space: nowrap`, aligned to the outer edges.
- Keep the Flow / Matrix tabs, but make the active tab unmistakable.
- Use existing site tokens for every colour, space, radius, and type size. No new fonts, no decorative gradients, no emoji.
- Avoid `∝` and other symbols outside the body font's glyph set — write "scales with".

## Deliverable

Show the diff, then screenshots of: resting state, one hover trace, and the <720px fallback. Call out anything you had to guess about the data model.
