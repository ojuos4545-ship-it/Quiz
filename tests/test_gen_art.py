import base64
import io
import os
import unittest
from unittest import mock

from PIL import Image

from tools import gen_art
from tools.common import load_case


class GenArtTest(unittest.TestCase):
    def test_key_missing_exits(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                gen_art.get_key()

    def test_parse_image(self):
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (1, 2, 3)).save(buf, "PNG")
        resp = {"candidates": [{"content": {"parts": [
            {"text": "ok"}, {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}}]}}]}
        self.assertEqual(gen_art.parse_image(resp).size, (8, 8))

    def test_parse_no_image_exits(self):
        with self.assertRaises(SystemExit):
            gen_art.parse_image({"candidates": [{"content": {"parts": [{"text": "sorry"}]}}]})

    def test_prompt_forbids_props(self):
        p = gen_art.build_art_prompt(load_case("001"))
        self.assertIn("EMPTY", p)
        self.assertIn("NO slippers", p)


if __name__ == "__main__":
    unittest.main()
