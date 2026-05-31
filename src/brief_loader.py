from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from src.config import RATIO_SPECS


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


SUPPORTED_LOCALE_PATTERN = re.compile(r"^[a-z]{2}_[A-Z]{2}$")
UNSUPPORTED_RATIO_FIELD_NAMES = frozenset({"ratio", "ratios", "ratio_specs"})
SUPPORTED_RATIO_LABEL = ", ".join(RATIO_SPECS)


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

    authoring_errors = _collect_authoring_errors(raw_data)
    if authoring_errors:
        raise BriefValidationError(_format_authoring_errors(authoring_errors))

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


def _collect_authoring_errors(raw_data: dict) -> list[str]:
    errors: list[str] = []
    _collect_unsupported_ratio_fields(raw_data, "", errors)

    if not _has_required_text(raw_data, "campaign_name"):
        errors.append("campaign_name is required.")

    _collect_brand_errors(raw_data.get("brand"), errors)
    _collect_markets_errors(raw_data.get("markets"), errors)
    _collect_products_errors(raw_data.get("products"), errors)
    return errors


def _collect_brand_errors(raw_brand: object, errors: list[str]) -> None:
    if not isinstance(raw_brand, dict):
        errors.append("brand must be a mapping with name, slug, logo_path, colors, and compliance.")
        return

    _collect_unsupported_ratio_fields(raw_brand, "brand", errors)
    for key in ("name", "slug", "logo_path"):
        if not _has_required_text(raw_brand, key):
            errors.append(f"brand.{key} is required.")

    colors = raw_brand.get("colors")
    if not isinstance(colors, dict):
        errors.append(
            "brand.colors must be a mapping with primary, secondary, accent, and text_light."
        )
    else:
        for key in ("primary", "secondary", "accent", "text_light"):
            field_name = f"brand.colors.{key}"
            value = _required_text_value(colors, key)
            if not value:
                errors.append(f"{field_name} is required.")
            elif not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                errors.append(f"{field_name} must be a hex color like #112233.")

    compliance = raw_brand.get("compliance")
    if not isinstance(compliance, dict):
        errors.append("brand.compliance must be a mapping with require_logo and prohibited_words.")
        return
    if not isinstance(compliance.get("require_logo"), bool):
        errors.append("brand.compliance.require_logo must be true or false.")
    if not isinstance(compliance.get("prohibited_words"), list):
        errors.append("brand.compliance.prohibited_words must be a list.")


def _collect_markets_errors(raw_markets: object, errors: list[str]) -> None:
    if not isinstance(raw_markets, list) or not raw_markets:
        errors.append(
            "markets must include at least one market with locale, region, audience, "
            "and campaign_message."
        )
        return

    seen_locales: set[str] = set()
    for index, raw_market in enumerate(raw_markets, start=1):
        field_prefix = f"markets[{index}]"
        if not isinstance(raw_market, dict):
            errors.append(f"{field_prefix} must be a mapping.")
            continue

        _collect_unsupported_ratio_fields(raw_market, field_prefix, errors)
        locale = _required_text_value(raw_market, "locale")
        if not locale:
            errors.append(f"{field_prefix}.locale is required.")
        elif not SUPPORTED_LOCALE_PATTERN.fullmatch(locale):
            errors.append(
                f"{field_prefix}.locale must use locale_REGION format like en_US; "
                f"received {locale!r}."
            )
        elif locale in seen_locales:
            errors.append(f"{field_prefix}.locale duplicates an earlier market: {locale}.")
        else:
            seen_locales.add(locale)

        for key in ("region", "audience", "campaign_message"):
            if not _has_required_text(raw_market, key):
                errors.append(f"{field_prefix}.{key} is required.")


def _collect_products_errors(raw_products: object, errors: list[str]) -> None:
    if not isinstance(raw_products, list) or len(raw_products) < 2:
        errors.append("products must include at least two products.")
        if not isinstance(raw_products, list):
            return

    for index, raw_product in enumerate(raw_products or [], start=1):
        field_prefix = f"products[{index}]"
        if not isinstance(raw_product, dict):
            errors.append(f"{field_prefix} must be a mapping.")
            continue
        _collect_unsupported_ratio_fields(raw_product, field_prefix, errors)
        if not _has_required_text(raw_product, "name"):
            errors.append(f"{field_prefix}.name is required.")


def _collect_unsupported_ratio_fields(
    container: dict,
    field_prefix: str,
    errors: list[str],
) -> None:
    for key in sorted(UNSUPPORTED_RATIO_FIELD_NAMES.intersection(container)):
        field_name = f"{field_prefix}.{key}" if field_prefix else key
        errors.append(
            f"{field_name} is not supported in campaign briefs yet; "
            f"current fixed ratios are {SUPPORTED_RATIO_LABEL}."
        )


def _format_authoring_errors(errors: list[str]) -> str:
    if len(errors) == 1:
        return errors[0]
    formatted_errors = "\n- ".join(errors)
    return f"{len(errors)} brief authoring issue(s) found:\n- {formatted_errors}"


def _has_required_text(container: dict, key: str) -> bool:
    return bool(_required_text_value(container, key))


def _required_text_value(container: dict, key: str) -> str:
    return str(container.get(key) or "").strip()


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
