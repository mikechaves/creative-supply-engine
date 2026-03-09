from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from src.asset_manager import (
    find_reusable_hero,
    get_campaign_output_dir,
    get_final_output_path,
    save_generated_hero_asset,
    slugify,
    to_relative_string,
)
from src.brief_loader import BriefValidationError, build_generation_prompt, load_brief
from src.checks import check_campaign_message
from src.config import AppConfig, default_config
from src.creative_builder import build_creatives
from src.image_generator import ImageGenerator, OpenAIImageGenerator
from src.logger import write_run_log
from src.overlay import apply_campaign_message

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for bare environments
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


def run_pipeline(
    brief_path: Path,
    config: AppConfig | None = None,
    generator: ImageGenerator | None = None,
) -> tuple[dict, Path]:
    config = config or default_config()
    generator = generator or OpenAIImageGenerator(config)
    brief = load_brief(brief_path)
    campaign_output_dir = get_campaign_output_dir(config, brief.campaign_name)

    run_warnings = check_campaign_message(
        brief.campaign_message, config.prohibited_words
    )
    run_log = {
        "campaign_name": brief.campaign_name,
        "campaign_slug": slugify(brief.campaign_name),
        "region": brief.region,
        "brief_path": to_relative_string(brief_path, config.project_root),
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "warnings": list(run_warnings),
        "products": [],
    }

    for product in brief.products:
        prompt = build_generation_prompt(brief, product)
        hero_path = find_reusable_hero(config, product.name)
        product_warnings: list[str] = []
        saved_hero_path: Path | None = None

        if hero_path:
            base_image = Image.open(hero_path).convert("RGBA")
            provenance = "reused_local"
        else:
            generated = generator.generate(prompt, config.default_generation_size)
            base_image = generated.image.convert("RGBA")
            provenance = generated.provenance
            if generated.warning:
                warning = f"{product.name}: {generated.warning}"
                product_warnings.append(generated.warning)
                run_log["warnings"].append(warning)
            if provenance == "generated_openai":
                saved_hero_path = save_generated_hero_asset(
                    config, product.name, base_image
                )

        output_paths: dict[str, str] = {}
        for ratio_name, variant in build_creatives(base_image, config.ratio_specs).items():
            final_image = apply_campaign_message(variant, brief.campaign_message)
            output_path = get_final_output_path(
                config=config,
                campaign_name=brief.campaign_name,
                product_name=product.name,
                ratio_name=ratio_name,
            )
            final_image.save(output_path)
            output_paths[ratio_name] = to_relative_string(output_path, config.project_root) or ""

        run_log["products"].append(
            {
                "name": product.name,
                "slug": slugify(product.name),
                "asset_provenance": provenance,
                "hero_source_path": to_relative_string(hero_path, config.project_root),
                "saved_hero_path": to_relative_string(saved_hero_path, config.project_root),
                "warnings": product_warnings,
                "outputs": output_paths,
            }
        )

    log_path = write_run_log(campaign_output_dir, run_log)
    return run_log, log_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Creative Supply Engine CLI")
    parser.add_argument(
        "--brief",
        default="briefs/campaign.yaml",
        help="Path to the campaign YAML brief.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    config = default_config()
    brief_path = Path(args.brief).expanduser()
    if not brief_path.is_absolute():
        brief_path = (config.project_root / brief_path).resolve()

    try:
        run_log, log_path = run_pipeline(brief_path=brief_path, config=config)
    except BriefValidationError as exc:
        print(f"Brief validation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI safety net
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Processed {len(run_log['products'])} product(s). "
        f"Run log: {to_relative_string(log_path, config.project_root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
