"""공통 유틸: 경로, 사건 로드, 상수."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"
INPUT = ROOT / "input"
OUT = ROOT / "out"

# 위치 코드: L0(좌상) R0(우상) L1(좌중) R1(우중) L2(좌하) R2(우하, 피해자 방)
POSITIONS = ["L0", "R0", "L1", "R1", "L2", "R2"]
VICTIM_POS = "R2"
POS_KO = {"L0": "좌상", "R0": "우상", "L1": "좌중", "R1": "우중", "L2": "좌하", "R2": "우하"}
POS_EN = {"L0": "top-left", "R0": "top-right", "L1": "middle-left",
          "R1": "middle-right", "L2": "bottom-left", "R2": "bottom-right"}

MAX_SUSPECTS = 5
MAX_PLATE_ITEMS = 4


def case_path(case_id: str) -> Path:
    return CASES / f"case_{case_id}.json"


def load_case(case_id: str) -> dict:
    p = case_path(case_id)
    if not p.exists():
        raise SystemExit(f"[오류] 사건 파일이 없습니다: {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def out_dir(case_id: str) -> Path:
    d = OUT / case_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def props(s: dict) -> dict:
    p = {"bananas": 0, "peels": 0, "slippers": 0}
    p.update(s.get("props", {}))
    return p


def plate_items(s: dict) -> int:
    """접시 위 물건 수 = 남은 바나나 + 껍질."""
    p = props(s)
    return p["bananas"] + p["peels"]


def suspect_by_id(case: dict, sid: str):
    for s in case.get("suspects", []):
        if s.get("id") == sid:
            return s
    return None
