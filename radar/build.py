"""Render the scored radar to a self-contained static HTML page + data.json.

Writes to docs/radar/ so GitHub Pages can serve it. No runtime JS dependencies.
"""
import json
import html
from datetime import date
from pathlib import Path

from score import score
import calibration

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "radar"

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

        rules = " · ".join(_esc(m) for m in r["model_rules"])
        rows.append(f"""
        <details class="fl">
          <summary>
            <span class="p" style="background:{_pressure_color(r['pressure'])}">{r['pressure']}</span>
            <span class="t">{_esc(r['title'])}</span>
            <span class="meta">{_trend_glyph(r['trend'])} · {_esc(r['horizon'])} · {_esc(r['layer'])}</span>
          </summary>
          <div class="body">
            <p class="vec"><b>Fault line:</b> {_esc(r['vector'])}</p>
            <p class="vec"><b>Driver:</b> {_esc(r['tech_driver'])}</p>
            <p class="vec build"><b>Build now:</b> {_esc(r['build_now'])}</p>
            <p class="vec small">Model Rules: {rules} &nbsp;|&nbsp; seed {r['pressure_seed']} → {r['pressure']}
               &nbsp;|&nbsp; weighted evidence {r['weighted_evidence']} &nbsp;|&nbsp;
               corroboration +{r['corroboration']} &nbsp;|&nbsp; {r['n_evidence']} items</p>
            <table class="ev"><thead><tr><th>Date</th><th>Tier</th><th>Evidence (provenance)</th></tr></thead>
              <tbody>{ev_rows}</tbody></table>
          </div>
        </details>""")

    cal = calibration.report()
    cal_rows = "".join(
        f'<tr><td class="d">{_esc(r["date"])}</td>'
        f'<td>{"<span class=\'hit\'>called</span>" if r["called"] else "<span class=\'miss\'>missed</span>"}</td>'
        f'<td>{_esc(r["fault_line"])}</td>'
        f'<td>{r["pressure_at_lead"]} → {r["pressure_at_event"]}</td>'
        f'<td>{_esc(r["title"])}</td></tr>'
        for r in cal["resolutions"]
    ) or '<tr><td colspan="5" class="src">No resolutions recorded yet.</td></tr>'
    hr = "n/a" if cal["hit_rate"] is None else f'{int(cal["hit_rate"]*100)}%'
    cal_panel = f"""
    <div class="cal">
      <h2>Calibration <span class="meta">grading the engine, not asserting the future</span></h2>
      <p class="small">Point-in-time backtest: replay the engine {cal['lead_days']} days before each
        ruling landed, using only evidence available then. "Called" = the right fault line was already
        at pressure &ge; {cal['call_threshold']}. Hit rate <b>{hr}</b>
        ({cal['hits']}/{cal['n_resolutions']}) · {cal['snapshots_recorded']} snapshots on record.
        Seed set is small; this is the honest track record so far, and it grows every run.</p>
      <table class="ev"><thead><tr><th>Landed</th><th>Result</th><th>Fault line</th>
        <th>Pressure (lead→event)</th><th>Resolution</th></tr></thead>
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
</style></head>
<body><div class="wrap">
  <h1>Legal-AI Fault-Line Radar</h1>
  <p class="sub">Forecasting where the next rulings land, weighted by source authority — not volume.</p>
  <p class="asof">As of {data['as_of']} · {data['n_items']} tracked items · sorted by pressure (0-10)</p>
  <div class="legend"><b>Source authority</b> (weight): &nbsp; {tier_legend}
    <br>Volume never moves the forecast. A vendor blog (T5) carries ~1/100 of an ABA opinion (T2) and ~1/125 of a binding ruling (T1).</div>
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "data.json").write_text(json.dumps(data, indent=2))
    (OUT_DIR / "index.html").write_text(render(data))
    return data


if __name__ == "__main__":
    d = build()
    print(f"Wrote {OUT_DIR}/index.html and data.json — {len(d['fault_lines'])} fault lines, "
          f"{d['n_items']} items, as of {d['as_of']}")
