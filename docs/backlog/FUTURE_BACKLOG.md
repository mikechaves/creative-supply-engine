# Future Backlog

> Deferred and long-range backlog programs that are not in the active execution queue.

_Current as of: 2026-05-31_

---

## Scope

This file is the parking lot. It should not be treated as a commitment to build everything here.
Move items into [Active Backlog](./ACTIVE_BACKLOG.md) only after they have a clear owner,
validation path, and reason to beat the current queue.

If another doc records a follow-up, finding, or proposed roadmap item, it must also appear here or in
[Active Backlog](./ACTIVE_BACKLOG.md). Otherwise it is context, not work.

## Campaign And Brief Expansion

- [ ] Support multiple campaign briefs in one batch run.
- [ ] Add campaign-level output manifests for cross-product comparison.
- [ ] Add custom ratio definitions in the YAML brief.
- [ ] Add per-market legal disclaimers to final creative overlays when required.
- [ ] Add optional campaign-level art direction presets.
- [ ] Add product-level reusable asset metadata beyond `hero.png`.
- [ ] Add locale-aware typography and text-length checks for overlay fit.

## Asset And Generation Pipeline

- [ ] Add reusable asset versioning and provenance history.
- [ ] Add support for alternate hero asset filenames and product image sets.
- [ ] Add model/provider abstraction beyond the current OpenAI image generator.
- [ ] Add generation retry policy with clearer API error classification.
- [ ] Add image quality scoring or manual review flags for generated heroes.
- [ ] Add background removal or product cutout support if reusable assets need compositing.
- [ ] Add deterministic fixture images for richer visual regression tests.

## Review And Collaboration

- [ ] Add side-by-side comparison views in the static review gallery.
- [ ] Add reviewer notes or approval metadata without requiring a hosted service.
- [ ] Add exportable creative QA report in Markdown or PDF.
- [ ] Add thumbnail contact sheet generation for quick stakeholder review.
- [ ] Reconsider a local web UI only after static gallery usage exposes real workflow limits,
      per the [CLI plus static gallery decision](../decisions/CLI_VS_LOCAL_WEB_REVIEW_UI_2026-05.md).

## Packaging And Distribution

- [ ] Publish the CLI as an installable internal package once setup smoke tests are stable.
- [ ] Add release notes and versioning guidance for CLI releases.
- [ ] Add a cleanup command for ignored outputs and generated placeholder assets.
- [ ] Add sample data reset command for demo rehearsals.
- [ ] Add Homebrew or `pipx` install guidance if the tool graduates beyond repo-local usage.

## Compliance And Brand Safety

- [ ] Expand prohibited-word checks beyond campaign headline text.
- [ ] Add logo placement collision checks against overlay panels.
- [ ] Add configurable brand compliance rules per campaign.
- [ ] Add evidence fields for legal review and marketing approval status.
- [ ] Add accessibility-oriented contrast checks for text overlays.

## Hosted Or Team Workflows

- [ ] Evaluate hosted dashboard for campaign upload, run history, and review.
- [ ] Add authenticated multi-user review workflow if stakeholder collaboration becomes core.
- [ ] Add cloud storage export for final creative bundles.
- [ ] Add CMS or DAM integration for reusable brand assets.
- [ ] Add notification hooks for completed runs.
- [ ] Add audit logs if multiple operators share the same campaign workspace.

## Strategic Framing

### Tier 1: Local Demo Reliability

- Setup works for a clean checkout.
- Placeholder mode and live generation mode are both easy to validate.
- Outputs are inspectable without reading JSON.

### Tier 2: Campaign Operator Usefulness

- Briefs are easy to author and debug.
- Assets are reused safely.
- Outputs are packageable and reviewable.

### Tier 3: Team Workflow

- Approvals, notes, bundles, and run history become structured.
- Compliance checks become explainable and repeatable.

### Tier 4: Platform Expansion

- Hosted dashboards, integrations, and multi-brand workflows only become active after local workflow
  evidence justifies the added complexity.

---

_For current execution, see [Active Backlog](./ACTIVE_BACKLOG.md)._
