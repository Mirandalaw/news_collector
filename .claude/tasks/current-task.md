# CURRENT TASK

## 작업명
dedup v2 STEP 3-B - builder 연결

## 목표
dedup.py의 그룹핑 보조 함수를 builder 레이어에 연결하여,
market_section과 symbol_section에서 유사 기사 중복 노출을 줄인다.

현재 단계에서는 event_section에는 적용하지 않는다.

---

## 현재 상태

- dedup v2 STEP 1: `normalize_title(title: str) -> str` 구현 완료
- dedup v2 STEP 2: `jaccard_similarity(a: str, b: str) -> float` 구현 완료
- dedup v2 STEP 3-A: `group_by_similarity(...)` 구현 완료
- dedup v2는 아직 builder에 연결되지 않았다

---

## 이번 단계에서 해야 할 일

1. builder에서 market 기사 리스트에 dedup v2 그룹핑 적용
2. builder에서 symbol 기사 리스트에 dedup v2 그룹핑 적용
3. 각 그룹의 대표 기사(현재는 첫 번째 기사)만 남긴다
4. 기존 `_group_and_build()` 흐름은 최대한 유지한다

---

## 이번 단계에서 하지 말아야 할 일

- event_section 적용
- renderer 수정
- signal 구조 변경
- 대표 기사 선택 기준 고도화
- threshold 조정
- DB / collector 수정

---

## 적용 원칙

1. builder 변경 범위를 최소화한다
2. dedup v2는 `_group_and_build()` 앞단에만 적용한다
3. 애매하면 기존 흐름을 유지한다
4. 오탐보다 미탐을 우선한다

---

## 완료 조건

1. market_section에서 유사 기사 중복이 줄어든다
2. symbol_section에서 유사 기사 중복이 줄어든다
3. event_section은 기존 동작 유지
4. 기존 signal / renderer 구조는 깨지지 않는다
5. builder 변경 범위가 작고 명확하다

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `dedup-v2-design.md`
- `output-format.md`

---

## 작업 판단 기준

좋은 결과:
- builder 변경이 작다
- dedup.py 재사용이 명확하다
- 기존 구조와 자연스럽게 맞물린다

좋지 않은 결과:
- 여러 레이어를 동시에 수정한다
- event까지 같이 건드린다
- 대표 기사 선택 로직까지 같이 넣는다