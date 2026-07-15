import asyncio
import io
import unittest

from fastapi import HTTPException, UploadFile
from backend import catalog
from backend.main import (
    MAX_UPLOAD_BYTES,
    _save_uploaded_image,
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

    def test_rejects_unbounded_dimensions_and_lora_mismatch(self):
        with self.assertRaises(HTTPException):
            _validate_generation_controls(**self._valid_controls(width=4096, height=4096))
        with self.assertRaises(HTTPException):
            _validate_generation_controls(**self._valid_controls(lora_names=["one"], lora_scales=[0.5, 0.6]))

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


if __name__ == "__main__":
    unittest.main()
