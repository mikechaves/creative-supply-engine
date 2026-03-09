from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from src.config import AppConfig


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "untitled"


def find_reusable_hero(config: AppConfig, product_name: str) -> Path | None:
    product_slug = slugify(product_name)
    product_dir = config.assets_dir / product_slug
    for extension in config.supported_hero_extensions:
        candidate = product_dir / f"hero{extension}"
        if candidate.exists():
            return candidate
    return None


def save_generated_hero_asset(
    config: AppConfig, product_name: str, image: Image.Image
) -> Path:
    product_slug = slugify(product_name)
    product_dir = config.assets_dir / product_slug
    product_dir.mkdir(parents=True, exist_ok=True)
    output_path = product_dir / "hero.png"
    image.convert("RGBA").save(output_path)
    return output_path


def get_campaign_output_dir(config: AppConfig, campaign_name: str) -> Path:
    campaign_slug = slugify(campaign_name)
    campaign_dir = config.outputs_dir / campaign_slug
    campaign_dir.mkdir(parents=True, exist_ok=True)
    return campaign_dir


def get_final_output_path(
    config: AppConfig,
    campaign_name: str,
    product_name: str,
    ratio_name: str,
) -> Path:
    campaign_slug = slugify(campaign_name)
    product_slug = slugify(product_name)
    output_dir = config.outputs_dir / campaign_slug / product_slug / ratio_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "final.png"


def to_relative_string(path: Path | None, project_root: Path) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
