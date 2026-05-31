from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from src.config import default_config


@dataclass(frozen=True)
class ReviewBundleResult:
    bundle_path: Path
    included_paths: tuple[Path, ...]


def package_review_bundle(
    project_root: Path | None = None,
    *,
    campaign: str | None = None,
    campaign_output_dir: Path | None = None,
    bundle_path: Path | None = None,
) -> ReviewBundleResult:
    config = default_config(project_root)
    resolved_campaign_output_dir = _resolve_campaign_output_dir(
        config.outputs_dir,
        campaign=campaign,
        campaign_output_dir=campaign_output_dir,
    )
    run_log_path = resolved_campaign_output_dir / "run_log.json"
    gallery_path = resolved_campaign_output_dir / "index.html"
    run_log = _load_run_log(run_log_path)
    files_to_include = _bundle_manifest(
        project_root=config.project_root,
        campaign_output_dir=resolved_campaign_output_dir,
        run_log=run_log,
        run_log_path=run_log_path,
        gallery_path=gallery_path,
    )
    resolved_bundle_path = _resolve_bundle_path(
        project_root=config.project_root,
        campaign_output_dir=resolved_campaign_output_dir,
        bundle_path=bundle_path,
    )

    resolved_bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        resolved_bundle_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as bundle:
        for path in files_to_include:
            bundle.write(path, path.relative_to(config.project_root).as_posix())

    return ReviewBundleResult(
        bundle_path=resolved_bundle_path,
        included_paths=tuple(files_to_include),
    )


def _resolve_campaign_output_dir(
    outputs_dir: Path,
    *,
    campaign: str | None,
    campaign_output_dir: Path | None,
) -> Path:
    if campaign and campaign_output_dir:
        raise RuntimeError("Use either --campaign or --campaign-output, not both.")
    if not campaign and not campaign_output_dir:
        raise RuntimeError("A campaign slug or campaign output directory is required.")
    if campaign_output_dir:
        raw_path = campaign_output_dir.expanduser()
        if raw_path.is_absolute():
            return raw_path.resolve()
        return (outputs_dir.parent / raw_path).resolve()
    return (outputs_dir / str(campaign)).resolve()


def _load_run_log(run_log_path: Path) -> dict:
    if not run_log_path.exists():
        raise RuntimeError(f"Run log not found: {run_log_path}")
    with run_log_path.open("r", encoding="utf-8") as handle:
        run_log = json.load(handle)
    if not isinstance(run_log, dict):
        raise RuntimeError(f"Run log must contain a JSON object: {run_log_path}")
    return run_log


def _bundle_manifest(
    *,
    project_root: Path,
    campaign_output_dir: Path,
    run_log: dict,
    run_log_path: Path,
    gallery_path: Path,
) -> list[Path]:
    files: list[Path] = [run_log_path, gallery_path]
    brief_path = run_log.get("brief_path")
    if not brief_path:
        raise RuntimeError("Run log did not include brief_path; cannot package source brief.")
    files.append(_project_path(brief_path, project_root))

    creative_count = 0
    for entry in run_log.get("localized_outputs") or []:
        if not isinstance(entry, dict):
            continue
        outputs = entry.get("outputs") or {}
        if not isinstance(outputs, dict):
            continue
        for output_path in outputs.values():
            files.append(_project_path(output_path, project_root))
            creative_count += 1

    if creative_count == 0:
        raise RuntimeError("Run log did not include any final creative output paths.")

    return _validate_bundle_files(
        files=files,
        project_root=project_root,
        campaign_output_dir=campaign_output_dir,
    )


def _validate_bundle_files(
    *,
    files: list[Path],
    project_root: Path,
    campaign_output_dir: Path,
) -> list[Path]:
    included: list[Path] = []
    missing: list[str] = []
    for path in files:
        resolved_path = path.resolve()
        _ensure_within_project(resolved_path, project_root)
        if not resolved_path.exists() or not resolved_path.is_file():
            missing.append(_relative_to_project(resolved_path, project_root))
            continue
        if _is_excluded_from_bundle(resolved_path, project_root, campaign_output_dir):
            continue
        if resolved_path not in included:
            included.append(resolved_path)

    if missing:
        formatted = ", ".join(missing)
        raise RuntimeError(f"Review bundle source file(s) missing: {formatted}")
    return included


def _is_excluded_from_bundle(
    path: Path,
    project_root: Path,
    campaign_output_dir: Path,
) -> bool:
    relative_parts = path.relative_to(project_root).parts
    if path.name == ".env" or "__pycache__" in relative_parts:
        return True
    if any(part.endswith(".egg-info") for part in relative_parts):
        return True
    return path == campaign_output_dir / f"{campaign_output_dir.name}-review-bundle.zip"


def _resolve_bundle_path(
    *,
    project_root: Path,
    campaign_output_dir: Path,
    bundle_path: Path | None,
) -> Path:
    if bundle_path is None:
        return campaign_output_dir / f"{campaign_output_dir.name}-review-bundle.zip"
    raw_path = bundle_path.expanduser()
    if raw_path.is_absolute():
        return raw_path.resolve()
    return (project_root / raw_path).resolve()


def _project_path(path_value: object, project_root: Path) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def _ensure_within_project(path: Path, project_root: Path) -> None:
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise RuntimeError(f"Review bundle path is outside the project: {path}") from exc


def _relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pulse-cse-package",
        description="Package generated review artifacts into a shareable ZIP bundle.",
    )
    parser.add_argument(
        "--campaign",
        help="Campaign output slug under outputs/, for example summer-citrus-reset.",
    )
    parser.add_argument(
        "--campaign-output",
        type=Path,
        default=None,
        help="Path to an existing campaign output directory containing run_log.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional ZIP output path. Defaults to outputs/<campaign>/<campaign>-review-bundle.zip.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root. Defaults to the current Creative Supply Engine checkout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = package_review_bundle(
            project_root=args.project_root,
            campaign=args.campaign,
            campaign_output_dir=args.campaign_output,
            bundle_path=args.output,
        )
    except Exception as exc:  # noqa: BLE001 - packaging CLI should report failures plainly
        print(f"Review bundle packaging failed: {exc}", file=sys.stderr)
        return 1

    print("Review bundle created.")
    print(f"Bundle: {result.bundle_path}")
    print(f"Included files: {len(result.included_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
