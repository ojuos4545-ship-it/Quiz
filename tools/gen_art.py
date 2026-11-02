"""Google AI Studio(Gemini) 이미지 모델로 배경+인물 그림을 만든다.

- 키는 환경변수 GEMINI_API_KEY (또는 GOOGLE_API_KEY)에서만 읽는다. 코드·저장소에 넣지 않는다.
- 모델 이름은 GEMINI_IMAGE_MODEL 로 바꿀 수 있다 (기본: gemini-2.5-flash-image).
- 소품(접시 속 바나나·껍질, 슬리퍼, 복도 소품)은 AI에게 그리지 말라고 하고, scene.build_scene 이 코드로 넣는다.
- 구도가 흔들리지 않도록 코드가 그린 뼈대(build_skeleton)를 참고 이미지로 함께 보낸다.
"""
import base64
import io
import json
import os
import urllib.error
import urllib.request

from PIL import Image

DEFAULT_MODEL = "gemini-2.5-flash-image"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

STYLE = (
    "Hand-drawn editorial cartoon illustration, thick dark outlines, warm flat colors, "
    "top-down view of a lodging house cross-section, like a puzzle book picture."
)


def get_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("[오류] GEMINI_API_KEY 환경변수가 없습니다. AI Studio 키를 환경변수로만 설정하세요 "
                         "(예: export GEMINI_API_KEY=...). 키를 채팅이나 저장소에 붙여넣지 마세요.")
    return key


def build_art_prompt(case: dict) -> str:
    people = "\n".join(f"- Room {s['id']}: {s.get('desc', 'sleeping person')}" for s in case["suspects"])
    return (
        f"Redraw the attached layout sketch as a finished illustration. {STYLE}\n"
        "KEEP THE LAYOUT EXACTLY: 2 columns x 3 rows of rooms, red carpet corridor in the middle, "
        "every bed, nightstand, door and the letter circles A-E in the same positions. "
        "The bottom-right room is empty (only a bed and a suitcase). A man in striped pajamas lies on the corridor carpet.\n"
        f"Sleeping people (eyes closed):\n{people}\n"
        "IMPORTANT: leave every nightstand top completely EMPTY (no plate, no banana, no peel). "
        "Draw NO slippers anywhere and NO objects on the corridor floor except the man. "
        "No extra text besides the letters A-E. Square image."
    )


def _post(model: str, key: str, body: dict) -> dict:
    req = urllib.request.Request(
        ENDPOINT.format(model=model), data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"[오류] Gemini 호출 실패 (HTTP {e.code}): {detail}")


def parse_image(resp: dict) -> Image.Image:
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            data = part.get("inlineData") or part.get("inline_data")
            if data and data.get("data"):
                return Image.open(io.BytesIO(base64.b64decode(data["data"]))).convert("RGB")
    reason = resp.get("promptFeedback", {}).get("blockReason") or "이미지 없이 글자만 돌아옴"
    raise SystemExit(f"[오류] 응답에 이미지가 없습니다: {reason}")


def generate_art(case: dict, skeleton: Image.Image) -> Image.Image:
    key = get_key()
    model = os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL)
    buf = io.BytesIO()
    skeleton.save(buf, "PNG")
    body = {
        "contents": [{"parts": [
            {"text": build_art_prompt(case)},
            {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}},
        ]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    return parse_image(_post(model, key, body))
