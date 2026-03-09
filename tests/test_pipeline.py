from __future__ import annotations

import base64
from contextlib import redirect_stderr
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from PIL import Image

from src.brief_loader import BriefValidationError, load_brief
from src.config import default_config
from src.image_generator import GeneratedImageResult, ImageGenerator, OpenAIImageGenerator
from src.main import main, run_pipeline


class FakeGenerator(ImageGenerator):
    def __init__(self, provenance: str, warning: str | None = None) -> None:
        self.provenance = provenance
        self.warning = warning
        self.calls: list[tuple[str, tuple[int, int]]] = []

    def generate(self, prompt: str, size: tuple[int, int]) -> GeneratedImageResult:
        self.calls.append((prompt, size))
        image = Image.new("RGBA", size, "#7f9c6b")
        return GeneratedImageResult(
            image=image,
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
    def test_load_brief_raises_for_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            brief_path = Path(temp_dir) / "campaign.yaml"
            brief_path.write_text(
                "campaign_name: Demo\nregion: US\ntarget_audience: Everyone\nproducts: []\n",
                encoding="utf-8",
            )
            with self.assertRaises(BriefValidationError):
                load_brief(brief_path)

    def test_load_brief_raises_for_malformed_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            brief_path = Path(temp_dir) / "campaign.yaml"
            brief_path.write_text("campaign_name: [oops\n", encoding="utf-8")
            with self.assertRaises(BriefValidationError):
                load_brief(brief_path)

    def test_pipeline_reuses_local_asset_and_persists_openai_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
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

            self.assertEqual(len(generator.calls), 1)
            self.assertTrue(log_path.exists())
            oat_hero_path = project_root / "assets" / "oat-energy-bar" / "hero.png"
            self.assertTrue(oat_hero_path.exists())
            citrus_entry = run_log["products"][0]
            oat_entry = run_log["products"][1]
            self.assertEqual(citrus_entry["asset_provenance"], "reused_local")
            self.assertEqual(oat_entry["asset_provenance"], "generated_openai")
            self.assertEqual(oat_entry["saved_hero_path"], "assets/oat-energy-bar/hero.png")
            for ratio, expected_size in {
                "1x1": (1080, 1080),
                "9x16": (1080, 1920),
                "16x9": (1920, 1080),
            }.items():
                final_path = project_root / oat_entry["outputs"][ratio]
                self.assertTrue(final_path.exists())
                with Image.open(final_path) as output_image:
                    self.assertEqual(output_image.size, expected_size)

    def test_pipeline_uses_placeholder_without_polluting_asset_library(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
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

            oat_entry = run_log["products"][1]
            self.assertEqual(oat_entry["asset_provenance"], "generated_placeholder")
            self.assertIsNone(oat_entry["saved_hero_path"])
            self.assertFalse(
                (project_root / "assets" / "oat-energy-bar" / "hero.png").exists()
            )
            self.assertTrue(run_log["warnings"])

    def test_pipeline_regenerates_when_local_asset_is_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
            corrupted_path = (
                project_root / "assets" / "citrus-sparkling-water" / "hero.png"
            )
            corrupted_path.write_bytes(b"not-an-image")
            generator = FakeGenerator(provenance="generated_openai")

            run_log, _ = run_pipeline(
                brief_path=project_root / "briefs" / "campaign.yaml",
                config=default_config(project_root),
                generator=generator,
            )

            self.assertEqual(len(generator.calls), 2)
            citrus_entry = run_log["products"][0]
            self.assertEqual(citrus_entry["asset_provenance"], "generated_openai")
            self.assertEqual(
                citrus_entry["saved_hero_path"],
                "assets/citrus-sparkling-water/hero.png",
            )
            self.assertIsNone(citrus_entry["hero_source_path"])
            self.assertTrue(
                any(
                    "Local hero asset could not be opened and was ignored"
                    in warning
                    for warning in citrus_entry["warnings"]
                )
            )
            with Image.open(project_root / "assets" / "citrus-sparkling-water" / "hero.png") as image:
                self.assertEqual(image.size, (1024, 1024))

    def test_run_log_contains_concise_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            self._create_project_structure(project_root)
            self._write_brief(project_root)
            self._write_image(
                project_root / "assets" / "citrus-sparkling-water" / "hero.png",
                (1200, 900),
                "#ffd56b",
            )
            generator = FakeGenerator(provenance="generated_openai")

            _, log_path = run_pipeline(
                brief_path=project_root / "briefs" / "campaign.yaml",
                config=default_config(project_root),
                generator=generator,
            )

            payload = json.loads(log_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["campaign_slug"], "summer-citrus-reset")
            self.assertIn("warnings", payload)
            self.assertEqual(len(payload["products"]), 2)
            self.assertEqual(
                sorted(payload["products"][1]["outputs"].keys()),
                ["16x9", "1x1", "9x16"],
            )

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
            responses=[
                {
                    "created": 1234567890,
                    "data": [{"b64_json": encoded_image}],
                }
            ]
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            result = generator.generate("A polished product hero shot", (1024, 1024))

        self.assertEqual(result.provenance, "generated_openai")
        self.assertIsNone(result.warning)
        self.assertEqual(result.image.size, (1024, 1024))
        self.assertEqual(
            generator.requests,
            ["https://api.openai.com/v1/images/generations"],
        )

    def test_openai_generator_downloads_url_image_response(self) -> None:
        generator = StubOpenAIImageGenerator(
            responses=[
                {
                    "created": 1234567890,
                    "data": [{"url": "https://example.com/generated-hero.png"}],
                }
            ]
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            result = generator.generate("A polished product hero shot", (1024, 1024))

        self.assertEqual(result.provenance, "generated_openai")
        self.assertIsNone(result.warning)
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
            responses=[
                {
                    "created": 1234567890,
                    "data": [{"url": "https://example.com/generated-hero.png"}],
                }
            ]
        )

        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_IMAGE_MODEL": "gpt-image-1-mini",
            },
            clear=True,
        ):
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

    def _write_brief(self, project_root: Path) -> None:
        brief_path = project_root / "briefs" / "campaign.yaml"
        brief_path.write_text(
            "\n".join(
                [
                    "campaign_name: Summer Citrus Reset",
                    "region: North America",
                    "target_audience: Busy professionals looking for clean-label convenience snacks",
                    "campaign_message: Reset your routine with bright flavor and steady energy.",
                    "products:",
                    "  - name: citrus-sparkling-water",
                    "  - name: oat-energy-bar",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_image(self, path: Path, size: tuple[int, int], color: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGBA", size, color)
        image.save(path)


if __name__ == "__main__":
    unittest.main()
