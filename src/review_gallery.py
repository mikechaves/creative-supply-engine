from __future__ import annotations

from collections import defaultdict
from html import escape
import os
from pathlib import Path
from urllib.parse import quote


def write_review_gallery(
    campaign_output_dir: Path,
    run_log: dict,
    project_root: Path,
) -> Path:
    campaign_output_dir.mkdir(parents=True, exist_ok=True)
    gallery_path = campaign_output_dir / "index.html"
    gallery_path.write_text(
        _render_gallery_html(run_log, campaign_output_dir, project_root),
        encoding="utf-8",
    )
    return gallery_path


def _render_gallery_html(
    run_log: dict,
    campaign_output_dir: Path,
    project_root: Path,
) -> str:
    localized_outputs = list(run_log.get("localized_outputs") or [])
    products = _group_by_product(localized_outputs)
    warnings = list(run_log.get("warnings") or [])
    brand = run_log.get("brand") or {}
    brand_name = brand.get("name") if isinstance(brand, dict) else None
    image_count = 0
    passed_count = 0
    for entry in localized_outputs:
        if not isinstance(entry, dict):
            continue
        image_count += len(entry.get("outputs") or {})
        compliance = entry.get("compliance") or {}
        if isinstance(compliance, dict) and compliance.get("passed"):
            passed_count += 1

    product_sections = "\n".join(
        _render_product_section(
            product_name=product_name,
            entries=entries,
            campaign_output_dir=campaign_output_dir,
            project_root=project_root,
        )
        for product_name, entries in products.items()
    )
    warning_panel = _render_warning_panel(warnings)
    run_log_href = _relative_href(
        campaign_output_dir / "run_log.json", campaign_output_dir
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{escape(str(run_log.get("campaign_name") or "Campaign"))} Review Gallery</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #16232c;
      --muted: #65717a;
      --paper: #f7f4ed;
      --panel: #ffffff;
      --line: #dde2df;
      --brand: #13324a;
      --accent: #f4c542;
      --ok: #23765a;
      --warn: #a15f12;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
    }}

    a {{
      color: inherit;
    }}

    .shell {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}

    .hero {{
      display: grid;
      gap: 20px;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: end;
      border-bottom: 1px solid var(--line);
      padding-bottom: 24px;
    }}

    h1, h2, h3, p {{
      margin: 0;
    }}

    h1 {{
      font-size: 34px;
      line-height: 1.08;
      letter-spacing: 0;
    }}

    h2 {{
      font-size: 22px;
      line-height: 1.2;
      letter-spacing: 0;
      margin-top: 34px;
    }}

    h3 {{
      font-size: 17px;
      line-height: 1.25;
      letter-spacing: 0;
    }}

    .meta {{
      color: var(--muted);
      margin-top: 10px;
      line-height: 1.55;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(96px, 1fr));
      gap: 10px;
    }}

    .stat {{
      min-width: 96px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 12px;
    }}

    .stat strong {{
      display: block;
      font-size: 24px;
      line-height: 1;
    }}

    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 6px;
    }}

    .warning-panel {{
      margin-top: 20px;
      border: 1px solid #e5c68f;
      background: #fff8e8;
      border-radius: 8px;
      padding: 14px 16px;
      color: #5e3d0b;
    }}

    .warning-panel ul {{
      margin: 8px 0 0;
      padding-left: 20px;
    }}

    .locale-grid {{
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      margin-top: 16px;
    }}

    .card {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      overflow: hidden;
    }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }}

    .badge {{
      flex: 0 0 auto;
      align-self: start;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 700;
      background: #e8f4ee;
      color: var(--ok);
    }}

    .badge.warn {{
      background: #fff2d9;
      color: var(--warn);
    }}

    .details {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin-top: 9px;
    }}

    .asset-row {{
      padding: 0 16px 14px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}

    .asset-row code {{
      color: var(--ink);
      word-break: break-all;
    }}

    .creative-grid {{
      display: grid;
      gap: 1px;
      background: var(--line);
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    }}

    .creative {{
      background: #f9faf8;
      margin: 0;
      padding: 12px;
    }}

    .creative img {{
      display: block;
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: contain;
      background: #ecefed;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}

    .creative.ratio-9x16 img {{
      aspect-ratio: 9 / 16;
    }}

    .creative.ratio-16x9 img {{
      aspect-ratio: 16 / 9;
    }}

    .creative a {{
      display: block;
      color: var(--brand);
      font-size: 13px;
      font-weight: 700;
      margin-top: 8px;
      text-decoration: none;
    }}

    @media (max-width: 760px) {{
      .shell {{
        width: min(100% - 22px, 1180px);
        padding-top: 22px;
      }}

      .hero {{
        grid-template-columns: 1fr;
      }}

      .stats {{
        grid-template-columns: repeat(3, 1fr);
      }}

      h1 {{
        font-size: 28px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <h1>{escape(str(run_log.get("campaign_name") or "Campaign"))}</h1>
        <p class="meta">
          {escape(str(brand_name or "Brand"))} creative review gallery<br>
          Started {escape(str(run_log.get("run_started_at") or "unknown"))} &middot; <a href="{run_log_href}">run log</a>
        </p>
      </div>
      <div class="stats" aria-label="Run summary">
        <div class="stat"><strong>{len(localized_outputs)}</strong><span>localized sets</span></div>
        <div class="stat"><strong>{image_count}</strong><span>creative files</span></div>
        <div class="stat"><strong>{passed_count}</strong><span>passed sets</span></div>
      </div>
    </section>
    {warning_panel}
    {product_sections}
  </main>
</body>
</html>
"""


def _group_by_product(entries: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        product_name = str(
            entry.get("product_name") or entry.get("product_slug") or "Product"
        )
        grouped[product_name].append(entry)
    return dict(grouped)


def _render_warning_panel(warnings: list[str]) -> str:
    if not warnings:
        return ""
    items = "\n".join(f"        <li>{escape(str(warning))}</li>" for warning in warnings)
    return f"""<section class="warning-panel" aria-label="Warnings">
      <strong>{len(warnings)} warning(s)</strong>
      <ul>
{items}
      </ul>
    </section>"""


def _render_product_section(
    product_name: str,
    entries: list[dict],
    campaign_output_dir: Path,
    project_root: Path,
) -> str:
    cards = "\n".join(
        _render_locale_card(entry, campaign_output_dir, project_root) for entry in entries
    )
    return f"""<section>
      <h2>{escape(product_name)}</h2>
      <div class="locale-grid">
{cards}
      </div>
    </section>"""


def _render_locale_card(
    entry: dict,
    campaign_output_dir: Path,
    project_root: Path,
) -> str:
    compliance = entry.get("compliance") or {}
    passed = bool(compliance.get("passed"))
    badge_class = "badge" if passed else "badge warn"
    badge_text = "Passed" if passed else "Review"
    warnings = entry.get("warnings") or []
    warning_text = ""
    if warnings:
        warning_text = " &middot; " + escape(f"{len(warnings)} warning(s)")
    asset_path = entry.get("hero_source_path") or entry.get("saved_hero_path")
    asset_label = "Hero asset"
    if entry.get("saved_hero_path"):
        asset_label = "Saved hero asset"
    asset_html = ""
    if asset_path:
        asset_href = _relative_href(
            _project_path(asset_path, project_root),
            campaign_output_dir,
        )
        asset_html = (
            f'<div class="asset-row">{asset_label}: '
            f'<a href="{asset_href}"><code>{escape(str(asset_path))}</code></a></div>'
        )

    creative_tiles = "\n".join(
        _render_creative_tile(ratio_name, output_path, campaign_output_dir, project_root)
        for ratio_name, output_path in (entry.get("outputs") or {}).items()
    )

    return f"""        <article class="card">
          <div class="card-header">
            <div>
              <h3>{escape(str(entry.get("locale") or "Locale"))}</h3>
              <div class="details">
                <span>{escape(str(entry.get("region") or "Unknown region"))}</span>
                <span>{escape(str(entry.get("campaign_message") or ""))}</span>
                <span>{escape(str(entry.get("cta") or "No CTA"))}</span>
                <span>{escape(str(entry.get("asset_provenance") or "unknown"))}{warning_text}</span>
              </div>
            </div>
            <span class="{badge_class}">{badge_text}</span>
          </div>
          {asset_html}
          <div class="creative-grid">
{creative_tiles}
          </div>
        </article>"""


def _render_creative_tile(
    ratio_name: str,
    output_path: str,
    campaign_output_dir: Path,
    project_root: Path,
) -> str:
    href = _relative_href(_project_path(output_path, project_root), campaign_output_dir)
    ratio_class = "ratio-" + "".join(
        character if character.isalnum() else "x" for character in str(ratio_name)
    )
    return f"""            <figure class="creative {escape(ratio_class)}">
              <img src="{href}" alt="{escape(str(ratio_name))} creative">
              <a href="{href}">{escape(str(ratio_name))}</a>
            </figure>"""


def _project_path(path_value: object, project_root: Path) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    return project_root / path


def _relative_href(target_path: Path, from_dir: Path) -> str:
    relative_path = os.path.relpath(target_path.resolve(), from_dir.resolve())
    return quote(Path(relative_path).as_posix(), safe="/")
