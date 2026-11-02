import unittest

from tools.common import load_case
from tools.scene import build_scene, count_check


class SceneTest(unittest.TestCase):
    def test_plate_counts_match_design(self):
        """코드가 배치한 접시 물건 수를 이미지에서 다시 세면 설계값과 항상 같다."""
        case = load_case("001")
        self.assertEqual(count_check(build_scene(case), case), [])

    def test_all_plate_combinations(self):
        """바나나+껍질 1~4개의 모든 조합에서도 일치한다."""
        case = load_case("001")
        s = case["suspects"][0]
        for total in range(1, 5):
            for peels in range(total + 1):
                s["props"] = {"bananas": total - peels, "peels": peels, "slippers": 2}
                self.assertEqual(count_check(build_scene(case), case), [], (total, peels))


if __name__ == "__main__":
    unittest.main()
