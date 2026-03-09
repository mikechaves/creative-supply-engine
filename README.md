# Creative Supply Engine

Creative Supply Engine is a local-first Python CLI that turns a structured campaign brief into reusable social creative outputs.

The proof of concept is intentionally simple:

- load a YAML brief
- reuse existing local product hero assets when available
- generate missing hero assets through a thin OpenAI image wrapper
- fall back to a labeled placeholder when generation fails
- produce final creatives in `1:1`, `9:16`, and `16:9`
- overlay the campaign message with a deterministic bottom-banner treatment
- save outputs into a clean folder structure
- write a concise `run_log.json`

## Project Overview

This project demonstrates a reuse-first creative automation pipeline for social marketing assets. The main design choice is to prioritize clarity over flexibility:

- the CLI is the only interface
- the pipeline runs sequentially in one readable flow
- local folders are the system of record for inputs, reusable assets, and outputs
- OpenAI image generation is isolated behind an image generator interface so the pipeline can swap providers later without changing the orchestration code
- the live provider uses the OpenAI Images API with a single prompt-based generation call sized for downstream social crops

## 60-Second Walkthrough

If you need to explain the project quickly in an interview, the clean walkthrough is:

1. `brief_loader.py` loads the YAML brief and validates the required campaign fields and product list.
2. `main.py` checks each product for a reusable local hero asset in `assets/` before doing any generation.
3. If a hero is missing, `image_generator.py` calls OpenAI behind a small provider interface; if that fails, the pipeline uses a runtime-only placeholder and keeps going.
4. `creative_builder.py` creates the `1:1`, `9:16`, and `16:9` variants, and `overlay.py` adds the campaign message with a fixed bottom-banner treatment.
5. The run writes final images into `outputs/` and records provenance, warnings, and output paths in `run_log.json`.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` if you want to test live OpenAI generation:

```bash
cp .env.example .env
```

## Environment Variables

The CLI uses `python-dotenv` to load environment variables from `.env`.

Required for live OpenAI image generation:

- `OPENAI_API_KEY`

Optional:

- `OPENAI_IMAGE_MODEL` to override the default image model
  - default: `gpt-image-1.5`
  - lower-cost alternative: `gpt-image-1-mini`

If `OPENAI_API_KEY` is missing, or the OpenAI request fails, the pipeline continues with a generated placeholder image for that run.

## How To Run

Use the sample brief:

```bash
python -m src.main
```

Use the deterministic fallback demo path:

```bash
make demo
```

Use the live provider path when `OPENAI_API_KEY` is configured:

```bash
make demo-live
```

If you previously generated a reusable hero for `oat-energy-bar`, delete
`assets/oat-energy-bar/hero.png` before rerunning `make demo-live` so the sample
demo shows the missing-asset generation path again.

Use a custom brief:

```bash
python -m src.main --brief briefs/campaign.yaml
```

Run tests:

```bash
python -m unittest discover -s tests
```

Or use:

```bash
make test
```

## Sample Input And Output Structure

```text
creative-supply-engine/
├── briefs/
│   └── campaign.yaml
├── assets/
│   ├── citrus-sparkling-water/
│   │   └── hero.png
│   ├── oat-energy-bar/
│   └── common/
├── outputs/
│   └── summer-citrus-reset/
│       ├── citrus-sparkling-water/
│       │   ├── 1x1/
│       │   │   └── final.png
│       │   ├── 9x16/
│       │   │   └── final.png
│       │   └── 16x9/
│       │       └── final.png
│       ├── oat-energy-bar/
│       └── run_log.json
└── src/
```

The sample brief includes two products:

- `citrus-sparkling-water` reuses a committed local hero asset
- `oat-energy-bar` starts without a hero asset so the pipeline exercises OpenAI generation or placeholder fallback
- both sample products include tighter `prompt_override` copy aimed at cleaner, more photorealistic advertising compositions with safe crop margins and no readable packaging text

## Reusable Assets vs Runtime Outputs

Storage behavior is strict by design:

- reusable product assets live under `assets/`
- final campaign outputs live under `outputs/`
- a generated hero is saved back into `assets/<product-slug>/hero.png` only if it is a real OpenAI result
- placeholder fallback images are never written into the reusable asset library

This keeps the reusable asset library clean and prevents placeholder images from being mistakenly treated as approved product photography later.

## Design Decisions

- **Local-first storage:** The assignment is a local proof of concept, so the code uses direct filesystem paths instead of a storage abstraction.
- **Thin OpenAI wrapper:** OpenAI integration is isolated in `image_generator.py`, while the rest of the pipeline only cares about image provenance and the returned Pillow image.
- **Explicit model selection:** The generator defaults to `gpt-image-1.5`, but `OPENAI_IMAGE_MODEL` can override it without changing code.
- **Pragmatic provider choice:** OpenAI was used for this local proof of concept because it is dependable to wire into a local CLI with a single API key. In a production Adobe-aligned environment, Firefly would be the natural provider to revisit.
- **Deterministic image treatment:** Resize/crop is always center-based, and text overlay always uses a bottom banner with wrapped text.
- **Readable orchestration:** `src/main.py` performs the pipeline step by step so it is easy to explain in a short interview walkthrough.
- **Concise logging:** `run_log.json` records only the data needed to understand what happened during a run.

## Assumptions And Limitations

- The prohibited-words check is intentionally basic and only scans `campaign_message`.
- The OpenAI wrapper supports a small subset of the Images API surface and only requests one hero image at a time.
- OpenAI requests use a supported square source size and Pillow derives the required social ratios from that base asset.
- The default overlay style is simple and not brand-aware.
- The sample pipeline assumes one hero asset per product.
- This proof of concept does not include approvals, review workflows, asset versioning, or concurrency controls.

## Future Scale Path

If this moved beyond a take-home proof of concept, the most natural next step would be AWS-oriented:

- move reusable assets and outputs from local folders to Amazon S3
- keep the same folder semantics as object key prefixes
- store run logs in S3 alongside outputs or in a structured store for reporting
- add a job queue and worker model for parallel campaign processing
- keep the image generator interface and swap providers without changing the core orchestration contract

In an enterprise Adobe context, Firefly would be the natural brand-aligned provider to consider once enterprise provisioning is available. This proof of concept uses OpenAI instead because it is easier to run dependably in a local interview environment.

The current local-first structure is meant to make that path obvious without adding unnecessary abstraction to the v1 codebase.
