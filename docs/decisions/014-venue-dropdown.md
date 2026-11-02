# 014: Venue dropdown on the mega-category trend chart (issue #4, Stage 2)

Date: 2026-10-29
Status: decided (presentation); thresholds unchanged from 013 (still PROVISIONAL)

## Context

013 added per-venue series to `analytics.json` and measured sample sizes: ACL, EMNLP and
NAACL have 61-83% of cells under 30 papers, ICLR/ICML/NeurIPS 0-9%. Stage 2 puts that on the
Analytics page. The task fixed the control (a dropdown: "All" plus each venue), the rules
(013's values, not new ones), and gaps / hidden / grey behaviour. No Phase 2-6 change, no GPU.

## Dropdown versus small multiples

- **Dropdown (chosen).** One chart at a time, at the size the existing chart already has.
  "All" stays exactly as it was (verified: its legend and chart markup are byte-identical
  to before). A phone shows one readable chart instead of six.
- **Small multiples (six panels).** Allows side-by-side comparison, which is what the issue
  motivates. Not chosen for this stage: six 7-line charts are unreadable at phone width, the
  y-axis would need to be shared to be comparable (the NLP venues reach ~90%, ML venues
  ~30%, flattening the ML panels), and most NLP-venue panels would be mostly hidden anyway.
- **Revisit if** the comparison "NeurIPS vs ACL" turns out to matter more than readability,
  or the maintainer wants a two-venue overlay.

## Presentation choices (judgment calls)

- **Pre-rendered SVG per venue, JS only toggles.** Thresholds are computed once, in Python,
  in one block at the top of `build_analytics_page.py`. Cost: page weight (see PR). The
  alternative, drawing in JS from JSON, would be lighter but would put a second renderer
  next to the Python one.
- **Same top-6 + "Other" set for every venue** (013), with the same colour for the same area
  in every venue view. "Other" is a dashed line so it reads as a remainder.
- **Hidden points break the line**, as do venue-years that do not exist (NAACL 2020, 2023).
  A line through a hidden point would imply a value the rule says is unreliable. A
  segment touching a grey point is drawn grey and dashed.
- **Per-view y-axis**, as the existing chart does (max of what is drawn). Switching venue
  therefore changes the axis; it is labelled on every view. A fixed 0-100% axis was rejected
  because it flattens the ML venues.
- **Denominator shown under the x-axis** (n = labelled papers per year, "-" where the venue
  did not run), and in the tooltip as "k of n labelled papers".

## Thresholds

No change. 013's proposed values are used as-is: hide when the 95% Wilson half-width exceeds
100% of the point's own share (a zero count is always hidden), grey above 50%. They remain
provisional pending the maintainer. They are named constants in one place.

One NEW number was needed, not in 013: the note "this level cannot resolve trends here" shows
when more than **half** of a venue's points are hidden or grey (`NOTE_FRACTION = 0.5`). It is
a judgment call. "Hidden" alone would not trigger it for any venue (30.4 / 28.6 / 47.6% for ACL
/ EMNLP / NAACL), so the count is hidden **plus** grey (62.5 / 60.7 / 71.4%). ICLR is 7.1%, ICML and
NeurIPS 0%.

## What would make us revisit

- The maintainer changes the 013 thresholds (edit the constants, rebuild).
- Page weight matters more than the pre-render simplicity (move to JS rendering).
- A finer category level for the NLP venues (013 follow-up), which would change which points
  are hidden.
