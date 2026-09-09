"""Phase 7, polished: real 902 clusters, real LLM labels, clickable paper links,
abstract snippets, year-range filtering, browsable topic tree.

hover_text_html_template + extra_point_data (confirmed via DataMapPlot source,
interactive_rendering.py) is what makes the HTML tooltip render a real link and
snippet instead of plain text: not a workaround, a documented feature.
"""
import json
import html as htmllib
import numpy as np
import pandas as pd
import datamapplot
import matplotlib.colors as mcolors
from paper_atlas.embed import load_corpus
from nav import LOGO_SVG, NAV_CSS, nav_html

# Cool/muted palette (blues -> teals -> violets), restricted to that hue arc rather than
# the library's default full hue wheel, deliberate, not a tuning knob left at default.
# Cyclic (first == last anchor) per the cmap docstring's own requirement. Moderate
# saturation/lightness: enough contrast to read on the dark background without looking
# neon.
_COOL_ANCHORS = ["#3B5F8A", "#3E8E8A", "#6B6FB0", "#8567A8", "#3B5F8A"]
COOL_CMAP = mcolors.LinearSegmentedColormap.from_list("cool_muted", _COOL_ANCHORS)

# @import inside custom_css works regardless of exactly where the resulting <style> tag
# lands in the document, sidesteps needing to know custom_html's exact injection point
# (unverified, and every DataMapPlot internal we guessed at blind tonight needed a fix).
CUSTOM_CSS = """
/* Valley Sans (Helsinki Type Studio, SIL OFL 1.1, self-hosted, see fonts/VALLEY_SANS_OFL.txt).
   Self-hosted rather than fetched from Google Fonts specifically because that external
   fetch was confirmed NOT loading reliably here: a local, same-directory file avoids
   the whole class of problem and works identically under file:// and once deployed. */
@font-face {
    font-family: "Valley Sans";
    src: url("fonts/ValleySans-Variable.woff2") format("woff2-variations"),
         url("fonts/ValleySans-Variable.woff2") format("woff2");
    font-weight: 100 900;
    font-style: normal;
}
/* Instrument Serif (SIL OFL 1.1, self-hosted, see fonts/INSTRUMENT_SERIF_OFL.txt),
   fetched from Google's own OFL font repo (google/fonts on GitHub), same self-hosting
   reasoning as Valley Sans above. Italic-only: this is the reference-site pairing (bold
   rounded sans for a declarative line + one elegant italic serif for the payoff line),
   used in exactly one place, the map's headline, not as a general body font. */
@font-face {
    font-family: "Instrument Serif";
    src: url("fonts/InstrumentSerif-Italic.woff2") format("woff2");
    font-weight: 400;
    font-style: italic;
}
:root { --ui-font: "Valley Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
body, .container-box, #text-search { font-family: var(--ui-font) !important; }

.container-box {
    background: rgba(20, 24, 32, 0.72) !important;
    backdrop-filter: blur(8px);
    border: 1px solid rgba(107, 111, 176, 0.35) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
}

/* The CONTAINER (#search-container, a .container-box) owns the entire visible border
   + radius + background. The input itself is borderless/transparent so there is only
   ONE visible rounded rectangle, not two nested ones. (The previous double-border,
   which is what read as "weird": input had its own border+radius INSIDE the
   container's, which also had its own.) */
#text-search {
    border: none !important;
    border-radius: inherit !important;
    background: transparent !important;
    color: #e8e8f0 !important;
    padding: 10px 68px 10px 14px !important;   /* room for both icon+clear, verified below */
    width: 100%;
    outline: none;
}
/* Suppress the NATIVE browser clear button on type="search" inputs (Safari/Chrome both
   render one via these pseudo-elements); without this it renders ALONGSIDE our own
   custom clear button, which is exactly the two-x bug. table.html already had this;
   this input didn't, and that gap was the actual cause, not a styling tweak. */
#text-search::-webkit-search-cancel-button,
#text-search::-webkit-search-decoration { display: none !important; -webkit-appearance: none !important; }

/* The nav pill carries the logo and "Paper Atlas" brand (see nav.py), so the library's
   native title ("id=main-title", top-left) doesn't need to repeat the brand. It also
   used to inherit .container-box's bordered/backgrounded panel treatment (the same
   boxy look the search widget uses): right for an interactive control, wrong for a
   headline. Reported as looking bad: a giant bold stat wrapping awkwardly inside a
   visible border. Reference-site fix is to drop the panel entirely and let the
   headline float directly on the background (Supaste's hero text has no card around
   it at all), and to split the headline into the reference's own pairing: one bold
   declarative line, one elegant italic-serif payoff line, instead of dumping both
   numbers into a single oversized line. */
#title-container {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    padding: 0 !important;
    /* No max-width by default (containers_and_stacks.css only sets top/left: 0), so a
       wide headline can physically overlap the nav pill's top-right corner: caught by
       screenshotting at several widths, not assumed. A fixed px value cleared it at
       1600px but re-overlapped at 1440px, because the nav re-centers with viewport width
       while the title stays pinned left; needed a vw-relative formula instead, verified
       at 1280/1440/1600/1920px. */
    max-width: max(340px, calc(50vw - 220px));
}
/* Reproduced in isolation (minimal synthetic call, no project code involved):
   create_interactive_plot's font_weight= param never reaches the title's inline
   font-weight; it renders as the literal, invalid "font-weight:;" no matter what value
   is passed. A datamapplot bug, not something wrong on our end; harmless here since
   both headline spans below set their own font-weight explicitly, but left as a safety
   net for #main-title itself. */
#main-title {
    font-weight: 700 !important;
    display: block;
    line-height: 1.08;
    text-shadow: 0 2px 16px rgba(0, 0, 0, 0.55);
}
.pa-headline-strong {
    font-family: var(--ui-font);
    font-weight: 800;
    font-size: 40pt;
    color: #f4f4f8;
}
.pa-headline-serif {
    font-family: "Instrument Serif", Georgia, serif;
    font-style: italic;
    font-weight: 400;
    font-size: 36pt;
    color: rgba(244, 244, 248, 0.9);
}
/* Subtitle span has no id/class of its own in the library's template (just
   #main-title followed by a bare <br> + <span style="...">), so it's addressed as
   "the span after #main-title" rather than by a selector that doesn't exist. */
#main-title + br + span {
    text-shadow: 0 2px 12px rgba(0, 0, 0, 0.5);
}
""" + NAV_CSS + """

/* Topic tree: the container itself already inherits our dark glass .container-box
   treatment (confirmed via source: TopicTreeWidget.html is literally
   '<div id=... class="container-box"></div>', same as search/title), but everything
   INSIDE it (topic_tree_style.css) is unstyled light-theme defaults with no relationship
   to our palette: a bright saturated RoyalBlue hover, a #3ba5e7 square-cornered "Expand
   All" button, a #ddd header divider and #f1f1f1 scrollbar track meant for a white
   background. Recolored to the same muted violet-blue used everywhere else (nav active
   state, search accents, headline), and the "Expand All" button reshaped into the same
   pill convention as the nav links instead of a squared-off bright-blue button. */
/* #topic-tree itself has NO padding in the library's default CSS at all (checked: no
   rule sets it anywhere, not even the small-screen media queries, which only apply
   below 768px). Reported as looking bad: "Expand All" touching the top-right corner,
   "Minor subtopics" sitting flush against the bottom edge. Confirmed by rendering this
   exact panel in isolation (a standalone test file reusing the real compiled CSS, since
   the full page's data load never completes under headless Chrome). Verified the fix
   the same way before shipping it here. */
#topic-tree {
    position: relative;
    padding: 20px 22px 22px 22px;
}
/* The library positions the collapse button (a DOM SIBLING of .topic-tree-container, not
   a child of .topic-tree-header) via a margin-top:-2em / padding-left:2em hack tuned to
   its own default font-size, pulling the header up to visually overlap where the button
   naturally falls in flow. That's what broke ("the arrow is not aligned") once
   topic_tree_kwds set a different font_size than the library's 12pt default: the em-based
   offsets are relative to font-size, so they no longer landed where they used to. Taken
   out of flow entirely (position: absolute, anchored to #topic-tree's own padding box)
   instead of re-tuning another em-relative offset that would just break again on the
   next font-size change. */
/* Fully self-contained rather than relying on display:flex/align-items:center surviving
   unclobbered from the library's earlier rule on the same selector: reported as still not
   vertically centered after the first pass, which is a sign that assumption shouldn't be
   trusted blindly. Redeclares every property this row's layout depends on. */
.topic-tree-header {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(107, 111, 176, 0.3);
    margin: 0 0 10px 0;
    padding: 0 0 10px 28px;
}
.topic-tree-header h3 {
    font-size: 15px;
    font-weight: 700;
    line-height: 1;
    margin: 0;
    color: #e8e8f0;
}
/* Reported as still having a large unexplained gap below the header after the first pass.
   Cause: neither the library's CSS nor the first-pass fix reset the default browser
   margin a bare <ul> carries (topic_tree.js emits a plain <ul class="nested">, and
   .nested only sets margin-left/padding-inline-start, never margin-top/bottom); that
   default margin was stacking on top of the header's own spacing. Zeroed here, keeping
   only the deliberate left indent. */
.nested { margin-top: 0; margin-bottom: 0; }
.expand-all-btn {
    background: rgba(107, 111, 176, 0.2);
    color: rgba(232, 232, 240, 0.85);
    border-radius: 999px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
    transition: background 0.15s ease, color 0.15s ease;
}
.expand-all-btn:hover {
    background: #e8e8f0;
    color: #0d0f14;
    text-decoration: none;
}
.topic-tree-btn:hover { background-color: rgba(107, 111, 176, 0.4); }
.caret::before, .bullet::before { color: rgba(159, 163, 224, 0.85); }
.caret, .bullet { opacity: 0.6; }
/* Always plain white, full opacity: reported that the dimmed-unless-matched treatment
   (see TOPIC_TREE_HIGHLIGHT_JS below) read as unwanted complication, the same complaint
   raised about the reference implementation's zoom-based light/dark label dimming.
   Selection state is carried by an underline instead of a brightness change. */
.topic-tree-label {
    color: #f0f0f5;
    text-decoration: none;
}
.topic-tree-label:hover { color: #ffffff; }
/* Library default is font-size: 1.5em relative to the tree's own 13px container font,
   landing at ~19.5px next to a 15px heading, visibly oversized/mismatched next to it,
   which is what read as "weird." Fixed, proportionate size instead of a relative one. */
.topic-tree-close-btn, .topic-tree-close-btn.closed {
    position: absolute;
    top: 20px;
    left: 22px;
    color: rgba(232, 232, 240, 0.75);
    font-size: 14px;
    line-height: 1;
    margin: 0;
    padding: 0;
}
li { margin: 4px 0; font-size: 14px; }
#topic-tree-body::-webkit-scrollbar-track { background: transparent; }
#topic-tree-body::-webkit-scrollbar-thumb { background: rgba(107, 111, 176, 0.4); border-radius: 4px; }
#topic-tree-body::-webkit-scrollbar-thumb:hover { background: rgba(107, 111, 176, 0.7); }

/* Search box polish: the library's own default is a bare <input placeholder="🔍">,
   which behaves like plain text: visible until you type, then just gone, rather than
   a real icon-in-input UI. get_container_id() confirmed via source: SearchWidget's
   container is deterministically #search-container (widget_id "search" + "-container").
   Real icon (fixed, rightmost, decorative), real placeholder text, and a clear button,
   the pattern used by Google/most modern search inputs. */
/* Explicit, direct override rather than tracing exactly which library default (stack
   layout, a JS-set inline style, etc.) was inflating the container's height; couldn't
   find a clear single cause in the library's own CSS, so this wins regardless of the
   actual mechanism. Targets #search-container specifically, not the shared
   .container-box class, so other widgets (topic tree, histogram) aren't affected. */
#search-container {
    position: relative;
    padding: 4px !important;
    height: auto !important;
}
#text-search::placeholder { color: rgba(232, 232, 240, 0.4) !important; font-weight: 400; }
#search-icon {
    position: absolute; right: 16px; top: 50%; transform: translateY(-50%);
    width: 15px; height: 15px; pointer-events: none;
}
#search-clear {
    position: absolute; right: 40px; top: 50%; transform: translateY(-50%);
    width: 16px; height: 16px; border: none; background: none; cursor: pointer;
    color: rgba(232, 232, 240, 0.5); font-size: 15px; line-height: 1; padding: 0;
    display: none; align-items: center; justify-content: center;
}
#search-clear:hover { color: rgba(232, 232, 240, 0.9); }
"""

CUSTOM_HTML = (
    nav_html("map")
    + f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,{LOGO_SVG.replace(chr(34), chr(39))}">'
)


t = load_corpus()
ids = t.column("paper_id").to_pylist()
titles = t.column("title").to_pylist()
abstracts = t.column("abstract").to_pylist()
venues = t.column("venue").to_pylist()
years = t.column("year").to_pylist()
urls = t.column("source_url").to_pylist()
authors = t.column("authors").to_pylist()

proj = np.load("data/knn/umap_mindist0.5.npz", allow_pickle=False)
proj_ids, coords = proj["ids"], proj["coords"]
clust = np.load("data/knn/cluster_umap10d_mcs15_ms5.npz", allow_pickle=False)
clust_ids, labels = clust["ids"], clust["labels"]
cluster_labels = json.load(open("data/knn/cluster_labels.json"))

# Two-level hierarchy (011-clustering.md addendum): the top-level clustering was
# derived from the SAME 10D UMAP coords by raising min_cluster_size, validated at
# 97-100% nesting into the leaf clusters above, not an independent, possibly
# inconsistent grouping.
top = np.load("data/knn/midlevel_mcs400_ms5.npz", allow_pickle=False)
top_ids, top_labels = top["ids"], top["labels"]
toplevel_labels = json.load(open("data/knn/toplevel_labels.json"))

# Three-level hierarchy: mega-category, requested for layperson accessibility after
# the 44-topic level proved too technical on inspection (011-clustering.md). Same
# proven technique (raise min_cluster_size further on the same 10D UMAP coords),
# swept to find a genuine plateau (8 clusters, stable across mcs 1900-2200) rather
# than forcing an arbitrary count.
mega = np.load("data/knn/megacat_mcs2000_ms5.npz", allow_pickle=False)
mega_ids, mega_labels = mega["ids"], mega["labels"]
megacat_labels = json.load(open("data/knn/megacat_labels.json"))

pos = {p: i for i, p in enumerate(ids)}
order = [pos[p] for p in proj_ids]
assert (proj_ids == clust_ids).all(), "projection/cluster id order mismatch"
assert (proj_ids == top_ids).all(), "projection/toplevel id order mismatch"
assert (proj_ids == mega_ids).all(), "projection/megacat id order mismatch"

# 12,664 points (18%) are leaf-clustered but land in TOP-LEVEL noise. Traced this to
# 256 ENTIRE leaf clusters (15-355 papers each, median 34) with zero non-noise
# top-level members, not stragglers from otherwise-parented clusters (verified: no
# leaf cluster has a MIX of noise and non-noise top parents). A "majority parent"
# reassignment cannot apply here; there is no majority to inherit. These are real,
# coherent leaf topics that are simply too narrow to meet the mcs=400 density bar
# anywhere. Giving them an honest shared parent label rather than lumping them into
# "Unclustered" alongside points with no real topic at either level. Sentinel -2
# marks this distinct case so the label lookup below can tell them apart.
SPECIALIZED_SENTINEL = -2
top_labels = top_labels.copy()
for leaf_id in range(int(labels.max()) + 1):
    idx = np.where(labels == leaf_id)[0]
    if len(idx) == 0:
        continue
    parents = top_labels[idx]
    if (parents >= 0).sum() == 0:      # entire leaf cluster is top-level noise
        top_labels[idx] = SPECIALIZED_SENTINEL

# Same orphaning pattern one level up: 10 of 44 topics (8,864 papers) and, more
# granularly, 231 of 902 leaf clusters (13,185 papers, a superset, since a leaf
# cluster can be mega-orphaned even when its parent topic isn't) have zero non-noise
# mega-level members. Grouping by the DISTINCT VALUE actually in top_labels (real
# topic ids 0-43, the -2 specialized sentinel, or genuine -1 noise) rather than
# range(44), since each needs its own independent orphan check against mega.
CROSS_CUTTING_SENTINEL = -3
mega_labels = mega_labels.copy()
for group_val in np.unique(top_labels):
    idx = np.where(top_labels == group_val)[0]
    parents = mega_labels[idx]
    if (parents >= 0).sum() == 0:      # entire topic-level group is mega-noise
        mega_labels[idx] = CROSS_CUTTING_SENTINEL

def snippet(a, n=220):
    a = (a or "").strip()
    return a[:n].rsplit(" ", 1)[0] + "…" if len(a) > n else a

# Author names were already in the corpus schema (paper_atlas/schema.py's authors
# field, list<struct{name, source_author_id}>), just never wired into the hover card.
# Confirmed near-universal coverage before using it (70,859 of 70,861 papers), unlike
# the keywords/primary_area columns, which are ICLR-only and would make the hover card
# inconsistent depending on which venue a point happens to be from. Truncated rather
# than shown in full: this is the compact hover card, not the richer detail panel
# scoped in issue #2 (jalammar's reference shows full author lists there, which fits a
# click-through panel but not a card meant to stay scannable while hovering quickly).
def format_authors(author_list, max_shown=3):
    names = [a.get("name", "") for a in (author_list or []) if a.get("name")]
    if not names:
        return ""
    if len(names) <= max_shown:
        return ", ".join(names)
    return ", ".join(names[:max_shown]) + ", et al."

titles_o = [titles[i] for i in order]
venues_o = [venues[i] for i in order]
years_o = [years[i] for i in order]
urls_o = [urls[i] for i in order]
snippets_o = [snippet(abstracts[i]) for i in order]
authors_o = [format_authors(authors[i]) for i in order]

label_strings = np.array([
    cluster_labels.get(str(l), {}).get("label", "Unclustered") if l >= 0 else "Unclustered"
    for l in labels
])
# *label_layers ordering is finest-first, coarsest-last (create_interactive_plot's own
# documented requirement): this second array is what activates the native topic-tree
# nesting and the zoom-based label reveal (hierarchical_collision_priority), instead of
# the flat single-layer list we shipped earlier tonight.
toplevel_strings = np.array([
    toplevel_labels.get(str(l), {}).get("label", "Unclustered") if l >= 0
    else "Specialized / Niche Topics" if l == SPECIALIZED_SENTINEL
    else "Unclustered"
    for l in top_labels
])
megacat_strings = np.array([
    megacat_labels.get(str(l), {}).get("label", "Unclustered") if l >= 0
    else "Cross-Cutting & Specialized Research" if l == CROSS_CUTTING_SENTINEL
    else "Unclustered"
    for l in mega_labels
])
hover = [f"{ti} [{v.upper()} {y}]" for ti, v, y in zip(titles_o, venues_o, years_o)]

# Mega + leaf as a two-level breadcrumb (e.g. "Vision & 3D › Video Concept Transfer and
# Dense Motion Editing"), same pattern the reference implementation uses. Mid-level (44
# topics) deliberately skipped here to keep the hover card to one line; all three levels
# are still fully browsable via the topic tree itself.
breadcrumbs_o = [f"{mc} › {lf}" for mc, lf in zip(megacat_strings, label_strings)]

extra = pd.DataFrame({
    "title": [htmllib.escape(x) for x in titles_o],
    "venue": [v.upper() for v in venues_o],
    "year": years_o,
    "authors": [htmllib.escape(x) for x in authors_o],
    "breadcrumb": [htmllib.escape(x) for x in breadcrumbs_o],
    "snippet": [htmllib.escape(x) for x in snippets_o],
    "url": urls_o,
    # enable_topic_tree has no connection to search state (confirmed via source: it's
    # a static full list, never reads the selection the search box drives): typing a
    # query narrows the MAP correctly but the sidebar kept listing all 902 names
    # regardless, which read as broken. Dropped the tree; folded cluster label into the
    # searchable text instead, so search covers topic names, not just paper titles.
    "search_text": [f"{cl} {ti}" for cl, ti in zip(label_strings, titles_o)],
})

# Giving up on click-to-filter-map-points from the topic tree after three failed
# approaches (direct addSelection x2, simulated search input x1); all shared one
# trait: triggered from within a click handler on the SAME element the library's own
# zoomToLabelBounds also fires on, and manual retyping in the search box works while a
# single programmatic dispatch does not, pointing at that shared click/viewport-change
# context as the actual blocker, not the specific API called. The reference
# implementation this project is modeled on doesn't support this interaction either.
#
# Simpler, safer replacement: reuse the tree's own NATIVE highlightElements() method
# (topic_tree.js): it adds a `.highlighted` class without hiding anything, exactly
# matching "I still need to see the topics, but the one I selected must be highlighted."
# Previously dismissed as insufficient when the goal was thought to be hiding; it is
# exactly right for the corrected goal. Wired to the EXISTING search box (typing, not
# clicking), which is the one interaction already proven to work end-to-end.
# Real placeholder text + a fixed, decorative right-aligned icon + a clear ("x") button
# that appears once there's text: the library's default is a bare emoji-as-placeholder
# input, which reads as unpolished. Runs once #search-container exists; container is
# present from initial page render (only the tree/histogram widgets wait for
# datamapDataLoaded), so no event-listening dance needed here.
SEARCH_POLISH_JS = """
(function() {
  const container = document.querySelector('#search-container');
  const input = document.querySelector('#text-search');
  if (!container || !input) return;

  input.placeholder = 'Search...';

  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.id = 'search-icon';
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.innerHTML = '<circle cx="11" cy="11" r="7" fill="none" stroke="rgba(232,232,240,0.45)" stroke-width="2"/>' +
                   '<line x1="16.5" y1="16.5" x2="21" y2="21" stroke="rgba(232,232,240,0.45)" stroke-width="2" stroke-linecap="round"/>';
  container.appendChild(icon);

  const clearBtn = document.createElement('button');
  clearBtn.id = 'search-clear';
  clearBtn.type = 'button';
  clearBtn.textContent = '\u00d7';
  clearBtn.setAttribute('aria-label', 'Clear search');
  container.appendChild(clearBtn);

  function refreshClearVisibility() {
    clearBtn.style.display = input.value.length > 0 ? 'block' : 'none';
  }
  input.addEventListener('input', refreshClearVisibility);
  clearBtn.addEventListener('click', function() {
    input.value = '';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    refreshClearVisibility();
    input.focus();
  });
  refreshClearVisibility();
})();
"""

TOPIC_TREE_HIGHLIGHT_JS = """
(function() {
  function applyHighlight(searchTerm) {
    const tree = window.datamap && window.datamap.widgets && window.datamap.widgets['topic-tree'];
    if (!tree || !window.datamap.labelData) return;
    const term = searchTerm.trim().toLowerCase();
    const matches = term === ''
      ? window.datamap.labelData
      : window.datamap.labelData.filter(d => (d.label || '').toLowerCase().includes(term));
    tree.highlightElements(matches);
  }
  const searchInput = document.querySelector('#text-search');
  if (searchInput) {
    searchInput.addEventListener('input', function(event) {
      applyHighlight(event.target.value);
    });
  }

  // Reported that opacity-based dimming (everything else fades while a match stays lit)
  // was unwanted complication, same complaint raised about the reference implementation's
  // zoom-based light/dark label treatment. Replaced with a plain underline on the match;
  // everything else stays full-brightness white (set in CUSTOM_CSS's .topic-tree-label),
  // no dimming at all.
  const style = document.createElement('style');
  style.textContent = '.topic-tree-label.highlighted { text-decoration: underline; text-underline-offset: 3px; }';
  document.head.appendChild(style);
})();
"""

# Passing noise_label="Unclustered" (needed for correct noise-point coloring on the map
# canvas itself) has a side effect in the library's own hierarchy-construction code
# (interactive_helpers.py): wherever leftover noise exists within a parent that is ITSELF
# a synthesized noise bucket, it recurses and creates another node with the exact same
# hardcoded "Minor subtopics" text, one level deeper. Reported as confusing: expanding
# "Minor subtopics" reveals another "Minor subtopics" inside it. Confirmed by decoding the
# actual tree data directly: exactly 2 of 54 "Minor subtopics" nodes have this property
# (their own parent's label is ALSO "Minor subtopics"), and both are genuine dead ends
# (zero children). The other 52 are legitimate leaf nodes under a real, distinct topic
# name and are left untouched. Rule is structural (matches on "parent's label is also
# Minor subtopics"), not hardcoded IDs, so it stays correct if a future re-cluster
# changes which specific nodes this happens to.
# title= is used verbatim for BOTH the on-canvas headline (deliberately raw HTML, two
# styled spans for the bold+italic-serif pairing) AND the page's <title> tag
# (deckgl_template.html.jinja2 does <title>{{ title }}</title>, no escaping, no separate
# plain-text variant). Reported: the browser tab literally showed the raw
# "<span class=\"pa-headline..." markup. Fixed with a plain document.title override
# rather than passing a plain-text title= (which would have meant giving up the
# bold+serif pairing on the canvas headline entirely). Matches the "Paper Atlas · X"
# convention table.html/analytics.html already use for their <title> tags.
TAB_TITLE_JS = """
document.title = "Paper Atlas · Map";
"""

TOPIC_TREE_DEDUPE_JS = """
document.addEventListener('datamapLabelsLoaded', function(e) {
  const labelData = e.detail.labelData;
  const byId = {};
  labelData.forEach(function(d) { byId[d.id] = d; });
  function isMinorSubtopics(d) {
    return !!d && !!d.label && d.label.replace(/\\n/g, ' ').trim() === 'Minor subtopics';
  }
  labelData.forEach(function(d) {
    if (isMinorSubtopics(d) && isMinorSubtopics(byId[d.parent])) {
      const el = document.querySelector('[data-label-id="' + d.id + '"]');
      const li = el && el.closest('li');
      if (li) li.remove();
    }
  });
});
"""

hover_template = """
<div style="max-width:340px">
  <div style="font-weight:600;margin-bottom:4px">{title}</div>
  <div style="opacity:0.7;font-size:0.85em;margin-bottom:4px">{venue} {year}</div>
  <div style="opacity:0.6;font-size:0.8em;margin-bottom:4px">{authors}</div>
  <div style="opacity:0.5;font-size:0.78em;margin-bottom:8px">{breadcrumb}</div>
  <div style="font-size:0.9em;margin-bottom:8px">{snippet}</div>
  <a href="{url}" target="_blank" rel="noopener" style="color:#4da6ff">Read paper →</a>
</div>
"""

plot = datamapplot.create_interactive_plot(
    coords, label_strings, toplevel_strings, megacat_strings,
    hover_text=hover,
    extra_point_data=extra,
    hover_text_html_template=hover_template,
    # Brand now lives in the nav (nav_html), so the on-canvas title carries the actual
    # headline instead of repeating "Paper Atlas" a second time. title_text is inserted
    # UNESCAPED into the widget's span (confirmed via source), which is what makes the
    # bold-line/italic-serif-line pairing possible: two explicitly-styled child spans
    # instead of one plain string forced through a single font/size/weight.
    title=(
        f'<span class="pa-headline-strong">{len(titles_o):,} papers.</span>'
        '<br>'
        '<span class="pa-headline-serif">One living map.</span>'
    ),
    sub_title=f"{int(labels.max())+1} topics across NeurIPS · ICML · ICLR · ACL · EMNLP · NAACL, 2018-2026",
    # An earlier attempt set font_family="Inter" directly and got a console error
    # ("Font Inter did not load within 500ms"). Later found the SAME error fires for
    # the library's own DEFAULT font (Roboto) too, with or without any font_family
    # override, meaning it's a benign quirk in the library's internal JS load-check
    # under file://, not something that actually blocks fonts or breaks functionality
    # (everything else kept working around it all night). Deliberately NOT setting
    # font_family here to avoid poking that check differently; the actual visual font
    # comes entirely from CUSTOM_CSS's @import + !important overrides, which use the
    # browser's normal CSS font loading, a different, working path.
    # The map's cluster labels are deck.gl WebGL canvas text (TextLayer), not HTML.
    # Confirmed via datamap.js: fontFamily is a constructor prop feeding the TextLayer
    # directly, entirely separate from the page's CSS cascade. custom_css could only
    # ever style the surrounding chrome (search box, panels), never these labels,
    # which is almost certainly what looked unchanged. font_family is the real lever.
    font_family="Valley Sans",
    font_weight=600,
    cmap=COOL_CMAP,
    custom_css=CUSTOM_CSS,
    custom_html=CUSTOM_HTML,
    title_font_size=42,
    sub_title_font_size=15,
    noise_label="Unclustered",
    enable_search=True,
    search_field="search_text",
    enable_topic_tree=True,
    # font_size is set as an inline style on the tree's own container (confirmed via
    # topic_tree.js: `this.container.style.fontSize = this.fontSize`), not per-item, so
    # setting it here rather than fighting it from CSS keeps one source of truth for size.
    topic_tree_kwds={"font_size": "14px"},
    custom_js=SEARCH_POLISH_JS + "\n" + TOPIC_TREE_HIGHLIGHT_JS + "\n" + TOPIC_TREE_DEDUPE_JS + "\n" + TAB_TITLE_JS,
    # Clicking opens the paper directly. Originally relied on a link INSIDE the hover
    # tooltip, but moving the cursor from the point to the tooltip to click it made the
    # tooltip disappear first (the tooltip tracks point hover, not itself). on_click
    # avoids that whole class of problem.
    on_click="window.open(`{url}`, '_blank')",  # backticks needed: {url} becomes a JS
    # template-literal expression (${hoverData.url[index]}), which only interpolates
    # inside backticks: single quotes made it a literal string, which is what
    # produced the broken file:// URL with the raw placeholder text in it.
    # Three attempts to get here, verified server-side before shipping this time
    # (interactive_helpers.py:prepare_histogram_data branches on pandas DTYPE, not
    # string content): plain ints -> NUMERICAL -> SI-prefix format ("2.018k"). Bare
    # "2018" strings -> object dtype -> is_string_dtype()==True -> CATEGORICAL branch,
    # which silently ignores histogram_group_datetime_by AND removes brush/drag-select
    # entirely (d3_histogram.js:755). Plain ISO strings ("2018-01-01") are STILL object
    # dtype, same trap. pd.to_datetime() is required to get real datetime64 dtype,
    # which is what actually routes to generate_bins_from_temporal_data with year
    # grouping and keeps brush-select (only CATEGORICAL disables it).
    histogram_data=pd.to_datetime(pd.Series([f"{y}-01-01" for y in years_o])),
    histogram_n_bins=9,
    histogram_group_datetime_by="year",
    # Click a bar to LOCK the hover-filter behavior in place (click again to release).
    # This is a complete, tested feature already built into d3_histogram.js
    # (#handleClick, gated behind this exact flag): not something to hand-roll.
    histogram_enable_click_persistence=True,
    inline_data=True, darkmode=True,
)
plot.save("index.html")
print("wrote index.html")
