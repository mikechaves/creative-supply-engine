# Active Backlog

> Current execution queue for Creative Supply Engine.

_Current as of: 2026-05-31_

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
- Setup, smoke validation, packaging, CI, and the CLI/static-gallery product direction are now in
  place.
- The strongest near-term work is local operator usefulness and trust: faster output inspection,
  environment/asset diagnostics, and explainable brand-safety validation.
- Large platform features such as approval workflows, hosted dashboards, and multi-brand campaign
  operations remain deferred until the local CLI demo is repeatable and easy to evaluate.

## Priority Legend

- `P0`: Blocks setup, demo reliability, trust, compliance, or basic product validation.
- `P1`: Near-term product usefulness or operational leverage.
- `P2`: Worth shaping, but not allowed to displace P0/P1 work without an explicit decision.
- `RESEARCH`: Needs a product or architecture decision before implementation.

## Active Workboard

| Priority | Area                | Item                                                                      | Status | Validation / Exit Criteria                                                                                                                                       |
| -------- | ------------------- | ------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1       | Review Gallery      | Add gallery filters for product, locale, ratio, provenance, and warnings. | TODO   | `pulse-cse-smoke` generates a static gallery with filter controls; tests cover filter metadata and HTML escaping for filtered values.                             |
| P1       | Diagnostics         | Add a `pulse-cse doctor` command for environment and asset checks.         | TODO   | Console script reports Python/package status, project root, sample brief/logo/asset state, and OpenAI key presence without exposing secrets; unit tests cover OK and missing-asset paths. |
| P1       | Brand Safety        | Add safe-area validation for supported output ratios.                      | TODO   | Unit tests exercise pass/fail safe-area cases; generated `run_log.json` and the review gallery surface safe-area warnings per ratio without blocking placeholder runs. |

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

- [Completed CI Backlog](./archive/COMPLETED_CI_BACKLOG_2026-05.md)
- [Completed Product Direction Backlog](./archive/COMPLETED_PRODUCT_DIRECTION_BACKLOG_2026-05.md)
- [CLI Plus Static Review Gallery Decision](../decisions/CLI_VS_LOCAL_WEB_REVIEW_UI_2026-05.md)
- [Completed Output Packaging Backlog](./archive/COMPLETED_OUTPUT_PACKAGING_BACKLOG_2026-05.md)
- [Completed Brief Authoring Backlog](./archive/COMPLETED_BRIEF_AUTHORING_BACKLOG_2026-05.md)
- [Completed Review Gallery Backlog](./archive/COMPLETED_REVIEW_GALLERY_BACKLOG_2026-05.md)
- [Completed Asset Hygiene Backlog](./archive/COMPLETED_ASSET_HYGIENE_BACKLOG_2026-05.md)
- [Completed Demo Reliability Backlog](./archive/COMPLETED_DEMO_RELIABILITY_BACKLOG_2026-05.md)
- [Completed Setup Backlog](./archive/COMPLETED_SETUP_BACKLOG_2026-05.md)
- [Project README](../../README.md)
- [Sample Campaign Brief](../../briefs/campaign.yaml)
- Generated run logs under `outputs/<campaign-slug>/run_log.json`
- Generated review galleries under `outputs/<campaign-slug>/index.html`
