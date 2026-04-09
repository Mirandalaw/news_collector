# CURRENT TASK

## 작업명
dedup v2 symbols 조건 완화

## 목표
dedup v2에서 같은 회사 기사임에도 symbols 태깅 누락 때문에 그룹핑 후보에서 제외되는 문제를 줄인다.

현재 단계에서는 threshold나 normalize를 수정하지 않고,
`_symbols_compatible` 조건만 최소 수정한다.

---

## 현재 상태

- dedup v2는 market_section, symbol_section에 적용 완료
- 기사쌍 분석 결과, 가장 큰 구조적 문제는 symbols 조건 과도함으로 판단했다
- 현재 `_symbols_compatible`은 한쪽만 symbols가 있어도 비호환 처리한다

---

## 이번 단계에서 해야 할 일

1. `_symbols_compatible` 조건을 완화한다
2. 둘 다 non-empty이고 서로 다른 경우만 차단한다
3. 한쪽만 symbols가 있는 경우는 허용한다
4. 기존 group_by_similarity 흐름은 유지한다

---

## 이번 단계에서 하지 말아야 할 일

- threshold 변경
- normalize_title 수정
- builder 로직 수정
- 대표 기사 선택 고도화
- event dedup 적용

---

## 수정 원칙

1. 최소 수정만 한다
2. 태깅 누락을 구조적으로 허용한다
3. 명확히 다른 종목끼리는 계속 차단한다
4. 오탐 위험이 커지지 않도록 조건 변경 범위를 제한한다

---

## 완료 조건

1. `_symbols_compatible`이 새 규칙으로 동작한다
2. 기존 흐름에 다른 변경이 없다
3. 다음 검증에서 태깅 누락 기사도 similarity 판단에 들어간다