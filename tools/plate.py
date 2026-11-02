"""접시 직접 합성 (GPT가 개수를 계속 틀릴 때의 대응).

1) sprite: 그림 속 접시에서 바나나/껍질 조각을 잘라 assets/sprites/에 저장 (화풍 유지, 한 번만)
2) rebuild: 지정한 방의 접시를 비우고, 사건 JSON 개수대로 조각을 다시 배치

좌표는 ROOM_BOXES(방) 기준 비율이다. 구도가 바뀌면 PLATE_CENTER / PLATE_R 를 조정한다.
"""
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

from tools.common import ROOT, props
from tools.compose import ROOM_BOXES

SPRITES = ROOT / "assets" / "sprites"
PLATE_CENTER = (0.80, 0.335)  # 방 안 접시 중심 (방 폭·높이 기준 비율)
PLATE_R = 0.143               # 접시 반지름 (방 폭 기준 비율)
INNER = 0.86                  # 접시 테두리를 남기고 비울 범위 (반지름 비율)

# 물건 n개 배치: (x, y) 는 접시 반지름 기준, 마지막 값은 조각 폭 / 접시 지름
LAYOUTS = {  # 모든 바나나/껍질 조합에서 "서로 안 닿음 + 접시 밖 침범 없음"을 만족하는 최대 크기 (tests/test_plate.py)
    1: ([(0, 0)], 0.70),
    2: ([(-0.10, -0.40), (0.10, 0.40)], 0.62),
    3: ([(0, -0.36), (-0.38, 0.26), (0.38, 0.26)], 0.40),
    4: ([(-0.36, -0.28), (0.36, -0.28), (-0.36, 0.28), (0.36, 0.28)], 0.36),
}


def plate_geom(img: Image.Image, pos: str):
    x0, y0, x1, y1 = ROOM_BOXES[pos]
    W, H = img.size
    rx0, ry0, rw, rh = x0 * W, y0 * H, (x1 - x0) * W, (y1 - y0) * H
    cx, cy = rx0 + rw * PLATE_CENTER[0], ry0 + rh * PLATE_CENTER[1]
    return cx, cy, rw * PLATE_R


def _is_white(px):
    return px[0] > 210 and px[1] > 210 and px[2] > 205


def _plate_color(img, cx, cy, r):
    samples = []
    for dx in range(-int(r), int(r), 3):
        for dy in range(-int(r), int(r), 3):
            if dx * dx + dy * dy < (r * INNER) ** 2:
                px = img.getpixel((int(cx + dx), int(cy + dy)))
                if _is_white(px):
                    samples.append(px)
    if not samples:
        return (248, 248, 246)
    samples.sort(key=sum)
    return samples[len(samples) // 2]


def components(img: Image.Image, pos: str, min_px=150):
    """접시 안의 물건 조각들 (위→아래 순서). 각 조각은 RGBA 이미지."""
    img = img.convert("RGB")
    cx, cy, r = plate_geom(img, pos)
    rr = r * INNER
    x0, y0 = int(cx - rr), int(cy - rr)
    size = int(rr * 2)
    mask = [[False] * size for _ in range(size)]
    for j in range(size):
        for i in range(size):
            dx, dy = i - rr, j - rr
            if dx * dx + dy * dy < rr * rr and not _is_white(img.getpixel((x0 + i, y0 + j))):
                mask[j][i] = True
    seen = [[False] * size for _ in range(size)]
    comps = []
    for j in range(size):
        for i in range(size):
            if mask[j][i] and not seen[j][i]:
                q, pts = deque([(i, j)]), []
                seen[j][i] = True
                while q:
                    a, b = q.popleft()
                    pts.append((a, b))
                    for na, nb in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= na < size and 0 <= nb < size and mask[nb][na] and not seen[nb][na]:
                            seen[nb][na] = True
                            q.append((na, nb))
                if len(pts) >= min_px:
                    comps.append(pts)
    out = []
    for pts in comps:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        bx0, by0, bx1, by1 = min(xs), min(ys), max(xs) + 1, max(ys) + 1
        spr = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
        pset = set(pts)
        for a, b in pts:
            r_, g_, b_ = img.getpixel((x0 + a, y0 + b))
            edge = any((na, nb) not in pset for na, nb in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)))
            if edge and r_ + g_ + b_ > 560:  # 접시와 섞인 밝은 가장자리는 버림
                continue
            spr.putpixel((a - bx0, b - by0), (r_, g_, b_, 255))
        out.append(((bx0 + bx1) / 2 + x0, (by0 + by1) / 2 + y0, spr))
    out.sort(key=lambda t: t[1])
    return [s for _, _, s in out]


def extract_sprite(img: Image.Image, pos: str, index: int, name: str) -> Path:
    comps = components(img, pos)
    if not comps:
        raise SystemExit(f"[오류] {pos} 접시에서 조각을 찾지 못했습니다. PLATE_CENTER/PLATE_R 확인.")
    if index >= len(comps):
        raise SystemExit(f"[오류] {pos} 접시 조각은 {len(comps)}개뿐입니다 (index {index}).")
    SPRITES.mkdir(parents=True, exist_ok=True)
    path = SPRITES / f"{name}.png"
    comps[index].save(path)
    return path


def load_sprites():
    b, p = SPRITES / "banana.png", SPRITES / "peel.png"
    if not (b.exists() and p.exists()):
        raise SystemExit("[오류] assets/sprites/banana.png, peel.png 가 없습니다. 먼저 sprite 명령으로 만드세요.")
    return Image.open(b).convert("RGBA"), Image.open(p).convert("RGBA")


def rebuild_plate(img: Image.Image, case: dict, sid: str) -> Image.Image:
    s = next((x for x in case["suspects"] if x["id"] == sid), None)
    if s is None:
        raise SystemExit(f"[오류] 없는 방: {sid}")
    p = props(s)
    items = ["banana"] * p["bananas"] + ["peel"] * p["peels"]
    if len(items) > max(LAYOUTS):
        raise SystemExit(f"[오류] {sid} 접시 물건 {len(items)}개는 배치할 수 없습니다 (최대 {max(LAYOUTS)}).")
    banana, peel = load_sprites()
    img = img.convert("RGB").copy()
    cx, cy, r = plate_geom(img, s["pos"])
    color = _plate_color(img, cx, cy, r)
    d = ImageDraw.Draw(img)
    rr = r * INNER
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color)
    if not items:
        return img
    spots, wfrac = LAYOUTS[len(items)]
    for (ux, uy), kind in zip(spots, items):
        spr = banana if kind == "banana" else peel
        tw = 2 * r * wfrac
        scale = tw / max(spr.width, spr.height)
        sp = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.LANCZOS)
        px, py = cx + ux * r - sp.width / 2, cy + uy * r - sp.height / 2
        img.paste(sp, (int(px), int(py)), sp)
    return img
