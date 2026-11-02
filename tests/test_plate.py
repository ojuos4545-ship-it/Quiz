"""접시 직접 합성 테스트: 조각 수 = 설계값, 조각끼리 안 닿음, 접시 밖 침범 없음."""
import itertools
import unittest

from PIL import Image, ImageDraw

from tools.common import load_case
from tools.plate import LAYOUTS, components, plate_geom, rebuild_plate


def blank_art(size=1254):
    img = Image.new("RGB", (size, size), (200, 150, 90))
    d = ImageDraw.Draw(img)
    for pos in ["L0", "R0", "L1", "R1", "L2"]:
        cx, cy, r = plate_geom(img, pos)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 250), outline=(30, 30, 30), width=3)
    return img


class TestPlate(unittest.TestCase):
    def test_case_001_counts(self):
        case = load_case("001")
        img = blank_art()
        for s in case["suspects"]:
            img = rebuild_plate(img, case, s["id"])
        for s in case["suspects"]:
            p = s["props"]
            self.assertEqual(len(components(img, s["pos"])), p["bananas"] + p["peels"], f"{s['id']}방")

    def test_all_layouts_separate_and_inside(self):
        base = blank_art()
        cx, cy, r = plate_geom(base, "L0")
        ring = [(x, y) for y in range(int(cy - 1.3 * r), int(cy + 1.3 * r))
                for x in range(int(cx - 1.3 * r), int(cx + 1.3 * r))
                if 0.93 * r < ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 < 1.3 * r]
        for n in LAYOUTS:
            for combo in itertools.product("bp", repeat=n):
                case = {"suspects": [{"id": "X", "pos": "L0",
                                      "props": {"bananas": combo.count("b"), "peels": combo.count("p")}}]}
                img = rebuild_plate(base, case, "X")
                with self.subTest(combo="".join(combo)):
                    self.assertEqual(len(components(img, "L0")), n, "조각이 붙음")
                    self.assertFalse(any(img.getpixel(p) != base.getpixel(p) for p in ring), "접시 밖 침범")


if __name__ == "__main__":
    unittest.main()
