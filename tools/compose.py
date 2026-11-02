"""카드 합성 (FR-5): 퍼즐 카드 + 정답 카드, 1080x1350 PNG.

GPT 구도가 바뀌어 라벨이 어긋나면 아래 ROOM_BOXES / CORRIDOR_BOX 좌표를 조정한다.
좌표는 원본 그림 기준 비율(0~1)이다.
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tools.common import INPUT, POSITIONS, VICTIM_POS, props

# ---------------------------------------------------------------- 조정용 상수
W, H = 1080, 1350
ROOM_BOXES = {  # (x0, y0, x1, y1) 비율 — 사건 001 GPT 그림(1254px) 실측 기준
    "L0": (0.015, 0.010, 0.360, 0.302), "R0": (0.642, 0.010, 0.990, 0.302),
    "L1": (0.015, 0.329, 0.360, 0.632), "R1": (0.642, 0.329, 0.990, 0.632),
    "L2": (0.015, 0.659, 0.360, 0.978), "R2": (0.642, 0.659, 0.990, 0.978),
}
CORRIDOR_BOX = (0.415, 0.010, 0.585, 0.978)
# 방 안에서 라벨을 놓을 영역 (방 기준 비율). 접시(우상단)·슬리퍼(우하단)를 가리지 않도록 이불 위.
LABEL_REGION = (0.03, 0.52, 0.62, 0.98)
CORRIDOR_LABEL_Y = 0.06  # 복도 라벨 세로 위치(비율, 빈 카펫 위)

C_BG = (250, 246, 238)
C_BAR = (32, 36, 58)
C_ACCENT = (255, 204, 64)
C_RED = (220, 40, 40)
C_TEXT = (40, 40, 48)
C_SUB = (110, 110, 120)

PUZZLE_IMG_BOX = (30, 165, 1050, 1045)
ANSWER_IMG_BOX = (60, 158, 1020, 1100)

# ---------------------------------------------------------------- 폰트
FONT_CANDIDATES = [
    # Windows
    "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
    # macOS
    "/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/AppleGothic.ttf",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    # Linux
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def find_font() -> str:
    env = os.environ.get("FONT_PATH")
    if env:
        if not Path(env).exists():
            raise SystemExit(f"[오류] FONT_PATH 파일이 없습니다: {env}")
        return env
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    raise SystemExit("[오류] 한글 폰트를 찾지 못했습니다. FONT_PATH 환경변수로 .ttf/.ttc 경로를 지정하세요.")


class Fonts:
    def __init__(self):
        self.path = find_font()
        self._cache = {}

    def __call__(self, size: int):
        if size not in self._cache:
            self._cache[size] = ImageFont.truetype(self.path, size)
        return self._cache[size]


# ---------------------------------------------------------------- 그리기 도우미
def wrap(text: str, font, max_w: int) -> list:
    lines, cur = [], ""
    for word in text.split(" "):
        trial = f"{cur} {word}".strip()
        if font.getlength(trial) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = ""
        for ch in word:  # 한 단어가 너무 길면 글자 단위로 자름
            if font.getlength(cur + ch) > max_w:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
    if cur:
        lines.append(cur)
    return lines


def draw_text_block(d, text_lines, font, x, y, max_w, color, gap=10, bullet=False):
    lh = font.size + gap
    indent = int(font.size * 0.9) if bullet else 0
    for t in text_lines:
        if bullet:  # 폰트에 없는 기호로 깨지지 않도록 점을 직접 그림
            r = font.size * 0.14
            cy = y + font.size * 0.55
            d.ellipse([x + 4, cy - r, x + 4 + 2 * r, cy + r], fill=C_RED)
        for ln in wrap(t, font, max_w - indent):
            d.text((x + indent, y), ln, font=font, fill=color)
            y += lh
    return y


def dashed_rect(d, box, color, width=6, dash=22, gap=12):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        length = max(abs(bx - ax), abs(by - ay))
        steps = int(length // (dash + gap)) + 1
        for i in range(steps):
            s = i * (dash + gap)
            e = min(s + dash, length)
            if s >= length:
                break
            fx = lambda t: ax + (bx - ax) * t / length
            fy = lambda t: ay + (by - ay) * t / length
            d.line([(fx(s), fy(s)), (fx(e), fy(e))], fill=color, width=width)


def title_bar(d, F, left, right, left_color=(255, 255, 255)):
    d.rectangle([0, 0, W, 145], fill=C_BAR)
    d.text((48, 72), left, font=F(68), fill=left_color, anchor="lm",
           stroke_width=1, stroke_fill=left_color)
    d.text((W - 48, 72), right, font=F(40), fill=C_ACCENT, anchor="rm")


def paste_contain(card, img, box):
    """그림을 box 안에 비율 유지로 넣고, 실제 배치 영역 (x, y, w, h)를 돌려준다."""
    bx0, by0, bx1, by1 = box
    bw, bh = bx1 - bx0, by1 - by0
    scale = min(bw / img.width, bh / img.height)
    w, h = int(img.width * scale), int(img.height * scale)
    x, y = bx0 + (bw - w) // 2, by0 + (bh - h) // 2
    card.paste(img.convert("RGB").resize((w, h), Image.LANCZOS), (x, y))
    ImageDraw.Draw(card).rectangle([x - 2, y - 2, x + w + 1, y + h + 1], outline=C_BAR, width=3)
    return x, y, w, h


def to_px(frac_box, area):
    x, y, w, h = area
    fx0, fy0, fx1, fy1 = frac_box
    return (x + fx0 * w, y + fy0 * h, x + fx1 * w, y + fy1 * h)


def label(d, F, center_x, top_y, lines, max_w, size=24, fg=C_TEXT, bg=(255, 255, 255), border=C_BAR):
    """여러 줄 라벨. max_w 안에 들어가도록 글자 크기를 자동으로 줄인다."""
    if isinstance(lines, str):
        lines = [lines]
    pad = 8
    while size > 12 and max(F(size).getlength(t) for t in lines) + pad * 2 > max_w:
        size -= 1
    f = F(size)
    tw = max(f.getlength(t) for t in lines)
    lh = size + 6
    box = (center_x - tw / 2 - pad, top_y, center_x + tw / 2 + pad, top_y + lh * len(lines) + pad)
    d.rounded_rectangle(box, radius=8, fill=bg, outline=border, width=2)
    for i, t in enumerate(lines):
        d.text((center_x, top_y + pad / 2 + 3 + i * lh), t, font=f, fill=fg, anchor="mt")
    return box


# ---------------------------------------------------------------- 임시 그림
def draw_banana(d, x, y):
    """노란 초승달 = 먹지 않은 바나나."""
    d.arc([x, y - 20, x + 48, y + 36], 20, 160, fill=(250, 205, 30), width=14)


def draw_peel(d, x, y):
    """갈색 별 모양 = 바나나 껍질."""
    cx, cy = x + 24, y + 18
    pts = [(cx, cy - 20), (cx + 6, cy - 4), (cx + 22, cy + 14), (cx, cy + 6),
           (cx - 22, cy + 14), (cx - 6, cy - 4)]
    d.polygon(pts, fill=(150, 105, 40), outline=(70, 50, 10))


def placeholder_image(case: dict, size=1024) -> Image.Image:
    """GPT 그림이 없을 때 파이프라인 확인용 임시 그림 (ROOM_BOXES 기준)."""
    img = Image.new("RGB", (size, size), (236, 228, 214))
    d = ImageDraw.Draw(img)
    F = Fonts()
    S = lambda b: tuple(v * size for v in b)
    d.rectangle(S(CORRIDOR_BOX), fill=(214, 200, 180))
    by_pos = {s["pos"]: s for s in case["suspects"]}
    for pos in POSITIONS:
        x0, y0, x1, y1 = S(ROOM_BOXES[pos])
        d.rectangle([x0, y0, x1, y1], fill=(255, 250, 240), outline=(90, 70, 50), width=5)
        s = by_pos.get(pos)
        cx = (x0 + x1) / 2
        # 침대
        d.rounded_rectangle([x0 + 20, y0 + 20, x0 + 120, y1 - 20], radius=12, fill=(170, 200, 230))
        # 문 + 글자
        door_x = x1 - 14 if pos.startswith("L") else x0 + 14
        d.rectangle([door_x - 10, y0 + 100, door_x + 10, y0 + 200], fill=(150, 100, 60))
        if s:
            d.text((door_x + (-40 if pos.startswith("L") else 40), y0 + 150), s["id"],
                   font=F(52), fill=(60, 40, 30), anchor="mm")
            p = props(s)
            # 접시 (침대와 문 글자 사이)
            px0, py0, px1, py1 = x0 + 125, y0 + 100, x0 + 275, y0 + 215
            d.ellipse([px0, py0, px1, py1], fill="white", outline=(150, 150, 150), width=3)
            items = ["b"] * p["bananas"] + ["p"] * p["peels"]
            for i, it in enumerate(items):
                ix = px0 + 30 + (i % 2) * 58
                iy = py0 + 14 + (i // 2) * 48
                (draw_banana if it == "b" else draw_peel)(d, ix, iy)
            # 슬리퍼
            for i in range(p["slippers"]):
                sx = x0 + 135 + i * 34
                d.rounded_rectangle([sx, y1 - 70, sx + 26, y1 - 22], radius=10, fill=(220, 90, 120))
        elif pos == VICTIM_POS:
            d.text((cx, (y0 + y1) / 2), "(빈 방)", font=F(32), fill=(150, 140, 130), anchor="mm")
    # 복도 소품
    cx0, cy0, cx1, cy1 = S(CORRIDOR_BOX)
    ccx = (cx0 + cx1) / 2
    c = case.get("corridor", {})
    vy = size * 0.86
    d.ellipse([ccx - 50, vy - 25, ccx + 50, vy + 25], fill=(90, 90, 110))
    for i in range(c.get("peels", 0)):
        yy = size * 0.72 - i * 50
        draw_peel(d, ccx - 24, yy)
    for i in range(c.get("slippers", 0)):
        yy = size * 0.60 - i * 60
        d.rounded_rectangle([ccx - 13, yy, ccx + 13, yy + 48], radius=10, fill=(220, 90, 120))
    d.text((size / 2, size * 0.5), "임시 그림", font=F(30), fill=(150, 130, 110), anchor="mm")
    return img


def load_art(case: dict):
    """input/NNN.png → 없으면 임시 그림. (그림, 임시여부) 반환."""
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = INPUT / f"{case['id']}.{ext}"
        if p.exists():
            return Image.open(p), False
    return placeholder_image(case), True


# ---------------------------------------------------------------- 카드
def room_label_lines(case: dict, s: dict) -> list:
    p = props(s)
    lines = [f"{s['id']}방"]
    if "banana_start" in case.get("world", {}):
        lines.append(f"바나나 {p['bananas']} · 껍질 {p['peels']}")
    if "slipper_pair" in case.get("world", {}):
        lines.append(f"슬리퍼 {p['slippers']}")
    return lines


def corridor_label_lines(case: dict) -> list:
    c = case.get("corridor", {})
    items = []
    if c.get("peels"):
        items.append(f"껍질 {c['peels']}")
    if c.get("slippers"):
        items.append(f"슬리퍼 {c['slippers']}")
    return ["복도"] + items if items else []


def corridor_label_text(case: dict) -> str:
    lines = corridor_label_lines(case)
    return f"복도: {', '.join(lines[1:])}" if lines else ""


def make_puzzle_card(case: dict, art: Image.Image, F: Fonts) -> Image.Image:
    card = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(card)
    title_bar(d, F, case.get("title", "범인은 누구?"), f"CASE {case['id']}")
    paste_contain(card, art, PUZZLE_IMG_BOX)
    draw_text_block(d, [case["premise"]], F(34), 48, 1062, W - 96, C_TEXT, gap=12)
    # 댓글 유도 버튼
    btn = (190, 1252, W - 190, 1322)
    d.rounded_rectangle(btn, radius=35, fill=C_ACCENT)
    d.text((W / 2, (btn[1] + btn[3]) / 2), "범인을 댓글로 남겨주세요!", font=F(36), fill=C_BAR, anchor="mm")
    return card


def make_answer_card(case: dict, art: Image.Image, F: Fonts) -> Image.Image:
    card = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(card)
    title_bar(d, F, f"범인은 {case['culprit']}", f"CASE {case['id']} 정답", left_color=(255, 120, 120))
    area = paste_contain(card, art, ANSWER_IMG_BOX)
    # 방별 개수 라벨 (방 안쪽 위)
    for s in case["suspects"]:
        x0, y0, x1, y1 = to_px(ROOM_BOXES[s["pos"]], area)
        is_c = s["id"] == case["culprit"]
        if is_c:
            dashed_rect(d, (x0 - 5, y0 - 5, x1 + 5, y1 + 5), C_RED)
        rw, rh = x1 - x0, y1 - y0
        lx0, ly0, lx1, ly1 = (x0 + rw * LABEL_REGION[0], y0 + rh * LABEL_REGION[1],
                              x0 + rw * LABEL_REGION[2], y0 + rh * LABEL_REGION[3])
        lines = room_label_lines(case, s)
        f_size = 30
        while f_size > 14 and (f_size + 6) * len(lines) + 8 > (ly1 - ly0):
            f_size -= 1
        box_h = (f_size + 6) * len(lines) + 8
        label(d, F, (lx0 + lx1) / 2, (ly0 + ly1 - box_h) / 2, lines,
              max_w=lx1 - lx0, size=f_size,
              fg=(255, 255, 255) if is_c else C_TEXT,
              bg=C_RED if is_c else (255, 255, 255),
              border=C_RED if is_c else C_BAR)
    # 복도 라벨 (복도 폭 안에서 여러 줄)
    clines = corridor_label_lines(case)
    if clines:
        cx0, cy0, cx1, cy1 = to_px(CORRIDOR_BOX, area)
        cy = cy0 + (cy1 - cy0) * CORRIDOR_LABEL_Y
        label(d, F, (cx0 + cx1) / 2, cy, clines, max_w=(cx1 - cx0) - 6, size=24,
              fg=C_BAR, bg=C_ACCENT, border=C_BAR)
    # 해설
    top, bottom = area[1] + area[3] + 16, H - 72 - 12
    size = 31
    while size > 20:
        f = F(size)
        n = sum(len(wrap(t, f, W - 96 - int(size * 0.9))) for t in case["explanation"])
        if n * (size + 10) <= bottom - top:
            break
        size -= 1
    draw_text_block(d, case["explanation"], F(size), 48, top, W - 96, C_TEXT, gap=10, bullet=True)
    # 다음 사건 예고
    try:
        nxt = f"{int(case['id']) + 1:03d}"
    except ValueError:
        nxt = "다음"
    d.rectangle([0, H - 72, W, H], fill=C_BAR)
    d.text((W / 2, H - 36), f"다음 사건 CASE {nxt} · 내일 공개", font=F(32), fill=C_ACCENT, anchor="mm")
    return card


def compose(case: dict, out: Path) -> dict:
    F = Fonts()
    art, is_placeholder = load_art(case)
    make_puzzle_card(case, art, F).save(out / "puzzle.png")
    make_answer_card(case, art, F).save(out / "answer.png")
    if is_placeholder:
        art.save(out / "placeholder_art.png")
    return {"font": F.path, "placeholder": is_placeholder}
