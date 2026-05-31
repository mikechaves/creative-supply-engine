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
    provenance_counts = _count_asset_provenance(localized_outputs)
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
    provenance_summary = _render_provenance_summary(provenance_counts, len(warnings))
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

    .summary-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 20px;
    }}

    .summary-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 999px;
      padding: 6px 11px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }}

    .summary-chip strong {{
      color: var(--ink);
      font-size: 15px;
    }}

    .summary-chip.generated {{
      border-color: #b8d8cd;
      background: #ecf8f3;
    }}

    .summary-chip.placeholder,
    .summary-chip.warn {{
      border-color: #e5c68f;
      background: #fff8e8;
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

    .badge-stack {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 6px;
      min-width: 120px;
    }}

    .badge {{
      display: inline-flex;
      flex: 0 0 auto;
      align-items: center;
      align-self: flex-start;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 700;
      background: #e8f4ee;
      color: var(--ok);
    }}

    .badge.generated {{
      background: #eef3fb;
      color: #285a8c;
    }}

    .badge.placeholder,
    .badge.warn {{
      background: #fff2d9;
      color: var(--warn);
    }}

    .badge.reused {{
      background: #e8f4ee;
      color: var(--ok);
    }}

    .badge.unknown {{
      background: #eef0ef;
      color: var(--muted);
    }}

    .details {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin-top: 9px;
    }}

    .card-warnings {{
      margin: 0;
      padding: 12px 16px 14px 34px;
      border-bottom: 1px solid var(--line);
      background: #fff8e8;
      color: #5e3d0b;
      font-size: 13px;
      line-height: 1.4;
    }}

    .card-warnings li + li {{
      margin-top: 5px;
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
    {provenance_summary}
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


def _count_asset_provenance(entries: list[dict]) -> dict[str, int]:
    counts = {
        "reused_local": 0,
        "generated_openai": 0,
        "generated_placeholder": 0,
        "unknown": 0,
    }
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        provenance = str(entry.get("asset_provenance") or "unknown")
        if provenance not in counts:
            provenance = "unknown"
        counts[provenance] += 1
    return counts


def _render_provenance_summary(provenance_counts: dict[str, int], warning_count: int) -> str:
    chips = (
        ("reused", "Reused heroes", provenance_counts.get("reused_local", 0)),
        ("generated", "Generated heroes", provenance_counts.get("generated_openai", 0)),
        (
            "placeholder",
            "Placeholder heroes",
            provenance_counts.get("generated_placeholder", 0),
        ),
        ("unknown", "Unknown provenance", provenance_counts.get("unknown", 0)),
        ("warn", "Run warnings", warning_count),
    )
    chip_html = "\n".join(
        f'      <span class="summary-chip {escape(css_class)}">'
        f"<strong>{count}</strong>{escape(label)}</span>"
        for css_class, label, count in chips
        if count
    )
    if not chip_html:
        return ""
    return f"""<section class="summary-strip" aria-label="Asset and warning summary">
{chip_html}
    </section>"""


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
    warnings = entry.get("warnings") or []
    status_badges = _render_status_badges(entry, compliance, passed, len(warnings))
    warning_list = _render_card_warnings(warnings)
    asset_path = entry.get("hero_source_path") or entry.get("saved_hero_path")
    asset_html = _render_asset_row(entry, asset_path, campaign_output_dir, project_root)

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
                <span>{escape(_asset_provenance_label(entry.get("asset_provenance")))}</span>
              </div>
            </div>
            <div class="badge-stack" aria-label="Set status">
{status_badges}
            </div>
          </div>
          {warning_list}
          {asset_html}
          <div class="creative-grid">
{creative_tiles}
          </div>
        </article>"""


def _render_status_badges(
    entry: dict,
    compliance: dict,
    passed: bool,
    warning_count: int,
) -> str:
    badges = [
        ("badge" if passed else "badge warn", "Passed" if passed else "Review"),
    ]
    provenance_class, provenance_label = _asset_provenance_badge(
        entry.get("asset_provenance")
    )
    badges.append((provenance_class, provenance_label))
    logo_label = _logo_status_label(compliance)
    if logo_label:
        badges.append(("badge warn", logo_label))
    warning_class = "badge warn" if warning_count else "badge unknown"
    badges.append((warning_class, f"{warning_count} warning(s)"))
    return "\n".join(
        f'              <span class="{escape(css_class)}">{escape(label)}</span>'
        for css_class, label in badges
    )


def _render_card_warnings(warnings: list[str]) -> str:
    if not warnings:
        return ""
    items = "\n".join(
        f"            <li>{escape(str(warning))}</li>" for warning in warnings
    )
    return f"""<ul class="card-warnings" aria-label="Localized set warnings">
{items}
          </ul>"""


def _render_asset_row(
    entry: dict,
    asset_path: object,
    campaign_output_dir: Path,
    project_root: Path,
) -> str:
    provenance = str(entry.get("asset_provenance") or "")
    if asset_path:
        asset_href = _relative_href(
            _project_path(asset_path, project_root),
            campaign_output_dir,
        )
        asset_label = "Hero asset"
        if entry.get("saved_hero_path"):
            asset_label = "Saved generated hero"
        if entry.get("hero_source_path"):
            asset_label = "Reused hero source"
        return (
            f'<div class="asset-row">{asset_label}: '
            f'<a href="{asset_href}"><code>{escape(str(asset_path))}</code></a></div>'
        )
    if provenance == "generated_placeholder":
        return (
            '<div class="asset-row">Placeholder hero generated for this run; '
            "no reusable hero asset was saved.</div>"
        )
    return '<div class="asset-row">No hero asset path recorded.</div>'


def _asset_provenance_badge(provenance: object) -> tuple[str, str]:
    provenance_value = str(provenance or "")
    if provenance_value == "reused_local":
        return "badge reused", "Reused hero"
    if provenance_value == "generated_openai":
        return "badge generated", "Generated hero"
    if provenance_value == "generated_placeholder":
        return "badge placeholder", "Placeholder hero"
    return "badge unknown", "Unknown hero"


def _asset_provenance_label(provenance: object) -> str:
    _, label = _asset_provenance_badge(provenance)
    return label


def _logo_status_label(compliance: dict) -> str | None:
    logo = compliance.get("logo") if isinstance(compliance, dict) else None
    if not isinstance(logo, dict) or not logo.get("required"):
        return None
    if not logo.get("configured_path"):
        return "Logo missing"
    if not logo.get("file_exists"):
        return "Logo missing"
    if not logo.get("applied_to_all_outputs"):
        return "Logo not applied"
    return None


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
