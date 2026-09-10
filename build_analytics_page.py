"""Analytics page: mega-category share-of-corpus over time, venue paper-count trends.
Hand-rolled SVG (no CDN charting library: tonight's repeated external-dependency
failures under file:// made that risk not worth taking for what's genuinely small data).
Same visual language as the main map: self-hosted Valley Sans, cool/muted palette,
dark glass panels.
"""
import html
import json
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

# Chart 2: venue share of accepted papers, grouped bars by year
manifest = data["venue_counts_by_year"]
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
</style>
</head>
<body>
{nav_html("analytics")}
<h1>Analytics</h1>
<div class="subtitle">70,861 papers · NeurIPS · ICML · ICLR · ACL · EMNLP · NAACL · 2018&ndash;2025</div>

<div class="panel">
  <h2>What the field pays attention to, over time</h2>
  <div class="panel-desc">Share of that year's corpus, by broad research area. Not raw counts (the corpus itself grew ~5x over this period): this shows which areas grew faster or slower than the field as a whole.</div>
  <svg viewBox="0 0 200 240" class="chart" style="max-width:220px;float:right">{"".join(legend_svg)}</svg>
  {chart1}
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
</script>
</body>
</html>
'''

open("analytics.html", "w").write(PAGE)
print(f"wrote analytics.html ({len(PAGE)} bytes)")
