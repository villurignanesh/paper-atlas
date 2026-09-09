# Contributing to Paper Atlas

Thanks for looking at this. A few things about how this repo works, so your first PR
doesn't need three rounds of "actually, here's why we didn't do it that way."

## Read the decision logs first

`docs/decisions/` is the actual history of this project: every non-trivial choice
(which embedding model, how clusters are built, why one source was picked over
another) is written up there, with the options considered, what was chosen, why, and
what would change the decision. Before touching a phase, read the relevant log. Before
*proposing* a change to a phase, check whether it's already been tried and rejected.
Several approaches in `011-clustering.md` in particular were tested and abandoned for
measured, not assumed, reasons.

**If you make a non-trivial decision in your PR, add a log entry for it**, same format
as the existing ones: context, options considered, what you chose, why, what would
make you revisit it. This is the single most important convention in this repo. It's
what makes the project reproducible and defensible, not just working.

## Local setup

```bash
uv sync          # installs the project's Python environment
```

Data (`data/`) is gitignored and not checked in; you'll need to run the ingestion
adapters yourself (`paper_atlas/adapters/`) to build a local corpus, or ask in an issue
if you need a copy of the processed Parquet files for development.

## The GPU / remote-job pattern

Several phases (embedding, projection, clustering) are compute-heavy enough that they
were run on a remote GPU box during development, not the author's laptop
(`docs/compute.md` has the reasoning; the honest summary is a 4096-dim embedding over
70k+ papers is a bad time on 8GB of unified memory). The `remote_jobs/` directory holds
self-contained scripts meant to be pushed to *any* GPU machine and run there. They
don't depend on the rest of this package, only on the normalized Parquet files.

If you have GPU access: `remote_jobs/RUN.md` shows the push → run → pull pattern.
Genericize the hostnames to your own machine. The ones in earlier project history
pointed at a specific university lab box and have been scrubbed from this public
version.

If you don't: most experiments are still doable on CPU at reduced scale (subsample the
corpus, use a smaller embedding model). Say so in your PR and it's a fine tradeoff for
a first pass.

## Before proposing changes to Phases 2-6

Embedding model choice, projection settings, clustering approach, and evaluation
methodology are all *measured* decisions with numbers behind them, not defaults. If you
think one should change, the strongest PR includes a comparison: old approach vs. new,
on the same data, not just an assertion that the new approach is generally better.
This project's whole ethos is "measure, don't guess" (see the noise-baseline and
seed-stability work in `docs/decisions/003-success-criteria.md` and
`011-clustering.md` for what that looks like in practice). PRs are held to the same
bar.

## Task backlog

`future_work.md` has scoped-out tasks with suggested approaches and open questions,
roughly ordered by difficulty within each item. Good first issues are marked as such.
If you want to take one on, comment on the corresponding issue (or open one if it
doesn't exist yet) before starting; some of these have real architectural forks in
them worth agreeing on before writing code.

## Long-term direction

[papercopilot.com](https://papercopilot.com) is the closest thing to a scale reference
for where this project could grow: submission/acceptance statistics, reviewer score
dynamics, institution rankings, live-updated, at a similar corpus size. It does **not**
have a semantic content map; that's this project's actual differentiator and isn't
something later tasks should trade away in pursuit of feature parity. Tasks 6-8 in
`future_work.md` are the direct Paper-Copilot-inspired additions (institution rankings,
submission/acceptance rates, review-and-rebuttal analytics), each is scoped as its own
significant undertaking, not a quick add-on, because each needs data this project does
not currently collect. Read the "why this is hard" section of each before starting one.

## What a good PR looks like here

- Cites the relevant decision log(s) it builds on or changes.
- If it changes methodology (not just UI/tooling), includes before/after numbers.
- Adds its own decision log entry if it made a non-trivial call.
- Doesn't silently widen scope: if you notice something else that's broken while
  working on your task, mention it in the PR description rather than fixing it inline,
  unless it's trivial.
