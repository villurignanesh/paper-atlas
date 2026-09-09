"""Blog page: renders blog/paper-atlas-launch.md into the site's own visual language
(same dark glass panel, Valley Sans, nav pill as index/table/analytics) instead of
linking out to a raw markdown file on GitHub. A minimal hand-rolled markdown-to-HTML
pass, not a dependency: the input is one file we author ourselves, not arbitrary
user markdown, and it only ever needs to handle the handful of constructs actually
used in that file (h1/h2, bold, italic, inline code, links, bullet lists, paragraphs),
so pulling in a general markdown library would be a dependency for five regexes.
"""
import html
import re
from nav import NAV_CSS, nav_html

SRC = "blog/paper-atlas-launch.md"
raw = open(SRC).read()


def inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r'<code>\1</code>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r'<strong>\1</strong>', text)
    text = re.sub(r"\*([^*]+)\*", r'<em>\1</em>', text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        text,
    )
    return text


def render(md):
    lines = md.split("\n")
    out, para, list_items = [], [], []
    in_list = False

    def flush_para():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    def flush_list():
        nonlocal in_list
        if list_items:
            out.append("<ul>" + "".join(f"<li>{inline(li)}</li>" for li in list_items) + "</ul>")
            list_items.clear()
        in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            flush_list()
        elif stripped.startswith("## "):
            flush_para()
            flush_list()
            out.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            flush_para()
            flush_list()
            out.append(f"<h1>{inline(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            flush_para()
            list_items.append(stripped[2:])
            in_list = True
        elif in_list:
            # Indented continuation of the current list item (source wraps long bullet
            # text across lines at 2-space indent), not a new paragraph.
            list_items[-1] += " " + stripped
        else:
            para.append(stripped)
    flush_para()
    flush_list()
    return "\n".join(out)


body_html = render(raw)
# Byline injected right after the rendered <h1> (source markdown's own first line),
# not floated above it, so reading order is title-then-date like any normal post.
DATE = "September 2026"
h1_close = body_html.index("</h1>") + len("</h1>")
body_html = (
    body_html[:h1_close]
    + f'\n<div class="byline">{DATE}</div>'
    + body_html[h1_close:]
)

PAGE = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Paper Atlas &middot; Blog</title>
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
.post {{
    background: var(--panel); backdrop-filter: blur(8px);
    border: 1px solid rgba(107,111,176,0.35); border-radius: 12px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    padding: 48px; max-width: 720px; margin: 0 auto;
}}
.post .byline {{ opacity: 0.55; font-size: 13px; margin: -8px 0 32px; }}
.post h1 {{
    font-weight: 700; font-size: 30px; line-height: 1.28; margin: 0 0 4px;
}}
.post h2 {{
    font-weight: 600; font-size: 20px; margin: 40px 0 12px;
}}
.post p {{ line-height: 1.65; font-size: 15.5px; margin: 0 0 18px; opacity: 0.92; }}
.post ul {{ margin: 0 0 18px; padding-left: 22px; }}
.post li {{ line-height: 1.6; font-size: 15.5px; margin-bottom: 10px; opacity: 0.92; }}
.post a {{ color: #9a9de0; text-decoration: none; border-bottom: 1px solid rgba(154,157,224,0.35); }}
.post a:hover {{ border-bottom-color: #9a9de0; }}
.post code {{
    background: rgba(107,111,176,0.18); border-radius: 4px; padding: 1px 6px;
    font-family: "SF Mono", Menlo, monospace; font-size: 0.88em;
}}
</style>
</head>
<body>
{nav_html("blog")}
<article class="post">
{body_html}
</article>
</body>
</html>
'''

open("blog.html", "w").write(PAGE)
print(f"wrote blog.html ({len(PAGE)} bytes)")
