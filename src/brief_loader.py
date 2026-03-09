from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class BriefValidationError(ValueError):
    """Raised when a campaign brief is missing required data."""


@dataclass(frozen=True)
class ProductBrief:
    name: str
    prompt_override: str | None = None


@dataclass(frozen=True)
class CampaignBrief:
    campaign_name: str
    region: str
    target_audience: str
    campaign_message: str
    products: list[ProductBrief]


def load_brief(path: Path) -> CampaignBrief:
    if not path.exists():
        raise BriefValidationError(f"Brief file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            raw_data = yaml.safe_load(handle) or {}
    except OSError as exc:
        raise BriefValidationError(f"Could not read brief file: {path}") from exc
    except yaml.YAMLError as exc:
        raise BriefValidationError(f"Brief YAML is invalid: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise BriefValidationError("Brief YAML must contain a top-level mapping.")

    required_fields = (
        "campaign_name",
        "region",
        "target_audience",
        "campaign_message",
        "products",
    )
    missing_fields = [field for field in required_fields if not raw_data.get(field)]
    if missing_fields:
        raise BriefValidationError(
            f"Brief is missing required field(s): {', '.join(missing_fields)}"
        )

    raw_products = raw_data["products"]
    if not isinstance(raw_products, list) or len(raw_products) < 2:
        raise BriefValidationError("Brief must include at least two products.")

    products: list[ProductBrief] = []
    for index, product in enumerate(raw_products, start=1):
        if not isinstance(product, dict):
            raise BriefValidationError(f"Product #{index} must be a mapping.")
        name = str(product.get("name", "")).strip()
        if not name:
            raise BriefValidationError(f"Product #{index} is missing a name.")
        prompt_override = product.get("prompt_override")
        if prompt_override is not None:
            prompt_override = str(prompt_override).strip() or None
        products.append(ProductBrief(name=name, prompt_override=prompt_override))

    return CampaignBrief(
        campaign_name=str(raw_data["campaign_name"]).strip(),
        region=str(raw_data["region"]).strip(),
        target_audience=str(raw_data["target_audience"]).strip(),
        campaign_message=str(raw_data["campaign_message"]).strip(),
        products=products,
    )


def build_generation_prompt(brief: CampaignBrief, product: ProductBrief) -> str:
    if product.prompt_override:
        return product.prompt_override

    return (
        f"Create a premium advertising hero image for {product.name}. "
        f"Audience: {brief.target_audience}. "
        f"Region: {brief.region}. "
        f"Visual mood: modern, polished, high-end studio lighting, premium product focus. "
        f"Campaign message to support: {brief.campaign_message}"
    )
