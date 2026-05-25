# Creative Supply Engine Backlog

This directory is the active planning home for Creative Supply Engine.

Use backlog documents for current and future work. README notes, sample briefs, generated run logs,
and review galleries can provide evidence, but they should not become shadow planning systems.

## Source Of Truth

[Active Backlog](./ACTIVE_BACKLOG.md) and [Future Backlog](./FUTURE_BACKLOG.md) are the only
canonical work queues.

Other docs may contain decisions, setup notes, validation evidence, or historical context, but they
must not become separate backlog lists. If a run, review, or demo uncovers new work, do one of the
following in the same change:

- Add near-term work to [Active Backlog](./ACTIVE_BACKLOG.md) with priority, ownerable scope, and
  validation criteria.
- Add deferred or decision-bound work to [Future Backlog](./FUTURE_BACKLOG.md).
- Mark the finding `DONE / SUPERSEDED` with a short rationale if it is no longer valid.
- Keep validation-only checklists next to the feature only when they describe how to verify current
  behavior, not what to build next.

## Canonical Files

- [Active Backlog](./ACTIVE_BACKLOG.md): current product, demo, and packaging execution queue.
- [Future Backlog](./FUTURE_BACKLOG.md): deferred, long-range, or decision-bound work.
- [Backlog Archive](./archive/): completed and superseded execution boards.

## Rules

- Add new work to a backlog, not to scattered README notes or generated artifacts.
- Do not leave roadmap commitments, follow-up tasks, or open findings only inside run logs,
  review galleries, sample briefs, or ad hoc demo notes.
- Keep completed work out of the active queue unless it is needed as validation evidence.
- Keep the active queue short enough to force real priority tradeoffs.
- Move long-range ideas to the future backlog until they have a clear owner, validation path, and
  reason to beat the current queue.
