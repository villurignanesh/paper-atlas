# 016: Mobile layouts for Map, Browse, and Analytics (issue #10)

Date: 2026-11-11
Status: decided

## Context

At phone width the shared nav clips, the map controls compete with its headline,
Browse's columns run off-screen, and Analytics shrinks dense charts until their labels
are hard to read. The generated pages also lack a viewport meta tag.

## Options considered

- **Minimal pass:** add viewport sizing and a compact nav, then allow wide tables and
  charts to scroll. Fast, but Browse remains cramped and the map controls compete.
- **Page-specific layouts (chosen):** share a compact nav, then adapt each page to its
  content. More code, but each interaction remains usable on a phone.
- **Full mobile redesign:** rebuild all three pages around mobile use. More freedom,
  with substantially more scope than the current issue.

## Decision

At 640px and below, stack the nav and give Browse full-width controls and paper cards.
Keep sorting available through a mobile select. Show Analytics legends as wrapping
text, and keep charts readable by letting users scroll them horizontally at a fixed
minimum width. Tap opens tooltips. On the map, place search below nav, move the topic
tree to a bounded lower panel, and enlarge the visible zoom buttons. The map's
deck.gl controller already enables one-finger drag pan and pinch zoom by default;
the topic tree keeps vertical touch scrolling for its own list.

Issue #11's search and zoom controls are included through the parent branch. This
layout change does not alter search matching, projection, or clustering.

## Revisit if

- Device testing shows a map overlay intercepting a needed gesture.
- Readers need direct year filtering on phones; the library hides its histogram at
  narrow widths, so that would need a separate compact control.
- Analytics needs side-by-side comparisons on mobile rather than one scrollable view.
