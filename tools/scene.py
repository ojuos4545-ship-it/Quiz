"""방식 B 프로토타입: 배경·인물은 그림으로, 단서 소품은 사건 JSON 개수대로 코드가 직접 배치한다.

GPT 그림이 개수를 틀리는 문제를 원천 차단한다 (소품 개수 = 설계값, 항상 100%).
나중에 배경/인물 부분만 이미지 API(GPT·Gemini)로 바꿔도, 소품 배치 단계(place_props)는 그대로 쓴다.

python run.py scene NNN  →  input/NNN.png (compose가 바로 읽는 정사각형 그림)
"""
from PIL import Image, ImageDraw

from tools.common import POSITIONS, VICTIM_POS, props
from tools.compose import CORRIDOR_BOX, ROOM_BOXES
from tools.plate import LAYOUTS, PLATE_CENTER, PLATE_R, load_sprites

SIZE = 1254
SS = 2  # 2배 크기로 그린 뒤 줄여 선을 매끄럽게

OUTLINE = (45, 30, 25)
WOOD = (205, 150, 85)
WOOD_DARK = (150, 100, 55)
CARPET = (178, 42, 38)
CARPET_DARK = (140, 30, 30)
WALL = (240, 228, 205)
SHEET = (240, 238, 232)
PLATE_WHITE = (250, 250, 247)
SLIPPER_COLORS = [(70, 100, 190), (230, 130, 170), (80, 160, 120), (230, 170, 70), (120, 90, 170)]
SKIN = [(250, 214, 180), (240, 196, 160), (252, 224, 196), (232, 188, 150), (246, 208, 172)]


def _look(desc: str, idx: int) -> dict:
    """영문 외모 설명에서 그릴 특징을 뽑는다 (프로토타입용 단순 키워드 매핑)."""
    t = desc.lower()
    hair = (60, 40, 30)
    if any(k in t for k in ("elderly", "grey", "gray", "white-haired")):
        hair = (200, 200, 205)
    elif "red" in t or "ginger" in t:
        hair = (170, 70, 40)
    elif "blond" in t:
        hair = (225, 190, 90)
    elif "black" in t:
        hair = (25, 22, 25)
    return {
        "hair": hair, "skin": SKIN[idx % len(SKIN)],
        "bald": "bald" in t, "curly": "curly" in t, "ponytail": "ponytail" in t,
        "glasses": "glasses" in t, "headphones": "headphones" in t, "mask": "mask" in t,
        "mustache": "mustache" in t, "hairnet": "hair net" in t or "bonnet" in t,
        "long": any(k in t for k in ("long hair", "girl", "woman")),
    }


class Canvas:
    def __init__(self):
        self.s = SIZE * SS
        self.img = Image.new("RGB", (self.s, self.s), WALL)
        self.d = ImageDraw.Draw(self.img)

    def px(self, fx, fy):
        return fx * self.s, fy * self.s

    def rect(self, box, fill, w=5, r=0):
        x0, y0, x1, y1 = box
        if r:
            self.d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=OUTLINE, width=w * SS)
        else:
            self.d.rectangle([x0, y0, x1, y1], fill=fill, outline=OUTLINE, width=w * SS)

    def ellipse(self, cx, cy, rx, ry, fill, w=4):
        self.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill, outline=OUTLINE, width=w * SS)

    def finish(self) -> Image.Image:
        return self.img.resize((SIZE, SIZE), Image.LANCZOS)


# ------------------------------------------------------------------ 그리기 부품
def draw_slipper(c: Canvas, cx, cy, color, scale=1.0, angle_down=True):
    rx, ry = 20 * SS * scale, 34 * SS * scale
    c.ellipse(cx, cy, rx, ry, color, w=4)
    c.ellipse(cx, cy - ry * 0.35, rx * 0.72, ry * 0.45, tuple(min(255, v + 35) for v in color), w=3)


def draw_person(c: Canvas, x0, y0, rw, rh, look: dict):
    """침대에서 자는 인물 (위에서 본 모습): 베개 + 머리 + 이불."""
    bx0, by0, bx1, by1 = x0 + rw * 0.05, y0 + rh * 0.07, x0 + rw * 0.60, y0 + rh * 0.99
    c.rect((bx0, by0 - rh * 0.02, bx1, by1), WOOD_DARK, r=10 * SS)           # 침대 프레임
    c.rect((bx0 + rw * 0.02, by0 + rh * 0.02, bx1 - rw * 0.02, by1 - rh * 0.02), SHEET, r=8 * SS)
    pcx, pcy = (bx0 + bx1) / 2, by0 + rh * 0.17
    c.rect((pcx - rw * 0.22, pcy - rh * 0.09, pcx + rw * 0.22, pcy + rh * 0.12), (255, 255, 255), w=3, r=8 * SS)
    hr = rw * 0.115
    hx, hy = pcx, pcy + rh * 0.01
    if look["long"]:
        c.rect((hx - hr * 1.2, hy - hr * 0.2, hx + hr * 1.2, hy + hr * 1.9), look["hair"], w=3, r=int(hr * 0.5))
    c.ellipse(hx, hy, hr, hr * 1.1, look["skin"])
    if not look["bald"]:
        c.d.pieslice([hx - hr * 1.08, hy - hr * 1.25, hx + hr * 1.08, hy + hr * 0.9], 180, 360,
                     fill=look["hair"], outline=OUTLINE, width=4 * SS)
        if look["curly"]:
            for dx in (-0.8, -0.3, 0.3, 0.8):
                c.ellipse(hx + dx * hr, hy - hr * 1.05, hr * 0.38, hr * 0.38, look["hair"], w=3)
        if look["ponytail"]:
            c.ellipse(hx - hr * 1.2, hy + hr * 0.3, hr * 0.4, hr * 0.9, look["hair"], w=3)
        if look["hairnet"]:
            c.d.arc([hx - hr * 1.15, hy - hr * 1.3, hx + hr * 1.15, hy + hr * 1.0], 180, 360, fill=(240, 160, 190), width=7 * SS)
    ey = hy + hr * 0.1
    if look["mask"]:
        c.rect((hx - hr * 1.0, ey - hr * 0.35, hx + hr * 1.0, ey + hr * 0.4), (50, 60, 130), w=3, r=8 * SS)
    else:
        for dx in (-0.4, 0.4):  # 감은 눈
            c.d.arc([hx + dx * hr - hr * 0.22, ey - hr * 0.1, hx + dx * hr + hr * 0.22, ey + hr * 0.3],
                    0, 180, fill=OUTLINE, width=3 * SS)
        if look["glasses"]:
            for dx in (-0.4, 0.4):
                c.ellipse(hx + dx * hr, ey + hr * 0.1, hr * 0.32, hr * 0.32, None, w=3)
    if look["mustache"]:
        c.rect((hx - hr * 0.45, hy + hr * 0.5, hx + hr * 0.45, hy + hr * 0.7), (60, 35, 25), w=2, r=6 * SS)
    c.d.arc([hx - hr * 0.2, hy + hr * 0.55, hx + hr * 0.2, hy + hr * 0.85], 0, 180, fill=OUTLINE, width=2 * SS)
    if look["headphones"]:
        c.d.arc([hx - hr * 1.15, hy - hr * 1.3, hx + hr * 1.15, hy + hr * 0.9], 180, 360, fill=(235, 235, 240), width=7 * SS)
        for dx in (-1.1, 1.1):
            c.ellipse(hx + dx * hr, hy + hr * 0.05, hr * 0.28, hr * 0.42, (235, 235, 240), w=3)
    # 이불
    c.rect((bx0 + rw * 0.02, by0 + rh * 0.34, bx1 - rw * 0.02, by1 - rh * 0.02), (250, 248, 244), r=10 * SS)
    c.d.line([(bx0 + rw * 0.05, by0 + rh * 0.38), (bx1 - rw * 0.05, by0 + rh * 0.38)], fill=(215, 212, 205), width=3 * SS)


def draw_room_shell(c: Canvas, x0, y0, x1, y1):
    c.rect((x0, y0, x1, y1), WOOD, w=6)
    step = (y1 - y0) / 9
    for i in range(1, 9):  # 마루 결
        c.d.line([(x0 + 6 * SS, y0 + i * step), (x1 - 6 * SS, y0 + i * step)], fill=(190, 135, 75), width=2 * SS)


def draw_nightstand(c: Canvas, x0, y0, rw, rh):
    c.rect((x0 + rw * 0.66, y0 + rh * 0.13, x0 + rw * 0.95, y0 + rh * 0.50), WOOD_DARK, r=6 * SS)


def draw_door(c: Canvas, pos: str, letter: str, y0, rh):
    left = pos.startswith("L")
    cx = (CORRIDOR_BOX[0] - 0.026) if left else (CORRIDOR_BOX[2] + 0.026)
    px, py = c.px(cx, 0)
    py = y0 + rh * 0.08
    c.rect((px - 12 * SS, py, px + 12 * SS, py + rh * 0.62), (150, 95, 50), r=6 * SS)
    c.ellipse(px, py + rh * 0.03, 22 * SS, 22 * SS, (255, 255, 255), w=4)
    from tools.compose import Fonts  # 글자만 필요해서 늦게 불러옴
    f = Fonts()(26 * SS)
    c.d.text((px, py + rh * 0.03), letter, font=f, fill=OUTLINE, anchor="mm")


def draw_victim(c: Canvas, cx, cy):
    """복도에 엎어진 피해자 (줄무늬 잠옷)."""
    w = c.s * 0.052
    c.rect((cx - w, cy - w * 0.4, cx + w, cy + w * 1.9), (110, 150, 215), r=18 * SS)          # 몸
    for i in range(-3, 4):
        c.d.line([(cx + i * w * 0.27, cy - w * 0.3), (cx + i * w * 0.27, cy + w * 1.8)], fill=(235, 240, 255), width=4 * SS)
    c.ellipse(cx - w * 0.45, cy + w * 2.25, w * 0.25, w * 0.35, SKIN[1])                    # 발
    c.ellipse(cx + w * 0.45, cy + w * 2.25, w * 0.25, w * 0.35, SKIN[1])
    c.ellipse(cx, cy - w * 0.75, w * 0.62, w * 0.62, (70, 45, 35))                           # 머리
    c.ellipse(cx - w * 1.15, cy - w * 0.25, w * 0.3, w * 0.3, SKIN[1])                       # 손
    c.ellipse(cx + w * 1.15, cy - w * 0.25, w * 0.3, w * 0.3, SKIN[1])


# ------------------------------------------------------------------ 소품 배치 (개수 = 설계값)
def _paste_sprite(c: Canvas, spr: Image.Image, cx, cy, target_w):
    scale = target_w / max(spr.width, spr.height)
    sp = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.LANCZOS)
    c.img.paste(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)), sp)


def place_plate(c: Canvas, banana, peel, x0, y0, rw, rh, p: dict):
    cx, cy, r = x0 + rw * PLATE_CENTER[0], y0 + rh * PLATE_CENTER[1], rw * PLATE_R
    c.ellipse(cx, cy, r, r, PLATE_WHITE, w=4)
    items = ["banana"] * p["bananas"] + ["peel"] * p["peels"]
    if not items:
        return
    spots, wfrac = LAYOUTS[len(items)]
    for (ux, uy), kind in zip(spots, items):
        _paste_sprite(c, banana if kind == "banana" else peel, cx + ux * r, cy + uy * r, 2 * r * wfrac)


def place_props(c: Canvas, case: dict):
    """접시·슬리퍼·복도 소품을 사건 JSON 개수 그대로 그린다."""
    banana, peel = load_sprites()
    banana, peel = _scale_sprite(banana, c), _scale_sprite(peel, c)
    by_pos = {s["pos"]: (i, s) for i, s in enumerate(case["suspects"])}
    for pos, (i, s) in by_pos.items():
        x0, y0, x1, y1 = (v * c.s for v in (ROOM_BOXES[pos][0], ROOM_BOXES[pos][1], ROOM_BOXES[pos][2], ROOM_BOXES[pos][3]))
        rw, rh = x1 - x0, y1 - y0
        p = props(s)
        place_plate(c, banana, peel, x0, y0, rw, rh, p)
        color = SLIPPER_COLORS[i % len(SLIPPER_COLORS)]
        n = p["slippers"]
        for k in range(n):
            draw_slipper(c, x0 + rw * (0.78 + (k - (n - 1) / 2) * 0.115), y0 + rh * 0.72, color)
    # 복도: 껍질 · 슬리퍼 (피해자 아래쪽)
    cx0, cy0, cx1, cy1 = (v * c.s for v in CORRIDOR_BOX)
    ccx = (cx0 + cx1) / 2
    cor = case.get("corridor", {})
    items = [("peel", None)] * cor.get("peels", 0) + [("slipper", None)] * cor.get("slippers", 0)
    for k, (kind, _) in enumerate(items):
        x = ccx + (-0.35 if k % 2 == 0 else 0.35) * (cx1 - cx0) * 0.45
        y = c.s * (0.79 + 0.075 * k)
        if kind == "peel":
            _paste_sprite(c, peel, x, y, (cx1 - cx0) * 0.34)
        else:
            draw_slipper(c, x, y, SLIPPER_COLORS[0], scale=0.95)


def _scale_sprite(spr, c):
    return spr.resize((spr.width * SS, spr.height * SS), Image.LANCZOS)


# ------------------------------------------------------------------ 전체 장면
def build_scene(case: dict) -> Image.Image:
    c = Canvas()
    cx0, cy0, cx1, cy1 = (v * c.s for v in CORRIDOR_BOX)
    c.rect((cx0, cy0, cx1, cy1), CARPET, w=5)
    c.d.rectangle([cx0 + 10 * SS, cy0, cx0 + 22 * SS, cy1], fill=CARPET_DARK)
    c.d.rectangle([cx1 - 22 * SS, cy0, cx1 - 10 * SS, cy1], fill=CARPET_DARK)
    by_pos = {s["pos"]: (i, s) for i, s in enumerate(case["suspects"])}
    for pos in POSITIONS:
        x0, y0, x1, y1 = (ROOM_BOXES[pos][0] * c.s, ROOM_BOXES[pos][1] * c.s, ROOM_BOXES[pos][2] * c.s, ROOM_BOXES[pos][3] * c.s)
        rw, rh = x1 - x0, y1 - y0
        draw_room_shell(c, x0, y0, x1, y1)
        if pos in by_pos:
            i, s = by_pos[pos]
            draw_person(c, x0, y0, rw, rh, _look(s.get("desc", ""), i))
            draw_nightstand(c, x0, y0, rw, rh)
            draw_door(c, pos, s["id"], y0, rh)
        elif pos == VICTIM_POS:  # 피해자의 빈 방: 침대 + 가방
            c.rect((x0 + rw * 0.05, y0 + rh * 0.07, x0 + rw * 0.60, y0 + rh * 0.99), WOOD_DARK, r=10 * SS)
            c.rect((x0 + rw * 0.07, y0 + rh * 0.09, x0 + rw * 0.58, y0 + rh * 0.97), SHEET, r=8 * SS)
            c.rect((x0 + rw * 0.12, y0 + rh * 0.60, x0 + rw * 0.52, y0 + rh * 0.82), (125, 70, 40), r=10 * SS)
            draw_nightstand(c, x0, y0, rw, rh)
    draw_victim(c, (cx0 + cx1) / 2, c.s * 0.50)
    place_props(c, case)
    return c.finish()


def count_check(img: Image.Image, case: dict) -> list:
    """그려진 접시의 물건 수를 이미지에서 다시 세어 설계값과 대조한다 (자동 검수). 불일치 목록 반환."""
    from tools.common import plate_items
    from tools.plate import components
    bad = []
    for s in case["suspects"]:
        found = len(components(img, s["pos"]))
        if found != plate_items(s):
            bad.append((s["id"], plate_items(s), found))
    return bad
