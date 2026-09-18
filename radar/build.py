"""Render the scored radar to a self-contained static HTML page + data.json.

Writes to docs/radar/ so GitHub Pages can serve it. No runtime JS dependencies.
"""
import json
import html
from datetime import date
from pathlib import Path

from score import score
import calibration
import milestones
import ordering
import actions
import kb
import advisory

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "radar"
# Second output: the app serves the radar as a static asset (Vercel deploys only
# frontend/, so docs/radar isn't bundled). The in-app /radar page reads these.
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend" / "public" / "radar"

COPY = json.loads((Path(__file__).resolve().parent / "copy.json").read_text())


def _c(key):
    """Shared copy. Both renderers read copy.json so a heading cannot drift."""
    return COPY[key]


# Emitted into inline `style="color:…"` attributes, so these must be var() references
# rather than literal hex: a literal cannot follow the light/dark toggle, and the old
# gold ramp would have stayed gold in both themes. Defined in PAGE_CSS.
TIER_COLOR = {"T1": "var(--t1)", "T2": "var(--t2)", "T3": "var(--t3)",
              "T4": "var(--t4)", "T5": "var(--t5)"}


def _esc(s):
    return html.escape(str(s))


def _pressure_color(p):
    """L2 ruling chip fill. var() references for the same reason as TIER_COLOR."""
    if p >= 8:
        return "var(--p-hot)"
    if p >= 6.5:
        return "var(--p-warm)"
    if p >= 5:
        return "var(--p-mid)"
    return "var(--p-cool)"


def _trend_glyph(t):
    return {"rising": "▲ rising", "steady": "► steady", "quiet": "· quiet"}.get(t, t)


def _strength_line(d, lead_by_line):
    """How we know, stated at the claim: source counts by kind, plus the warning window."""
    s = d["strength"]
    bits = [f'{s["total"]} sources']
    for key, label in (("appellate", "appellate"), ("trial", "trial court"),
                       ("primary", "statute/rule"), ("guidance", "bar guidance")):
        if s[key]:
            bits.append(f'{s[key]} {label}')
    lead = _lead_cell(lead_by_line.get(d["id"]))
    if lead != "—":
        bits.append(f"first signal {lead} before it bound")
    return " · ".join(bits)


def _lead_cell(days_list):
    """Median antecedent -> binding lead for a line, or a dash when none is on record."""
    if not days_list:
        return "—"
    s = sorted(days_list)
    return f"{s[len(s) // 2]}d"


def _staleness(r):
    """When did this fault line last get new evidence? A line is stale when no ruling,
    market action, or capability demo has landed in a long while — the re-curation cue."""
    if r.get("stale_days") is None or not r.get("last_evidence_date"):
        return ""
    d = r["stale_days"]
    label = f"last evidence {r['last_evidence_date']}"
    if d <= 45:
        return f'<span class="fresh">· {label} ({d}d)</span>'
    if d <= 180:
        return f'<span class="mid">· {label} ({d}d)</span>'
    return f'<span class="stale">· {label} — {d}d stale</span>'


# --- Page chrome, hoisted out of render()'s f-string -------------------------
# render() returns ONE f-string, so every literal brace inside it has to be doubled.
# The stylesheet alone was ~110 lines of doubled braces, and the theme toggle's JS would have
# added more. These are plain module-level strings instead: braces, comments and quotes
# are written normally, and the f-string drops each one in with a single {NAME}.
# Nothing here is interpolated, so none of it needs to be inside an f-string at all.
#
# The look matches the legal/ diagram pages (diagrams repo): rose + teal on warm paper,
# Mulish, sticky nav with breadcrumbs, light/dark toggle. Token names are the same, so
# the two surfaces read as one family.

PAGE_FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Mulish:ital,wght@0,300;0,400;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">"""

# Runs before first paint so the stored theme is applied without a flash of the wrong
# palette. The class toggled is `light`; dark is its absence -- so the dark values live
# in :root and html.light overrides them, and a reader with no JS gets the paper look.
PAGE_THEME_HEAD = """<script>
  (function () {
    try {
      var t = localStorage.getItem('diagram-theme');
      if (t === 'dark') document.documentElement.classList.remove('light');
      else document.documentElement.classList.add('light');
    } catch (e) {}
  })();
</script>"""

# Breadcrumbs are absolute on purpose: this page is served from the legal-os GitHub Pages
# site at /legal-os/radar/, where the relative ../index.html the diagram pages use would
# 404. Every crumb walks back toward the diagrams hub, terminal crumb is this page.
PAGE_NAV = """<div class="nav">
  <div class="nav-inner">
    <nav class="crumbs" aria-label="Breadcrumb">
      <a href="https://sickofancy.ai/diagrams/index.html">Index</a>
      <span class="sep">/</span>
      <a href="https://sickofancy.ai/diagrams/legal/index.html">Legal</a>
      <span class="sep">/</span>
      <a href="https://sickofancy.ai/diagrams/legal/legal-os-radar.html">Radar</a>
      <span class="sep">/</span>
      <span class="current" aria-current="page">Live radar</span>
    </nav>
    <button class="theme-toggle" id="themeToggle" type="button" aria-label="Toggle light and dark theme">&#9788;</button>
  </div>
</div>"""

PAGE_THEME_JS = """
(function () {
  "use strict";
  var root = document.documentElement;
  var btn = document.getElementById('themeToggle');
  var SUN = '\\u263C', MOON = '\\u263E';
  function paint() {
    var light = root.classList.contains('light');
    btn.textContent = light ? MOON : SUN;
    btn.setAttribute('aria-label', light ? 'Switch to dark theme' : 'Switch to light theme');
  }
  btn.addEventListener('click', function () {
    root.classList.toggle('light');
    try { localStorage.setItem('diagram-theme', root.classList.contains('light') ? 'light' : 'dark'); } catch (e) {}
    paint();
  });
  paint();
})();
"""

PAGE_CSS = """
  :root {
    --font-body: 'Mulish', 'Segoe UI', Helvetica, sans-serif;
    --font-mono: 'Mulish', ui-monospace, 'SF Mono', Consolas, monospace;
    --bg:#171416; --surface:#1E1A1D; --surface2:#262024;
    --border:#332D31; --border-bright:#463D42;
    --text:#F5F2F1; --text-dim:#C9C3C1; --text-faint:#8A8481;
    --primary:#E39CB2; --primary-dim:rgba(227,156,178,0.12);
    --metric:#5FBF9B; --metric-dim:rgba(95,191,155,0.12);
    --amber:#D9A05B;  --amber-dim:rgba(217,160,91,0.14);
    --rose:#E36C89;   --rose-dim:rgba(227,108,137,0.14);
    --violet:#A78BB8; --violet-dim:rgba(167,139,184,0.14);
    --slate:#948E8C;  --slate-dim:rgba(148,142,140,0.14);
    /* Rank-chart ramp. The old four were points on a gold ramp, which only worked while
       the whole page was gold: --primary and --amber were both gold, so "appellate" and
       "trial court" were near-identical in the bar AND the legend. These are the family's
       semantic accents instead, so a bar segment and the same accent elsewhere name the
       same thing. Bar order runs app -> trial -> statute -> guide, which keeps the two
       closest hues (rose, violet) apart in a 9px bar. */
    --rk-app:#E36C89; --rk-trial:#D9A05B; --rk-statute:#5FBF9B; --rk-guide:#A78BB8;
    /* Evidence tiers (TIER_COLOR in Python) and the L2 pressure chip fills
       (_pressure_color in Python). Both are emitted as inline var() references rather
       than literal hex, because a literal hex in an inline style cannot follow the
       toggle and would leave the old gold ramp showing in one of the two themes. */
    --t1:#E36C89; --t2:#D9A05B; --t3:#5FBF9B; --t4:#A78BB8; --t5:#8A8481;
    --p-hot:#B83159; --p-warm:#D9A05B; --p-mid:#B07C2E; --p-cool:#948E8C;
  }
  html.light {
    --bg:#F5F2F1; --surface:#FFFFFF; --surface2:#EDE8E6;
    --border:#D9D2CE; --border-bright:#C4B9B4;
    --text:#171416; --text-dim:#4A4442; --text-faint:#8A8481;
    --primary:#B83159; --primary-dim:rgba(184,49,89,0.10);
    --metric:#1E8A6A; --metric-dim:rgba(30,138,106,0.10);
    --amber:#B07C2E;  --amber-dim:rgba(176,124,46,0.10);
    --rose:#C4506B;   --rose-dim:rgba(196,80,107,0.10);
    --violet:#8A5A76; --violet-dim:rgba(138,90,118,0.10);
    --slate:#6A6461;  --slate-dim:rgba(106,100,97,0.10);
    --rk-app:#C4506B; --rk-trial:#B07C2E; --rk-statute:#1E8A6A; --rk-guide:#8A5A76;
    --t1:#C4506B; --t2:#B07C2E; --t3:#1E8A6A; --t4:#8A5A76; --t5:#8A8481;
    --p-hot:#B83159; --p-warm:#B07C2E; --p-mid:#8A6A1E; --p-cool:#6A6461;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; background:var(--bg); color:var(--text);
    font-family:var(--font-body); font-size:15px; line-height:1.65;
    -webkit-font-smoothing:antialiased;
    /* The family's two-stop wash. This page is thousands of pixels taller than any
       diagram page, so it needs no-repeat + fixed or the 40% stop repeats as visible
       horizontal bands on the way down. */
    background-image:
      radial-gradient(at 10% 0%, var(--primary-dim) 0%, transparent 40%),
      radial-gradient(at 90% 80%, var(--metric-dim) 0%, transparent 40%);
    background-repeat:no-repeat, no-repeat;
    background-attachment:fixed, fixed;
  }
  .nav { position:sticky; top:0; z-index:100; backdrop-filter:blur(16px);
    background:var(--surface);
    background:color-mix(in srgb, var(--surface) 85%, transparent);
    border-bottom:1px solid var(--border); }
  .nav-inner { max-width:1040px; margin:0 auto; padding:12px 24px; display:flex;
    align-items:center; justify-content:space-between; gap:12px; }
  .crumbs { font-family:var(--font-mono); font-size:13px; font-weight:600; display:flex;
    align-items:center; gap:8px; flex-wrap:wrap; }
  .crumbs a { color:var(--primary); text-decoration:none; }
  .crumbs a:hover, .crumbs a:focus-visible { text-decoration:underline; outline:none; }
  .crumbs .sep { color:var(--text-faint); }
  .crumbs .current { color:var(--text-dim); font-weight:400; }
  .theme-toggle { width:36px; height:36px; border-radius:10px; border:1px solid var(--border);
    background:var(--surface); cursor:pointer; display:flex; align-items:center;
    justify-content:center; font-size:16px; line-height:1; color:var(--text-dim);
    transition:all .2s; flex-shrink:0; }
  .theme-toggle:hover, .theme-toggle:focus-visible { border-color:var(--primary);
    color:var(--primary); outline:none; }

  .container { max-width:1040px; margin:0 auto; padding:44px 24px 80px; }
  @keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
  /* Animated on the hero and the first panel only. There are ~15 panels and 11 fault-line
     cards below; staggering all of them reads as jank and delays the first paint of the
     tables, which are the part a reader actually came for. */
  .hero { margin-bottom:26px; animation:fadeUp .5s ease both; }
  .hero .kicker { font-family:var(--font-mono); font-size:11px; font-weight:700;
    letter-spacing:.2em; text-transform:uppercase; color:var(--text-faint); margin-bottom:12px; }
  .hero h1 { font-size:42px; font-weight:800; letter-spacing:-1px; margin:0 0 10px; max-width:760px;
    background:linear-gradient(135deg,var(--primary),var(--metric));
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
  .hero p { font-size:17px; color:var(--text-dim); max-width:760px; margin:0; }
  .hero .asof { font-family:var(--font-mono); font-size:12.5px; color:var(--text-faint); margin-top:12px; }

  .legend { font-size:13px; color:var(--text-dim); background:var(--surface2);
    border:1px solid var(--border); border-radius:12px; padding:14px 16px; margin:0 0 18px; }
  .legend b { color:var(--text); }
  .legend code { font-family:var(--font-mono); font-size:12px; }

  .panel { background:var(--surface); border:1px solid var(--border); border-radius:14px;
    padding:24px 26px; margin:0 0 18px; }
  .panel:first-of-type { animation:fadeUp .5s ease .08s both; }
  .panel h2 { font-size:20px; font-weight:800; letter-spacing:-.2px; margin:0 0 8px; }
  .panel .small { color:var(--text-dim); font-size:14px; margin:.5rem 0; }
  .panel .eyebrow { font-family:var(--font-mono); font-size:10px; font-weight:700;
    letter-spacing:.14em; text-transform:uppercase; color:var(--text-faint); margin:1.2rem 0 .3rem; }
  .meta { color:var(--text-faint); font-size:11.5px; font-family:var(--font-mono); }
  .panel h2 .meta { font-weight:600; margin-left:.6rem; }
  .meta .fresh { color:var(--metric); }
  .meta .mid { color:var(--amber); }
  .meta .stale { color:var(--rose); font-weight:700; }
  b { color:var(--text); }
  a { color:var(--primary); }

  .fl { background:var(--surface); border:1px solid var(--border); border-radius:12px;
    margin:0 0 10px; overflow:hidden; transition:border-color .15s; }
  .fl[open] { border-color:var(--border-bright); }
  summary { cursor:pointer; list-style:none; padding:14px 18px; display:flex;
    align-items:center; gap:12px; flex-wrap:wrap; }
  summary::-webkit-details-marker { display:none; }
  .chev { margin-left:auto; color:var(--text-faint); font-size:12px; transition:transform .15s; }
  details[open] > summary .chev { transform:rotate(90deg); }
  .fl summary .meta { margin-left:auto; }
  .p { font-weight:700; color:#171416; border-radius:6px; padding:2px 8px; min-width:2.6rem;
    text-align:center; font-family:var(--font-mono); font-size:13px; }
  .p.a { background:transparent !important; color:var(--metric); border:1px solid var(--metric-dim); }
  .p.c { background:transparent !important; color:var(--violet); border:1px dashed var(--violet-dim); }
  .t { font-size:16px; font-weight:700; color:var(--text); }
  .body { padding:0 18px 18px; border-top:1px solid var(--border); }
  .vec { margin:.7rem 0; font-size:14px; color:var(--text-dim); }
  .vec.build { color:var(--metric); }
  .vec.small { color:var(--text-faint); font-size:12px; }

  .tw { overflow-x:auto; -webkit-overflow-scrolling:touch; }
  table.ev { width:100%; border-collapse:collapse; font-size:13px; margin-top:.5rem; }
  table.ev th { text-align:left; color:var(--text-faint); font-family:var(--font-mono);
    font-size:10px; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
    border-bottom:1px solid var(--border); padding:8px 10px; }
  table.ev td { padding:8px 10px; border-bottom:1px solid var(--border); vertical-align:top;
    color:var(--text-dim); }
  table.ev tr:last-child td { border-bottom:none; }
  td.d { white-space:nowrap; color:var(--text-faint); font-family:var(--font-mono); font-size:12px; }
  td.c { text-align:center; white-space:nowrap; color:var(--text-faint); }
  .queue table.ev td { vertical-align:middle; }
  .tier { font-weight:700; font-family:var(--font-mono); }
  .src { color:var(--text-faint); font-size:11.5px; margin-top:2px; font-family:var(--font-mono); }
  .flag { font-size:10px; background:var(--metric-dim); color:var(--metric); border-radius:4px;
    padding:1px 6px; margin-left:4px; font-family:var(--font-mono); font-weight:700; }
  .flag.conflict { background:var(--rose-dim); color:var(--rose); }
  .hit { color:var(--metric); font-weight:700; }
  .miss { color:var(--rose); font-weight:700; }
  .mkt { font-size:11px; background:var(--metric-dim); color:var(--metric); border-radius:4px;
    padding:2px 6px; font-family:var(--font-mono); text-transform:uppercase; letter-spacing:.04em; }
  .cap { font-size:11px; background:var(--violet-dim); color:var(--violet); border-radius:4px;
    padding:2px 6px; font-family:var(--font-mono); text-transform:uppercase; letter-spacing:.04em; }

  /* Action list — the answer, before the working. */
  .acts { list-style:none; margin:16px 0 0; padding:0; }
  .act { background:var(--surface2); border:1px solid var(--border); border-radius:12px;
    padding:16px 18px; margin:0 0 10px; }
  .act-h { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }
  .act-n { font-family:var(--font-mono); color:var(--text-faint); font-weight:800; font-size:13px; }
  .act-t { font-size:16px; font-weight:700; color:var(--text); }
  .act-s { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.08em;
    padding:3px 8px; border-radius:5px; font-family:var(--font-mono); }
  .act-s.strong { background:var(--metric-dim); color:var(--metric); }
  .act-s.moderate { background:var(--amber-dim); color:var(--amber); }
  .act-s.thin { background:var(--violet-dim); color:var(--violet); }
  .act-k { color:var(--text-dim); font-size:14px; margin:10px 0 4px; }
  .act-m { font-family:var(--font-mono); font-size:11.5px; color:var(--text-faint); margin:4px 0 8px; }
  .act details summary { cursor:pointer; font-family:var(--font-mono); font-size:11.5px;
    font-weight:700; color:var(--primary); padding:0; }
  .act details summary:hover { text-decoration:underline; }
  .act-ev { margin:12px 0 0; padding-top:12px; border-top:1px solid var(--border);
    font-size:13px; color:var(--text-dim); }
  .act-ev .mtr { font-family:var(--font-mono); font-size:11.5px; color:var(--text-dim); margin:8px 0; }
  .act-ev .mtr-note { font-size:12px; color:var(--text-faint); margin:6px 0 12px;
    max-width:44rem; line-height:1.6; }
  .act-ev .d { font-family:var(--font-mono); color:var(--text-faint); margin-right:6px; }
  .act-ev .src { display:block; color:var(--text-faint); font-size:11px; margin:2px 0 8px 6px; }

  .seq { margin:20px 0 0; padding-top:16px; border-top:1px solid var(--border); }
  /* Text colour is --surface so it flips with the background it sits on: white on the
     deep light-mode rose, near-black on the pale dark-mode one. */
  .seq a { display:inline-block; font-family:var(--font-mono); font-size:13px; font-weight:700;
    text-decoration:none; color:var(--surface); border-radius:10px; padding:12px 22px;
    background:var(--primary); background:linear-gradient(135deg,var(--primary),var(--metric)); }
  .seq a:hover { filter:brightness(1.08); }

  /* The whole board — one stacked bar per duty, in list order. */
  .rk { margin:0; }
  .rk-head, .rk-row { display:grid; grid-template-columns:1.5rem minmax(0,1.3fr) 2.4fr 4.5rem;
    gap:10px; }
  .rk-head { margin:16px 0 6px; font-family:var(--font-mono); font-size:10px; font-weight:700;
    letter-spacing:.08em; text-transform:uppercase; color:var(--text-faint); }
  /* The count spans the bar and total columns; it labels both. */
  .rk-head span:nth-child(3) { grid-column:3 / span 2; }
  .rk-row { align-items:center; margin:0 0 6px; }
  .rk-n { font-family:var(--font-mono); font-size:12px; color:var(--text-faint); text-align:right; }
  .rk-l { font-size:13px; color:var(--text); white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; }
  .rk-b { display:block; }
  .rk-fill { display:flex; height:9px; border-radius:5px; overflow:hidden; background:var(--surface2); }
  .rk-fill i { display:block; height:100%; }
  .rk-t { font-family:var(--font-mono); font-size:12px; color:var(--text-faint); text-align:center; }
  .rk-split { display:flex; align-items:center; gap:10px; margin:12px 0 8px; }
  .rk-split span { flex:1; border-top:1px dashed var(--border); }
  .rk-split em { font-style:normal; font-family:var(--font-mono); font-size:10px; font-weight:700;
    letter-spacing:.08em; text-transform:uppercase; color:var(--text-faint); }
  .rk-legend { display:flex; flex-wrap:wrap; gap:14px; margin-top:14px; padding-top:12px;
    border-top:1px solid var(--border); font-size:12px; color:var(--text-dim); }
  .rk-legend span { display:inline-flex; align-items:center; gap:6px; }
  .rk-legend i { width:12px; height:12px; border-radius:3px; display:inline-block; }

  .footer { margin-top:40px; padding-top:18px; border-top:1px solid var(--border);
    font-size:13px; color:var(--text-faint); }
  .footer code { font-family:var(--font-mono); color:var(--text-dim); }

  @media (max-width:768px) {
    .container { padding:32px 18px 64px; }
    .nav-inner { padding:10px 18px; }
    .hero h1 { font-size:28px; }
    .hero p { font-size:16px; }
    .panel { padding:18px; }
  }
  /* The chart's label column used to be minmax(15rem,...), which is wider than a 375px
     viewport and forced a horizontal page scroll. Let it wrap instead. */
  @media (max-width:640px) {
    .rk-head { display:none; }
    .rk-row { grid-template-columns:1.1rem minmax(0,1fr) 1.1fr 2rem; gap:6px; }
    .rk-l { white-space:normal; font-size:12px; line-height:1.35; }
    .rk-legend { gap:10px; font-size:11.5px; }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration:.01ms !important; transition-duration:.01ms !important; }
  }
"""


def render(data):
    fls = data["fault_lines"]
    rows = []
    for r in [x for x in fls if x["is_duty"]]:
        ev_rows = "".join(
            f'<tr><td class="d">{_esc(e["date"])}</td>'
            f'<td><span class="tier" style="color:{TIER_COLOR[e["tier"]]}">{e["tier"]}</span></td>'
            f'<td>{_esc(e["title"])}'
            f'{" <span class=\'flag\'>data</span>" if e["empirical"] else ""}'
            f'{" <span class=\'flag conflict\'>conflict</span>" if e["conflict"] else ""}'
            f'<div class="src">{_esc(e["source"])} · w={e["weight"]}</div></td></tr>'
            for e in r["evidence"]
        ) or '<tr><td colspan="3" class="src">No evidence yet — seed thesis only.</td></tr>'

        cap_rows = "".join(
            f'<tr><td class="d">{_esc(e["date"])}</td>'
            f'<td><span class="cap">{_esc(e["capability"])}</span></td>'
            f'<td>{_esc(e["title"])}'
            f'{" <span class=\'flag\'>data</span>" if e.get("empirical") else ""}'
            f'<div class="src">w={e["weight"]}</div></td></tr>'
            for e in r["capability_evidence"]
        ) or '<tr><td colspan="3" class="src">No capability demonstration on record — seed only.</td></tr>'

        adopt_rows = "".join(
            f'<tr><td class="d">{_esc(e["date"])}</td>'
            f'<td><span class="mkt">{_esc(e["market"])}</span></td>'
            f'<td>{_esc(e["title"])}<div class="src">w={e["weight"]}</div></td></tr>'
            for e in r["adoption_evidence"]
        ) or '<tr><td colspan="3" class="src">No market-adoption signal yet — seed only.</td></tr>'

        rules = " · ".join(_esc(m) for m in r["model_rules"])
        rows.append(f"""
        <details class="fl">
          <summary>
            <span class="p c" title="L1 capability">{r['capability']}</span>
            <span class="p" style="background:{_pressure_color(r['pressure'])}" title="L2 ruling">{r['pressure']}</span>
            <span class="p a" title="L3 adoption">{r['adoption']}</span>
            <span class="t">{_esc(r['title'])}</span>
            <span class="meta">{_trend_glyph(r['trend'])} · {_esc(r['horizon'])} · {_esc(r['layer'])} {_staleness(r)}</span>
            <span class="chev">&#9656;</span>
          </summary>
          <div class="body">
            <p class="vec"><b>Fault line:</b> {_esc(r['vector'])}</p>
            <p class="vec"><b>Driver:</b> {_esc(r['tech_driver'])}</p>
            <p class="vec build"><b>Control (build now):</b> {_esc(r['control'])} — {_esc(r['build_now'])}</p>
            <p class="vec small">Model Rules: {rules}
               &nbsp;|&nbsp; <b>L1 capability</b> seed {r['capability_seed']} → {r['capability']} ({r['n_capability_evidence']} demos, w={r['capability_weighted']})
               &nbsp;|&nbsp; <b>L2 ruling</b> seed {r['pressure_seed']} → {r['pressure']} ({r['n_evidence']} items, w={r['weighted_evidence']})
               &nbsp;|&nbsp; <b>L3 adoption</b> seed {r['adoption_seed']} → {r['adoption']} ({r['n_adoption_evidence']} signals, w={r['adoption_weighted']})
               &nbsp;|&nbsp; <b>E enablement</b> seed {r['enable_seed']} → {r['enable']} ({r['n_enable_evidence']} items, w={r['enable_weighted']})
               &nbsp;|&nbsp; <b>S software</b> seed {r['software_seed']} → {r['software']} ({r['n_software_evidence']} moves, w={r['software_weighted']})
               &nbsp;|&nbsp; <b>queue</b> {r['queue']} · lead {_esc(r['lead'])}</p>
            <div class="tw"><table class="ev"><thead><tr><th>Date</th><th>Demo</th><th>L1 capability evidence (weighted low, labeled — not a ruling)</th></tr></thead>
              <tbody>{cap_rows}</tbody></table></div>
            <div class="tw"><table class="ev"><thead><tr><th>Date</th><th>Tier</th><th>L2 ruling evidence (provenance)</th></tr></thead>
              <tbody>{ev_rows}</tbody></table></div>
            <div class="tw"><table class="ev"><thead><tr><th>Date</th><th>Market</th><th>L3 adoption signal</th></tr></thead>
              <tbody>{adopt_rows}</tbody></table></div>
          </div>
        </details>""")

    # Graded milestones supply the antecedent -> binding lead time, which is a fact about
    # the past: how much warning the record gave before each control became binding.
    ms = milestones.grade()

    # --- What the record already requires of any firm -------------------------
    # Firm-independent: `mandated` is the law having moved, which does not depend on who
    # you are. Sequencing those against a specific firm's readiness is the advisory page's
    # job; this is the part that is true of everyone.
    lead_by_line = {}
    for m in ms["milestones"]:
        if m["status"] == "landed" and m["lead_days"] is not None:
            lead_by_line.setdefault(m["fault_line"], []).append(m["lead_days"])
    # Ordered by the shared rule in ordering.py: requires before expects, then shortest
    # measured lead first. NOT by evidence strength, which is what the bar length draws and
    # what this page used to sort on. The two axes genuinely disagree — `vendor_liability`
    # has the fewest sources on the board and the second-shortest warning window — and the
    # brief is that a reader should be told what to do first, with the source count carried
    # alongside as a statement about how much to trust the line.
    duties = sorted([fl for fl in fls if fl["is_duty"]], key=lambda r: r["order_key"])
    duty_rows = "".join(
        f'<li class="act">'
        f'<div class="act-h"><span class="act-n">{i}</span>'
        f'<span class="act-t">{_esc(d["action"])}</span>'
        f'<span class="act-s {_esc(d["strength"]["label"])}">{_esc(d["strength"]["label"])}</span></div>'
        f'{f"<p class=\'act-k\'>{_esc(d['stakes'])}</p>" if d.get("stakes") else ""}'
        f'<p class="act-m">{_strength_line(d, lead_by_line)}</p>'
        f'<details><summary>See the {d["strength"]["total"]} sources, and how it reads</summary>'
        f'<div class="act-ev">'
        f'<p class="src">Model Rules: {_esc(" · ".join(d["model_rules"]))} '
        f'&middot; our shorthand for this line is &ldquo;{_esc(d["control"])}&rdquo;</p>'
        f'<p class="mtr"><b>L1</b> {d["capability_seed"]}&rarr;{d["capability"]} '
        f'&nbsp; <b>L2</b> {d["pressure_seed"]}&rarr;{d["pressure"]} '
        f'&nbsp; <b>L3</b> {d["adoption_seed"]}&rarr;{d["adoption"]} '
        f'&nbsp; <b>E</b> {d["enable_seed"]}&rarr;{d["enable"]}</p>'
        # The legend sits beside the meters it labels, where the exception is legible: this
        # line's own readings are the counterexample to any one-way cascade. Shared with the
        # app page through copy.json, so the two cannot describe the meters differently.
        f'<p class="mtr-note">{_c("meters_legend")}</p>'
        f'<p class="vec"><b>Why now:</b> {_esc(d["vector"])}</p>'
        f'<p class="vec"><b>What to put in place:</b> {_esc(d["build_now"])}</p>'
        + "".join(
            f'<div><span class="d">{_esc(e["date"])}</span> {_esc(e["title"])}'
            f'<span class="src">{_esc(e["source"])} · {_esc(e["tier"])}</span></div>'
            for e in d["evidence"])
        + f'</div></details></li>'
        for i, d in enumerate(duties, 1)
    ) or '<li class="src">No control on the record is required yet.</li>'

    # --- What's coming: the controls that are NOT required yet ----------------
    # Suppressing these made the page read as if agentic supervision did not exist, when it
    # is the one line with a live bill in Congress. A firm deciding what to build needs the
    # near list as much as the now list; it just has to be labelled as not-yet-required.
    watching = sorted([fl for fl in fls if not fl["is_duty"]],
                      key=lambda r: (-r["pressure"], -r["strength"]["total"]))
    # --- The whole board: the same eleven, one bar each ----------------------
    # The app page leads with this; the static page had no equivalent at all, so the only
    # overview here was the meter table at the bottom. Bar length is the number of sources,
    # coloured by KIND of authority: seven circuit courts and seven bar opinions are not
    # the same claim even when the totals match.
    # Labels come from copy.json, not from literals here. They are the same four strings,
    # but the copy contract pins them and the app page reads the same keys — typing them
    # twice is how the two surfaces start naming the same thing differently.
    _seg_order = [("appellate", _c("seg_appellate"), "var(--rk-app)"),
                  ("trial", _c("seg_trial"), "var(--rk-trial)"),
                  ("primary", _c("seg_primary"), "var(--rk-statute)"),
                  ("guidance", _c("seg_guidance"), "var(--rk-guide)")]
    _watching = [w for w in watching if w.get("watch_reason")]
    _all = duties + _watching
    _max = max([x["strength"]["total"] for x in _all] or [1])

    def _bars_for(rows, start, split_at=None):
        out = []
        for _i, x in enumerate(rows, start):
            if split_at is not None and _i == split_at:
                out.append('<div class="rk-split"><span></span>'
                           '<em>not required yet</em><span></span></div>')
            out.append(_bar(x, _i))
        return "".join(out)

    def _bar(x, _i):
        _st = x["strength"]
        _segs = "".join(
            f'<i style="width:{(_st[k] / (_st["total"] or 1)) * 100:.1f}%;'
            f'background:{col}" title="{_st[k]} {lab}"></i>'
            for k, lab, col in _seg_order if _st[k])
        return (
            f'<div class="rk-row"><span class="rk-n">{_i}</span>'
            f'<span class="rk-l" title="{_esc(x["action"])}">{_esc(x["action"])}</span>'
            f'<span class="rk-b"><i class="rk-fill" style="width:{(_st["total"] / _max) * 100:.1f}%">'
            f'{_segs}</i></span>'
            f'<span class="rk-t">{_st["total"]}</span></div>')
    _legend = "".join(f'<span><i style="background:{col}"></i>{lab}</span>'
                      for _k, lab, col in _seg_order)
    rank_panel = f"""
    <section class="panel">
      <h2>{_c("board_heading")}</h2>
      <p class="small">{_c("board_blurb")}</p>
      <div class="rk-head"><span></span><span>Duty</span><span># of sources</span></div>
      <div class="rk">{_bars_for(duties, 1)}</div>
      <div class="rk-legend">{_legend}</div>
    </section>"""

    duty_panel = f"""
    <section class="panel">
      <h2>{_c("actions_heading")}
        <span class="meta">{len(duties)} controls already required of any firm, whichever jurisdiction you practise in</span></h2>
      <p class="small">Each of these is a control the law has already moved on, at or above the
        flag threshold of {calibration.CALL_THRESHOLD} on ruling evidence only, so the list does not
        depend on which jurisdiction you practise in. The order is what to act on first: a control
        whose antecedents historically bound in 192 days gives less warning than one that took 907,
        so it comes first. The source count beside each one tells you how much to trust the line,
        not how soon to act on it. Open any of them to read the sources yourself.</p>
      <ol class="acts">{duty_rows}</ol>
      <p class="seq"><a href="https://sickofancy.ai/diagrams/legal/legal-os-radar.html">{_c("seq_cta")} &rarr;</a></p>
    </section>"""
    cal = calibration.report()
    cal_rows = "".join(
        f'<tr><td class="d">{_esc(r["date"])}</td>'
        f'<td class="c">L{r["order"]}</td>'
        f'<td>{"<span class=\'hit\'>called</span>" if r["called"] else "<span class=\'miss\'>missed</span>"}</td>'
        f'<td>{_esc(r["fault_line"])}</td>'
        f'<td class="c">{r["reading_at_lead"]} → {r["reading_at_event"]}</td>'
        f'<td>{_esc(r["title"])}</td></tr>'
        for r in cal["resolutions"]
    ) or '<tr><td colspan="6" class="src">No resolutions recorded yet.</td></tr>'
    hr = "n/a" if cal["hit_rate"] is None else f'{int(cal["hit_rate"]*100)}%'
    order_line = " &nbsp;·&nbsp; ".join(
        f'L{o} {calibration.K.ORDERS[o]["name"]} <b>'
        f'{"n/a" if s["hit_rate"] is None else str(int(s["hit_rate"]*100))+"%"}</b> ({s["hits"]}/{s["n"]})'
        for o, s in cal["by_order"].items()
    )
    def _cond_txt(key):
        cd = cal["conditionals"][key]
        rate = "n/a" if cd["rate"] is None else f'{int(cd["rate"]*100)}%'
        s = f'P({cd["post"]}|{cd["prior"]}) <b>{rate}</b> ({cd["n_backed"]}/{cd["n_eligible"]})'
        if cd["prior_called_without_post_event"]:
            s += (f' <span class="meta">[{cd["prior"]} called, no {cd["post"]} event yet: '
                  f'{", ".join(cd["prior_called_without_post_event"])}]</span>')
        return s
    cond_line = _cond_txt("L1_to_L2") + " &nbsp;·&nbsp; " + _cond_txt("L2_to_L3")
    # --- Why this is worth your time -----------------------------------------
    # The page asserts throughout and never says why it should be believed, or why the
    # firm-specific answer is worth more than the general one. Same copy as the app page.
    why_panel = f"""
    <section class="panel">
      <h2>Why this is worth your time</h2>
      <p class="eyebrow">How it works</p>
      <p class="small">Every reading comes from primary sources &mdash; court orders, statutes, bar
        opinions &mdash; weighted by who said it rather than by how many said it. A vendor blog
        carries a hundred and twenty-fifth the weight of a bar opinion, so it takes 125 of them to
        outweigh one ruling. Before anything is admitted, three independent reviews try to break
        the claim; what does not survive is dropped rather than softened. Every number here links to
        the sources behind it, so you can check the working instead of trusting the summary.</p>
      <p class="eyebrow">Why the advice is useful</p>
      <p class="small">This is a duty map, not a forecast. It reports what the law has already moved
        on, so acting on it is compliance rather than a bet on a prediction. The order is a sort for
        attention across controls you cannot all stand up at once, and it is graded against its own
        record rather than asserted. Where the evidence is thin, it says so; where a control is not
        required yet, this page does not pretend otherwise.</p>
      <p class="eyebrow">Why your fee structure changes the answer</p>
      <p class="small">The same control costs different firms different amounts, and whether it pays
        to put AI on a piece of work depends entirely on how you bill. On hourly billing, AI that cuts
        time cuts your revenue and the saving goes to the client, so adopting it is a net loss however
        good the tool is. On a fixed fee the same tool is margin. So the useful question is never
        &ldquo;should we adopt AI&rdquo; but &ldquo;which work is worth it at <em>our</em> fee
        structure, and which is worth deferring&rdquo; &mdash; and that answer is firm-specific, which
        is why the advisory layer asks for your pricing model before it tells you what to do.</p>
    </section>"""

    cal_panel = f"""
    <section class="panel">
      <h2>Calibration <span class="meta">grading the ranking across three orders, not asserting the future</span></h2>
      <p class="small">The engine tracks a cascade: <b>L1 capability</b> (AI can now do it) →
        <b>L2 ruling</b> (a court/bar moves) → <b>L3 adoption</b> (the control becomes table stakes).
        Each order depends on the one before it. Point-in-time backtest: replay the engine
        {cal['lead_days']} days before each event, using only evidence available then; "called" = the
        right meter was already &ge; {cal['call_threshold']}. Overall <b>{hr}</b>
        ({cal['hits']}/{cal['n_resolutions']}) · {cal['snapshots_recorded']} snapshots on record.</p>
      <p class="small">By order: {order_line}.</p>
      <p class="small">Cascade conditionals — each layer only counts if the one it depends on held:
        {cond_line}. A called L1 with no L2 event yet means the capability outran the law
        (reported, not scored as a fail). The seed set is small and the L1 lane is young — its
        first-of-kind capabilities have no precursor to call from — so this is the honest record so far.</p>
      <div class="tw"><table class="ev"><thead><tr><th>Landed</th><th>Order</th><th>Result</th><th>Fault line</th>
        <th>Reading (lead→event)</th><th>Resolution</th></tr></thead>
      <tbody>{cal_rows}</tbody></table></div>
    </section>"""

    tier_legend = " &nbsp; ".join(
        f'<span style="color:{TIER_COLOR[t]}">{t} {info["weight"]}</span> {info["label"]}'
        for t, info in data["tiers"].items()
    )

    return f"""<!doctype html>
<html lang="en" class="light"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="The live Fault-Line Radar: what the record already requires of a firm, how well the evidence supports each control, and the sources behind every reading.">
<link rel="icon" type="image/svg+xml" href="https://sickofancy.ai/diagrams/icon.svg">
<title>Legal-AI Fault-Line Radar</title>
{PAGE_FONTS}
{PAGE_THEME_HEAD}
<style>{PAGE_CSS}</style></head>
<body>
{PAGE_NAV}
<div class="container">
  <div class="hero">
    <div class="kicker">Legal AI OS &middot; the live board</div>
    <h1>Legal-AI Fault-Line Radar</h1>
    <p>Where AI stresses a legal duty, ranked by what the record already shows — capability (L1) → ruling (L2) → control adoption (L3), weighted by authority, not volume.</p>
    <p class="asof">As of {data['as_of']} · {data['n_items']} tracked items · each fault line shows L1 capability / L2 ruling / L3 adoption (0-10)</p>
  </div>
  <div class="legend"><b>Source authority</b> (weight): &nbsp; {tier_legend}
    <br>Volume never moves a reading. A vendor blog (T5) carries ~1/100 of an ABA opinion (T2) and ~1/125 of a binding ruling (T1).
    <br><b>What the ranking is for:</b> eleven controls are on this board and a firm cannot stand all of them up at once, so the ordering is a sort for attention. It is graded on its own, below, and is not a claim about which ruling lands next.</div>
  {rank_panel}
  {duty_panel}
  {why_panel}
  {''.join(rows)}
  {cal_panel}
  <footer class="footer">
    Generated by <code>radar/</code> in legal-os. Deterministic, replayable scores; every pressure
    reading cites its evidence and weight. Figures reflect the tracked feed at generation time —
    verify primary sources before relying on any number.
  </footer>
</div>
<script>{PAGE_THEME_JS}</script>
</body></html>"""


def milestone_report():
    """The firm-facing output, as data.

    Milestones are the claim that does not need the forward test, so the page leads with
    them and the meters become scoring provenance. Published as JSON so the in-app page can
    lead with the same thing the static page does, rather than the two drifting apart.
    """
    ms = milestones.grade()
    ms["blindside"] = milestones.blindside_scan()
    return ms


# --- Evidence strength: how well-supported is each duty? ---------------------
# A firm owner needs to know whether a duty rests on twenty appellate rulings or on two
# trial-court orders, and the page was presenting both identically. Classified from the
# item's `source` string, which is the only court-level signal the feed carries.
#
# Checked in this order on purpose: "District Court of Appeal of Florida" is APPELLATE and
# contains "District Court", so an appellate-first test is required or Florida's DCAs get
# filed as trial courts.
# First pass missed "Sixth Circuit", "Tenth Circuit" and "California Court of Appeal", all of
# which fell through to `other` and made `verification` read `moderate` off 20 sources
# including five circuit courts. The markers are matched on the operator's short court
# strings, not on reporter-style citations, so they have to include bare "circuit".
_APPELLATE = ("cir.", "circuit", "court of appeal", "supreme court", "supreme judicial",
              "appellate")
_TRIAL = ("d. ", "s.d.", "e.d.", "n.d.", "m.d.", "w.d.", "district court", "chancery",
          "bankr.", "trial court", "magistrate")


def _court_class(source, tier):
    """What KIND of authority is this? Tier first, because a T2 ethics opinion from an
    office whose name contains "Supreme Court" is guidance, not an appellate ruling."""
    if tier != "T1":
        return "guidance"
    s = (source or "").lower()
    if any(m in s for m in _APPELLATE):
        return "appellate"
    if any(m in s for m in _TRIAL):
        return "trial"
    return "primary"   # statutes, regulations, court rules, unattributed orders


def evidence_strength(fl):
    """Counts + a label, from the line's ruling-eligible evidence only.

    Ruling-eligible is the right basis: it is the set that actually moved the grade, so
    counting provenance instead would inflate strength with T4/T5 commentary nobody acted on.
    """
    items = [e for e in fl.get("evidence", []) if e.get("ruling_eligible")]
    counts = {"appellate": 0, "trial": 0, "primary": 0, "guidance": 0}
    for e in items:
        counts[_court_class(e.get("source"), e.get("tier"))] += 1
    dated = sorted((e["date"] for e in items), reverse=True)
    # A statute or regulation is binding primary law even though no court decided anything,
    # which is why `convergence` (all EU/state statutes) must not read as thin.
    if counts["appellate"] >= 3:
        label = "strong"
    elif counts["appellate"] >= 1 or counts["primary"] >= 3:
        label = "moderate"
    else:
        label = "thin"
    return {
        **counts,
        "total": len(items),
        "label": label,
        "newest": dated[0] if dated else None,
        "oldest": dated[-1] if dated else None,
    }


def watch_reason(fl, threshold, pending):
    """Why a line that is NOT yet required still deserves attention.

    Five lines sit below the duty threshold and were simply absent from the page, so a firm
    reading it saw six actions and no sign that agentic supervision has a bill in Congress.
    Absence is the wrong treatment: a control can be worth building before it is required,
    and the reason differs per line.

    Precedence matters. A precursor on the record outranks a near-threshold reading, because
    a proposed bill is a fact and 7.6-vs-8.0 is our own dial.
    """
    if fl["id"] in pending:
        p = pending[fl["id"]]
        return ("precursor", f"Precursor on the record: {p['title']} ({p['date']})")
    if fl["pressure"] >= threshold - 1.0:
        return ("near", f"Close to the threshold ({fl['pressure']} of {threshold}) "
                        f"but no ruling has landed yet")
    if fl.get("n_adoption_evidence", 0) or fl.get("n_enable_evidence", 0):
        return ("market", "No authority yet, but the market is moving on it")
    return ("defensive", "No authority yet — build it defensively or wait")


def _pending_precursors():
    return {m["fault_line"]: {"title": m["antecedent"], "date": m["antecedent_date"]}
            for m in milestones.grade()["milestones"]
            if m["status"] == "pending" and m["antecedent"]}


def enrich(data, threshold=None, pending=None):
    """Presentation enrichment, applied after scoring and before writing.

    Kept OUT of `score.py` on purpose: that file is a frozen input to the forecast
    experiment, and a sorting aid for a web page must not cost a re-freeze.
    """
    if threshold is None:
        threshold = calibration.CALL_THRESHOLD
    if pending is None:
        pending = _pending_precursors()
    for fl in data["fault_lines"]:
        fl["action"] = actions.plain_action(fl["id"], fl.get("control", ""))
        fl["stakes"] = actions.plain_stakes(fl["id"])
        fl["strength"] = evidence_strength(fl)
        # How well supported a line is, strongest first. This is an ATTRIBUTE of the line
        # and it is what the bar length draws, but it is no longer what sets the page order:
        # see `order_key` immediately below for why.
        fl["rank_key"] = (
            -fl["strength"]["appellate"],
            -fl["strength"]["total"],
            -fl["pressure"],
        )
        # What the page sorts by. Requires-before-expects, then shortest measured lead
        # first, from the shared rule in ordering.py — the same one the advisory page uses,
        # so the two surfaces stop disagreeing about what comes first. Deliberately reads
        # only the record: the radar page has no firm, so it cannot answer the firm-specific
        # question, but it can use the firm-specific page's ordering because that rule never
        # reads a firm input.
        fl["order_key"] = ordering.sort_key(fl["id"], tier=0,
                                            thin=(fl["strength"]["label"] == "thin"),
                                            pressure=fl["pressure"])
        fl["is_duty"] = fl["pressure"] >= threshold
        # Only non-duties get a watch reason. A duty reading "close to the threshold (9.7 of
        # 8.0)" is nonsense — it is over the threshold, which is the whole point of it.
        if fl["is_duty"]:
            fl["watch_kind"], fl["watch_reason"] = None, None
        else:
            fl["watch_kind"], fl["watch_reason"] = watch_reason(fl, threshold, pending)
    return data


def build(as_of=None):
    data = enrich(score(as_of=as_of), pending=_pending_precursors())
    kbd = kb.compose()  # the full source library: what + derived why, per doc
    msr = milestone_report()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data["copy"] = COPY
    (OUT_DIR / "data.json").write_text(json.dumps(data, indent=2))
    (OUT_DIR / "index.html").write_text(render(data))
    (OUT_DIR / "kb.json").write_text(json.dumps(kbd, indent=2))
    (OUT_DIR / "milestones.json").write_text(json.dumps(msr, indent=2))

    # Mirror the machine-readable outputs into the app's public dir so the in-app
    # /radar page can render the same deterministic scores + calibration + KB.
    if FRONTEND_DIR.parent.exists():  # only when the frontend is present
        FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
        (FRONTEND_DIR / "data.json").write_text(json.dumps(data, indent=2))
        (FRONTEND_DIR / "calibration.json").write_text(
            json.dumps(calibration.report(), indent=2))
        (FRONTEND_DIR / "kb.json").write_text(json.dumps(kbd, indent=2))
        (FRONTEND_DIR / "milestones.json").write_text(json.dumps(msr, indent=2))
        try:
            advisory.write_demos()   # in-app /radar/advisory demo postures
        except Exception as e:       # never let a demo-generation hiccup fail the build
            print(f"advisory demo write skipped: {e}")
    return data


if __name__ == "__main__":
    d = build()
    print(f"Wrote {OUT_DIR}/index.html and data.json — {len(d['fault_lines'])} fault lines, "
          f"{d['n_items']} items, as of {d['as_of']}")
