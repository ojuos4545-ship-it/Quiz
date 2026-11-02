"""최종검토 요청문 (FR-6) + 인스타 캡션 (FR-7)."""
from tools.common import POS_KO, props
from tools.compose import corridor_label_text


def build_review_request(case: dict, computed_difficulty: str | None) -> str:
    world = case.get("world", {})
    rows = ["| 방 | 위치 | 접시 위 바나나 | 접시 위 껍질 | 슬리퍼 | 인물 |", "|---|---|---|---|---|---|"]
    for s in sorted(case["suspects"], key=lambda x: x["id"]):
        p = props(s)
        mark = " (범인)" if s["id"] == case["culprit"] else ""
        rows.append(f"| {s['id']}{mark} | {POS_KO[s['pos']]} | {p['bananas']} | {p['peels']} | "
                    f"{p['slippers']} | {s.get('desc', '')} |")
    clues = "\n".join(f"- [{c['role']}] {c['text']}" for c in case["clues"])
    expl = "\n".join(f"- {t}" for t in case["explanation"])
    return f"""# CASE {case['id']} 최종검토 요청

첨부한 카드 2장(퍼즐 카드, 정답 카드)을 아래 설계값과 대조해서 검토해 주세요.
인스타그램에 올리기 전 마지막 확인입니다. 엄격하게 봐 주세요.

## 사건 설계값
- 상황: {case['premise']}
- 범인: **{case['culprit']}**
- 난이도: 선언 {case['difficulty']} / 자동 계산 {computed_difficulty}
- 규칙: 방마다 바나나 {world.get('banana_start', '-')}개, 슬리퍼 {world.get('slipper_pair', '-')}짝 지급
- {corridor_label_text(case) or '복도: 없음'}

{chr(10).join(rows)}

## 단서
{clues}

## 해설
{expl}

## 검토 항목 (각 항목 통과/문제 + 이유)
1. **개수 대조**: 그림 속 방별 바나나·껍질·슬리퍼 개수와 복도 소품 개수가 위 표와 정확히 일치하는가?
2. **정답 유일성**: 그림만 보고 범인이 {case['culprit']} 한 명으로만 특정되는가? 다른 용의자도 범인으로 볼 수 있는 해석이 있는가?
3. **모바일 가독성**: 휴대폰 화면 크기에서 접시 위 물건과 슬리퍼를 셀 수 있는가? 겹치거나 너무 작은 것이 있는가?
4. **글자**: 그림에 A~E 외의 글자가 있거나, 카드의 한글이 깨지거나 잘린 곳이 있는가?
5. **해설 모순**: 정답 카드의 해설·라벨이 그림, 설계값과 어긋나는 곳이 있는가?
6. **난이도 체감**: 처음 보는 사람 기준으로 선언 난이도({case['difficulty']})가 적절한가?

## 답변 형식
- 판정: **업로드 가능 / 수정 후 가능 / 불가** 중 하나
- 항목별 결과 (1~6)
- 수정이 필요하면: GPT에 그대로 붙여넣을 **영어 부분 수정 요청문** (\"나머지는 그대로 두고 지정한 방만 수정\" 형식)
"""


def build_caption(case: dict) -> str:
    return f"""🔍 CASE {case['id']} | {case.get('title', '범인은 누구?')}

{case['premise']}

범인은 누구일까요? 🤔
👉 정답은 댓글로! (A~E)
👉 같이 풀 친구를 태그해 보세요
✅ 정답은 내일 공개됩니다

{case.get('caption_hashtags', '')}
"""
