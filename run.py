"""추리 퍼즐 콘텐츠 자동화 명령어 진입점.

python run.py verify NNN
python run.py prompt NNN [--fix A,D]
python run.py compose NNN
python run.py review NNN
python run.py all NNN
python run.py sprite NNN --room A --index 0 --name banana   (그림에서 조각 저장, 한 번만)
python run.py scene NNN                                  (방식 B 프로토타입: 소품을 코드로 배치한 그림 → input/NNN.png)
python run.py plate NNN --rooms A                          (지정한 방 접시를 설계값대로 다시 그림)
"""
import argparse
import sys

from tools.common import load_case, out_dir
from tools.verify import format_report, verify_case


def cmd_verify(cid: str, quiet=False):
    case = load_case(cid)
    r = verify_case(case)
    report = format_report(case, r)
    (out_dir(cid) / "report.txt").write_text(report + "\n", encoding="utf-8")
    if not quiet or not r.ok:
        print(report)
    return case, r


def require_ok(cid: str):
    case, r = cmd_verify(cid, quiet=True)
    if not r.ok:
        sys.exit(f"\n[중단] CASE {cid} 검증 실패. 사건 JSON을 먼저 고치세요.")
    return case, r


def cmd_prompt(cid: str, fix: str | None):
    from tools.make_prompt import build_fix_prompt, build_prompt
    case, _ = require_ok(cid)
    d = out_dir(cid)
    if fix:
        rooms = [x.strip().upper() for x in fix.split(",") if x.strip()]
        txt = build_fix_prompt(case, rooms)
        path = d / f"gpt_fix_{''.join(rooms)}.txt"
    else:
        txt = build_prompt(case)
        path = d / "gpt_prompt.txt"
    path.write_text(txt, encoding="utf-8")
    print(f"[완료] {path.relative_to(d.parent.parent)}")


def cmd_compose(cid: str):
    from tools.compose import compose
    case, _ = require_ok(cid)
    d = out_dir(cid)
    info = compose(case, d)
    print(f"[완료] out/{cid}/puzzle.png, out/{cid}/answer.png  (폰트: {info['font']})")
    if info["placeholder"]:
        print(f"[주의] input/{cid}.png 이 없어 임시 그림으로 합성했습니다. GPT 그림을 저장한 뒤 다시 실행하세요.")


def cmd_review(cid: str):
    from tools.review_pack import build_caption, build_review_request
    case, r = require_ok(cid)
    d = out_dir(cid)
    (d / "review_request.md").write_text(build_review_request(case, r.computed_difficulty), encoding="utf-8")
    (d / "caption.txt").write_text(build_caption(case), encoding="utf-8")
    print(f"[완료] out/{cid}/review_request.md, out/{cid}/caption.txt")


def _art_path(cid: str):
    from tools.common import INPUT
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = INPUT / f"{cid}.{ext}"
        if p.exists():
            return p
    sys.exit(f"[오류] input/{cid}.png 이 없습니다.")


def cmd_sprite(cid: str, room: str, index: int, name: str):
    from PIL import Image
    from tools.common import suspect_by_id
    from tools.plate import extract_sprite
    case = load_case(cid)
    s = suspect_by_id(case, room)
    if not s:
        sys.exit(f"[오류] 없는 방: {room}")
    path = extract_sprite(Image.open(_art_path(cid)), s["pos"], index, name)
    print(f"[완료] {path}")


def cmd_plate(cid: str, rooms: str):
    from PIL import Image
    from tools.plate import rebuild_plate
    case, _ = require_ok(cid)
    src = _art_path(cid)
    orig = src.with_name(f"{cid}_orig{src.suffix}")
    if not orig.exists():  # GPT 원본은 한 번만 백업하고, 항상 원본에서 다시 합성
        orig.write_bytes(src.read_bytes())
    img = Image.open(orig)
    ids = [x.strip().upper() for x in rooms.split(",") if x.strip()]
    for sid in ids:
        img = rebuild_plate(img, case, sid)
    out = src.with_suffix(".png")
    img.save(out)
    print(f"[완료] {', '.join(ids)}방 접시를 설계값대로 다시 그림 → {out.name} (원본: {orig.name})")


def cmd_scene(cid: str, ai: bool = False):
    from tools.common import INPUT
    from tools.scene import build_scene, build_skeleton, count_check
    case, _ = require_ok(cid)
    base = None
    if ai:
        from tools.gen_art import generate_art
        base = generate_art(case, build_skeleton(case))
        base.save(INPUT / f"{cid}_base.png")  # AI가 그린 배경+인물 (소품 없음). 마음에 들면 재사용
        print(f"[AI] 배경+인물 생성 완료 → input/{cid}_base.png")
    img = build_scene(case, base)
    bad = count_check(img, case)
    path = INPUT / f"{cid}.png"
    img.save(path)
    print(f"[완료] {path.relative_to(INPUT.parent)} (프로토타입 장면, 소품 개수는 설계값대로 코드가 배치)")
    if bad:
        sys.exit("[경고] 접시 개수 자동 검수 불일치: " + ", ".join(f"{i}방 설계 {a} / 이미지 {b}" for i, a, b in bad))
    print("[검수] 모든 방 접시 개수가 설계값과 일치합니다.")


def main():
    ap = argparse.ArgumentParser(description="추리 퍼즐 콘텐츠 자동화")
    ap.add_argument("command", choices=["verify", "prompt", "compose", "review", "all", "sprite", "plate", "scene"])
    ap.add_argument("case_id", help="사건 번호 (예: 001)")
    ap.add_argument("--fix", help="부분 수정할 방 (예: A,D)")
    ap.add_argument("--ai", action="store_true", help="scene: 배경·인물을 Gemini(AI Studio)로 그림 (GEMINI_API_KEY 필요)")
    ap.add_argument("--rooms", help="plate: 접시를 다시 그릴 방 (예: A,D)")
    ap.add_argument("--room", help="sprite: 조각을 잘라올 방")
    ap.add_argument("--index", type=int, default=0, help="sprite: 접시 안 조각 번호 (위에서부터 0)")
    ap.add_argument("--name", choices=["banana", "peel"], help="sprite: 저장 이름")
    a = ap.parse_args()
    cid = a.case_id.zfill(3)

    if a.command == "verify":
        _, r = cmd_verify(cid)
        sys.exit(0 if r.ok else 1)
    if a.command == "prompt":
        cmd_prompt(cid, a.fix)
    elif a.command == "compose":
        cmd_compose(cid)
    elif a.command == "review":
        cmd_review(cid)
    elif a.command == "sprite":
        if not (a.room and a.name):
            sys.exit("[오류] --room 과 --name 이 필요합니다.")
        cmd_sprite(cid, a.room.upper(), a.index, a.name)
    elif a.command == "scene":
        cmd_scene(cid, a.ai)
    elif a.command == "plate":
        if not a.rooms:
            sys.exit("[오류] --rooms 가 필요합니다 (예: --rooms A).")
        cmd_plate(cid, a.rooms)
    elif a.command == "all":
        _, r = cmd_verify(cid)
        if not r.ok:
            sys.exit(1)
        cmd_prompt(cid, None)
        cmd_compose(cid)
        cmd_review(cid)


if __name__ == "__main__":
    main()
