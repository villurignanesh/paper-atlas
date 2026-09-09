"""Shared site chrome: the logo mark and the floating nav pill, used identically across
index.html, table.html, and analytics.html. Previously each page's generator carried its
own literal copy of the logo SVG (three copies, which had already drifted once this
session when only two of the three had a bug fix applied); factored out once here so an
edit only ever needs to happen in one place.

Nav visual pattern is adapted from supaste.com (docs/design-reference-supaste.md):
a single floating pill, logo+wordmark left, page links right, current page shown
inverted (light-on-dark) instead of a generic active-underline, echoing how their pill
uses one light element (the CTA button) against an otherwise dark bar. Kept as our
existing translucent/blurred dark treatment rather than their flat solid black: the map
page's background is itself near-black, so a flat black pill would have no separation
from it, where their reference page is on a white background.
"""

LOGO_SVG = '''<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" class="pa-logo-icon">
  <line x1="8" y1="10" x2="16" y2="7" stroke="#6b6fb0" stroke-width="1.4" opacity="0.7"/>
  <line x1="16" y1="7" x2="24" y2="12" stroke="#8567a8" stroke-width="1.4" opacity="0.7"/>
  <line x1="8" y1="10" x2="10" y2="20" stroke="#3e8e8a" stroke-width="1.4" opacity="0.7"/>
  <line x1="16" y1="7" x2="18" y2="18" stroke="#3b5f8a" stroke-width="1.4" opacity="0.7"/>
  <line x1="24" y1="12" x2="18" y2="18" stroke="#6b6fb0" stroke-width="1.4" opacity="0.7"/>
  <line x1="10" y1="20" x2="18" y2="18" stroke="#3e8e8a" stroke-width="1.4" opacity="0.7"/>
  <line x1="10" y1="20" x2="17" y2="25" stroke="#8567a8" stroke-width="1.4" opacity="0.7"/>
  <line x1="18" y1="18" x2="17" y2="25" stroke="#3b5f8a" stroke-width="1.4" opacity="0.7"/>
  <circle cx="8" cy="10" r="3.1" fill="#3b5f8a"/>
  <circle cx="16" cy="7" r="2.5" fill="#3e8e8a"/>
  <circle cx="24" cy="12" r="2.8" fill="#6b6fb0"/>
  <circle cx="18" cy="18" r="3.4" fill="#8567a8"/>
  <circle cx="10" cy="20" r="2.3" fill="#3e8e8a"/>
  <circle cx="17" cy="25" r="2.6" fill="#3b5f8a"/>
</svg>'''

NAV_CSS = """
#pa-nav {
    position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
    z-index: 1000;
    display: flex; align-items: center; gap: 22px;
    background: rgba(15, 18, 26, 0.82); backdrop-filter: blur(14px);
    border: 1px solid rgba(107, 111, 176, 0.35);
    border-radius: 999px;
    padding: 7px 8px 7px 16px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
    font-family: var(--ui-font, "Valley Sans", -apple-system, sans-serif);
}
#pa-nav-brand {
    display: flex; align-items: center; gap: 8px;
    font-weight: 700; font-size: 14px; color: #e8e8f0; text-decoration: none;
    white-space: nowrap;
}
#pa-nav-brand svg { width: 20px; height: 20px; flex-shrink: 0; }
#pa-nav-links { display: flex; align-items: center; gap: 2px; }
.pa-nav-link {
    font-weight: 600; font-size: 13px; text-decoration: none;
    color: rgba(232, 232, 240, 0.62);
    padding: 7px 15px; border-radius: 999px;
    white-space: nowrap;
    transition: color 0.15s ease, background 0.15s ease;
}
.pa-nav-link:hover { color: #e8e8f0; }
.pa-nav-link.active { color: #0d0f14; background: #e8e8f0; }
.pa-nav-link.active:hover { color: #0d0f14; }
"""

_PAGES = [
    ("map", "index.html", "Map"),
    ("browse", "table.html", "Browse"),
    ("analytics", "analytics.html", "Analytics"),
    ("blog", "blog.html", "Blog"),
]


def nav_html(active: str) -> str:
    """active is one of 'map', 'browse', 'analytics', 'blog' -- the current page, shown inverted."""
    links = "".join(
        f'<a href="{href}" class="pa-nav-link{" active" if key == active else ""}">{label}</a>'
        for key, href, label in _PAGES
    )
    return (
        '<nav id="pa-nav">'
        f'<a href="index.html" id="pa-nav-brand">{LOGO_SVG}<span>Paper Atlas</span></a>'
        f'<div id="pa-nav-links">{links}</div>'
        '</nav>'
    )
