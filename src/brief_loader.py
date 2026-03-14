from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


class BriefValidationError(ValueError):
    """Raised when a campaign brief is missing required data."""


@dataclass(frozen=True)
class BrandColors:
    primary: str
    secondary: str
    accent: str
    text_light: str


@dataclass(frozen=True)
class BrandCompliance:
    require_logo: bool
    prohibited_words: tuple[str, ...]


@dataclass(frozen=True)
class BrandBrief:
    name: str
    slug: str
    logo_path: Path
    colors: BrandColors
    compliance: BrandCompliance


@dataclass(frozen=True)
class MarketBrief:
    locale: str
    region: str
    audience: str
    campaign_message: str
    cta: str | None = None
    disclaimer: str | None = None


@dataclass(frozen=True)
class ProductBrief:
    name: str
    prompt_override: str | None = None


@dataclass(frozen=True)
class CampaignBrief:
    campaign_name: str
    brand: BrandBrief
    markets: list[MarketBrief]
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

    missing_fields = [
        field for field in ("campaign_name", "brand", "markets", "products") if not raw_data.get(field)
    ]
    if missing_fields:
        raise BriefValidationError(
            f"Brief is missing required field(s): {', '.join(missing_fields)}"
        )

    brand = _load_brand(raw_data["brand"])
    markets = _load_markets(raw_data["markets"])
    products = _load_products(raw_data["products"])

    return CampaignBrief(
        campaign_name=_require_text(raw_data, "campaign_name", "campaign_name"),
        brand=brand,
        markets=markets,
        products=products,
    )


def build_generation_prompt(brief: CampaignBrief, product: ProductBrief) -> str:
    if product.prompt_override:
        return product.prompt_override

    market_context = "; ".join(
        f"{market.locale} ({market.region}, audience: {market.audience})"
        for market in brief.markets
    )
    return (
        f"Create a premium brand-safe advertising hero for {brief.brand.name} featuring "
        f"{product.name}. Photorealistic consumer packaged goods photography with a single "
        f"hero product, polished studio lighting, clean negative space reserved for "
        f"deterministic post-production headline and logo overlay, and safe crop margins for "
        f"1:1, 9:16, and 16:9 social placements. Avoid readable packaging text, watermarks, "
        f"collage layouts, and extra products. Designed to support these localized markets: "
        f"{market_context}."
    )


def _load_brand(raw_brand: object) -> BrandBrief:
    brand = _require_mapping(raw_brand, "brand")
    colors = _require_mapping(brand.get("colors"), "brand.colors")
    compliance = _require_mapping(brand.get("compliance"), "brand.compliance")
    prohibited_words = compliance.get("prohibited_words")
    if not isinstance(prohibited_words, list):
        raise BriefValidationError("brand.compliance.prohibited_words must be a list.")

    color_values = BrandColors(
        primary=_require_color(colors, "primary"),
        secondary=_require_color(colors, "secondary"),
        accent=_require_color(colors, "accent"),
        text_light=_require_color(colors, "text_light"),
    )
    compliance_values = BrandCompliance(
        require_logo=_require_bool(compliance, "require_logo", "brand.compliance.require_logo"),
        prohibited_words=tuple(_require_list_text(prohibited_words, "brand.compliance.prohibited_words")),
    )
    return BrandBrief(
        name=_require_text(brand, "name", "brand.name"),
        slug=_require_slug(brand, "slug", "brand.slug"),
        logo_path=Path(_require_text(brand, "logo_path", "brand.logo_path")),
        colors=color_values,
        compliance=compliance_values,
    )


def _load_markets(raw_markets: object) -> list[MarketBrief]:
    if not isinstance(raw_markets, list) or not raw_markets:
        raise BriefValidationError("Brief must include at least one market.")

    markets: list[MarketBrief] = []
    seen_locales: set[str] = set()
    for index, raw_market in enumerate(raw_markets, start=1):
        market = _require_mapping(raw_market, f"markets[{index}]")
        locale = _require_text(market, "locale", f"markets[{index}].locale")
        if locale in seen_locales:
            raise BriefValidationError(f"Duplicate market locale found: {locale}")
        seen_locales.add(locale)
        markets.append(
            MarketBrief(
                locale=locale,
                region=_require_text(market, "region", f"markets[{index}].region"),
                audience=_require_text(market, "audience", f"markets[{index}].audience"),
                campaign_message=_require_text(
                    market, "campaign_message", f"markets[{index}].campaign_message"
                ),
                cta=_optional_text(market.get("cta")),
                disclaimer=_optional_text(market.get("disclaimer")),
            )
        )
    return markets


def _load_products(raw_products: object) -> list[ProductBrief]:
    if not isinstance(raw_products, list) or len(raw_products) < 2:
        raise BriefValidationError("Brief must include at least two products.")

    products: list[ProductBrief] = []
    for index, raw_product in enumerate(raw_products, start=1):
        product = _require_mapping(raw_product, f"products[{index}]")
        products.append(
            ProductBrief(
                name=_require_text(product, "name", f"products[{index}].name"),
                prompt_override=_optional_text(product.get("prompt_override")),
            )
        )
    return products


def _require_mapping(value: object, field_name: str) -> dict:
    if not isinstance(value, dict):
        raise BriefValidationError(f"{field_name} must be a mapping.")
    return value


def _require_text(container: dict, key: str, field_name: str) -> str:
    return _normalize_required_text(container.get(key), field_name)


def _normalize_required_text(value: object, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise BriefValidationError(f"{field_name} is required.")
    return normalized


def _optional_text(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _require_bool(container: dict, key: str, field_name: str) -> bool:
    value = container.get(key)
    if not isinstance(value, bool):
        raise BriefValidationError(f"{field_name} must be true or false.")
    return value


def _require_list_text(values: list[object], field_name: str) -> list[str]:
    normalized: list[str] = []
    for index, value in enumerate(values, start=1):
        text = str(value or "").strip()
        if not text:
            raise BriefValidationError(f"{field_name}[{index}] must be non-empty text.")
        normalized.append(text)
    return normalized


def _require_color(container: dict, key: str) -> str:
    field_name = f"brand.colors.{key}"
    value = _require_text(container, key, field_name)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise BriefValidationError(f"{field_name} must be a hex color like #112233.")
    return value


def _require_slug(container: dict, key: str, field_name: str) -> str:
    value = _require_text(container, key, field_name)
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not normalized:
        raise BriefValidationError(f"{field_name} must contain slug-safe characters.")
    return normalized
