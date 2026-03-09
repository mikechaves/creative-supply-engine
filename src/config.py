from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

RATIO_SPECS = {
    "1x1": (1080, 1080),
    "9x16": (1080, 1920),
    "16x9": (1920, 1080),
}

SUPPORTED_HERO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
DEFAULT_GENERATION_SIZE = (1024, 1024)
PROHIBITED_WORDS = ("banned", "illegal", "guaranteed cure")


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    briefs_dir: Path
    assets_dir: Path
    outputs_dir: Path
    ratio_specs: dict[str, tuple[int, int]] = field(default_factory=lambda: dict(RATIO_SPECS))
    prohibited_words: tuple[str, ...] = PROHIBITED_WORDS
    supported_hero_extensions: tuple[str, ...] = SUPPORTED_HERO_EXTENSIONS
    default_generation_size: tuple[int, int] = DEFAULT_GENERATION_SIZE
    openai_api_key_env: str = "OPENAI_API_KEY"
    openai_generate_url: str = "https://api.openai.com/v1/images/generations"
    openai_image_model: str = "gpt-image-1.5"
    openai_timeout_seconds: int = 60


def default_config(project_root: Path | None = None) -> AppConfig:
    resolved_root = project_root or Path(__file__).resolve().parent.parent
    resolved_root = resolved_root.resolve()
    return AppConfig(
        project_root=resolved_root,
        briefs_dir=resolved_root / "briefs",
        assets_dir=resolved_root / "assets",
        outputs_dir=resolved_root / "outputs",
    )
