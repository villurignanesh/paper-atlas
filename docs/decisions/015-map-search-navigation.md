# 015: Search navigation on the map (issue #11)

Date: 2026-11-11
Status: decided

## Context

The map highlights text matches but leaves the viewport where it was. A broad query
can match papers across the entire projection, so fitting every result while the user
types would often move the view away from the area they were exploring.

## Options considered

- **Always fit all matches.** Simple, but broad queries repeatedly zoom out.
- **Automatically focus compact results; offer an explicit action for broad results
  (chosen).** Precise searches become convenient without surprising movement for
  scattered matches. The extra action keeps broad results reachable.
- **Show a results list and move only after choosing a paper.** More control, but a
  larger search redesign than the current interaction issue requires.

## Decision

After a short pause in typing, automatically fit at most 12 matches when their bounding
box spans no more than 15% of the corpus extent on either axis. Otherwise show a
"Zoom to matches" action. Clearing search leaves the current view in place. These
numbers control navigation behavior, not search ranking or clustering; revisit them
after observing actual queries.

Put search below the floating navigation and add a visible slider with plus/minus
controls. Keep the underlying substring matching unchanged; semantic search is issue
#9 and needs its own measured design decision.

## Revisit if

- Broad searches usually target one cluster and users expect automatic movement.
- Mobile layout work in issue #10 needs a different control placement.
- Search gains ranked results or semantic retrieval, which can identify a single
  result to focus even for broad queries.
