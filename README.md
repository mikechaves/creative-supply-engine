# Creative Supply Engine

Local proof of concept for reuse-first campaign creative generation.

## What You Need

- Python 3.10+
- a terminal
- optional: `OPENAI_API_KEY` in `.env` if you want live image generation instead of placeholder fallback

## Setup

1. Download or clone this repository to your machine.
2. Open Terminal.
3. Change into the project folder.

```bash
cd /path/to/<downloaded-repo-folder>
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
cp .env.example .env
which pulse-cse
pulse-cse --version
```

The `python3 --version` output must be Python 3.10 or newer. If your system `python3` is older,
use a newer interpreter explicitly, for example `python3.12 -m venv .venv`.

After installation, `which pulse-cse` should point inside this checkout:

```text
/path/to/<downloaded-repo-folder>/.venv/bin/pulse-cse
```

If it points somewhere else, a stale global install is taking precedence. Reactivate the venv and
rerun the install commands above before using `pulse-cse`.

If you want live generation, add your OpenAI key to `.env`:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.5
```

## Run

From the project folder, run the default sample:

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

## Smoke Demo

Run the sample campaign in placeholder mode without mutating tracked assets:

```bash
pulse-cse-smoke
```

The smoke command copies the sample brief and assets into a temporary project, runs the real
pipeline with `OPENAI_API_KEY` unset, and verifies final creatives, `run_log.json`, and
`index.html`.

To test live OpenAI image generation explicitly:

```bash
pulse-cse-smoke --live
```

## Sample Inputs

- brief: [briefs/campaign.yaml](briefs/campaign.yaml)
- reusable assets: [assets/](assets/)

Sample repo state:

- `citrus-sparkling-water` already has a reusable hero asset
- `oat-energy-bar` starts without a reusable hero asset

Tracked reusable assets:

- `assets/common/pulse-beverages-logo.png`
- `assets/citrus-sparkling-water/hero.png`
- `assets/oat-energy-bar/.gitkeep`

Generated local files ignored by git:

- `outputs/`
- `assets/oat-energy-bar/hero.*`

If you want to re-show the missing-asset path after a live run, reset the sample state:

```bash
pulse-cse-reset-sample
```

To also clear generated review outputs:

```bash
pulse-cse-reset-sample --include-outputs
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

And a browser-friendly review gallery:

```text
outputs/<campaign-slug>/index.html
```

## Review Bundle

After a run, package review artifacts into a shareable ZIP:

```bash
pulse-cse-package --campaign summer-citrus-reset
```

The bundle includes final creatives, `run_log.json`, `index.html`, and the source brief. It does
not include `.env`, caches, reusable source assets, or generated local hero assets.

## Notes

- If `OPENAI_API_KEY` is not set, the pipeline still runs and uses a placeholder hero where generation is needed.
- Live generation uses GPT-5.5 through the Responses API image generation tool by default.
- The CLI header/styling is cosmetic only.
- Text and logo are applied deterministically after image generation.

## Planning

- [Backlog](docs/backlog/README.md)

## Validation

```bash
python -m unittest discover -s tests -v
```
