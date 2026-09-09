# UI implementation notes: mistakes made, and the rule that prevents each

Kept separate from `docs/decisions/` deliberately: those are methodology tradeoffs
(which embedding model, how clusters are built). These are implementation-care
mistakes: things that were simply done sloppily and are worth not repeating,
independent of any design decision.

## 1. `<input type="search">` has a native clear button. Always suppress it.

Safari and Chrome both render a built-in "×" via `::-webkit-search-cancel-button` on
any `type="search"` input. Add a custom clear button without suppressing the native one
and you get **two**, which is exactly what shipped on the map's search box while
`table.html`'s (built moments earlier) correctly had the suppression. The fix was
applied to one input and never checked against the other.

**Rule going forward:** any `type="search"` input gets this CSS by default, written at
the same time the input is created, not as an afterthought:
```css
input[type=search]::-webkit-search-cancel-button,
input[type=search]::-webkit-search-decoration { display: none !important; -webkit-appearance: none !important; }
```

## 2. Don't give a nested element its own border when the parent already has one.

The search input sat inside `#search-container`, which already has
`border + border-radius` from `.container-box`. The input *also* had its own
`border + border-radius`. Two nested rounded rectangles read as a visual glitch, not a
deliberate style: this is what "the border looks weird" was.

**Rule going forward:** one element owns the visible chrome (border, radius,
background). Everything nested inside it is `border: none; background: transparent;`
and fills the parent. Decide which element owns the chrome *before* writing any CSS,
not after something looks off.

## 3. CSS edited incrementally across a session accumulates stale, conflicting rules.

The map's search input had **three separate `#text-search { }` blocks** by the time this
was caught: an early one-off `padding-right: 56px`, a later full redesign that
recalculated padding as `68px` via the shorthand, and the old 56px rule was never
removed. Because it appeared *later* in the file, it silently won the CSS cascade over
the new, correct value. The padding fix I was confident about was never actually
applied.

**Rule going forward:** after editing a selector's styling more than once in a session,
`grep` for every occurrence of that selector before considering the change done. A
"new" rule does not remove an old one; CSS is additive, and nothing prunes the losers of
a cascade automatically.

## 4. Don't guess exact pixel spacing against text you can't see rendered.

Padding was calculated by estimating icon/button widths and picking a number, without
any way to confirm the input's actual rendered width. When wrong, the safe fallback is
shorter text ("Search...") rather than continuing to tune padding numbers against an
unknown. Precision was never available, so the design should have assumed that
from the start rather than acting as if a specific pixel value was reliable.

## 5. General

When there is no way to visually verify a change (no browser access), treat every
"should work" as unconfirmed until the user reports back. And when they do report a
bug, audit *every* similar element on the site for the same class of mistake before
re-shipping, not just the one that was reported.

## 6. A widget library's own injected CSS is an extra source of truth, not just yours.

`SearchWidget` self-injects `#{container_id} { width: fit-content; }` as a rule
separate from any custom CSS passed in. The search box's excess height was chased
through the library's stylesheet (`.container-box` padding, `.stack` flex layout)
without ever being conclusively pinned to one cause. The fix that shipped,
`#search-container { padding: 4px !important; height: auto !important; }`, is a
direct override, not a traced root cause, and was reported to the user as such rather
than as a confirmed diagnosis.

**Rule going forward:** when a container is styled by both a third-party widget and
custom CSS, don't assume the custom CSS is the only thing controlling its box model.
Grep the library's own stylesheet for the same selector before concluding a fix is
complete. And when a root cause genuinely can't be pinned down, say so plainly instead
of presenting a targeted override as if it were a diagnosis.
