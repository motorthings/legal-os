"""Render the scored radar to a self-contained static HTML page + data.json.

Writes to docs/radar/ so GitHub Pages can serve it. No runtime JS dependencies.
"""
import json
import html
from datetime import date
from pathlib import Path

from score import score
import calibration
import kb
import advisory

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "radar"
# Second output: the app serves the radar as a static asset (Vercel deploys only
# frontend/, so docs/radar isn't bundled). The in-app /radar page reads these.
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend" / "public" / "radar"

TIER_COLOR = {"T1": "#e8b04b", "T2": "#c9a227", "T3": "#6fae8f", "T4": "#7a8aa0", "T5": "#8a5a5a"}


def _esc(s):
    return html.escape(str(s))


def _pressure_color(p):
    if p >= 8:
        return "#e0603a"
    if p >= 6.5:
        return "#e8b04b"
    if p >= 5:
        return "#c9a227"
    return "#6f7f95"


def _trend_glyph(t):
    return {"rising": "▲ rising", "steady": "► steady", "quiet": "· quiet"}.get(t, t)


def render(data):
    fls = data["fault_lines"]
    rows = []
    for r in fls:
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
            <span class="meta">{_trend_glyph(r['trend'])} · {_esc(r['horizon'])} · {_esc(r['layer'])}</span>
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
               &nbsp;|&nbsp; <b>queue</b> {r['queue']} · lead {_esc(r['lead'])}</p>
            <table class="ev"><thead><tr><th>Date</th><th>Demo</th><th>L1 capability evidence (weighted low, labeled — not a ruling)</th></tr></thead>
              <tbody>{cap_rows}</tbody></table>
            <table class="ev"><thead><tr><th>Date</th><th>Tier</th><th>L2 ruling evidence (provenance)</th></tr></thead>
              <tbody>{ev_rows}</tbody></table>
            <table class="ev"><thead><tr><th>Date</th><th>Market</th><th>L3 adoption signal</th></tr></thead>
              <tbody>{adopt_rows}</tbody></table>
          </div>
        </details>""")

    # --- Operating-model queue: the intersection, sorted by both meters high ---
    q_sorted = sorted(fls, key=lambda r: r["queue"], reverse=True)
    q_rows = "".join(
        f'<tr><td>{_esc(r["control"])}</td>'
        f'<td class="c">{r["capability"]}</td>'
        f'<td class="c">{r["pressure"]}</td><td class="c">{r["adoption"]}</td>'
        f'<td class="c"><b>{r["queue"]}</b></td><td class="c">{_esc(r["lead"])}</td>'
        f'<td class="src">{_esc(r["title"])}</td></tr>'
        for r in q_sorted if r["queue"] > 0
    )
    queue_panel = f"""
    <div class="cal queue">
      <h2>Operating-model queue <span class="meta">where to build before it's mandatory</span></h2>
      <p class="small">Three lanes per fault line. <b>L1 capability</b> = can AI now do the thing
        that creates the fault line (weighted low, labeled — a demonstration, not a ruling).
        <b>L2 ruling</b> = will the law move here.
        <b>L3 adoption</b> = is the control becoming table stakes, court or no court, weighted by how
        binding the signal is on the market (an insurer changing a renewal form &gt; a pundit essay).
        <b>Queue</b> is the intersection: both high means the control is urgent <i>and</i> about to be
        mandatory. That's the third order, where the practice-building work lives.</p>
      <table class="ev"><thead><tr><th>Control</th><th>L1 cap</th><th>L2 rule</th><th>L3 adopt</th>
        <th>Queue</th><th>Lead</th><th>Fault line</th></tr></thead>
      <tbody>{q_rows}</tbody></table>
    </div>"""

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
    cal_panel = f"""
    <div class="cal">
      <h2>Calibration <span class="meta">grading the engine across three orders, not asserting the future</span></h2>
      <p class="small">The engine forecasts a cascade: <b>L1 capability</b> (AI can now do it) →
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
      <table class="ev"><thead><tr><th>Landed</th><th>Order</th><th>Result</th><th>Fault line</th>
        <th>Reading (lead→event)</th><th>Resolution</th></tr></thead>
      <tbody>{cal_rows}</tbody></table>
    </div>"""

    tier_legend = " &nbsp; ".join(
        f'<span style="color:{TIER_COLOR[t]}">{t} {info["weight"]}</span> {info["label"]}'
        for t, info in data["tiers"].items()
    )

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Legal-AI Fault-Line Radar</title>
<style>
  :root {{ --bg:#0f1216; --panel:#161b22; --ink:#e6e6e6; --dim:#9aa7b4; --line:#2a323c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:'Source Code Pro',ui-monospace,Menlo,monospace; line-height:1.5; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:2.4rem 1.2rem 4rem; }}
  h1 {{ font-family:Fraunces,Georgia,serif; font-weight:600; font-size:1.9rem; margin:0 0 .2rem; }}
  .sub {{ color:var(--dim); margin:0 0 .2rem; }}
  .asof {{ color:var(--dim); font-size:.82rem; margin:.4rem 0 1.4rem; }}
  .legend {{ font-size:.74rem; color:var(--dim); border:1px solid var(--line);
    border-radius:8px; padding:.6rem .8rem; margin-bottom:1.6rem; }}
  .fl {{ background:var(--panel); border:1px solid var(--line); border-radius:10px;
    margin:.6rem 0; overflow:hidden; }}
  summary {{ cursor:pointer; list-style:none; padding:.85rem 1rem; display:flex;
    align-items:center; gap:.7rem; flex-wrap:wrap; }}
  summary::-webkit-details-marker {{ display:none; }}
  .p {{ font-weight:700; color:#111; border-radius:6px; padding:.1rem .5rem; min-width:2.6rem;
    text-align:center; font-family:Fraunces,serif; }}
  .t {{ font-family:Fraunces,serif; font-size:1.06rem; }}
  .meta {{ color:var(--dim); font-size:.74rem; margin-left:auto; }}
  .body {{ padding:0 1rem 1rem; border-top:1px solid var(--line); }}
  .vec {{ margin:.6rem 0; font-size:.86rem; }}
  .vec.build {{ color:#8fd3b0; }}
  .vec.small {{ color:var(--dim); font-size:.74rem; }}
  b {{ color:#cfd8e3; }}
  table.ev {{ width:100%; border-collapse:collapse; font-size:.78rem; margin-top:.4rem; }}
  table.ev th {{ text-align:left; color:var(--dim); border-bottom:1px solid var(--line);
    padding:.3rem .4rem; font-weight:600; }}
  table.ev td {{ padding:.35rem .4rem; border-bottom:1px solid #20262e; vertical-align:top; }}
  td.d {{ white-space:nowrap; color:var(--dim); }}
  .tier {{ font-weight:700; }}
  .src {{ color:var(--dim); font-size:.72rem; margin-top:.15rem; }}
  .flag {{ font-size:.62rem; background:#243; color:#8fd3b0; border-radius:4px;
    padding:.02rem .3rem; margin-left:.3rem; }}
  .flag.conflict {{ background:#422; color:#e0a0a0; }}
  footer {{ color:var(--dim); font-size:.72rem; margin-top:2rem; border-top:1px solid var(--line);
    padding-top:1rem; }}
  a {{ color:#7fb0e0; }}
  .cal {{ background:#12171d; border:1px solid var(--line); border-radius:10px;
    padding:1rem 1.1rem; margin:0 0 1.6rem; }}
  .cal h2 {{ font-family:Fraunces,serif; font-size:1.1rem; margin:0 0 .3rem; }}
  .cal .small {{ color:var(--dim); font-size:.78rem; margin:.3rem 0 .7rem; }}
  .hit {{ color:#8fd3b0; font-weight:700; }}
  .miss {{ color:#e0a0a0; font-weight:700; }}
  .p.a {{ background:transparent !important; color:#8fd3b0; border:1px solid #2a4a3a; }}
  .p.c {{ background:transparent !important; color:#c7b3e0; border:1px dashed #4a3a5a; }}
  .mkt {{ font-size:.66rem; background:#1f3326; color:#8fd3b0; border-radius:4px; padding:.05rem .35rem; text-transform:uppercase; letter-spacing:.03em; }}
  .cap {{ font-size:.66rem; background:#2a2436; color:#c7b3e0; border-radius:4px; padding:.05rem .35rem; text-transform:uppercase; letter-spacing:.03em; }}
  td.c {{ text-align:center; white-space:nowrap; color:var(--dim); }}
  .queue table.ev td {{ vertical-align:middle; }}
</style></head>
<body><div class="wrap">
  <h1>Legal-AI Fault-Line Radar</h1>
  <p class="sub">Forecasting the cascade — capability (L1) → ruling (L2) → control adoption (L3) — weighted by authority, not volume.</p>
  <p class="asof">As of {data['as_of']} · {data['n_items']} tracked items · each fault line shows L1 capability / L2 ruling / L3 adoption (0-10)</p>
  <div class="legend"><b>Source authority</b> (weight): &nbsp; {tier_legend}
    <br>Volume never moves the forecast. A vendor blog (T5) carries ~1/100 of an ABA opinion (T2) and ~1/125 of a binding ruling (T1).</div>
  {queue_panel}
  {cal_panel}
  {''.join(rows)}
  <footer>
    Generated by <code>radar/</code> in legal-os. Deterministic, replayable scores; every pressure
    reading cites its evidence and weight. Figures reflect the tracked feed at generation time —
    verify primary sources before relying on any number.
  </footer>
</div></body></html>"""


def build(as_of=None):
    data = score(as_of=as_of)
    kbd = kb.compose()  # the full source library: what + derived why, per doc

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "data.json").write_text(json.dumps(data, indent=2))
    (OUT_DIR / "index.html").write_text(render(data))
    (OUT_DIR / "kb.json").write_text(json.dumps(kbd, indent=2))

    # Mirror the machine-readable outputs into the app's public dir so the in-app
    # /radar page can render the same deterministic scores + calibration + KB.
    if FRONTEND_DIR.parent.exists():  # only when the frontend is present
        FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
        (FRONTEND_DIR / "data.json").write_text(json.dumps(data, indent=2))
        (FRONTEND_DIR / "calibration.json").write_text(
            json.dumps(calibration.report(), indent=2))
        (FRONTEND_DIR / "kb.json").write_text(json.dumps(kbd, indent=2))
        try:
            advisory.write_demos()   # in-app /radar/advisory demo postures
        except Exception as e:       # never let a demo-generation hiccup fail the build
            print(f"advisory demo write skipped: {e}")
    return data


if __name__ == "__main__":
    d = build()
    print(f"Wrote {OUT_DIR}/index.html and data.json — {len(d['fault_lines'])} fault lines, "
          f"{d['n_items']} items, as of {d['as_of']}")
