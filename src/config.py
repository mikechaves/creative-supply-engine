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
DEFAULT_OPENAI_IMAGE_MODEL = "gpt-image-1.5"


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
    openai_image_model_env: str = "OPENAI_IMAGE_MODEL"
    openai_generate_url: str = "https://api.openai.com/v1/images/generations"
    openai_image_model: str = DEFAULT_OPENAI_IMAGE_MODEL
    openai_timeout_seconds: int = 60


def default_config(project_root: Path | None = None) -> AppConfig:
    resolved_root = project_root or _discover_project_root()
    resolved_root = resolved_root.resolve()
    return AppConfig(
        project_root=resolved_root,
        briefs_dir=resolved_root / "briefs",
        assets_dir=resolved_root / "assets",
        outputs_dir=resolved_root / "outputs",
    )


def _discover_project_root() -> Path:
    for candidate in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
        if _looks_like_project_root(candidate):
            return candidate
    return Path(__file__).resolve().parent.parent


def _looks_like_project_root(path: Path) -> bool:
    return (
        (path / "briefs" / "campaign.yaml").exists()
        and (path / "assets").exists()
        and (path / "src").exists()
    )
