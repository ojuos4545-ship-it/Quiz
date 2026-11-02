# 추리 퍼즐 인스타그램 콘텐츠 자동화

"범인은 누구?" 퍼즐 카드를 하루 10분 안팎으로 만드는 반자동 시스템.
**그림을 그리기 전에 퍼즐 논리 오류를 코드로 걸러내는 것**이 핵심이다.

## 설치
```bash
pip install -r requirements.txt
```
한글 폰트는 Windows(맑은 고딕), macOS(Apple SD 고딕), Linux(나눔·Noto CJK·WenQuanYi)에서 자동으로 찾는다.
직접 지정하려면 `FONT_PATH=/경로/폰트.ttf`를 쓴다.

## 명령어
| 명령 | 기능 | 산출물 |
|---|---|---|
| `python run.py verify 001` | 논리 검증 + 난이도 계산 | `out/001/report.txt` |
| `python run.py prompt 001` | GPT 그림 프롬프트 | `out/001/gpt_prompt.txt` |
| `python run.py prompt 001 --fix A,D` | 지정한 방만 고치는 부분 수정 프롬프트 | `out/001/gpt_fix_AD.txt` |
| `python run.py compose 001` | 퍼즐·정답 카드 (1080×1350) | `out/001/puzzle.png`, `answer.png` |
| `python run.py review 001` | Claude 채팅용 최종검토 요청문 + 캡션 | `out/001/review_request.md`, `caption.txt` |
| `python run.py all 001` | 위 전체 연속 실행 | |
| `python run.py plate 001 --rooms A` | GPT가 계속 틀린 방의 접시를 설계값대로 직접 합성 | `input/001.png` (원본은 `001_orig.png`로 백업) |
| `python run.py sprite 001 --room A --index 0 --name banana` | 그림 속 접시에서 바나나/껍질 조각 저장 (화풍 바뀔 때만) | `assets/sprites/*.png` |

검증에 실패하면 이후 단계는 실행되지 않는다.

## 일일 워크플로
1. Claude Code에 "새 사건 만들어줘 (normal)" → 사건 JSON 작성, 검증 통과까지 반복
2. `gpt_prompt.txt`를 GPT에 붙여넣기 → 단서 개수 확인 → 틀리면 `--fix`로 부분 수정 → `input/NNN.png`로 저장
   - 부분 수정을 2번 해도 틀리면 `python run.py plate NNN --rooms A`로 접시를 직접 합성
3. `python run.py compose NNN`
4. 카드 2장 + `review_request.md`를 Claude 채팅에 붙여넣기 → 업로드 가능/수정 후 가능/불가 판정
5. 퍼즐 카드 업로드(`caption.txt`), 다음 날 정답 카드 업로드

`input/NNN.png`이 없으면 임시 그림으로 합성한다 (파이프라인 확인용).

## 라벨 위치 조정
GPT 그림 구도가 다르면 정답 카드 라벨이 어긋난다. `tools/compose.py` 상단의
`ROOM_BOXES`, `CORRIDOR_BOX` 비율 좌표(0~1)를 그림에 맞게 고친다.

## 폴더
```
cases/    사건 JSON
input/    GPT가 그린 그림 (NNN.png)
out/NNN/  생성 결과
tools/    verify.py, make_prompt.py, compose.py, review_pack.py
tests/    검증기 테스트 (python -m unittest discover tests)
```
