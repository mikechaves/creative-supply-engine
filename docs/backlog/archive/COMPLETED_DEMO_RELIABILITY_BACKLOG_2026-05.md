# Completed Demo Reliability Backlog - May 2026

> Completed demo-reliability work moved out of the active backlog.

_Current as of: 2026-05-24_

---

## Completed Work

| Priority | Area             | Item                                                               | Status | Evidence                                                                                              |
| -------- | ---------------- | ------------------------------------------------------------------ | ------ | ----------------------------------------------------------------------------------------------------- |
| P0       | Demo Reliability | Add a repeatable smoke/demo command for placeholder and live modes. | DONE   | `pulse-cse-smoke` copies sample inputs to a temp project, runs placeholder mode without mutating tracked assets, verifies creative outputs, `run_log.json`, and `index.html`, and supports explicit `--live` validation. |

## Validation

- `git diff --check`
- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m unittest discover -s tests -v`
- `.venv/bin/pulse-cse-smoke`
