"""Paper table page: searchable, filterable, sortable, client-side paginated. Dark
theme, matching the map and analytics pages: same --bg/--panel/--accent palette as
build_analytics_page.py so all three pages read as one product.

Data embedded inline rather than fetched as a separate JSON file: tonight's earlier
font-loading investigation surfaced a same-origin restriction under file:// that blocks
even same-directory resource loading in some cases; inline sidesteps that risk
entirely, same reasoning as self-hosting the font instead of a CDN fetch.
"""
import json
from nav import NAV_CSS, nav_html

rows = json.load(open("data/table_data.json"))
DATA_JSON = json.dumps(rows, separators=(",", ":"))
# Defensive: a future venue-year could include a paper whose title literally contains
# "</script>" (e.g. a security paper on script injection), which would prematurely
# terminate this block. Corpus currently has zero such titles (checked), but this
# guards future re-runs rather than relying on that staying true.
DATA_JSON = DATA_JSON.replace("</", "<\\/")

PAGE = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Paper Atlas · Browse</title>
<style>
@font-face {{
    font-family: "Valley Sans";
    src: url("fonts/ValleySans-Variable.woff2") format("woff2-variations"),
         url("fonts/ValleySans-Variable.woff2") format("woff2");
    font-weight: 100 900;
}}
:root {{
    --bg: #14181f; --panel: rgba(24,28,38,0.75); --border: rgba(107,111,176,0.35);
    --text: #e8e8f0; --text-dim: rgba(232,232,240,0.55); --accent: #8b8fd0;
    --accent-bg: rgba(107,111,176,0.15);
}}
* {{ box-sizing: border-box; }}
body {{
    background: var(--bg); color: var(--text); margin: 0; padding: 84px 24px 60px;
    font-family: "Valley Sans", -apple-system, sans-serif; font-weight: 400;
}}
{NAV_CSS}
h1 {{ font-weight: 700; font-size: 26px; margin: 8px 0 4px; }}
.subtitle {{ color: var(--text-dim); font-size: 13px; margin-bottom: 20px; }}

.controls {{
    display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
    background: var(--panel); backdrop-filter: blur(8px);
    border: 1px solid var(--border); border-radius: 10px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    padding: 14px; margin-bottom: 16px;
}}
.search-wrap {{ position: relative; flex: 1 1 220px; }}
.controls input[type=search] {{
    width: 100%; padding: 8px 44px 8px 12px; border: 1px solid var(--border);
    border-radius: 7px; font-family: inherit; font-size: 13px; background: var(--bg);
    color: var(--text);
}}
.controls input[type=search]::-webkit-search-cancel-button,
.controls input[type=search]::-webkit-search-decoration {{ display: none !important; -webkit-appearance: none !important; }}
.controls input[type=search]::placeholder {{ color: var(--text-dim); font-weight: 400; }}
#tbl-search-icon {{
    position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
    width: 15px; height: 15px; pointer-events: none;
}}
#tbl-search-clear {{
    position: absolute; right: 32px; top: 50%; transform: translateY(-50%);
    width: 16px; height: 16px; border: none; background: none; cursor: pointer;
    color: var(--text-dim); font-size: 15px; line-height: 1; padding: 0; display: none;
}}
#tbl-search-clear:hover {{ color: var(--text); }}
/* Native select arrow rendered flush against the text with no reserved space at all
   (reported: "no right padding"), and its color/style isn't ours to control anyway.
   Same fix as the search input's icon: suppress the native rendering and draw our own,
   with real padding reserved for it. */
.controls select {{
    appearance: none; -webkit-appearance: none; -moz-appearance: none;
    padding: 8px 34px 8px 12px; border: 1px solid var(--border); border-radius: 7px;
    font-family: inherit; font-size: 13px; background-color: var(--bg); color: var(--text);
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M6 9l6 6 6-6' fill='none' stroke='rgba(232,232,240,0.5)' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 10px center; background-size: 14px;
    cursor: pointer;
}}
.result-count {{ color: var(--text-dim); font-size: 12px; margin-bottom: 10px; }}

table {{ width: 100%; border-collapse: collapse; background: var(--panel);
        backdrop-filter: blur(8px); border: 1px solid var(--border);
        border-radius: 10px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.35); }}
th {{
    text-align: left; padding: 10px 12px; font-size: 12px; font-weight: 600;
    color: var(--text-dim); border-bottom: 1px solid var(--border);
    cursor: pointer; user-select: none; white-space: nowrap;
}}
th:hover {{ color: var(--text); }}
th.sorted::after {{ content: " \\25BE"; }}
th.sorted.asc::after {{ content: " \\25B4"; }}
td {{ padding: 9px 12px; font-size: 13px; border-bottom: 1px solid var(--border); vertical-align: top; }}
tr:last-child td {{ border-bottom: none; }}
tr:hover {{ background: var(--accent-bg); }}
td.title a {{ color: var(--text); text-decoration: none; }}
td.title a:hover {{ color: var(--accent); text-decoration: underline; }}
.tag {{ display: inline-block; background: var(--accent-bg); color: var(--accent);
       border-radius: 5px; padding: 2px 7px; font-size: 11px; white-space: nowrap; }}
.venue-tag {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
             color: var(--text-dim); }}

.pagination {{ display: flex; gap: 6px; align-items: center; justify-content: center;
              margin-top: 16px; font-size: 13px; }}
.pagination button {{
    padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px;
    background: var(--panel); cursor: pointer; font-family: inherit; font-size: 13px;
}}
.pagination button:disabled {{ opacity: 0.4; cursor: default; }}
.pagination button:not(:disabled):hover {{ background: var(--accent-bg); }}
</style>
</head>
<body>
{nav_html("browse")}
<h1>Browse</h1>
<div class="subtitle">70,861 papers. Search, filter, sort. Click a title to read the paper.</div>

<div class="controls">
  <div class="search-wrap">
    <input type="search" id="q" placeholder="Search titles...">
    <button id="tbl-search-clear" type="button" aria-label="Clear search">&times;</button>
    <svg id="tbl-search-icon" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="7" fill="none" stroke="rgba(232,232,240,0.4)" stroke-width="2"/>
      <line x1="16.5" y1="16.5" x2="21" y2="21" stroke="rgba(232,232,240,0.4)" stroke-width="2" stroke-linecap="round"/>
    </svg>
  </div>
  <select id="venueFilter"><option value="">All venues</option></select>
  <select id="yearFilter"><option value="">All years</option></select>
  <select id="megaFilter"><option value="">All categories</option></select>
</div>
<div class="result-count" id="count"></div>

<table>
  <thead><tr>
    <th data-key="t">Title</th>
    <th data-key="v" style="width:90px">Venue</th>
    <th data-key="y" style="width:70px">Year</th>
    <th data-key="mega" style="width:220px">Category</th>
  </tr></thead>
  <tbody id="tbody"></tbody>
</table>
<div class="pagination" id="pagination"></div>

<script>
const DATA = {DATA_JSON};
const PAGE_SIZE = 100;
let filtered = DATA, page = 0, sortKey = null, sortAsc = true;

function unique(key) {{ return [...new Set(DATA.map(r => r[key]))].sort(); }}
const venueSel = document.getElementById('venueFilter');
unique('v').forEach(v => venueSel.innerHTML += `<option value="${{v}}">${{v.toUpperCase()}}</option>`);
const yearSel = document.getElementById('yearFilter');
unique('y').sort((a,b)=>b-a).forEach(y => yearSel.innerHTML += `<option value="${{y}}">${{y}}</option>`);
const megaSel = document.getElementById('megaFilter');
unique('mega').forEach(m => megaSel.innerHTML += `<option value="${{m}}">${{m}}</option>`);

function applyFilters() {{
  const q = document.getElementById('q').value.toLowerCase();
  const v = venueSel.value, y = yearSel.value, m = megaSel.value;
  filtered = DATA.filter(r =>
    (!q || r.t.toLowerCase().includes(q)) &&
    (!v || r.v === v) && (!y || String(r.y) === y) && (!m || r.mega === m)
  );
  if (sortKey) {{
    filtered = [...filtered].sort((a, b) => {{
      const x = a[sortKey], y = b[sortKey];
      const cmp = typeof x === 'number' ? x - y : String(x).localeCompare(String(y));
      return sortAsc ? cmp : -cmp;
    }});
  }}
  page = 0;
  render();
}}

function render() {{
  document.getElementById('count').textContent = `${{filtered.length.toLocaleString()}} papers`;
  const start = page * PAGE_SIZE;
  const pageRows = filtered.slice(start, start + PAGE_SIZE);
  document.getElementById('tbody').innerHTML = pageRows.map(r => `
    <tr>
      <td class="title"><a href="${{r.u}}" target="_blank" rel="noopener">${{escapeHtml(r.t)}}</a></td>
      <td class="venue-tag">${{r.v}}</td>
      <td>${{r.y}}</td>
      <td><span class="tag">${{escapeHtml(r.mega)}}</span></td>
    </tr>
  `).join('');
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  document.getElementById('pagination').innerHTML = `
    <button id="prev" ${{page===0?'disabled':''}}>&larr; Prev</button>
    <span>Page ${{page+1}} of ${{totalPages}}</span>
    <button id="next" ${{page>=totalPages-1?'disabled':''}}>Next &rarr;</button>
  `;
  document.getElementById('prev').onclick = () => {{ page--; render(); }};
  document.getElementById('next').onclick = () => {{ page++; render(); }};
}}

function escapeHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

const qInput = document.getElementById('q'), qClear = document.getElementById('tbl-search-clear');
function refreshClear() {{ qClear.style.display = qInput.value.length > 0 ? 'block' : 'none'; }}
qInput.addEventListener('input', () => {{ applyFilters(); refreshClear(); }});
qClear.addEventListener('click', () => {{ qInput.value = ''; applyFilters(); refreshClear(); qInput.focus(); }});
venueSel.addEventListener('change', applyFilters);
yearSel.addEventListener('change', applyFilters);
megaSel.addEventListener('change', applyFilters);
document.querySelectorAll('th[data-key]').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.dataset.key;
    if (sortKey === key) {{ sortAsc = !sortAsc; }} else {{ sortKey = key; sortAsc = true; }}
    document.querySelectorAll('th').forEach(t => t.classList.remove('sorted','asc'));
    th.classList.add('sorted'); if (sortAsc) th.classList.add('asc');
    applyFilters();
  }});
}});

applyFilters();
</script>
</body>
</html>
'''

open("table.html", "w").write(PAGE)
import os
print(f"wrote table.html ({os.path.getsize('table.html')/1e6:.1f} MB)")
