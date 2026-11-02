"""검증기 테스트: python -m unittest discover tests"""
import copy
import unittest

from tools.common import load_case
from tools.make_prompt import build_fix_prompt, build_prompt
from tools.verify import verify_case

BASE = load_case("001")


def mutate(fn):
    c = copy.deepcopy(BASE)
    fn(c)
    return verify_case(c)


def sus(c, sid):
    return next(s for s in c["suspects"] if s["id"] == sid)


class TestVerify(unittest.TestCase):
    def test_case_001_passes(self):
        r = verify_case(BASE)
        self.assertTrue(r.ok, r.errors)
        self.assertEqual(r.computed_difficulty, "easy")
        self.assertEqual(r.warnings, [])

    def test_wrong_culprit(self):
        r = mutate(lambda c: c.update(culprit="A"))
        self.assertFalse(r.ok)

    def test_peel_count_mismatch(self):
        # 바나나 개수 오류 재현: 접시 바나나를 하나 줄이면 사라진 껍질 합계가 복도와 안 맞음
        r = mutate(lambda c: sus(c, "A")["props"].update(bananas=1))
        self.assertTrue(any("껍질" in e for e in r.errors), r.errors)

    def test_too_many_items(self):
        r = mutate(lambda c: sus(c, "B")["props"].update(bananas=4))
        self.assertTrue(any("시작 개수" in e for e in r.errors), r.errors)

    def test_two_suspects_remain(self):
        # 슬리퍼 단서 제거 + A도 껍질 부족 → 교집합 2명
        def f(c):
            c["clues"] = [x for x in c["clues"] if x["id"] != "slipper"]
            sus(c, "A")["props"].update(bananas=1)
            c["corridor"]["peels"] = 2
        r = mutate(f)
        self.assertTrue(any("교집합" in e for e in r.errors), r.errors)

    def test_duplicate_position(self):
        r = mutate(lambda c: sus(c, "B").update(pos="L0"))
        self.assertTrue(any("위치 중복" in e for e in r.errors))

    def test_victim_room(self):
        r = mutate(lambda c: sus(c, "B").update(pos="R2"))
        self.assertFalse(r.ok)

    def test_herring_must_hit_innocent(self):
        r = mutate(lambda c: c["clues"].append(
            {"id": "h", "type": "custom", "role": "herring", "implicates": ["E"], "text": "-"}))
        self.assertTrue(any("가짜 단서" in e for e in r.errors))

    def test_difficulty_normal_with_herring(self):
        r = mutate(lambda c: c["clues"].append(
            {"id": "h", "type": "custom", "role": "herring", "implicates": ["B"], "text": "-"}))
        self.assertTrue(r.ok, r.errors)
        self.assertEqual(r.computed_difficulty, "normal")
        self.assertTrue(any("난이도" in w for w in r.warnings))

    def test_difficulty_hard(self):
        # 각 핵심 단서가 2명씩 지목 → 합쳐야 풀림 + 가짜 단서
        def f(c):
            c["clues"] = [
                {"id": "k1", "type": "custom", "role": "key", "implicates": ["C", "E"], "text": "-"},
                {"id": "k2", "type": "custom", "role": "key", "implicates": ["D", "E"], "text": "-"},
                {"id": "h", "type": "custom", "role": "herring", "implicates": ["A"], "text": "-"},
            ]
            c["difficulty"] = "hard"
        r = mutate(f)
        self.assertTrue(r.ok, r.errors)
        self.assertEqual(r.computed_difficulty, "hard")


class TestPrompt(unittest.TestCase):
    def test_prompt_counts(self):
        p = build_prompt(BASE)
        self.assertIn("A, B, C, D, E", p)
        self.assertIn("Room E", p)
        self.assertIn("1 single slipper", p)

    def test_fix_prompt(self):
        p = build_fix_prompt(BASE, ["A", "D"])
        self.assertIn("Room A", p)
        self.assertIn("Room D", p)
        self.assertNotIn("Room B", p)


if __name__ == "__main__":
    unittest.main()
