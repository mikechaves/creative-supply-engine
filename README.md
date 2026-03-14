# Creative Supply Engine

Creative Supply Engine is a local-first Python CLI that turns a structured campaign brief into brand-aware, localized social creatives.

The proof of concept stays intentionally small:

- load a YAML brief with brand, markets, and products
- reuse local hero assets when available
- generate missing hero assets through a thin OpenAI image wrapper
- fall back gracefully when generation fails
- create `1:1`, `9:16`, and `16:9` outputs
- apply campaign text and CTA with a deterministic brand-aware overlay
- composite a transparent PNG logo after generation
- run lightweight compliance checks and write a concise `run_log.json`

## Project Overview

This version of the pipeline is designed to feel closer to a governed enterprise campaign workflow without adding unnecessary infrastructure or abstraction:

- the CLI remains the only interface
- local folders remain the system of record for briefs, assets, and outputs
- hero generation stays provider-isolated in `image_generator.py`
- brand styling, logo placement, and compliance are deterministic post-generation steps
- localized market outputs are generated per product, per locale, and per ratio

## 60-Second Walkthrough

1. `brief_loader.py` validates a YAML brief with `brand`, `markets`, and `products`.
2. `main.py` resolves one reusable or generated hero per product, then loops through every market and ratio.
3. `creative_builder.py` creates the three aspect ratios from the base hero.
4. `overlay.py` applies a brand-aware message panel using colors from the brief and adds CTA text when present.
5. `logo_compositor.py` places the transparent brand logo inside safe margins.
6. `compliance.py` runs lightweight checks on output existence, dimensions, campaign text, prohibited words, and logo application.
7. `logger.py` writes a readable `run_log.json` with one entry per product and locale.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Environment Variables

Required for live image generation:

- `OPENAI_API_KEY`

Optional:

- `OPENAI_IMAGE_MODEL`
  - default: `gpt-image-1.5`
  - lower-cost alternative: `gpt-image-1-mini`

If `OPENAI_API_KEY` is missing, the pipeline continues with a generated placeholder hero for the current run.

## Sample Brief Schema

The sample brief in [briefs/campaign.yaml](/Users/michaelchaves/GitHub/creative-supply-engine/briefs/campaign.yaml) includes:

- `campaign_name`
- `brand`
  - `name`
  - `slug`
  - `logo_path`
  - `colors.primary`
  - `colors.secondary`
  - `colors.accent`
  - `colors.text_light`
  - `compliance.require_logo`
  - `compliance.prohibited_words`
- `markets[]`
  - `locale`
  - `region`
  - `audience`
  - `campaign_message`
  - `cta`
  - optional `disclaimer`
- `products[]`
  - `name`
  - optional `prompt_override`

The fictional sample brand is `Pulse Beverages`, with two products:

- `citrus-sparkling-water`
- `oat-energy-bar`

In the sample repo state:

- `citrus-sparkling-water` already has a reusable local hero asset
- `oat-energy-bar` starts without a reusable hero asset so the pipeline exercises generation or placeholder fallback

## How To Run

Run the sample brief:

```bash
python -m src.main
```

Run the deterministic fallback path:

```bash
make demo
```

Run the live provider path when `OPENAI_API_KEY` is configured:

```bash
make demo-live
```

If you want to re-demonstrate the missing-asset path after a live run, delete
`assets/oat-energy-bar/hero.png` first.

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
│       └── pulse-beverages-logo.png
├── outputs/
│   └── summer-citrus-reset/
│       ├── citrus-sparkling-water/
│       │   └── en_US/
│       │       └── 1x1/
│       │           └── final.png
│       ├── oat-energy-bar/
│       │   └── es_MX/
│       │       └── 16x9/
│       │           └── final.png
│       └── run_log.json
└── src/
```

The localized output pattern is:

`outputs/<campaign-slug>/<product-slug>/<locale>/<ratio>/final.png`

Example:

`outputs/summer-citrus-reset/citrus-sparkling-water/en_US/1x1/final.png`

## Reusable Assets vs Runtime Outputs

Storage behavior stays strict:

- reusable product heroes live under `assets/`
- the Pulse Beverages logo also lives under `assets/`
- localized campaign outputs live under `outputs/`
- a generated hero is saved back to `assets/<product-slug>/hero.png` only when it is a real OpenAI result
- placeholder fallbacks are never written into the reusable asset library

This keeps reusable assets clean and makes the reuse-first story easy to explain.

## Why Text And Logo Are Applied Post-Generation

Campaign text and logos are composited after image generation on purpose:

- deterministic typography is more reliable than model-rendered text
- the same hero can be reused across multiple markets
- safe margins and logo placement stay consistent across aspect ratios
- brand governance is easier to explain and verify in code

The model is used to create the hero image. Pillow handles the final brand composition.

## Design Decisions

- **Localized but reuse-first:** Hero generation happens once per product, while localization happens in the composition layer.
- **Brand-aware overlay:** The overlay uses brand colors from the brief and includes CTA text when present, without turning into a design system.
- **Deterministic logo compositing:** The logo is loaded from `brand.logo_path` and placed inside safe margins after the text overlay.
- **Lightweight compliance:** Checks are rule-based and readable: file existence, dimensions, campaign message presence, prohibited words, and logo application.
- **Thin provider boundary:** OpenAI stays isolated in `image_generator.py`; the rest of the pipeline only cares about a returned Pillow image and provenance.
- **Local-first storage:** The repo remains a local POC with organized folders rather than cloud services or storage abstractions.

## Assumptions And Limitations

- The same hero asset is reused across markets for a given product.
- Compliance checks are deterministic and metadata-driven; there is no OCR or computer vision.
- The overlay is intentionally simple and only uses the brand color palette plus CTA text.
- Logo placement is consistent but not product-aware beyond safe margins.
- The OpenAI wrapper only requests one base hero image at a time.
- This proof of concept does not include approvals, concurrency, asset versioning, or workflow orchestration.

## Future Improvements Intentionally Left Out

- richer brand rules such as legal disclaimers per ratio or per market
- logo-safe zones that vary by product category
- asset review states and approval flows
- parallel execution for high campaign volume
- stronger compliance checks beyond deterministic rules
