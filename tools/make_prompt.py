"""GPT 그림 프롬프트 생성 (FR-4)."""
from tools.common import POS_EN, VICTIM_POS, props

STYLE = ("Flat, clean cartoon illustration with thick outlines and soft pastel colors. "
         "Consistent house style for a mystery-puzzle Instagram series.")

LAYOUT = (
    "Top-down cutaway view of one floor of a small boarding house, square image. "
    "Six identical rooms arranged in a 2-column x 3-row grid: left column and right column, "
    "with one vertical corridor running between the two columns from top to bottom. "
    "Every room has the same layout: a bed with a sleeping person, a small table with ONE round white plate, "
    "and a spot beside the bed for slippers. Each room's door opens to the corridor."
)

RULES = [
    "The ONLY text allowed in the image is the single capital letter (A, B, C, D, E) on each room's door. No other words, numbers or signs.",
    "Objects on each plate must be large, clearly separated, and must NOT overlap, so they can be counted on a phone screen.",
    "Draw exactly the counts listed above. Do not add extra bananas, peels or slippers anywhere.",
    "Keep the camera angle, grid layout and room sizes exactly as described.",
]


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def room_line(case: dict, s: dict) -> str:
    p = props(s)
    pair = case.get("world", {}).get("slipper_pair", 2)
    slip = ("a pair of slippers (2 slippers)" if p["slippers"] >= pair
            else _count(p["slippers"], "single slipper", "slippers") + " (incomplete pair)"
            if p["slippers"] > 0 else "no slippers")
    plate = []
    if p["bananas"]:
        plate.append(_count(p["bananas"], "whole yellow banana", "whole yellow bananas"))
    if p["peels"]:
        plate.append(_count(p["peels"], "empty banana peel", "empty banana peels"))
    plate_txt = " and ".join(plate) if plate else "nothing (empty plate)"
    return (f"- Room {s['id']} ({POS_EN[s['pos']]}, door letter \"{s['id']}\"): {s.get('desc', 'a person')} "
            f"sleeping in bed. Plate: exactly {plate_txt}. Beside the bed: {slip}.")


def corridor_line(case: dict) -> str:
    c = case.get("corridor", {})
    items = []
    if c.get("peels"):
        items.append(_count(c["peels"], "banana peel", "banana peels") + " on the floor")
    if c.get("slippers"):
        items.append(_count(c["slippers"], "single slipper", "single slippers") + " lying on the floor")
    items_txt = ", ".join(items) if items else "nothing else"
    return (f"- Corridor: near the {POS_EN[VICTIM_POS]} room, a person lies collapsed face-down (cartoon, not graphic, no blood), "
            f"with {items_txt}. The {POS_EN[VICTIM_POS]} room ({VICTIM_POS}) is the victim's room: empty bed, no letter on the door.")


def build_prompt(case: dict) -> str:
    rooms = sorted(case["suspects"], key=lambda s: s["id"])
    parts = [STYLE, "", LAYOUT, "", "Rooms (draw these counts EXACTLY):"]
    parts += [room_line(case, s) for s in rooms]
    parts.append(corridor_line(case))
    parts += ["", "Strict rules:"] + [f"{i}. {t}" for i, t in enumerate(RULES, 1)]
    return "\n".join(parts) + "\n"


def build_fix_prompt(case: dict, room_ids: list) -> str:
    targets = [s for s in case["suspects"] if s["id"] in room_ids]
    unknown = set(room_ids) - {s["id"] for s in targets}
    if unknown:
        raise SystemExit(f"[오류] 없는 방: {sorted(unknown)}")
    lines = [
        "Edit the previous image. Keep EVERYTHING else exactly the same "
        "(layout, characters, colors, other rooms, corridor, door letters).",
        f"Only change room(s) {', '.join(room_ids)} so that they match these exact counts:",
    ]
    lines += [room_line(case, s) for s in targets]
    lines += ["", "Objects on the plate must be large and must not overlap. Do not add any text."]
    return "\n".join(lines) + "\n"
