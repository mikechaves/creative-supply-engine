# Active Backlog

> Current execution queue for Creative Supply Engine.

_Current as of: 2026-05-24_

---

## Scope

This file is the canonical backlog for work we are willing to start next.

Rules:

- Keep this file short enough to make real priority tradeoffs.
- Add only work that has a clear owner, validation path, or decision gate.
- Move completed work to an archive or decision note instead of leaving `DONE` rows here.
- Keep broad wishlist or long-range ideas in [Future Backlog](./FUTURE_BACKLOG.md).
- Do not treat follow-up sections in README files, generated run logs, output galleries, or sample
  briefs as a work queue. Promote them here or park them in Future Backlog before acting.

## Current Product Posture

- Creative Supply Engine is a local proof of concept for reuse-first campaign creative generation.
- The current CLI can load a YAML campaign brief, reuse or generate product hero assets, produce
  localized ratio variants, write a run log, and generate a browser-friendly review gallery.
- The strongest near-term work is demo reliability: setup clarity, deterministic validation,
  output inspection, and asset/provenance hygiene.
- Large platform features such as approval workflows, hosted dashboards, and multi-brand campaign
  operations remain deferred until the local CLI demo is repeatable and easy to evaluate.

## Priority Legend

- `P0`: Blocks setup, demo reliability, trust, compliance, or basic product validation.
- `P1`: Near-term product usefulness or operational leverage.
- `P2`: Worth shaping, but not allowed to displace P0/P1 work without an explicit decision.
- `RESEARCH`: Needs a product or architecture decision before implementation.

## Active Workboard

| Priority | Area              | Item                                                                 | Status | Validation / Exit Criteria                                                                                                                                      |
| -------- | ----------------- | -------------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0       | Asset Hygiene     | Prevent accidental tracked asset drift during local demo runs.        | TODO   | Demo instructions and tests make clear which generated files are ignored, which reusable assets are tracked, and how to reset generated heroes without deleting required brand assets. |
| P1       | Review Gallery    | Improve review gallery status visibility for provenance and warnings. | TODO   | Gallery clearly distinguishes reused, generated, and placeholder hero assets; warning counts are visible per localized set; missing logo and placeholder states are easy to spot. |
| P1       | Brief Authoring   | Add brief validation feedback for common authoring mistakes.          | TODO   | Malformed or incomplete briefs return actionable field-level messages for missing brand colors, products, markets, logo paths, and unsupported locale/ratio assumptions. |
| P1       | Output Packaging  | Add an optional review bundle export.                                | TODO   | A command can package final creatives, `run_log.json`, `index.html`, and source brief into a shareable ZIP without including `.env`, caches, or untracked source assets. |
| P2       | CI                | Add lightweight CI for install, tests, and sample placeholder run.    | TODO   | GitHub Actions or equivalent validates Python version support, editable install, unit tests, and a no-key sample run on every push. |
| P2       | Product Direction | Decide whether CSE stays CLI-only or gains a local web review UI.     | RESEARCH | Decision note compares CLI plus static gallery against a small local web app, including demo value, implementation cost, and maintenance risk. |

## Deferred

The following remain intentionally non-active:

- Hosted campaign dashboard.
- Multi-user approval and commenting workflow.
- Multi-brand asset library.
- Marketplace or agency workflow integrations.
- Paid packaging or distribution strategy.
- Advanced model/provider routing beyond the current OpenAI image generator abstraction.

See [Future Backlog](./FUTURE_BACKLOG.md) for the full parking lot.

## Evidence

- [Completed Demo Reliability Backlog](./archive/COMPLETED_DEMO_RELIABILITY_BACKLOG_2026-05.md)
- [Completed Setup Backlog](./archive/COMPLETED_SETUP_BACKLOG_2026-05.md)
- [Project README](../../README.md)
- [Sample Campaign Brief](../../briefs/campaign.yaml)
- Generated run logs under `outputs/<campaign-slug>/run_log.json`
- Generated review galleries under `outputs/<campaign-slug>/index.html`
