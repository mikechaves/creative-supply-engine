from __future__ import annotations

import base64
from contextlib import redirect_stderr
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from PIL import Image

from src.asset_hygiene import reset_sample_assets
from src.asset_manager import get_final_output_path
from src.brief_loader import BriefValidationError, load_brief
from src.compliance import evaluate_compliance
from src.config import default_config
from src.image_generator import GeneratedImageResult, ImageGenerator, OpenAIImageGenerator
from src.main import main, run_pipeline
from src.review_gallery import write_review_gallery
from src.smoke_demo import run_smoke_demo


class FakeGenerator(ImageGenerator):
    def __init__(self, provenance: str, warning: str | None = None) -> None:
        self.provenance = provenance
        self.warning = warning
        self.calls: list[tuple[str, tuple[int, int]]] = []

    def generate(self, prompt: str, size: tuple[int, int]) -> GeneratedImageResult:
        self.calls.append((prompt, size))
        return GeneratedImageResult(
            image=Image.new("RGBA", size, "#6c8f77"),
            provenance=self.provenance,
            warning=self.warning,
        )


class StubOpenAIImageGenerator(OpenAIImageGenerator):
    def __init__(self, responses: list[dict]) -> None:
        super().__init__(default_config(Path("/tmp")))
        self.responses = list(responses)
        self.requests: list[str] = []
        self.payloads: list[dict] = []

    def _open_json(self, request):  # type: ignore[override]
        self.requests.append(request.full_url)
        if request.data:
            self.payloads.append(json.loads(request.data.decode("utf-8")))
        if not self.responses:
            raise AssertionError("No stub response available for request.")
        return self.responses.pop(0)

    def _download_image(self, image_url: str) -> Image.Image:  # type: ignore[override]
        self.requests.append(image_url)
        return Image.new("RGBA", (1024, 1024), "#4b7f52")


class CreativeSupplyEngineTests(unittest.TestCase):
    def test_load_brief_parses_brand_and_markets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            brief_path = self._write_brief(project_root)

            brief = load_brief(brief_path)

            self.assertEqual(brief.brand.name, "Pulse Beverages")
            self.assertEqual(brief.brand.slug, "pulse-beverages")
            self.assertEqual(brief.brand.logo_path.as_posix(), "assets/common/pulse-beverages-logo.png")
            self.assertEqual(len(brief.markets), 2)
            self.assertEqual(brief.markets[0].locale, "en_US")
            self.assertEqual(brief.markets[1].cta, "Compra el reset")

    def test_load_brief_raises_for_malformed_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            brief_path = Path(temp_dir) / "campaign.yaml"
            brief_path.write_text("campaign_name: [oops\n", encoding="utf-8")
            with self.assertRaises(BriefValidationError):
                load_brief(brief_path)

    def test_load_brief_reports_multiple_authoring_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            brief_path = Path(temp_dir) / "campaign.yaml"
            brief_path.write_text(
                "\n".join(
                    [
                        "campaign_name: Authoring Errors",
                        "ratios:",
                        "  - 4x5",
                        "brand:",
                        "  name: Pulse Beverages",
                        "  slug: pulse-beverages",
                        "  colors:",
                        "    primary: \"#13324A\"",
                        "    secondary: blue",
                        "  compliance:",
                        "    require_logo: true",
                        "    prohibited_words: []",
                        "markets: []",
                        "products:",
                        "  - prompt_override: Demo",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(BriefValidationError) as context:
                load_brief(brief_path)

            message = str(context.exception)
            self.assertIn("brief authoring issue(s) found", message)
            self.assertIn("ratios is not supported", message)
            self.assertIn("brand.logo_path is required.", message)
            self.assertIn("brand.colors.secondary must be a hex color", message)
            self.assertIn("brand.colors.accent is required.", message)
            self.assertIn("brand.colors.text_light is required.", message)
            self.assertIn("markets must include at least one market", message)
            self.assertIn("products must include at least two products.", message)
            self.assertIn("products[1].name is required.", message)

    def test_load_brief_rejects_unsupported_locale_and_ratio_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            brief_path = Path(temp_dir) / "campaign.yaml"
            brief_path.write_text(
                "\n".join(
                    [
                        "campaign_name: Locale And Ratio Errors",
                        "brand:",
                        "  name: Pulse Beverages",
                        "  slug: pulse-beverages",
                        "  logo_path: assets/common/pulse-beverages-logo.png",
                        "  colors:",
                        "    primary: \"#13324A\"",
                        "    secondary: \"#214B67\"",
                        "    accent: \"#F4C542\"",
                        "    text_light: \"#F7F4ED\"",
                        "  compliance:",
                        "    require_logo: true",
                        "    prohibited_words: []",
                        "markets:",
                        "  - locale: en-US",
                        "    ratios:",
                        "      - 4x5",
                        "    region: United States",
                        "    audience: Busy professionals",
                        "    campaign_message: Bright Start.",
                        "  - locale: es_MX",
                        "    region: Mexico",
                        "    audience: Profesionales ocupados",
                        "    campaign_message: Sabor brillante.",
                        "products:",
                        "  - name: citrus-sparkling-water",
                        "    ratio: 4x5",
                        "  - name: oat-energy-bar",
                        "    ratio_specs:",
                        "      4x5: [1080, 1350]",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(BriefValidationError) as context:
                load_brief(brief_path)

            message = str(context.exception)
            self.assertIn("markets[1].locale must use locale_REGION format like en_US", message)
            self.assertIn("markets[1].ratios is not supported", message)
            self.assertIn("products[1].ratio is not supported", message)
            self.assertIn("products[2].ratio_specs is not supported", message)

    def test_localized_output_path_includes_locale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config(Path(temp_dir))
            output_path = get_final_output_path(
                config=config,
                campaign_name="Summer Citrus Reset",
                product_name="citrus-sparkling-water",
                locale="en_US",
                ratio_name="1x1",
            )
            self.assertEqual(
                output_path.relative_to(config.project_root).as_posix(),
                "outputs/summer-citrus-reset/citrus-sparkling-water/en_US/1x1/final.png",
            )

    def test_default_config_discovers_project_root_from_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
            (project_root / "src").mkdir()
            nested_dir = project_root / "briefs"
            previous_cwd = Path.cwd()
            try:
                os.chdir(nested_dir)
                config = default_config()
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(config.project_root, project_root.resolve())
            self.assertEqual(config.briefs_dir, project_root.resolve() / "briefs")

    def test_default_config_honors_explicit_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "explicit"

            config = default_config(project_root)

            self.assertEqual(config.project_root, project_root.resolve())

    def test_pipeline_creates_localized_outputs_and_compliance_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
            self._write_logo(project_root / "assets" / "common" / "pulse-beverages-logo.png")
            self._write_image(
                project_root / "assets" / "citrus-sparkling-water" / "hero.png",
                (1200, 900),
                "#ffd56b",
            )
            generator = FakeGenerator(provenance="generated_openai")

            run_log, log_path = run_pipeline(
                brief_path=project_root / "briefs" / "campaign.yaml",
                config=default_config(project_root),
                generator=generator,
            )

            self.assertTrue(log_path.exists())
            gallery_path = project_root / "outputs" / "summer-citrus-reset" / "index.html"
            self.assertTrue(gallery_path.exists())
            self.assertEqual(
                run_log["review_gallery_path"],
                "outputs/summer-citrus-reset/index.html",
            )
            self.assertEqual(len(generator.calls), 1)
            self.assertEqual(len(run_log["localized_outputs"]), 4)

            oat_en_us = next(
                entry
                for entry in run_log["localized_outputs"]
                if entry["product_slug"] == "oat-energy-bar" and entry["locale"] == "en_US"
            )
            self.assertEqual(oat_en_us["asset_provenance"], "generated_openai")
            self.assertEqual(oat_en_us["saved_hero_path"], "assets/oat-energy-bar/hero.png")
            self.assertEqual(
                oat_en_us["outputs"]["1x1"],
                "outputs/summer-citrus-reset/oat-energy-bar/en_US/1x1/final.png",
            )
            self.assertEqual(oat_en_us["cta"], "Shop the reset")
            self.assertTrue(oat_en_us["compliance"]["passed"])
            self.assertTrue(
                (project_root / "assets" / "oat-energy-bar" / "hero.png").exists()
            )
            gallery_html = gallery_path.read_text(encoding="utf-8")
            self.assertIn("Summer Citrus Reset", gallery_html)
            self.assertIn("oat-energy-bar/en_US/1x1/final.png", gallery_html)
            self.assertIn("../../assets/oat-energy-bar/hero.png", gallery_html)

    def test_review_gallery_escapes_content_and_links_relative_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            campaign_output_dir = project_root / "outputs" / "launch"
            run_log = {
                "campaign_name": "Spring <Launch>",
                "brand": {"name": "Pulse & Co"},
                "run_started_at": "2026-05-23T00:00:00+00:00",
                "warnings": ["Use <logo>"],
                "localized_outputs": [
                    {
                        "product_name": "Energy <Bar>",
                        "locale": "en_US",
                        "region": "United States",
                        "campaign_message": "<script>bad()</script>",
                        "cta": "Shop & save",
                        "asset_provenance": "generated_openai",
                        "saved_hero_path": "assets/demo hero.png",
                        "warnings": [],
                        "outputs": {
                            "1x1": "outputs/launch/energy-bar/en_US/1x1/final image.png",
                        },
                        "compliance": {"passed": False},
                    }
                ],
            }

            gallery_path = write_review_gallery(
                campaign_output_dir=campaign_output_dir,
                run_log=run_log,
                project_root=project_root,
            )

            gallery_html = gallery_path.read_text(encoding="utf-8")
            self.assertIn("Spring &lt;Launch&gt;", gallery_html)
            self.assertIn("&lt;script&gt;bad()&lt;/script&gt;", gallery_html)
            self.assertNotIn("<script>bad()</script>", gallery_html)
            self.assertIn("../../assets/demo%20hero.png", gallery_html)
            self.assertIn("energy-bar/en_US/1x1/final%20image.png", gallery_html)

    def test_review_gallery_surfaces_asset_warning_and_logo_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            run_log = {
                "campaign_name": "Launch",
                "brand": {"name": "Pulse"},
                "warnings": [
                    "Oat Bar/en_US: OpenAI API key not configured; used placeholder image.",
                    "Oat Bar/en_US: Logo is required but the configured file is missing.",
                ],
                "localized_outputs": [
                    {
                        "product_name": "Sparkling Water",
                        "locale": "en_US",
                        "region": "United States",
                        "campaign_message": "Bright Start.",
                        "cta": "Shop now",
                        "asset_provenance": "reused_local",
                        "hero_source_path": "assets/citrus-sparkling-water/hero.png",
                        "warnings": [],
                        "outputs": {"1x1": "outputs/launch/water/en_US/1x1/final.png"},
                        "compliance": {
                            "passed": True,
                            "logo": {
                                "required": True,
                                "configured_path": "assets/common/pulse-beverages-logo.png",
                                "file_exists": True,
                                "applied_to_all_outputs": True,
                            },
                        },
                    },
                    {
                        "product_name": "Oat Bar",
                        "locale": "en_US",
                        "region": "United States",
                        "campaign_message": "Steady Energy.",
                        "cta": "Shop now",
                        "asset_provenance": "generated_placeholder",
                        "warnings": [
                            "OpenAI API key not configured; used placeholder image.",
                            "Logo is required but the configured file is missing.",
                        ],
                        "outputs": {"1x1": "outputs/launch/oat/en_US/1x1/final.png"},
                        "compliance": {
                            "passed": False,
                            "logo": {
                                "required": True,
                                "configured_path": "assets/common/missing-logo.png",
                                "file_exists": False,
                                "applied_to_all_outputs": False,
                            },
                        },
                    },
                ],
            }

            gallery_path = write_review_gallery(
                campaign_output_dir=project_root / "outputs" / "launch",
                run_log=run_log,
                project_root=project_root,
            )

            gallery_html = gallery_path.read_text(encoding="utf-8")
            self.assertIn("<strong>1</strong>Reused heroes", gallery_html)
            self.assertIn("<strong>1</strong>Placeholder heroes", gallery_html)
            self.assertIn("<strong>2</strong>Run warnings", gallery_html)
            self.assertIn("Reused hero", gallery_html)
            self.assertIn("Placeholder hero", gallery_html)
            self.assertIn("2 warning(s)", gallery_html)
            self.assertIn("0 warning(s)", gallery_html)
            self.assertIn("Logo missing", gallery_html)
            self.assertIn(
                "Placeholder hero generated for this run; no reusable hero asset was saved.",
                gallery_html,
            )

    def test_review_gallery_tolerates_null_brand_and_compliance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            run_log = {
                "campaign_name": "Launch",
                "brand": None,
                "localized_outputs": [
                    {
                        "product_name": "Sparkling Water",
                        "locale": "en_US",
                        "outputs": {},
                        "compliance": None,
                    }
                ],
            }

            gallery_path = write_review_gallery(
                campaign_output_dir=project_root / "outputs" / "launch",
                run_log=run_log,
                project_root=project_root,
            )

            gallery_html = gallery_path.read_text(encoding="utf-8")
            self.assertIn("Brand creative review gallery", gallery_html)
            self.assertIn("<strong>0</strong><span>passed sets</span>", gallery_html)

    def test_pipeline_uses_placeholder_without_saving_reusable_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
            self._write_logo(project_root / "assets" / "common" / "pulse-beverages-logo.png")
            self._write_image(
                project_root / "assets" / "citrus-sparkling-water" / "hero.png",
                (1200, 900),
                "#ffd56b",
            )
            generator = FakeGenerator(
                provenance="generated_placeholder",
                warning="OpenAI image generation failed; used placeholder image.",
            )

            run_log, _ = run_pipeline(
                brief_path=project_root / "briefs" / "campaign.yaml",
                config=default_config(project_root),
                generator=generator,
            )

            oat_entries = [
                entry
                for entry in run_log["localized_outputs"]
                if entry["product_slug"] == "oat-energy-bar"
            ]
            self.assertTrue(oat_entries)
            self.assertTrue(
                all(entry["asset_provenance"] == "generated_placeholder" for entry in oat_entries)
            )
            self.assertTrue(all(entry["saved_hero_path"] is None for entry in oat_entries))
            self.assertFalse(
                (project_root / "assets" / "oat-energy-bar" / "hero.png").exists()
            )

    def test_smoke_demo_runs_in_temp_project_without_mutating_source_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
            self._write_logo(project_root / "assets" / "common" / "pulse-beverages-logo.png")
            self._write_image(
                project_root / "assets" / "citrus-sparkling-water" / "hero.png",
                (1200, 900),
                "#ffd56b",
            )
            source_oat_hero = project_root / "assets" / "oat-energy-bar" / "hero.png"
            self._write_image(source_oat_hero, (1024, 1024), "#8a6f4d")

            result = run_smoke_demo(source_root=project_root)

            self.assertEqual(result.localized_set_count, 4)
            self.assertEqual(result.creative_file_count, 12)
            self.assertEqual(result.placeholder_count, 2)
            self.assertTrue(source_oat_hero.exists())

    def test_reset_sample_assets_removes_generated_heroes_and_preserves_tracked_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            logo_path = project_root / "assets" / "common" / "pulse-beverages-logo.png"
            citrus_hero_path = project_root / "assets" / "citrus-sparkling-water" / "hero.png"
            oat_png_path = project_root / "assets" / "oat-energy-bar" / "hero.png"
            oat_jpg_path = project_root / "assets" / "oat-energy-bar" / "hero.jpg"
            output_path = project_root / "outputs" / "summer-citrus-reset" / "index.html"

            self._write_logo(logo_path)
            self._write_image(citrus_hero_path, (1200, 900), "#ffd56b")
            self._write_image(oat_png_path, (1024, 1024), "#8a6f4d")
            oat_jpg_path.write_text("generated sample hero", encoding="utf-8")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("<html></html>", encoding="utf-8")

            result = reset_sample_assets(project_root, include_outputs=True)

            self.assertFalse(oat_png_path.exists())
            self.assertFalse(oat_jpg_path.exists())
            self.assertFalse((project_root / "outputs").exists())
            self.assertTrue(logo_path.exists())
            self.assertTrue(citrus_hero_path.exists())
            self.assertIn(oat_png_path.resolve(), result.removed_paths)
            self.assertIn(oat_jpg_path.resolve(), result.removed_paths)
            self.assertIn((project_root / "outputs").resolve(), result.removed_paths)

    def test_compliance_flags_missing_required_logo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            output_path = project_root / "final.png"
            Image.new("RGBA", (1080, 1080), "#ffffff").save(output_path)

            compliance = evaluate_compliance(
                output_paths={"1x1": output_path},
                expected_sizes={"1x1": (1080, 1080)},
                campaign_message="Bright Start.",
                prohibited_words=("miracle",),
                logo_required=True,
                logo_path=project_root / "missing-logo.png",
                logo_applied_by_ratio={"1x1": False},
            )

            self.assertFalse(compliance["passed"])
            self.assertIn("Logo is required but the configured file is missing.", compliance["warnings"])

    def test_openai_generator_returns_placeholder_when_api_key_is_missing(self) -> None:
        generator = OpenAIImageGenerator(default_config(Path("/tmp")))
        with patch.dict("os.environ", {}, clear=True):
            result = generator.generate("A polished product hero shot", (1024, 1024))

        self.assertEqual(result.provenance, "generated_placeholder")
        self.assertIn("OpenAI API key not configured", result.warning or "")
        self.assertEqual(result.image.size, (1024, 1024))

    def test_openai_generator_decodes_base64_image_response(self) -> None:
        buffer = io.BytesIO()
        Image.new("RGBA", (1024, 1024), "#4b7f52").save(buffer, format="PNG")
        encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        generator = StubOpenAIImageGenerator(
            responses=[{"created": 1234567890, "data": [{"b64_json": encoded_image}]}]
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            result = generator.generate("A polished product hero shot", (1024, 1024))

        self.assertEqual(result.provenance, "generated_openai")
        self.assertEqual(result.image.size, (1024, 1024))
        self.assertEqual(generator.requests, ["https://api.openai.com/v1/images/generations"])

    def test_openai_generator_downloads_url_image_response(self) -> None:
        generator = StubOpenAIImageGenerator(
            responses=[{"created": 1234567890, "data": [{"url": "https://example.com/generated-hero.png"}]}]
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            result = generator.generate("A polished product hero shot", (1024, 1024))

        self.assertEqual(result.provenance, "generated_openai")
        self.assertEqual(result.image.size, (1024, 1024))
        self.assertEqual(
            generator.requests,
            [
                "https://api.openai.com/v1/images/generations",
                "https://example.com/generated-hero.png",
            ],
        )

    def test_openai_generator_honors_model_env_override(self) -> None:
        generator = StubOpenAIImageGenerator(
            responses=[{"created": 1234567890, "data": [{"url": "https://example.com/generated-hero.png"}]}]
        )

        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_IMAGE_MODEL": "gpt-image-1-mini",
            },
            clear=True,
        ):
            generator.generate("A polished product hero shot", (1024, 1024))

        self.assertEqual(generator.payloads[0]["model"], "gpt-image-1-mini")

    def test_main_reports_malformed_yaml_as_brief_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            brief_path = Path(temp_dir) / "campaign.yaml"
            brief_path.write_text("campaign_name: [oops\n", encoding="utf-8")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = main(["--brief", str(brief_path)])

            self.assertEqual(exit_code, 1)
            self.assertIn("Brief validation failed:", stderr.getvalue())

    def _create_project_structure(self, project_root: Path) -> None:
        for relative_dir in (
            "briefs",
            "assets/citrus-sparkling-water",
            "assets/oat-energy-bar",
            "assets/common",
            "outputs",
        ):
            (project_root / relative_dir).mkdir(parents=True, exist_ok=True)

    def _write_brief(self, project_root: Path) -> Path:
        brief_path = project_root / "briefs" / "campaign.yaml"
        brief_path.write_text(
            "\n".join(
                [
                    "campaign_name: Summer Citrus Reset",
                    "brand:",
                    "  name: Pulse Beverages",
                    "  slug: pulse-beverages",
                    "  logo_path: assets/common/pulse-beverages-logo.png",
                    "  colors:",
                    "    primary: \"#13324A\"",
                    "    secondary: \"#214B67\"",
                    "    accent: \"#F4C542\"",
                    "    text_light: \"#F7F4ED\"",
                    "  compliance:",
                    "    require_logo: true",
                    "    prohibited_words:",
                    "      - guaranteed cure",
                    "      - miracle",
                    "markets:",
                    "  - locale: en_US",
                    "    region: United States",
                    "    audience: Busy professionals",
                    "    campaign_message: Bright Start. Steady Energy.",
                    "    cta: Shop the reset",
                    "  - locale: es_MX",
                    "    region: Mexico",
                    "    audience: Profesionales ocupados",
                    "    campaign_message: Sabor brillante. Energia constante.",
                    "    cta: Compra el reset",
                    "products:",
                    "  - name: citrus-sparkling-water",
                    "  - name: oat-energy-bar",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return brief_path

    def _write_image(self, path: Path, size: tuple[int, int], color: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", size, color).save(path)

    def _write_logo(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        logo = Image.new("RGBA", (320, 96), (0, 0, 0, 0))
        logo.paste((19, 50, 74, 255), (0, 0, 320, 96))
        logo.save(path)


if __name__ == "__main__":
    unittest.main()
