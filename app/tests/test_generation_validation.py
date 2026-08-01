import asyncio
import io
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from backend import catalog
from backend import sizes
from backend.generation import ASPECT_PRESETS
from backend.main import (
    MAX_UPLOAD_BYTES,
    _resolve_local_model_revision,
    _save_uploaded_image,
    _validate_local_size_selection,
    _validate_generation_controls,
)


class GenerationValidationTests(unittest.TestCase):
    def _valid_controls(self, **overrides):
        values = {
            "prompt": "a test image",
            "width": 512,
            "height": 512,
            "steps": 4,
            "guidance": 3.5,
            "seed": 123,
            "quantize": None,
            "lora_names": [],
            "lora_scales": [],
        }
        values.update(overrides)
        return values

    def test_rejects_mflux_zero_division_step(self):
        with self.assertRaises(HTTPException) as raised:
            _validate_generation_controls(**self._valid_controls(steps=1))
        self.assertEqual(raised.exception.status_code, 422)

    def test_generation_presets_come_from_local_catalog_defaults(self):
        self.assertEqual(ASPECT_PRESETS, sizes.local_default_presets())
        self.assertEqual(ASPECT_PRESETS["16:9"], (1280, 720))

    def test_genstudio_ladder_is_ordered_true_ratio_and_has_1k_2k(self):
        options = sizes.local_aspect_options()
        self.assertEqual([item["ratio"] for item in options[:3]], ["16:9", "9:16", "1:1"])
        expected = {
            "16:9": ((1280, 720), (2560, 1440)),
            "9:16": ((720, 1280), (1440, 2560)),
            "1:1": ((1024, 1024), (1984, 1984)),
            "4:3": ((1152, 864), (2304, 1728)),
            "3:4": ((864, 1152), (1728, 2304)),
            "3:2": ((1200, 800), (2400, 1600)),
            "2:3": ((800, 1200), (1600, 2400)),
            "5:4": ((1120, 896), (2160, 1728)),
            "4:5": ((896, 1120), (1728, 2160)),
            "21:9": ((1680, 720), (3024, 1296)),
            "2:1": ((1408, 704), (2816, 1408)),
            "1:2": ((704, 1408), (1408, 2816)),
        }
        for item in options:
            sizes_by_tier = {size["resolution"]: (size["width"], size["height"]) for size in item["sizes"]}
            self.assertEqual((sizes_by_tier["1K"], sizes_by_tier["2K"]), expected[item["ratio"]])
            for width, height in sizes_by_tier.values():
                self.assertEqual(width % 16, 0)
                self.assertEqual(height % 16, 0)
                self.assertEqual(width / height, int(item["ratio"].split(":")[0]) / int(item["ratio"].split(":")[1]))

    def test_rejects_unbounded_dimensions_and_lora_mismatch(self):
        with self.assertRaises(HTTPException):
            _validate_generation_controls(**self._valid_controls(width=4096, height=4096))
        with self.assertRaises(HTTPException):
            _validate_generation_controls(**self._valid_controls(lora_names=["one"], lora_scales=[0.5, 0.6]))

    def test_rejects_local_resolution_dimension_mismatch(self):
        with self.assertRaises(HTTPException) as raised:
            _validate_local_size_selection(
                repo="AITRADER/FLUX2-klein-4B-mlx-4bit",
                aspect_ratio="16:9",
                resolution="2K",
                width=1280,
                height=720,
                is_cloud=False,
            )
        self.assertEqual(raised.exception.status_code, 422)

    def test_rejects_invalid_or_oversized_uploads(self):
        invalid = UploadFile(file=io.BytesIO(b"not an image"), filename="input.png")
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(_save_uploaded_image(invalid))
        self.assertEqual(raised.exception.status_code, 400)

        oversized = UploadFile(file=io.BytesIO(b"x" * (MAX_UPLOAD_BYTES + 1)), filename="input.png")
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(_save_uploaded_image(oversized))
        self.assertEqual(raised.exception.status_code, 413)

    def test_edit_profiles_hide_ignored_strength_control(self):
        qwen = catalog.get_model("Qwen/Qwen-Image-Edit-2509")
        fibo = catalog.get_model("briaai/Fibo-Edit")
        self.assertFalse(catalog.generation_profile(qwen)["controls"]["image_strength"])
        self.assertFalse(catalog.generation_profile(fibo)["controls"]["image_strength"])

    def test_explicit_cached_revision_can_be_used_after_main_ref_moves(self):
        with patch("backend.main.cache.snapshot_path", return_value=object()):
            self.assertEqual(_resolve_local_model_revision("owner/model", "a" * 40), "a" * 40)


if __name__ == "__main__":
    unittest.main()
