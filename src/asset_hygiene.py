from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from src.asset_manager import slugify
from src.config import AppConfig, default_config

GENERATED_SAMPLE_PRODUCT_NAME = "oat-energy-bar"
TRACKED_SAMPLE_ASSETS = (
    Path("assets/common/pulse-beverages-logo.png"),
    Path("assets/citrus-sparkling-water/hero.png"),
    Path("assets/oat-energy-bar/.gitkeep"),
)


@dataclass(frozen=True)
class AssetResetResult:
    project_root: Path
    removed_paths: tuple[Path, ...]
    missing_paths: tuple[Path, ...]
    preserved_paths: tuple[Path, ...]


def generated_sample_hero_paths(config: AppConfig) -> tuple[Path, ...]:
    product_dir = config.assets_dir / slugify(GENERATED_SAMPLE_PRODUCT_NAME)
    return tuple(product_dir / f"hero{extension}" for extension in config.supported_hero_extensions)


def reset_sample_assets(
    project_root: Path | None = None,
    *,
    include_outputs: bool = False,
) -> AssetResetResult:
    config = default_config(project_root)
    removed_paths: list[Path] = []
    missing_paths: list[Path] = []

    for hero_path in generated_sample_hero_paths(config):
        if not hero_path.exists():
            missing_paths.append(hero_path)
            continue
        if not hero_path.is_file() and not hero_path.is_symlink():
            raise RuntimeError(
                "Refusing to remove non-file generated hero path: "
                f"{_relative_to_root(hero_path, config.project_root)}"
            )
        hero_path.unlink()
        removed_paths.append(hero_path)

    if include_outputs and config.outputs_dir.exists():
        if config.outputs_dir.is_symlink() or config.outputs_dir.is_file():
            config.outputs_dir.unlink()
        else:
            shutil.rmtree(config.outputs_dir)
        removed_paths.append(config.outputs_dir)

    preserved_paths = tuple(config.project_root / path for path in TRACKED_SAMPLE_ASSETS)
    return AssetResetResult(
        project_root=config.project_root,
        removed_paths=tuple(removed_paths),
        missing_paths=tuple(missing_paths),
        preserved_paths=preserved_paths,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pulse-cse-reset-sample",
        description="Reset generated sample assets without deleting tracked reusable brand assets.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root to reset. Defaults to the current Creative Supply Engine checkout.",
    )
    parser.add_argument(
        "--include-outputs",
        action="store_true",
        help="Also remove the generated outputs directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = reset_sample_assets(
            project_root=args.project_root,
            include_outputs=args.include_outputs,
        )
    except Exception as exc:  # noqa: BLE001 - reset command should fail with a plain CLI message
        print(f"Sample asset reset failed: {exc}", file=sys.stderr)
        return 1

    print("Sample asset reset complete.")
    if result.removed_paths:
        print("Removed generated path(s):")
        for path in result.removed_paths:
            print(f"- {_relative_to_root(path, result.project_root)}")
    else:
        print("No generated sample heroes were present.")

    print("Preserved tracked sample asset(s):")
    for path in result.preserved_paths:
        print(f"- {_relative_to_root(path, result.project_root)}")
    return 0


def _relative_to_root(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
