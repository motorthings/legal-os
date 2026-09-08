/* Fault-Line Radar — corroboration board.
   Dependency-free. One call: renderStreamsChart(el, DATA, opts).
   Coordinate space is a fixed 1160x780 viewBox; the SVG scales to its container. */

export const STREAMS = [
  { id: 'rules',      name: 'Rules & rulings',    items: 25, color: '#A4093F' },
  { id: 'vendors',    name: 'Vendors',            items: 24, color: '#7F8C30' },
  { id: 'capability', name: 'Capability',         items: 17, color: '#8FBFAE' },
  { id: 'market',     name: 'Market & insurers',  items: 10, color: '#EFAE42' }
];

/* Ordered by queue, descending — row order IS the ranking. */
export const PREDICTIONS = [
  { name: 'verification',    queue: 8.6, cells: { rules: 13, vendors: 3, capability: 3, market: 4 } },
  { name: 'competence',      queue: 7.9, cells: { rules: 5, capability: 5, market: 4 } },
  { name: 'disclosure',      queue: 7.6, cells: { rules: 9, market: 1 } },
  { name: 'convergence',     queue: 7.5, cells: { rules: 4, vendors: 3, market: 1 } },
  { name: 'insurance',       queue: 7.3, cells: { market: 1 } },
  { name: 'confidentiality', queue: 6.9, cells: { rules: 8, market: 2 } },
  { name: 'benchmark',       queue: 6.9, cells: { vendors: 15, capability: 4, market: 1 } },
  { name: 'agentic',         queue: 5.8, cells: { vendors: 12, capability: 6, market: 1 } },
  { name: 'vendor liability',queue: 2.3, cells: { rules: 3, vendors: 3 } },
  { name: 'judge analytics', queue: 1.9, cells: { rules: 1 } },
  { name: 'fees',            queue: 1.7, cells: { rules: 1 } }
];

const L = {
  W: 1160, H: 780,
  labelRight: 152,          // right edge of the stream label column
  railX: 170, railW: 18,
  railTop: 40, railSpan: 660, railGap: 16,
  barX: 470, barMax: 430,   // queue 10 => 430px bar
  rowTop: 46, rowH: 62,
  queueX: 960, pipX: 1010,
  dim: 0.07, dimNode: 0.28, rest: 0.5, lit: 0.85
};

const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs, text) => {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text != null) n.textContent = text;   // native SVG <text>, no foreignObject
  return n;
};

export function layout(streams = STREAMS, preds = PREDICTIONS) {
  const totalItems = streams.reduce((a, s) => a + s.items, 0);
  const usable = L.railSpan - L.railGap * (streams.length - 1);
  const rails = {};
  let y = L.railTop;
  streams.forEach(s => {
    rails[s.id] = { y, h: (s.items / totalItems) * usable, color: s.color, name: s.name, items: s.items };
    y += rails[s.id].h + L.railGap;
  });

  const rows = preds.map((p, i) => {
    const rowY = L.rowTop + i * L.rowH;
    const total = Object.values(p.cells).reduce((a, b) => a + b, 0);
    const barH = 10 + p.queue * 2.6;              // thickness reads as weight, not just length
    const barLen = (p.queue / 10) * L.barMax;
    const barY = rowY + 22;
    const active = streams.filter(s => p.cells[s.id]);
    let x = L.barX;
    const segments = active.map(s => {
      const w = (p.cells[s.id] / total) * barLen;
      const seg = { x, y: barY, w: Math.max(w, 1.5), h: barH, color: s.color, stream: s.id };
      x += w; return seg;
    });
    return { ...p, rowY, barY, barH, barLen, total, active, segments };
  });

  /* Tapering ribbons: left edge is sized in ITEMS (share of that stream's rail),
     right edge in SHARE OF THE PREDICTION. That taper is what lets the two
     units (items vs 0-10 queue) live in one picture without fudging either. */
  const cursor = {}; streams.forEach(s => { cursor[s.id] = rails[s.id].y; });
  const ribbons = [];
  rows.forEach(r => {
    let ay = r.barY;                               // arrival order == segment order => no crossing at the join
    r.active.forEach(s => {
      const streamTotal = preds.reduce((a, q) => a + (q.cells[s.id] || 0), 0);
      const w1 = (r.cells[s.id] / streamTotal) * rails[s.id].h;
      const w2 = (r.cells[s.id] / r.total) * r.barH;
      const y0 = cursor[s.id], y1 = y0 + w1, y2 = ay, y3 = ay + w2;
      const x0 = L.railX + L.railW, x1 = L.barX, mx = (x0 + x1) / 2;
      ribbons.push({ stream: s.id, pred: r.name, color: s.color,
        d: `M${x0},${y0} C${mx},${y0} ${mx},${y2} ${x1},${y2} L${x1},${y3} C${mx},${y3} ${mx},${y1} ${x0},${y1} Z` });
      cursor[s.id] = y1; ay = y3;
    });
  });
  return { rails, rows, ribbons };
}

export function renderStreamsChart(mount, opts = {}) {
  const streams = opts.streams || STREAMS;
  const preds = opts.predictions || PREDICTIONS;
  const { rails, rows, ribbons } = layout(streams, preds);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const svg = el('svg', { viewBox: `0 0 ${L.W} ${L.H}`, style: 'width:100%;height:auto;display:block',
    role: 'img', 'aria-label': 'Four evidence streams feeding eleven ranked fault-line predictions' });

  const field = el('g', {});
  svg.appendChild(field);
  const paths = ribbons.map(r => {
    const p = el('path', { d: r.d, fill: r.color, style: 'transition:opacity 180ms ease-out' });
    p.__r = r; field.appendChild(p); return p;
  });

  const railNodes = streams.map(s => {
    const r = rails[s.id];
    const g = el('g', { style: 'cursor:default;transition:opacity 180ms ease-out', tabindex: '0' });
    g.appendChild(el('rect', { x: L.railX, y: r.y, width: L.railW, height: r.h, rx: 3, fill: r.color }));
    g.appendChild(el('text', { x: L.labelRight, y: r.y + r.h / 2 - 2, 'text-anchor': 'end',
      'font-size': 15, 'font-weight': 600, fill: '#1F1A1C' }, s.name));
    g.appendChild(el('text', { x: L.labelRight, y: r.y + r.h / 2 + 16, 'text-anchor': 'end',
      'font-size': 12, 'font-weight': 500, 'letter-spacing': '0.06em', fill: '#938E8C' }, `${s.items} items`));
    g.__stream = s.id; svg.appendChild(g); return g;
  });

  const rowNodes = rows.map(r => {
    const hit = el('g', { style: 'cursor:default', tabindex: '0' });
    hit.appendChild(el('rect', { x: 160, y: r.rowY, width: 1000, height: 56, fill: 'transparent' }));
    const g = el('g', { opacity: 1, style: 'transition:opacity 180ms ease-out' });
    g.appendChild(el('text', { x: L.barX, y: r.rowY + 12, 'font-size': 17, 'font-weight': 600, fill: '#1F1A1C' }, r.name));
    g.appendChild(el('text', { x: 940, y: r.rowY + 12, 'text-anchor': 'end', 'font-size': 12, 'font-weight': 500,
      'letter-spacing': '0.04em', fill: '#938E8C' },
      `${r.active.length} ${r.active.length === 1 ? 'stream' : 'streams'} · ${r.total} ${r.total === 1 ? 'item' : 'items'}`));
    r.segments.forEach(s => g.appendChild(el('rect', { x: s.x, y: s.y, width: s.w, height: s.h, fill: s.color })));
    g.appendChild(el('text', { x: L.queueX, y: r.barY + r.barH / 2 + 7, 'font-size': 21, 'font-weight': 300,
      fill: '#1F1A1C' }, r.queue.toFixed(1)));
    streams.forEach((s, i) => g.appendChild(el('rect', { x: L.pipX + i * 14, y: r.barY + r.barH / 2 - 4.5,
      width: 9, height: 9, rx: 2, fill: r.cells[s.id] ? s.color : '#E7E4E2' })));
    hit.appendChild(g); hit.__row = r; hit.__inner = g; svg.appendChild(hit); return hit;
  });

  let hs = null, hp = null, revealed = false;
  const paint = () => {
    if (!revealed) { revealed = true; field.getAnimations().forEach(a => a.cancel()); }
    const idle = !hs && !hp;
    const row = hp && rows.find(r => r.name === hp);
    paths.forEach(p => { p.style.opacity =
      idle ? L.rest : (p.__r.stream === hs || p.__r.pred === hp) ? L.lit : L.dim; });
    railNodes.forEach(g => g.setAttribute('opacity',
      idle || g.__stream === hs || (row && row.cells[g.__stream]) ? 1 : 0.22));
    rowNodes.forEach(g => g.__inner.setAttribute('opacity',
      idle || g.__row.name === hp || (hs && g.__row.cells[hs]) ? 1 : L.dimNode));
  };
  const set = (s, p) => { hs = s; hp = p; paint(); };
  railNodes.forEach(g => { g.onmouseenter = g.onfocus = () => set(g.__stream, null); });
  rowNodes.forEach(g => { g.onmouseenter = g.onfocus = () => set(null, g.__row.name); });
  svg.onmouseleave = () => set(null, null);
  svg.addEventListener('blur', () => set(null, null), true);
  svg.addEventListener('keydown', e => { if (e.key === 'Escape') set(null, null); });

  paths.forEach(p => { p.style.opacity = L.rest; });
  mount.replaceChildren(svg);

  /* Reveal runs on the mounted wrapper <g> — never the same property paint()
     writes — and any interaction cancels it, so rest and hover always win. */
  if (!reduced && typeof field.animate === 'function') {
    field.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 520, easing: 'ease-out', fill: 'none' });
  }

  return { svg, setHover: set, layout: { rails, rows, ribbons } };
}
