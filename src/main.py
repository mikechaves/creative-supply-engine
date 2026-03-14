from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from src.asset_manager import (
    find_reusable_hero,
    get_campaign_output_dir,
    get_final_output_path,
    save_generated_hero_asset,
    slugify,
    to_relative_string,
)
from src.brief_loader import (
    BriefValidationError,
    CampaignBrief,
    ProductBrief,
    build_generation_prompt,
    load_brief,
)
from src.compliance import evaluate_compliance
from src.config import AppConfig, default_config
from src.creative_builder import build_creatives
from src.image_generator import ImageGenerator, OpenAIImageGenerator
from src.logger import write_run_log
from src.logo_compositor import composite_logo
from src.overlay import apply_campaign_message, overlay_style_from_brand

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
    overlay_style = overlay_style_from_brand(brief.brand)
    brand_logo_path = _resolve_project_path(config.project_root, brief.brand.logo_path)

    run_log = {
        "campaign_name": brief.campaign_name,
        "campaign_slug": slugify(brief.campaign_name),
        "brand": {
            "name": brief.brand.name,
            "slug": brief.brand.slug,
        },
        "brief_path": to_relative_string(brief_path, config.project_root),
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "warnings": [],
        "localized_outputs": [],
    }

    for product in brief.products:
        base_image, provenance, hero_source_path, saved_hero_path, base_warnings = _load_or_generate_base_image(
            config=config,
            generator=generator,
            brief=brief,
            product=product,
        )
        for warning in base_warnings:
            _append_warning(run_log, None, product.name, warning)

        for market in brief.markets:
            localized_warnings = list(base_warnings)
            absolute_output_paths: dict[str, Path] = {}
            output_paths: dict[str, str] = {}
            logo_applied_by_ratio: dict[str, bool] = {}

            for ratio_name, variant in build_creatives(base_image, config.ratio_specs).items():
                composed = apply_campaign_message(
                    variant,
                    market.campaign_message,
                    style=overlay_style,
                    cta=market.cta,
                )
                logo_result = composite_logo(
                    composed,
                    logo_path=brand_logo_path,
                    logo_required=brief.brand.compliance.require_logo,
                    safe_margin_ratio=overlay_style.safe_margin_x_ratio,
                )
                if logo_result.warning:
                    _append_warning(
                        run_log,
                        localized_warnings,
                        f"{product.name}/{market.locale}",
                        logo_result.warning,
                    )

                output_path = get_final_output_path(
                    config=config,
                    campaign_name=brief.campaign_name,
                    product_name=product.name,
                    locale=market.locale,
                    ratio_name=ratio_name,
                )
                logo_result.image.save(output_path)
                absolute_output_paths[ratio_name] = output_path
                output_paths[ratio_name] = (
                    to_relative_string(output_path, config.project_root) or ""
                )
                logo_applied_by_ratio[ratio_name] = logo_result.applied

            compliance = evaluate_compliance(
                output_paths=absolute_output_paths,
                expected_sizes=config.ratio_specs,
                campaign_message=market.campaign_message,
                prohibited_words=brief.brand.compliance.prohibited_words,
                logo_required=brief.brand.compliance.require_logo,
                logo_path=brand_logo_path,
                logo_applied_by_ratio=logo_applied_by_ratio,
            )
            compliance["logo"]["configured_path"] = to_relative_string(
                brand_logo_path, config.project_root
            )
            for warning in compliance["warnings"]:
                _append_warning(
                    run_log,
                    localized_warnings,
                    f"{product.name}/{market.locale}",
                    warning,
                )

            run_log["localized_outputs"].append(
                {
                    "product_name": product.name,
                    "product_slug": slugify(product.name),
                    "locale": market.locale,
                    "region": market.region,
                    "audience": market.audience,
                    "campaign_message": market.campaign_message,
                    "cta": market.cta,
                    "disclaimer": market.disclaimer,
                    "asset_provenance": provenance,
                    "hero_source_path": to_relative_string(
                        hero_source_path, config.project_root
                    ),
                    "saved_hero_path": to_relative_string(
                        saved_hero_path, config.project_root
                    ),
                    "warnings": localized_warnings,
                    "outputs": output_paths,
                    "compliance": compliance,
                }
            )

    log_path = write_run_log(campaign_output_dir, run_log)
    return run_log, log_path


def _load_or_generate_base_image(
    config: AppConfig,
    generator: ImageGenerator,
    brief: CampaignBrief,
    product: ProductBrief,
) -> tuple[Image.Image, str, Path | None, Path | None, list[str]]:
    prompt = build_generation_prompt(brief, product)
    hero_path = find_reusable_hero(config, product.name)
    warnings: list[str] = []
    saved_hero_path: Path | None = None
    used_hero_path: Path | None = None

    if hero_path:
        try:
            with Image.open(hero_path) as existing_image:
                return existing_image.convert("RGBA"), "reused_local", hero_path, None, warnings
        except (OSError, UnidentifiedImageError) as exc:
            warnings.append(
                "Local hero asset could not be opened and was ignored: "
                f"{to_relative_string(hero_path, config.project_root)}. Reason: {exc}"
            )

    generated = generator.generate(prompt, config.default_generation_size)
    base_image = generated.image.convert("RGBA")
    if generated.warning:
        warnings.append(generated.warning)
    if generated.provenance == "generated_openai":
        saved_hero_path = save_generated_hero_asset(config, product.name, base_image)
    return base_image, generated.provenance, used_hero_path, saved_hero_path, warnings


def _append_warning(
    run_log: dict,
    localized_warnings: list[str] | None,
    scope: str,
    message: str,
) -> None:
    if localized_warnings is not None and message not in localized_warnings:
        localized_warnings.append(message)
    scoped_message = f"{scope}: {message}"
    if scoped_message not in run_log["warnings"]:
        run_log["warnings"].append(scoped_message)


def _resolve_project_path(project_root: Path, raw_path: Path | None) -> Path | None:
    if raw_path is None:
        return None
    if raw_path.is_absolute():
        return raw_path
    return (project_root / raw_path).resolve()
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
        f"Processed {len(run_log['localized_outputs'])} localized creative set(s). "
        f"Run log: {to_relative_string(log_path, config.project_root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
