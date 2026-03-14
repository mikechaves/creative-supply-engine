from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

try:
    RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover - Pillow compatibility
    RESAMPLING = Image.LANCZOS


@dataclass(frozen=True)
class LogoCompositeResult:
    image: Image.Image
    applied: bool
    warning: str | None = None


def composite_logo(
    image: Image.Image,
    logo_path: Path | None,
    logo_required: bool,
    safe_margin_ratio: float = 0.055,
) -> LogoCompositeResult:
    canvas = image.convert("RGBA").copy()
    if logo_path is None:
        warning = "Logo is required but no logo path was configured." if logo_required else None
        return LogoCompositeResult(image=canvas, applied=False, warning=warning)
    if not logo_path.exists():
        warning = (
            f"Required logo file not found: {logo_path.as_posix()}"
            if logo_required
            else None
        )
        return LogoCompositeResult(image=canvas, applied=False, warning=warning)

    try:
        with Image.open(logo_path) as logo_file:
            logo = logo_file.convert("RGBA")
    except OSError as exc:
        warning = (
            f"Required logo file could not be opened: {logo_path.as_posix()}. Reason: {exc}"
            if logo_required
            else None
        )
        return LogoCompositeResult(image=canvas, applied=False, warning=warning)

    width, height = canvas.size
    margin = max(28, int(min(width, height) * safe_margin_ratio))
    max_logo_width = _max_logo_width(width, height)
    max_logo_height = max(44, int(height * 0.12))

    scale = min(
        max_logo_width / max(logo.width, 1),
        max_logo_height / max(logo.height, 1),
        1.0,
    )
    resized_logo = logo.resize(
        (max(1, int(logo.width * scale)), max(1, int(logo.height * scale))),
        RESAMPLING,
    )
    canvas.alpha_composite(resized_logo, (margin, margin))
    return LogoCompositeResult(image=canvas, applied=True)


def _max_logo_width(width: int, height: int) -> int:
    if width > height:
        return int(width * 0.16)
    if width == height:
        return int(width * 0.22)
    return int(width * 0.28)
