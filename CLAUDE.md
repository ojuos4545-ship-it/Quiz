# CLAUDE.md — 추리 퍼즐 콘텐츠 자동화 작업 지침

이 저장소는 "범인은 누구?" 인스타그램 퍼즐 카드(퍼즐 1장 + 정답 1장)를 만든다.
Claude Code의 역할: **사건 설계와 논리 검증**, 프롬프트·카드·검수 요청문 생성.
출력과 설명은 한글로 한다.

## "새 사건 만들어줘 (난이도)" 요청을 받으면
1. `cases/` 안의 마지막 번호 다음 번호로 `cases/case_NNN.json`을 만든다 (형식은 `case_001.json` 참고).
2. `python run.py verify NNN` 실행 → **오류 0개, 경고 0개**가 될 때까지 JSON을 고친다.
3. `python run.py prompt NNN` 실행 → `out/NNN/gpt_prompt.txt` 내용을 사용자에게 보여준다.
4. 사용자가 그림을 `input/NNN.png`로 저장하면 `python run.py compose NNN` → `python run.py review NNN`.

## 사건 설계 규칙 (반드시 지킴)
1. 정답은 정확히 1명. 핵심 단서(key) 교집합 = 범인 1명.
2. 눈으로 확인 가능한 단서만 (개수, 있다/없다). 모호한 표현 금지.
3. 접시 위 물건(바나나+껍질) 4개 이하, 용의자 5명 이하.
4. 방에서 사라진 소품 합계 = 복도 소품 수.
5. 가짜 단서(herring)는 무고한 용의자를 1명 이상 지목.
6. 사건마다 인물 외모, 숫자, 가짜 단서를 바꾼다. 구도(2열×3행, R2=피해자 방)는 유지한다.
7. 다른 계정의 사건·그림을 따라 하지 않는다.

## 난이도
- easy: 핵심 단서 하나로 특정, 가짜 단서 없음
- normal: 단서를 합쳐야 함 **또는** 하나로 풀리지만 가짜 단서 있음
- hard: 단서를 합쳐야 하고 가짜 단서도 있음

## 단서 타입
| type | 지목 조건 |
|---|---|
| peel_balance | banana_start − 접시 바나나 − 껍질 > 0 |
| slipper_missing | 슬리퍼 < slipper_pair |
| custom | `implicates` 목록 (개수 검증 없음, 신중히 사용) |

새 단서 타입은 `tools/verify.py`(지목 규칙), `tools/make_prompt.py`(그림 지시), `tools/compose.py`(라벨)에 함께 추가하고 `tests/`에 테스트를 넣는다.

## 코드 수정 후
`python -m unittest discover tests` 통과를 확인한다.
