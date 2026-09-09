# Design reference: supaste.com

Captured via headless Chrome screenshots (WebFetch strips CSS/visual styling down to
markdown, so it can't answer a "what does this look like" question; the actual page was
rendered and inspected pixel-by-pixel instead). Notes below are measured from the
rendered page, not guessed from the HTML.

## Color palette

| Role | Value | Where |
|---|---|---|
| Nav / primary buttons / bold text | `#000000` | floating nav pill, CTA buttons, headline text |
| Page background / cards (bright) | `#FFFFFF` | body background, some card variants |
| Card background (muted) | `#F7F7F7` | alternating feature-card sections, FAQ pills, inactive tag pills |
| Hero/pricing gradient, top | `#2143C2` (approx, varies ~`#213FC2`-`#1966E3`) | top of hero and pricing section |
| Hero/pricing gradient, upper-mid | `#2394FE` | |
| Hero/pricing gradient, lower-mid | `#48AEFF` | |
| Hero/pricing gradient, bottom | `#8FDAFF` | fades into a photographic landscape image |
| Accent blue (active states) | ~`#1E88F5`-`#2094FE` | active filter pill, progress-bar fill |
| Star rating | warm amber/gold | testimonial 5-star rows |

The entire site is otherwise black/white/gray. Color is spent on exactly ONE thing: the
navy-to-sky-blue gradient, used twice (hero, pricing) as a deliberate "bookend," plus
photographic macOS-wallpaper-style imagery (green hills, wildflowers) that the gradient
fades into. Every other surface, including all data/feature content, stays monochrome.

## Typography

- **Headlines**: ultra-bold, rounded geometric sans, very tight tracking, large (looks
  like something in the Aeonik/General Sans/Clash Display family; self-host the exact
  match, don't guess the license). Used for every section heading, always centered.
- **One accent line per hero-style section**: an elegant italic serif (editorial/display
  style, e.g. "Reuse anytime." under the bold "Copy once."). This pairing, bold rounded
  sans + italic serif for exactly one emphasized phrase, is the single most distinctive
  typographic move on the page. Not used anywhere else on the page; it is reserved for
  the one moment it's meant to land.
- **Body text**: plain sans, regular weight, muted gray (light sections) or reduced-
  opacity white (dark/gradient sections), centered, short line lengths (~3 lines max per
  paragraph).
- **Small labels**: bold, small caps-ish sans, often preceded by a small icon.

## Layout and components

- **Floating pill nav**: black rounded-pill bar, NOT full-width (has margin on both
  sides), fixed to top. Logo mark (small rounded-square icon) + wordmark on the left,
  nav links centered/left-of-center in muted white, one white pill CTA button on the far
  right. This exact bar reappears on every internal page (confirmed via the Privacy
  Policy screenshot nested in one of the feature mockups), so it's a real reusable
  component, not a one-off hero decoration.
- **Alternating section rhythm**: white sections and `#F7F7F7` sections alternate down
  the page, each a large rounded-corner block (24-32px radius) containing a centered
  bold heading, a centered muted subtitle, and one supporting visual (screenshot mockup
  or icon grid). Consistent, repeating pattern, not bespoke layouts per section.
- **Product mockups**: real macOS UI screenshots (Mail, Figma, a dark clipboard-history
  panel) shown inside a realistic window frame, floating on the same landscape-photo
  background used in the hero. This is the site's way of keeping photographic warmth
  present throughout an otherwise monochrome page.
- **Pill tags/filters**: rounded pill buttons, `#F7F7F7` background + black text when
  inactive, solid black background + white text when active, small numeric badge
  alongside the label (e.g. "History 24").
- **Icon-badge grid**: circular white badge with a simple black line icon, bold heading
  below, 2-3 line muted description. Used for a persona grid (Designers / Developers /
  Content and Marketing / etc.) — 3-column, 2-row.
- **Testimonials**: 5 gold stars, a 2-4 line quote in muted gray, small circular avatar
  photo + bold name (+ role, when given). No card/border around it; just whitespace.
- **Social proof row**: a horizontal row of small circular monochrome "award" seals
  (Product Hunt, design-award badges), understated, not the visual focus.
- **Pricing card**: white rounded card floating on the gradient background, a small
  black pill "tab" overlapping its top edge (icon + product name), a segmented pill
  toggle (1/2/3 devices), a huge bold price with the original price struck through in
  gray beside it, a slim progress bar with a scarcity label ("5 spots left"), a checklist
  with circular checkmark icons, and a full-width black CTA button at the bottom.
- **FAQ accordion**: big bold two-line heading, centered subtext, then a 2-column grid
  of `#F7F7F7` pill rows, each with a "+" icon on the left and the question text.

## Overall read

Apple-marketing-page DNA: supremely confident oversized typography, huge whitespace,
an almost entirely monochrome chrome punctuated by exactly one recurring signature
gradient, and photographic macOS-wallpaper imagery bridging sections instead of stock
icons. Every corner is rounded, nothing has a hard border, and the page reads as "one
component (the rounded card) repeated with different content" rather than bespoke
sections. The restraint (one accent color, one accent font) is what makes it read as
premium rather than busy.

## What does and doesn't transfer to Paper Atlas

Paper Atlas is a data tool, not a funnel with a "buy" moment, so the pricing card,
"Download," and persona-marketing grid don't map onto anything we have. The transferable
part is the *visual system*, not the sales-page content:

- The floating black pill nav (logo + wordmark + links + one CTA) directly replaces our
  current scattered fixed-position elements (bottom-right wordmark we already removed,
  separate Analytics/Browse pill buttons) with one coherent component.
- Bold rounded sans (we already have Valley Sans) + one italic serif accent line is a
  cheap, high-impact typographic move we don't currently use anywhere.
- The alternating white/`#F7F7F7` card rhythm, generous radius, and centered
  heading+subtext pattern is a direct upgrade path for `table.html` and
  `analytics.html`, which currently read as more utilitarian panels than designed pages.
- The FAQ accordion pattern is a ready-made shape for the "About / methodology" panel
  that was floated earlier and never built (the technical detail trimmed from the map's
  subtitle).
- The icon-badge grid (circle badge + bold heading + description) is a good fit for an
  "how this map was built" section (embed → project → cluster → label, four cards).
- Color restraint: right now Paper Atlas's chrome inherits the same cool palette as the
  data visualization. Supaste's lesson is to separate the two, keep nav/cards/buttons
  monochrome, and let color live only in the data itself (which we already have, in the
  cluster colors) plus maybe one signature gradient moment of our own.
