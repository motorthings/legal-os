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


def _watch_item(w, n):
    """One row of the 'not required yet' list. Built here rather than inline: nested
    f-strings with escaped quotes are a syntax error in the expression part, and the
    stakes line is conditional."""
    stakes = f'<p class="act-k">{_esc(w["stakes"])}</p>' if w.get("stakes") else ""
    label = _esc(w["strength"]["label"])
    return (
        f'<li class="act watch">'
        f'<div class="act-h"><span class="act-n">{n}</span>'
        f'<span class="act-t">{_esc(w["action"])}</span>'
        f'<span class="act-s thin">{label}</span></div>'
        f'{stakes}'
        f'<p class="act-m">{_esc(w["watch_reason"])}</p>'
        f'</li>'
    )


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

    # --- Operating-model queue: the intersection, sorted by both meters high ---
    # Duties only. The five watching lines live in their own collapsed section and nowhere
    # else, so this panel does not re-present them under a different ordering.
    q_sorted = sorted([r for r in fls if r["is_duty"]], key=lambda r: r["queue"], reverse=True)
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
      <h2>{_c("detail_heading_suffix")}</h2>
      <p class="small">Not the headline — the working. Three lanes per fault line.
        <b>L1 capability</b> = can AI now do the thing
        that creates the fault line (weighted low, labeled — a demonstration, not a ruling).
        <b>L2 ruling</b> = will the law move here.
        <b>L3 adoption</b> = is the control becoming table stakes, court or no court, weighted by how
        binding the signal is on the market (an insurer changing a renewal form &gt; a pundit essay).
        <b>Queue</b> is the intersection: both high means the control is urgent <i>and</i> about to be
        mandatory. That's the third order, where the practice-building work lives.</p>
      <details class="det"><summary class="det-s"><span class="chev">&#9656;</span> show &mdash; each row opens to its meters and evidence</summary>
      <div class="tw"><table class="ev"><thead><tr><th>Control</th><th>L1 cap</th><th>L2 rule</th><th>L3 adopt</th>
        <th>Queue</th><th>Lead</th><th>Fault line</th></tr></thead>
      <tbody>{q_rows}</tbody></table></div>
      </details>
    </div>"""

    # --- Milestone panel: the actionable half, graded on the record -----------
    # This panel answers the question a firm actually asks ("how long do I have, and
    # what is already required of me") without asserting a forecast. Lead time is
    # measured antecedent -> binding event, which is a fact about the past.
    ms = milestones.grade()
    bs = milestones.blindside_scan()
    lt = ms["lead_time_days"]

    # --- What the record already requires of any firm -------------------------
    # Firm-independent: `mandated` is the law having moved, which does not depend on who
    # you are. Sequencing those against a specific firm's readiness is the advisory page's
    # job; this is the part that is true of everyone.
    lead_by_line = {}
    for m in ms["milestones"]:
        if m["status"] == "landed" and m["lead_days"] is not None:
            lead_by_line.setdefault(m["fault_line"], []).append(m["lead_days"])
    # Ordered by how well-supported each duty is, not by meter height: a duty resting on
    # seven circuit courts is a different claim from one resting on two trial orders, and a
    # single ranking must not present them as equals.
    duties = sorted(
        [fl for fl in fls if fl["pressure"] >= calibration.CALL_THRESHOLD],
        key=lambda r: r["rank_key"])
    duty_rows = "".join(
        f'<li class="act">'
        f'<div class="act-h"><span class="act-n">{i}</span>'
        f'<span class="act-t">{_esc(d["action"])}</span>'
        f'<span class="act-s {_esc(d["strength"]["label"])}">{_esc(d["strength"]["label"])}</span></div>'
        f'{f"<p class=\'act-k\'>{_esc(d['stakes'])}</p>" if d.get("stakes") else ""}'
        f'<p class="act-m">{_strength_line(d, lead_by_line)}</p>'
        f'<details><summary>See the {d["strength"]["total"]} sources</summary>'
        f'<div class="act-ev">'
        + "".join(
            f'<div><span class="d">{_esc(e["date"])}</span> {_esc(e["title"])}'
            f'<span class="src">{_esc(e["source"])} · {_esc(e["tier"])}</span></div>'
            for e in d["evidence"][:12])
        + f'{"<p class=\'src\'>+ more, listed in full below</p>" if len(d["evidence"]) > 12 else ""}'
        f'</div></details></li>'
        for i, d in enumerate(duties, 1)
    ) or '<li class="src">No control on the record is required yet.</li>'

    # --- What's coming: the controls that are NOT required yet ----------------
    # Suppressing these made the page read as if agentic supervision did not exist, when it
    # is the one line with a live bill in Congress. A firm deciding what to build needs the
    # near list as much as the now list; it just has to be labelled as not-yet-required.
    watching = sorted([fl for fl in fls if not fl["is_duty"]],
                      key=lambda r: (-r["pressure"], -r["strength"]["total"]))
    watch_rows = "".join(_watch_item(w, i) for i, w in
                         enumerate((x for x in watching if x.get("watch_reason")),
                                   len(duties) + 1))
    # --- The whole board: the same eleven, one bar each ----------------------
    # The app page leads with this; the static page had no equivalent at all, so the only
    # overview here was the meter table at the bottom. Bar length is the number of sources,
    # coloured by KIND of authority: seven circuit courts and seven bar opinions are not
    # the same claim even when the totals match.
    _seg_order = [("appellate", "appellate court", "var(--rk-app)"),
                  ("trial", "trial court", "var(--rk-trial)"),
                  ("primary", "statute or rule", "var(--rk-statute)"),
                  ("guidance", "bar guidance", "var(--rk-guide)")]
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
    <div class="cal">
      <h2>{_c("board_heading")} <span class="meta">{_c("board_sub")}</span></h2>
      <p class="small">{_c("board_blurb")}</p>
      <div class="rk">{_bars_for(duties, 1)}</div>
      <div class="rk-legend">{_legend}<span class="src">&middot; trailing number = total sources</span></div>
    </div>"""

    watch_panel = f"""
    <div class="cal">
      <details class="watch-d"><summary class="watch-h"><span class="chev">&#9656;</span> show &mdash; {len(duties) + 1} to
        {len(duties) + len(watching)} not required yet</summary>
      <p class="small">The same single ranking continues below the line. These sit under the
        threshold, so nothing yet obliges you to act, but they are on the same list because a
        control can be worth building before it is required. The reason differs per line: a bill
        in Congress is a fact, while a reading near the line is only our own dial moving.</p>
      <ul class="acts">{watch_rows}</ul></details>
    </div>""" if watch_rows else ""
    duty_panel = f"""
    <div class="cal">
      <h2>{_c("actions_heading")}
        <span class="meta">{len(duties)} controls already required of any firm, whichever jurisdiction you practise in</span></h2>
      <p class="small">Each of these is a control the law has already moved on, at or above the
        flag threshold of {calibration.CALL_THRESHOLD} on ruling evidence only, so the list does not
        depend on which jurisdiction you practise in. Ordered by how well the record supports each
        one. Open any of them to read the sources yourself.</p>
      <ol class="acts">{duty_rows}</ol>
    </div>"""
    ms_rows = "".join(
        f'<tr><td class="d">{_esc(r["antecedent_date"] or "—")}</td>'
        f'<td>{_esc(r["fault_line"])}</td>'
        f'<td>{_esc((r["antecedent"] or "")[:70])}</td>'
        f'<td class="c">{("—" if r["lead_days"] is None else str(r["lead_days"]) + "d")}</td>'
        f'<td>{"<span class=\'hit\'>" + _esc(r["status"]) + "</span>" if r["status"] == "landed" else _esc(r["status"])}</td>'
        f'<td>{_esc((r["binding"] or "not yet landed")[:58])}</td>'
        f'<td class="c">{"Y" if r["called_before_antecedent"] else "·"}</td></tr>'
        for r in sorted(ms["milestones"], key=lambda x: x["antecedent_date"] or "9999")
    )
    actionable = "".join(
        f'<li><b>{_esc(a["fault_line"])}</b> — precursor on the record {_esc(a["precursor_date"])}: '
        f'{_esc(a["precursor"])}</li>'
        for a in ms["actionable_now"]
    ) or '<li class="src">none — every control with a precursor has since bound</li>'
    hr_ms = "n/a" if ms["engine_grade"]["hit_rate"] is None else f'{int(ms["engine_grade"]["hit_rate"]*100)}%'
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
  :root {{ --bg:#0f1216; --panel:#161b22; --ink:#e6e6e6; --dim:#9aa7b4; --line:#2a323c;
    /* Semantic accents. These were MISSING from this palette, so every var(--primary),
       var(--amber) and var(--metric) reference on the page silently resolved to nothing
       -- colour-coded elements rendered with no background at all. The rank chart made
       it visible because its whole point is the colour encoding. Keep this block in step
       with the tokens the templates reference. */
    --primary:#e8b04b; --amber:#c9a227; --metric:#6fae8f; --rose:#e0603a;
    /* Rank-chart ramp. The semantic accents are not far enough apart to carry four
       categories: --primary and --amber are both gold, so "appellate" and "trial court"
       were near-identical in the bar AND in the legend. Chart-only, strongest to weakest. */
    --rk-app:#e8b04b; --rk-trial:#b06a35; --rk-statute:#6fae8f; --rk-guide:#5a6672; }}
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
  .det-s {{ cursor:pointer; list-style:none; }}
  .det-s::-webkit-details-marker {{ display:none; }}
  .det-s::before {{ content:'\\25b8  '; color:var(--dim); }}
  .det[open] > .det-s::before {{ content:'\\25be  '; }}
  .chev {{ margin-left:auto; color:var(--dim); font-size:.8rem; transition:transform .15s; }}
  details[open] > summary .chev {{ transform:rotate(90deg); }}
  @media (prefers-reduced-motion: reduce) {{ .chev {{ transition:none; }} }}
  .p {{ font-weight:700; color:#111; border-radius:6px; padding:.1rem .5rem; min-width:2.6rem;
    text-align:center; font-family:Fraunces,serif; }}
  .t {{ font-family:Fraunces,serif; font-size:1.06rem; }}
  .meta {{ color:var(--dim); font-size:.74rem; margin-left:auto; }}
  .meta .fresh {{ color:#8fd3b0; }}
  .meta .mid {{ color:#c9a227; }}
  .meta .stale {{ color:#e0603a; font-weight:600; }}
  .body {{ padding:0 1rem 1rem; border-top:1px solid var(--line); }}
  .vec {{ margin:.6rem 0; font-size:.86rem; }}
  .vec.build {{ color:#8fd3b0; }}
  .vec.small {{ color:var(--dim); font-size:.74rem; }}
  b {{ color:#cfd8e3; }}
  .tw {{ overflow-x:auto; }}
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
  /* Action list — the answer, before the working. */
  .acts {{ list-style:none; margin:.9rem 0 0; padding:0; }}
  .act {{ border:1px solid var(--line); border-radius:8px; padding:.8rem .9rem; margin:0 0 .6rem; }}
  .act-h {{ display:flex; align-items:baseline; gap:.55rem; flex-wrap:wrap; }}
  .act-n {{ font-family:'Source Code Pro',monospace; color:var(--dim); font-weight:700; }}
  .act-t {{ font-size:.95rem; font-weight:700; color:var(--fg); }}
  .act-s {{ font-size:.6rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em;
    padding:.1rem .4rem; border-radius:4px; }}
  .act-s.strong {{ background:#1f3326; color:#8fd3b0; }}
  .act-s.moderate {{ background:#33291a; color:#e8b04b; }}
  .act-s.thin {{ background:#2a2436; color:#c7b3e0; }}
  .act-k {{ color:var(--fg); font-size:.82rem; margin:.45rem 0 .3rem; }}
  .act-m {{ font-family:'Source Code Pro',monospace; font-size:.7rem; color:var(--dim);
    margin:.2rem 0 .45rem; }}
  .act details summary {{ cursor:pointer; font-size:.72rem; font-weight:700; color:#7fb0e8; }}
  .act-ev {{ margin:.5rem 0 0; font-size:.75rem; color:var(--fg); }}
  .act-ev .d {{ font-family:'Source Code Pro',monospace; color:var(--dim); margin-right:.35rem; }}
  .act-ev .src {{ display:block; color:var(--dim); font-size:.68rem; margin:.1rem 0 .5rem .4rem; }}
  .watch-h {{ font-family:Fraunces,serif; font-size:.9rem; margin:1.4rem 0 .2rem;
    padding-top:.9rem; border-top:1px solid var(--line); }}
  .act.watch {{ opacity:.86; }}
  .watch-d summary {{ cursor:pointer; }}
  .watch-d summary::marker {{ color:var(--dim); }}
  /* The whole board — one stacked bar per duty, in list order. */
  .rk {{ margin:.9rem 0 0; }}
  .rk-row {{ display:grid; grid-template-columns:1.5rem minmax(15rem,1.1fr) 2.6fr 2rem;
    gap:.6rem; align-items:center; margin:0 0 .32rem; }}
  .rk-n {{ font-family:'Source Code Pro',monospace; font-size:.7rem; color:var(--dim);
    text-align:right; }}
  .rk-l {{ font-size:.76rem; color:var(--fg); white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; }}
  .rk-b {{ display:block; }}
  .rk-fill {{ display:flex; height:8px; border-radius:2px; overflow:hidden;
    background:var(--line); }}
  .rk-fill i {{ display:block; height:100%; }}
  .rk-t {{ font-family:'Source Code Pro',monospace; font-size:.7rem; color:var(--dim);
    text-align:right; }}
  .rk-split {{ display:flex; align-items:center; gap:.6rem; margin:.7rem 0 .5rem; }}
  .rk-split span {{ flex:1; border-top:1px dashed var(--line); }}
  .rk-split em {{ font-style:normal; font-size:.6rem; font-weight:700; letter-spacing:.06em;
    text-transform:uppercase; color:var(--dim); }}
  .rk-legend {{ display:flex; flex-wrap:wrap; gap:.9rem; margin-top:.9rem;
    padding-top:.7rem; border-top:1px solid var(--line); font-size:.68rem; color:var(--dim); }}
  .rk-legend span {{ display:inline-flex; align-items:center; gap:.35rem; }}
  .rk-legend i {{ width:9px; height:9px; border-radius:2px; display:inline-block; }}
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
  <p class="sub">Where AI stresses a legal duty, ranked by what the record already shows — capability (L1) → ruling (L2) → control adoption (L3), weighted by authority, not volume.</p>
  <p class="asof">As of {data['as_of']} · {data['n_items']} tracked items · each fault line shows L1 capability / L2 ruling / L3 adoption (0-10)</p>
  <div class="legend"><b>Source authority</b> (weight): &nbsp; {tier_legend}
    <br>Volume never moves a reading. A vendor blog (T5) carries ~1/100 of an ABA opinion (T2) and ~1/125 of a binding ruling (T1).
    <br><b>What the ranking is for:</b> eleven controls are on this board and a firm cannot stand all of them up at once, so the ordering is a sort for attention. It is graded on its own, below, and is not a claim about which ruling lands next.</div>
  {rank_panel}
  {duty_panel}
  {watch_panel}
  {''.join(rows)}
  {queue_panel}
  {cal_panel}
  <footer>
    Generated by <code>radar/</code> in legal-os. Deterministic, replayable scores; every pressure
    reading cites its evidence and weight. Figures reflect the tracked feed at generation time —
    verify primary sources before relying on any number.
  </footer>
</div></body></html>"""


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
        fl["rank_key"] = (
            -fl["strength"]["appellate"],
            -fl["strength"]["total"],
            -fl["pressure"],
        )
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
