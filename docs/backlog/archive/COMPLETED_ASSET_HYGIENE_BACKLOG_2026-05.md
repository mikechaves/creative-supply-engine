# Completed Asset Hygiene Backlog - May 2026

> Completed asset-hygiene work moved out of the active backlog.

_Current as of: 2026-05-24_

---

## Completed Work

| Priority | Area          | Item                                                          | Status | Evidence                                                                                                                                                                                                 |
| -------- | ------------- | ------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0       | Asset Hygiene | Prevent accidental tracked asset drift during local demo runs. | DONE   | `assets/oat-energy-bar/hero.*` is ignored as generated sample state, `pulse-cse-reset-sample` removes generated sample heroes without deleting tracked logo/citrus assets, and README documents tracked vs generated files. |

## Validation

- `git diff --check`
- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m unittest discover -s tests -v`
- `.venv/bin/pulse-cse-reset-sample`
- `.venv/bin/pulse-cse-smoke`
