from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.asset_manager import slugify
from src.config import SUPPORTED_HERO_EXTENSIONS, default_config
from src.main import run_pipeline


@dataclass(frozen=True)
class SmokeDemoResult:
    temp_root: Path
    run_log_path: Path
    gallery_path: Path
    localized_set_count: int
    creative_file_count: int
    placeholder_count: int
    generated_openai_count: int
    warning_count: int


def run_smoke_demo(
    source_root: Path | None = None,
    *,
    live: bool = False,
    keep_temp: bool = False,
) -> SmokeDemoResult:
    source_root = (source_root or default_config().project_root).resolve()
    _validate_source_project(source_root)

    if keep_temp:
        temp_root = Path(tempfile.mkdtemp(prefix="pulse-cse-smoke-")).resolve()
        _copy_sample_project(source_root, temp_root)
        return _run_and_verify(temp_root, live=live)

    with tempfile.TemporaryDirectory(prefix="pulse-cse-smoke-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        _copy_sample_project(source_root, temp_root)
        return _run_and_verify(temp_root, live=live)


def _validate_source_project(source_root: Path) -> None:
    required_paths = (
        source_root / "briefs" / "campaign.yaml",
        source_root / "assets",
        source_root / "assets" / "common" / "pulse-beverages-logo.png",
    )
    missing_paths = [path for path in required_paths if not path.exists()]
    if missing_paths:
        formatted = ", ".join(path.relative_to(source_root).as_posix() for path in missing_paths)
        raise RuntimeError(f"Smoke demo source project is missing required path(s): {formatted}")


def _copy_sample_project(source_root: Path, temp_root: Path) -> None:
    shutil.copytree(source_root / "briefs", temp_root / "briefs")
    shutil.copytree(
        source_root / "assets",
        temp_root / "assets",
        ignore=shutil.ignore_patterns(".DS_Store"),
    )
    generated_sample_dir = temp_root / "assets" / slugify("oat-energy-bar")
    for extension in SUPPORTED_HERO_EXTENSIONS:
        generated_sample_hero = generated_sample_dir / f"hero{extension}"
        if generated_sample_hero.exists():
            generated_sample_hero.unlink()


def _run_and_verify(temp_root: Path, *, live: bool) -> SmokeDemoResult:
    config = default_config(temp_root)
    brief_path = config.briefs_dir / "campaign.yaml"
    previous_api_key = os.environ.get(config.openai_api_key_env)
    if not live:
        os.environ.pop(config.openai_api_key_env, None)

    try:
        run_log, run_log_path = run_pipeline(brief_path=brief_path, config=config)
    finally:
        if not live and previous_api_key is not None:
            os.environ[config.openai_api_key_env] = previous_api_key

    gallery_path = temp_root / str(run_log.get("review_gallery_path") or "")
    localized_outputs = run_log.get("localized_outputs") or []
    if not isinstance(localized_outputs, list) or not localized_outputs:
        raise RuntimeError("Smoke demo did not produce localized outputs.")
    if not run_log_path.exists():
        raise RuntimeError(f"Smoke demo did not write run log: {run_log_path}")
    if not gallery_path.exists():
        raise RuntimeError(f"Smoke demo did not write review gallery: {gallery_path}")

    creative_file_count = 0
    placeholder_count = 0
    generated_openai_count = 0
    for entry in localized_outputs:
        if not isinstance(entry, dict):
            raise RuntimeError("Smoke demo run log contains a malformed localized output entry.")
        provenance = entry.get("asset_provenance")
        if provenance == "generated_placeholder":
            placeholder_count += 1
        if provenance == "generated_openai":
            generated_openai_count += 1
        for output_path in (entry.get("outputs") or {}).values():
            absolute_output_path = temp_root / str(output_path)
            if not absolute_output_path.exists():
                raise RuntimeError(
                    f"Smoke demo expected creative output is missing: {output_path}"
                )
            creative_file_count += 1

    if not live and placeholder_count == 0:
        raise RuntimeError("Placeholder smoke demo did not exercise placeholder generation.")
    if live and generated_openai_count == 0:
        raise RuntimeError("Live smoke demo did not produce an OpenAI-generated asset.")

    expected_creative_count = len(localized_outputs) * len(config.ratio_specs)
    if creative_file_count != expected_creative_count:
        raise RuntimeError(
            "Smoke demo output count mismatch: "
            f"expected {expected_creative_count}, found {creative_file_count}."
        )

    expected_saved_hero = config.assets_dir / slugify("oat-energy-bar") / "hero.png"
    if not live and expected_saved_hero.exists():
        raise RuntimeError(
            "Placeholder smoke demo mutated reusable generated hero assets in the temp project."
        )

    return SmokeDemoResult(
        temp_root=temp_root,
        run_log_path=run_log_path,
        gallery_path=gallery_path,
        localized_set_count=len(localized_outputs),
        creative_file_count=creative_file_count,
        placeholder_count=placeholder_count,
        generated_openai_count=generated_openai_count,
        warning_count=len(run_log.get("warnings") or []),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pulse-cse-smoke",
        description="Run the sample campaign in a temporary project and verify generated artifacts.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use the configured OPENAI_API_KEY and require an OpenAI-generated hero asset.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary smoke project so outputs can be inspected after the run.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Project root to copy sample briefs and assets from. Defaults to the current project.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_smoke_demo(
            source_root=args.source_root,
            live=args.live,
            keep_temp=args.keep_temp,
        )
    except Exception as exc:  # noqa: BLE001 - CLI smoke command should report failures plainly
        print(f"Smoke demo failed: {exc}")
        return 1

    mode = "live" if args.live else "placeholder"
    print(f"Smoke demo passed ({mode}).")
    print(f"Localized sets: {result.localized_set_count}")
    print(f"Creative files: {result.creative_file_count}")
    print(f"Warnings: {result.warning_count}")
    if args.keep_temp:
        print(f"Temp project: {result.temp_root}")
        print(f"Run log: {result.run_log_path}")
        print(f"Review gallery: {result.gallery_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
