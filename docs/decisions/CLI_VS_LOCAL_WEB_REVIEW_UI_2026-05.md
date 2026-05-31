# Decision: CLI Plus Static Review Gallery

> Product direction decision for whether Creative Supply Engine should stay CLI-only or add a
> local web review UI.

_Decision date: 2026-05-31_

---

## Status

Accepted.

Creative Supply Engine should stay CLI-first with a static review gallery for the current local
proof-of-concept phase. Do not build a local web review UI yet.

## Context

The current product is a local proof of concept for reuse-first campaign creative generation. It can:

- load a YAML campaign brief,
- reuse or generate product hero assets,
- produce localized ratio variants,
- write `run_log.json`,
- generate a browser-friendly static review gallery,
- package final review artifacts into a shareable ZIP.

Recent completed work strengthened the static path:

- setup and smoke demo validation are repeatable,
- sample asset reset is safe,
- review gallery status now exposes provenance, warnings, placeholder states, and logo issues,
- brief authoring errors are field-level and actionable,
- review bundles can be exported without secrets, caches, or source assets.

The remaining question is whether a small local web app would add enough review value to justify
new runtime and maintenance cost.

## Options

### Option A: CLI Plus Static Gallery

Keep the current CLI as the primary workflow and continue improving the static `index.html` gallery
and ZIP bundle.

Demo value:

- Works from a clean checkout with a Python virtual environment.
- Produces tangible artifacts that can be opened, zipped, shared, or archived.
- Keeps the review experience close to the generated assets and run log.
- Avoids requiring a separate local server during demos.

Implementation cost:

- Low. Improvements stay inside the existing Python CLI, HTML writer, and tests.
- Existing smoke tests can validate most behavior.
- No new frontend build stack, state model, API server, routing, or browser automation baseline.

Maintenance risk:

- Low. The static gallery is deterministic output, not a live app.
- Fewer moving parts means fewer setup failures for a local proof of concept.
- Review bundle boundaries stay explicit and auditable.

### Option B: Small Local Web Review UI

Add a local web app for review, filtering, approvals, notes, and run navigation.

Demo value:

- Could support richer interactions, especially filtering, side-by-side comparison, reviewer notes,
  and approval metadata.
- Could make repeated review sessions more ergonomic if campaign volume grows.

Implementation cost:

- Medium to high. Even a small local app needs a server command, routing, asset serving, UI state,
  error handling, tests, and setup documentation.
- It adds another runtime surface to a repo whose current strongest need is reliable local demo
  execution.

Maintenance risk:

- Medium. The app would need to stay aligned with output folder structure, run-log schema, review
  gallery semantics, and packaging behavior.
- It risks becoming a parallel product surface before there is enough evidence that static review
  is insufficient.

## Decision

Stay CLI-first and keep the static gallery as the review surface for now.

This is the right default because CSE is still proving a local campaign-generation workflow. The
static gallery and package export already cover the core demo questions:

- What was generated?
- Which assets were reused, generated, or placeholders?
- Were there warnings or logo/compliance issues?
- Where are the final files?
- Can the review package be shared without leaking local secrets or source assets?

A local web UI should not displace near-term work until static review usage exposes real workflow
limits that cannot be solved with static HTML, better bundles, or small CLI improvements.

## Reopen Criteria

Reconsider a local web review UI only if at least one of these becomes true:

- reviewers need persistent notes, approvals, or assignment state across runs;
- campaign volume makes static HTML scanning inefficient even after filters/contact sheets;
- demos require live navigation across many historical runs;
- operators need interactive edits before approving or packaging outputs;
- team workflows become active enough to justify a server-backed local or hosted surface.

Until then, local web UI work remains deferred.

## Follow-Up Placement

Keep deferred interaction ideas in [Future Backlog](../backlog/FUTURE_BACKLOG.md), especially under
Review And Collaboration and Hosted Or Team Workflows. Do not add local web UI implementation tasks
to the active backlog without a new decision or concrete workflow evidence.
