"""논리 검증기 (FR-2) + 난이도 자동 계산 (FR-3).

verify_case(case) -> Result(errors, warnings, implicated, computed_difficulty)
오류가 하나라도 있으면 그림 단계로 넘어가지 않는다.
"""
from dataclasses import dataclass, field

from tools.common import (MAX_PLATE_ITEMS, MAX_SUSPECTS, POSITIONS, VICTIM_POS,
                          plate_items, props)

REQUIRED = ["id", "title", "difficulty", "premise", "culprit", "suspects",
            "clues", "explanation"]
DIFFICULTIES = ["easy", "normal", "hard"]
CLUE_TYPES = ["peel_balance", "slipper_missing", "custom"]


@dataclass
class Result:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    implicated: dict = field(default_factory=dict)  # clue id -> [suspect ids]
    computed_difficulty: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def missing_peels(case: dict, s: dict) -> int:
    start = case.get("world", {}).get("banana_start", 0)
    p = props(s)
    return start - p["bananas"] - p["peels"]


def missing_slippers(case: dict, s: dict) -> int:
    pair = case.get("world", {}).get("slipper_pair", 2)
    return pair - props(s)["slippers"]


def implicated_by(case: dict, clue: dict) -> list:
    t = clue.get("type")
    suspects = case.get("suspects", [])
    if t == "peel_balance":
        return [s["id"] for s in suspects if missing_peels(case, s) > 0]
    if t == "slipper_missing":
        return [s["id"] for s in suspects if missing_slippers(case, s) > 0]
    if t == "custom":
        return list(clue.get("implicates", []))
    return []


def compute_difficulty(case: dict, implicated: dict) -> str | None:
    culprit = case.get("culprit")
    keys = [c for c in case.get("clues", []) if c.get("role") == "key"]
    has_herring = any(c.get("role") == "herring" for c in case.get("clues", []))
    if not keys:
        return None
    single = any(implicated.get(c["id"]) == [culprit] for c in keys)
    if single and not has_herring:
        return "easy"
    if single or not has_herring:
        return "normal"
    return "hard"


def verify_case(case: dict) -> Result:
    r = Result()

    # 0. 필수 필드
    for k in REQUIRED:
        if k not in case:
            r.errors.append(f"필수 항목 누락: {k}")
    if r.errors:
        return r

    suspects = case["suspects"]
    clues = case["clues"]
    culprit = case["culprit"]
    ids = [s.get("id") for s in suspects]
    poss = [s.get("pos") for s in suspects]

    # 1. 용의자 id / 위치
    if len(ids) != len(set(ids)):
        r.errors.append(f"용의자 id 중복: {ids}")
    if len(poss) != len(set(poss)):
        r.errors.append(f"용의자 위치 중복: {poss}")
    for s in suspects:
        if s.get("pos") not in POSITIONS:
            r.errors.append(f"{s.get('id')}: 알 수 없는 위치 코드 {s.get('pos')}")
        elif s.get("pos") == VICTIM_POS:
            r.errors.append(f"{s.get('id')}: {VICTIM_POS}는 피해자 방이라 용의자를 둘 수 없음")
        for k, v in props(s).items():
            if not isinstance(v, int) or v < 0:
                r.errors.append(f"{s.get('id')}: 소품 {k} 값이 올바르지 않음 ({v})")
    if culprit not in ids:
        r.errors.append(f"범인 {culprit}가 용의자 목록에 없음")
    if case["difficulty"] not in DIFFICULTIES:
        r.errors.append(f"난이도 값 오류: {case['difficulty']} (easy/normal/hard)")

    # 2. 단서 형식
    cids = [c.get("id") for c in clues]
    if len(cids) != len(set(cids)):
        r.errors.append(f"단서 id 중복: {cids}")
    for c in clues:
        if c.get("type") not in CLUE_TYPES:
            r.errors.append(f"단서 {c.get('id')}: 알 수 없는 타입 {c.get('type')}")
        if c.get("role") not in ("key", "herring"):
            r.errors.append(f"단서 {c.get('id')}: role은 key 또는 herring")
        if c.get("type") == "custom":
            bad = [x for x in c.get("implicates", []) if x not in ids]
            if not c.get("implicates"):
                r.errors.append(f"단서 {c.get('id')}: custom 단서는 implicates 필요")
            if bad:
                r.errors.append(f"단서 {c.get('id')}: 없는 용의자 지목 {bad}")
    if r.errors:
        return r

    # 3. 소품 개수 균형 (방에서 사라진 수 = 복도 수)
    uses_peel = any(c["type"] == "peel_balance" for c in clues)
    uses_slip = any(c["type"] == "slipper_missing" for c in clues)
    world = case.get("world", {})
    corridor = case.get("corridor", {})
    if uses_peel or "banana_start" in world:
        miss = {s["id"]: missing_peels(case, s) for s in suspects}
        neg = [k for k, v in miss.items() if v < 0]
        if neg:
            r.errors.append(f"바나나+껍질이 시작 개수({world.get('banana_start')})보다 많은 방: {neg}")
        total = sum(v for v in miss.values() if v > 0)
        if total != corridor.get("peels", 0):
            r.errors.append(f"사라진 껍질 합계 {total} ≠ 복도 껍질 {corridor.get('peels', 0)}")
    if uses_slip or "slipper_pair" in world:
        miss = {s["id"]: missing_slippers(case, s) for s in suspects}
        neg = [k for k, v in miss.items() if v < 0]
        if neg:
            r.errors.append(f"슬리퍼가 {world.get('slipper_pair', 2)}짝보다 많은 방: {neg}")
        total = sum(v for v in miss.values() if v > 0)
        if total != corridor.get("slippers", 0):
            r.errors.append(f"사라진 슬리퍼 합계 {total} ≠ 복도 슬리퍼 {corridor.get('slippers', 0)}")

    # 4. 단서 지목
    for c in clues:
        r.implicated[c["id"]] = implicated_by(case, c)
    keys = [c for c in clues if c["role"] == "key"]
    herrings = [c for c in clues if c["role"] == "herring"]
    if not keys:
        r.errors.append("핵심 단서(key)가 하나도 없음")
    for c in keys:
        if culprit not in r.implicated[c["id"]]:
            r.errors.append(f"핵심 단서 {c['id']}가 범인 {culprit}를 지목하지 않음 (지목: {r.implicated[c['id']]})")
    if keys:
        inter = set(ids)
        for c in keys:
            inter &= set(r.implicated[c["id"]])
        if len(inter) != 1:
            r.errors.append(f"핵심 단서 교집합이 1명이 아님: {sorted(inter) or '없음'}")
    for c in herrings:
        innocents = [x for x in r.implicated[c["id"]] if x != culprit]
        if not innocents:
            r.errors.append(f"가짜 단서 {c['id']}가 무고한 용의자를 지목하지 않음")

    # 5. 경고
    if len(suspects) > MAX_SUSPECTS:
        r.warnings.append(f"용의자 {len(suspects)}명 (권장 {MAX_SUSPECTS}명 이하)")
    for s in suspects:
        n = plate_items(s)
        if n > MAX_PLATE_ITEMS:
            r.warnings.append(f"{s['id']} 접시 위 물건 {n}개 (권장 {MAX_PLATE_ITEMS}개 이하)")
    r.computed_difficulty = compute_difficulty(case, r.implicated)
    if r.computed_difficulty and r.computed_difficulty != case["difficulty"]:
        r.warnings.append(f"선언 난이도 {case['difficulty']} ≠ 계산 난이도 {r.computed_difficulty}")
    return r


def format_report(case: dict, r: Result) -> str:
    lines = [f"[CASE {case.get('id')}] 검증 결과: {'통과' if r.ok else '실패'}"]
    if r.implicated:
        lines.append("단서별 지목:")
        for c in case.get("clues", []):
            lines.append(f"  - {c['id']} ({c.get('role')}, {c.get('type')}): {r.implicated.get(c['id'])}")
    if r.computed_difficulty:
        lines.append(f"난이도: 선언 {case.get('difficulty')} / 계산 {r.computed_difficulty}")
    for e in r.errors:
        lines.append(f"[오류] {e}")
    for w in r.warnings:
        lines.append(f"[경고] {w}")
    return "\n".join(lines)
