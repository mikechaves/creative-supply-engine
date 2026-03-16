# Creative Supply Engine

Local proof of concept for reuse-first campaign creative generation.

## What You Need

- Python 3.10+
- a terminal
- optional: `OPENAI_API_KEY` in `.env` if you want live image generation instead of placeholder fallback

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

If you want live generation, add your OpenAI key to `.env`:

```bash
OPENAI_API_KEY=your_key_here
```

## Run

Default sample run:

```bash
pulse-cse
```

Other useful commands:

```bash
pulse-cse --brief briefs/campaign.yaml
pulse-cse --no-color
pulse-cse --version
pulse-cse --help
```

The original module entrypoint also still works:

```bash
python -m src.main
```

## Sample Inputs

- brief: [briefs/campaign.yaml](/Users/michaelchaves/GitHub/creative-supply-engine/briefs/campaign.yaml)
- reusable assets: [assets/](/Users/michaelchaves/GitHub/creative-supply-engine/assets)

Sample repo state:

- `citrus-sparkling-water` already has a reusable hero asset
- `oat-energy-bar` starts without a reusable hero asset

If you want to re-show the missing-asset path after a live run, delete:

```bash
rm -f assets/oat-energy-bar/hero.png
```

## Outputs

Generated files are written to:

```text
outputs/<campaign-slug>/<product-slug>/<locale>/<ratio>/final.png
```

Example:

```text
outputs/summer-citrus-reset/citrus-sparkling-water/en_US/1x1/final.png
```

Each run also writes:

```text
outputs/<campaign-slug>/run_log.json
```

## Notes

- If `OPENAI_API_KEY` is not set, the pipeline still runs and uses a placeholder hero where generation is needed.
- The CLI header/styling is cosmetic only.
- Text and logo are applied deterministically after image generation.

## Validation

```bash
python -m unittest discover -s tests -v
```
