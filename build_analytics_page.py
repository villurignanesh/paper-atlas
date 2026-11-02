"""Analytics page: mega-category share-of-corpus over time, venue paper-count trends.
Hand-rolled SVG (no CDN charting library: tonight's repeated external-dependency
failures under file:// made that risk not worth taking for what's genuinely small data).
Same visual language as the main map: self-hosted Valley Sans, cool/muted palette,
dark glass panels.
"""
import html
import json
import math
from nav import NAV_CSS, nav_html, GTAG_SNIPPET

data = json.load(open("data/analytics.json"))
years = data["mega_share_by_year"]["years"]
series = data["mega_share_by_year"]["series"]

COLORS = ["#3b5f8a", "#3c718a", "#3d848a", "#468891", "#597ba0",
         "#6b6eaf", "#756bac", "#8068a9", "#7665a2", "#586295"]

# Chart 1: mega-category share of corpus, over time (line chart)
W, H, PAD_L, PAD_B, PAD_T, PAD_R = 900, 460, 55, 40, 20, 20
plot_w, plot_h = W - PAD_L - PAD_R, H - PAD_T - PAD_B
x_of = lambda i: PAD_L + i * plot_w / (len(years) - 1)
max_y = max(max(v) for v in series.values())
y_of = lambda v: PAD_T + plot_h * (1 - v / (max_y * 1.08))

lines_svg, points_svg, legend_svg = [], [], []
for i, (raw_name, color) in enumerate(zip(sorted(series, key=lambda k: -sum(series[k])), COLORS)):
    name = html.escape(raw_name)
    vals = series[raw_name]
    pts = " ".join(f"{x_of(j):.1f},{y_of(v):.1f}" for j, v in enumerate(vals))
    lines_svg.append(
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.2" '
        f'opacity="0.9" class="trend-line" data-series="{i}"/>'
    )
    for j, v in enumerate(vals):
        points_svg.append(
            f'<circle cx="{x_of(j):.1f}" cy="{y_of(v):.1f}" r="3.8" fill="{color}" '
            f'class="trend-pt" data-series="{i}" data-year="{years[j]}" data-val="{v}" '
            f'data-name="{name}" data-x="{x_of(j):.1f}"/>'
        )
    ly = 20 + i * 22
    legend_svg.append(
        f'<g class="legend-item" data-series="{i}">'
        f'<rect x="0" y="{ly}" width="12" height="12" rx="3" fill="{color}"/>'
        f'<text x="18" y="{ly+10}" class="legend-label">{name}</text></g>'
    )

y_ticks = "".join(
    f'<text x="{PAD_L-10}" y="{y_of(t)+4:.1f}" text-anchor="end" class="axis-label">{t}%</text>'
    f'<line x1="{PAD_L}" y1="{y_of(t):.1f}" x2="{W-PAD_R}" y2="{y_of(t):.1f}" class="gridline"/>'
    for t in range(0, int(max_y) + 10, 10)
)
x_ticks = "".join(
    f'<text x="{x_of(j):.1f}" y="{H-PAD_B+20}" text-anchor="middle" class="axis-label">{y}</text>'
    for j, y in enumerate(years)
)

chart1 = f'''
<svg viewBox="0 0 {W} {H}" class="chart">
  {y_ticks}
  <line id="hover-guide" x1="0" y1="{PAD_T}" x2="0" y2="{H-PAD_B}" class="hover-guide"/>
  {"".join(lines_svg)}
  {"".join(points_svg)}
  {x_ticks}
</svg>
'''

# Venue view (issue #4, Stage 2): the same chart for one venue, drawn from venue_year_mega.
# Every rule value below is from docs/decisions/013-per-venue-trends.md, where they are
# PROVISIONAL (proposed, not adopted by the maintainer). They live here and nowhere else.
Z95 = 1.959964             # 95% Wilson interval
HIDE_REL_WIDTH = 1.0       # hide a point when its Wilson half-width exceeds 100% of its share
GREY_REL_WIDTH = 0.5       # draw it grey when the half-width exceeds 50% of its share
TOP_N = 6                  # fixed top set (013: ranked on the pooled corpus), rest -> "Other"
NOTE_FRACTION = 0.5        # judgment call: "most" = more than half of a venue's points
GREY = "#8b8f9a"
OTHER = "Other"


def wilson_half_width(k, n):
    """Half-width of the 95% Wilson interval for k/n, as a fraction (matches the audit)."""
    p, z2 = k / n, Z95 ** 2
    return Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n ** 2)) / (1 + z2 / n)


def point_status(k, n):
    """'hide' | 'grey' | 'ok'. A zero count has no usable share, so it is always hidden."""
    if k == 0:
        return "hide"
    rel = wilson_half_width(k, n) / (k / n)
    return "hide" if rel > HIDE_REL_WIDTH else "grey" if rel > GREY_REL_WIDTH else "ok"


vy = data["venue_year_mega"]
vy_cats = vy["categories"]
by_vy = {(r["venue"], r["year"]): r for r in vy["rows"]}
pooled_n = {c: sum(r["counts"][c] for r in vy["rows"]) for c in vy_cats}
top = sorted(vy_cats, key=lambda c: (-pooled_n[c], c))[:TOP_N]  # same tie-break as the audit
vseries = top + [OTHER]
VSERIES_COLOR = dict(zip(vseries, COLORS))


def cell_count(r, c):
    return r["n_labeled"] - sum(r["counts"][t] for t in top) if c == OTHER else r["counts"][c]


def venue_view(ven):
    """One venue's chart + legend + notes. A venue-year that does not exist is a gap (None);
    hidden points break the line too, so no line ever implies a value we refuse to show."""
    cells = {c: [] for c in vseries}
    for yr in years:
        r = by_vy.get((ven, yr))
        for c in vseries:
            if r is None:
                cells[c].append(None)
                continue
            k, n = cell_count(r, c), r["n_labeled"]
            cells[c].append((point_status(k, n), k, n, 100 * k / n))
    flat = [x for c in vseries for x in cells[c] if x]
    vis = [x[3] for x in flat if x[0] != "hide"]
    vmax = max(vis)
    vy_of = lambda v: PAD_T + plot_h * (1 - v / (vmax * 1.08))
    lines, pts, legend = [], [], []
    for i, c in enumerate(vseries):
        color, name = VSERIES_COLOR[c], html.escape(c)
        dash = ' stroke-dasharray="6 4"' if c == OTHER else ""
        run = []
        for j, cl in enumerate(cells[c]):
            if cl and cl[0] != "hide":
                x, y = x_of(j), vy_of(cl[3])
                grey = cl[0] == "grey"
                ring = f'stroke="{color}" stroke-width="1.5" ' if grey else ""  # grey fill keeps its colour as a ring
                pts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8" fill="{GREY if grey else color}" '
                    f'{ring}'
                    f'stroke-opacity="1" class="vpt" data-name="{name}" data-year="{years[j]}" '
                    f'data-val="{cl[3]:.1f}" data-k="{cl[1]}" data-n="{cl[2]}" '
                    f'data-grey="{int(grey)}" data-x="{x:.1f}"/>')
            prev = cells[c][j - 1] if j else None
            if cl and prev and cl[0] != "hide" and prev[0] != "hide":
                a, b = (x_of(j - 1), vy_of(prev[3])), (x_of(j), vy_of(cl[3]))
                if cl[0] == "grey" or prev[0] == "grey":  # segment touching a grey point
                    if run:
                        lines.append((color, dash, run))
                        run = []
                    lines.append((GREY, ' stroke-dasharray="3 4"', [a, b]))
                else:
                    run = run or [a]
                    run.append(b)
            elif run:
                lines.append((color, dash, run))
                run = []
        if run:
            lines.append((color, dash, run))
        ly = 20 + i * 22
        legend.append(f'<g class="vlegend-item"><rect x="0" y="{ly}" width="12" height="12" rx="3" '
                      f'fill="{color}"/><text x="18" y="{ly+10}" class="legend-label">{name}</text></g>')
    line_svg = "".join(
        f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in p)}" fill="none" '
        f'stroke="{col}" stroke-width="2.2" opacity="0.9"{d}/>' for col, d, p in lines if len(p) > 1)
    yt = "".join(
        f'<text x="{PAD_L-10}" y="{vy_of(t)+4:.1f}" text-anchor="end" class="axis-label">{t}%</text>'
        f'<line x1="{PAD_L}" y1="{vy_of(t):.1f}" x2="{W-PAD_R}" y2="{vy_of(t):.1f}" class="gridline"/>'
        for t in range(0, int(vmax) + 10, 10))
    xt = "".join(
        f'<text x="{x_of(j):.1f}" y="{H-PAD_B+20}" text-anchor="middle" class="axis-label">{yr}</text>'
        f'<text x="{x_of(j):.1f}" y="{H-PAD_B+35}" text-anchor="middle" class="n-label">'
        f'{"n=" + str(by_vy[(ven, yr)]["n_labeled"]) if (ven, yr) in by_vy else "&mdash;"}</text>'
        for j, yr in enumerate(years))
    absent = [str(yr) for yr in years if (ven, yr) not in by_vy]
    gap_note = (f" {ven.upper()} did not run in {' and '.join(absent)}, so the lines break there."
                if absent else "")
    notes = [f'<p class="note">n = labelled papers that year (the denominator of every share). '
             f'Grey dot: too few papers for a reliable share. Hidden: even less reliable.'
             f'{gap_note}</p>']
    ven_n = {c: sum(r["counts"][c] for (v, _), r in by_vy.items() if v == ven) for c in vy_cats}
    big = max(ven_n, key=ven_n.get)
    if sum(x[0] != "ok" for x in flat) / len(flat) > NOTE_FRACTION:
        notes.insert(0, f'<p class="warn">Most points for {ven.upper()} are hidden or grey. '
                        f'{ven_n[big] / sum(ven_n.values()):.0%} of its papers fall in one broad area '
                        f'({html.escape(big)}), so this mega-category level cannot resolve trends here.</p>')
    return (f'<div class="view" id="view-{ven}" hidden>{"".join(notes)}'
            f'<svg viewBox="0 0 200 240" class="chart" style="max-width:220px;float:right">{"".join(legend)}</svg>'
            f'<svg viewBox="0 0 {W} {H+16}" class="chart"><line class="vguide" x1="0" y1="{PAD_T}" '
            f'x2="0" y2="{H-PAD_B}"/>{yt}{line_svg}{"".join(pts)}{xt}</svg></div>')


venue_names = sorted({r["venue"] for r in vy["rows"]})
venue_views = "".join(venue_view(v) for v in venue_names)
venue_options = '<option value="all">All</option>' + "".join(
    f'<option value="{v}">{v.upper()}</option>' for v in venue_names)

# Chart 2: venue share of accepted papers, grouped bars by year
manifest =data["venue_counts_by_year"]
venues = sorted(set(r["venue"] for r in manifest))
v_years = sorted(set(r["year"] for r in manifest))
lookup = {(r["venue"], r["year"]): r for r in manifest}
VCOLORS = dict(zip(venues, COLORS))

# Share of that year's total accepted papers, not an acceptance RATE (accepted /
# submitted): this project only ever ingested accepted papers (001-scope.md), so a true
# acceptance rate would need submission/rejection counts we don't have, per venue
# (future_work.md task #7, real, gated work, not something to fake here). This is the
# metric that's actually answerable from data already on hand. Plotted directly on the
# y-axis (not just in the tooltip) so cross-year comparison doesn't require mentally
# renormalizing raw counts against a total that's also grown ~5x over the same period.
year_totals = {}
for r in manifest:
    year_totals[r["year"]] = year_totals.get(r["year"], 0) + r["n_papers"]

W2, H2 = 900, 380
plot_w2, plot_h2 = W2 - PAD_L - PAD_R, H2 - PAD_T - PAD_B
group_w = plot_w2 / len(v_years)
bar_w = group_w / (len(venues) + 1)

bar_data = []
for gi, yr in enumerate(v_years):
    for vi, ven in enumerate(venues):
        rec = lookup.get((ven, yr))
        n = rec["n_papers"] if rec else 0
        complete = rec["complete"] if rec else True
        share = (n / year_totals[yr] * 100) if year_totals.get(yr) else 0
        bar_data.append((gi, vi, yr, ven, share, complete))
max_share = max(s for *_, s, _c in bar_data)

bars_svg = []
for gi, vi, yr, ven, share, complete in bar_data:
    bh = plot_h2 * (share / (max_share * 1.08)) if max_share else 0
    bx = PAD_L + gi * group_w + vi * bar_w
    by = PAD_T + plot_h2 - bh
    opacity = "1.0" if complete else "0.45"
    bars_svg.append(
        f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w*0.85:.1f}" height="{bh:.1f}" '
        f'fill="{VCOLORS[ven]}" opacity="{opacity}" class="bar" '
        f'data-venue="{ven}" data-year="{yr}" data-share="{share:.1f}" '
        f'data-complete="{str(complete).lower()}"/>'
    )

x_ticks2 = "".join(
    f'<text x="{PAD_L + gi*group_w + group_w/2:.1f}" y="{H2-PAD_B+20}" text-anchor="middle" class="axis-label">{yr}</text>'
    for gi, yr in enumerate(v_years)
)
y_ticks2 = "".join(
    f'<text x="{PAD_L-10}" y="{PAD_T+plot_h2*(1-t/(max_share*1.08))+4:.1f}" text-anchor="end" class="axis-label">{t}%</text>'
    f'<line x1="{PAD_L}" y1="{PAD_T+plot_h2*(1-t/(max_share*1.08)):.1f}" x2="{W2-PAD_R}" y2="{PAD_T+plot_h2*(1-t/(max_share*1.08)):.1f}" class="gridline"/>'
    for t in range(0, int(max_share) + 10, 10)
)
legend2 = "".join(
    f'<g class="legend-item2"><rect x="{i*110}" y="0" width="12" height="12" rx="3" fill="{VCOLORS[v]}"/>'
    f'<text x="{i*110+18}" y="10" class="legend-label">{v.upper()}</text></g>'
    for i, v in enumerate(venues)
)

chart2 = f'''
<svg viewBox="0 0 {W2} {H2+30}" class="chart">
  <g transform="translate(50,0)">{legend2}</g>
  <g transform="translate(0,30)">
    {y_ticks2}
    {"".join(bars_svg)}
    {x_ticks2}
  </g>
</svg>
<p class="note">Faded bars = incomplete venue-year (conference not yet concluded or proceedings not yet published).</p>
'''

VENUE_JS = '\nconst venueSelect = document.getElementById(\'venue-select\');\nvenueSelect.addEventListener(\'change\', () => {\n  document.querySelectorAll(\'#views .view\').forEach(v => { v.hidden = v.id !== \'view-\' + venueSelect.value; });\n  tooltip.style.display = \'none\';\n});\ndocument.querySelectorAll(\'.vpt\').forEach(pt => {\n  const guide = pt.closest(\'svg\').querySelector(\'.vguide\');\n  const show = e => {\n    tooltip.style.display = \'block\';\n    const low = pt.dataset.grey === \'1\'\n      ? \'<br><span style="opacity:0.6">few papers: read with caution</span>\' : \'\';\n    tooltip.innerHTML = `<b>${pt.dataset.name}</b><br>${pt.dataset.year}: ${pt.dataset.val}% `\n      + `(${pt.dataset.k} of ${pt.dataset.n} labelled papers)${low}`;\n    guide.setAttribute(\'x1\', pt.dataset.x); guide.setAttribute(\'x2\', pt.dataset.x);\n    guide.classList.add(\'visible\');\n    positionTooltip(e);\n  };\n  const hide = () => { tooltip.style.display = \'none\'; guide.classList.remove(\'visible\'); };\n  pt.addEventListener(\'mouseenter\', show);\n  pt.addEventListener(\'mousemove\', positionTooltip);\n  pt.addEventListener(\'mouseleave\', hide);\n  pt.addEventListener(\'click\', show);  // touch screens have no hover\n});\n// Tap anywhere that is not a venue point to dismiss the tooltip a tap opened.\ndocument.addEventListener(\'click\', e => {\n  if (!e.target.closest(\'.vpt\')) {\n    tooltip.style.display = \'none\';\n    document.querySelectorAll(\'.vguide\').forEach(g => g.classList.remove(\'visible\'));\n  }\n});\n'

PAGE = f'''<!doctype html>
<html>
<head>
{GTAG_SNIPPET}
<meta charset="utf-8">
<title>Paper Atlas · Analytics</title>
<style>
@font-face {{
    font-family: "Valley Sans";
    src: url("fonts/ValleySans-Variable.woff2") format("woff2-variations"),
         url("fonts/ValleySans-Variable.woff2") format("woff2");
    font-weight: 100 900;
}}
:root {{ --bg: #14181f; --panel: rgba(24,28,38,0.75); --text: #e8e8f0; --accent: #6b6eaf; }}
* {{ box-sizing: border-box; }}
body {{
    background: var(--bg); color: var(--text); margin: 0; padding: 96px 24px 80px;
    font-family: "Valley Sans", -apple-system, sans-serif; font-weight: 400;
}}
{NAV_CSS}
h1 {{ font-weight: 700; font-size: 28px; margin: 0 0 4px; }}
.subtitle {{ opacity: 0.65; font-size: 14px; margin-bottom: 32px; }}
.panel {{
    background: var(--panel); backdrop-filter: blur(8px);
    border: 1px solid rgba(107,111,176,0.35); border-radius: 12px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    padding: 24px; max-width: 960px; margin: 0 auto 32px;
}}
h2 {{ font-weight: 600; font-size: 18px; margin: 0 0 4px; }}
.panel-desc {{ opacity: 0.6; font-size: 13px; margin-bottom: 16px; }}
.chart {{ width: 100%; height: auto; }}
.axis-label {{ fill: rgba(232,232,240,0.55); font-size: 11px; }}
.gridline {{ stroke: rgba(232,232,240,0.08); stroke-width: 1; }}
.legend-label {{ fill: rgba(232,232,240,0.85); font-size: 12px; }}
.legend-item, .legend-item2 {{ cursor: default; }}
.trend-line {{ transition: opacity 0.15s; }}
.trend-line.dim {{ opacity: 0.12 !important; }}
.legend-item.dim .legend-label {{ opacity: 0.35; }}
.trend-pt {{ cursor: pointer; transition: r 0.12s ease; }}
.trend-pt:hover {{ r: 6.5; stroke: #f4f4f8; stroke-width: 1.5; }}
.hover-guide {{
    stroke: rgba(232,232,240,0.25); stroke-width: 1; stroke-dasharray: 3 3;
    opacity: 0; pointer-events: none; transition: opacity 0.12s ease;
}}
.hover-guide.visible {{ opacity: 1; }}
/* Bars: only visual feedback previously was the tooltip appearing, no highlight on the
   bar itself, which is what read as "not interactive" even though hovering worked.
   !important beats the per-bar inline opacity (1.0 complete / 0.45 incomplete) so a
   faded incomplete-year bar still snaps to full visibility and brightens on hover. */
.bar {{ cursor: pointer; transition: opacity 0.12s ease, filter 0.12s ease; }}
.bar:hover {{ opacity: 1 !important; filter: brightness(1.4); }}
.tooltip {{
    position: fixed; display: none; background: rgba(10,12,18,0.95);
    border: 1px solid rgba(107,111,176,0.5); border-radius: 8px; padding: 8px 12px;
    font-size: 12px; pointer-events: none; z-index: 10;
}}
.note {{ opacity: 0.5; font-size: 12px; margin-top: 8px; }}
.controls {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }}
.controls select {{
    background: rgba(10,12,18,0.9); color: var(--text); font: inherit; font-size: 16px;
    border: 1px solid rgba(107,111,176,0.5); border-radius: 8px; padding: 8px 12px;
    min-height: 44px; width: 100%; max-width: 260px;
}}
.warn {{ font-size: 13px; line-height: 1.4; margin: 0 0 12px; padding: 10px 12px;
    border-left: 3px solid #8b8f9a; background: rgba(139,143,154,0.12); border-radius: 4px; }}
.n-label {{ fill: rgba(232,232,240,0.4); font-size: 9px; }}
.vlegend-item {{ cursor: default; }}
.vpt {{ cursor: pointer; stroke-width: 1.5; transition: r 0.12s ease; }}
.vpt:hover {{ r: 6.5; }}
.vguide {{
    stroke: rgba(232,232,240,0.25); stroke-width: 1; stroke-dasharray: 3 3;
    opacity: 0; pointer-events: none; transition: opacity 0.12s ease;
}}
.vguide.visible {{ opacity: 1; }}
</style>
</head>
<body>
{nav_html("analytics")}
<h1>Analytics</h1>
<div class="subtitle">70,861 papers · NeurIPS · ICML · ICLR · ACL · EMNLP · NAACL · 2018&ndash;2025</div>

<div class="panel">
  <h2>What the field pays attention to, over time</h2>
  <div class="panel-desc">Share of that year's corpus, by broad research area. Not raw counts (the corpus itself grew ~5x over this period): this shows which areas grew faster or slower than the field as a whole.</div>
  <div class="controls"><label for="venue-select">Venue</label>
    <select id="venue-select" aria-controls="views">{venue_options}</select></div>
  <div id="views">
  <div class="view" id="view-all">
  <svg viewBox="0 0 200 240" class="chart" style="max-width:220px;float:right">{"".join(legend_svg)}</svg>
  {chart1}
  </div>
  {venue_views}
  </div>
</div>

<div class="panel">
  <h2>Share of accepted papers by venue, by year</h2>
  <div class="panel-desc">Each venue's share of that year's total accepted papers, not raw counts (the corpus grew ~5x over this period, so raw counts alone would mostly just show that growth rather than how the venue mix shifted). From the ingestion manifest ({len(manifest)} venue-years).</div>
  {chart2}
</div>

<!-- Deliberately a direct child of <body>, not nested inside either .panel: .panel has
     backdrop-filter, and a backdrop-filter/filter/transform ANYWHERE in an element's
     ancestor chain creates a new containing block for its position:fixed descendants in
     modern browsers, meaning "fixed" stops being relative to the viewport and becomes
     relative to that filtered ancestor instead. That's the actual root cause of the
     reported off-page tooltip: found by instrumenting getBoundingClientRect() and
     discovering the tooltip's computed style.left/top (correct, viewport-relative math)
     didn't match its actual on-screen position at all once backdrop-filter entered the
     picture. The positionTooltip() viewport math below is only correct if #tooltip's
     containing block truly is the viewport, which requires it living outside any
     filtered ancestor. -->
<div id="tooltip" class="tooltip"></div>

<script>
const tooltip = document.getElementById('tooltip');
const hoverGuide = document.getElementById('hover-guide');

// Fixed cursor+14px offset ran the tooltip off the right edge for points/bars on the
// right side of a wide chart (reported: rightmost point's box lands off-page). Measures
// the tooltip's own rendered size, so this must run AFTER innerHTML is set, not before,
// and flips to the opposite side of the cursor whenever the default placement would
// overflow the viewport, same logic a well-behaved chart library's tooltip uses.
function positionTooltip(e) {{
  const pad = 16;
  const rect = tooltip.getBoundingClientRect();
  let left = e.clientX + pad;
  let top = e.clientY + pad;
  if (left + rect.width > window.innerWidth - 8) {{
    left = e.clientX - rect.width - pad;
  }}
  if (top + rect.height > window.innerHeight - 8) {{
    top = e.clientY - rect.height - pad;
  }}
  tooltip.style.left = Math.max(8, left) + 'px';
  tooltip.style.top = Math.max(8, top) + 'px';
}}

document.querySelectorAll('.trend-pt').forEach(pt => {{
  pt.addEventListener('mouseenter', e => {{
    tooltip.style.display = 'block';
    tooltip.innerHTML = `<b>${{pt.dataset.name}}</b><br>${{pt.dataset.year}}: ${{pt.dataset.val}}%`;
    hoverGuide.setAttribute('x1', pt.dataset.x);
    hoverGuide.setAttribute('x2', pt.dataset.x);
    hoverGuide.classList.add('visible');
    positionTooltip(e);
  }});
  pt.addEventListener('mousemove', positionTooltip);
  pt.addEventListener('mouseleave', () => {{
    tooltip.style.display = 'none';
    hoverGuide.classList.remove('visible');
  }});
}});
document.querySelectorAll('.legend-item').forEach(item => {{
  item.addEventListener('mouseenter', () => {{
    const s = item.dataset.series;
    document.querySelectorAll('.trend-line').forEach(l => {{
      if (l.dataset.series !== s) l.classList.add('dim');
    }});
  }});
  item.addEventListener('mouseleave', () => {{
    document.querySelectorAll('.trend-line').forEach(l => l.classList.remove('dim'));
  }});
}});
document.querySelectorAll('.bar').forEach(bar => {{
  bar.addEventListener('mouseenter', e => {{
    tooltip.style.display = 'block';
    // Paper count dropped from here deliberately: the bar's own height against the
    // y-axis already shows that number directly, so repeating it in the tooltip was
    // redundant. Share is the one number the chart can't show visually, so that's what
    // the tooltip is for.
    const complete = bar.dataset.complete === 'true'
      ? '' : ' <span style="opacity:0.6">(partial)</span>';
    tooltip.innerHTML = `<b>${{bar.dataset.venue.toUpperCase()}} ${{bar.dataset.year}}</b><br>${{bar.dataset.share}}% of that year's total${{complete}}`;
    positionTooltip(e);
  }});
  bar.addEventListener('mousemove', positionTooltip);
  bar.addEventListener('mouseleave', () => tooltip.style.display = 'none');
}});
{VENUE_JS}</script>
</body>
</html>
'''

open("analytics.html", "w").write(PAGE)
print(f"wrote analytics.html ({len(PAGE)} bytes)")
