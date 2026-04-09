# DEDUP V2 VALIDATION

## 목적

dedup v2가 실제 브리핑 출력에서 중복 기사를 줄이고 있는지 검증한다.

현재 단계에서는 바로 threshold를 바꾸거나 정규화 규칙을 확대하지 않고,  
먼저 "왜 기대한 만큼 묶이지 않았는지"를 분석하는 데 목적이 있다.

---

## 현재 상태

- dedup v2 STEP 1: `normalize_title(title: str) -> str` 구현 완료
- dedup v2 STEP 2: `jaccard_similarity(a: str, b: str) -> float` 구현 완료
- dedup v2 STEP 3-A: `group_by_similarity(...)` 구현 완료
- dedup v2 STEP 3-B: builder의 market/symbol 섹션에 적용 완료
- event_section은 기존 동작 유지

실출력 기준으로 dedup v2가 완전히 실패한 것은 아니지만,  
중복 감소 체감은 아직 약한 상태다.

---

## 현재 관찰된 문제

1. symbol_section 기사 수가 여전히 많다
2. 같은 이슈로 보이는 기사들이 여러 개 남아 있다
3. 과한 병합은 없지만, 보수성이 너무 강할 수 있다
4. threshold, normalize 규칙, 표현 차이 대응 중 어느 요인이 큰지 아직 확정되지 않았다

---

## 검증 목표

1. dedup v2가 실제로 어떤 기사쌍에서 묶이지 않았는지 확인한다
2. similarity 값이 낮은 원인을 분석한다
3. 문제 원인이 아래 중 어디에 있는지 구분한다
   - normalize 부족
   - threshold 과도
   - symbols 조건 과도
   - 표현 차이(동의어/영문/한글 혼용)

---

## 검증 방식

### 1. 후보 기사쌍 선정
실제로 같은 이슈로 보이는 기사 3~5쌍을 선정한다.

예시:
- 메타 관련 기사들
- 쿠팡 관련 기사들
- 삼성/삼성전자 관련 기사들

### 2. 기사쌍별 확인 항목
각 기사쌍에 대해 아래를 확인한다.

- 원본 제목
- normalize_title 결과
- jaccard_similarity 값
- symbols 값
- group_by_similarity에서 묶였는지 여부

### 3. 원인 분류
묶이지 않은 경우 아래 중 어디가 원인인지 분류한다.

- normalize_title 결과가 너무 다름
- similarity 값이 threshold(0.6)보다 낮음
- symbols 조건에서 차단됨
- 실제로는 같은 이슈가 아님

---

## 분석 원칙

1. 추측으로 threshold를 바꾸지 않는다
2. 실제 기사쌍 기준으로 판단한다
3. 오탐보다 미탐을 우선 허용한다
4. event_section은 이번 분석 범위에서 제외한다

---

## 이번 단계에서 하지 말아야 할 일

- threshold 즉시 변경
- normalize_title 즉시 수정
- builder 로직 수정
- 대표 기사 선택 로직 추가
- event dedup 적용

이번 단계는 "분석과 판단"만 수행한다.

---

## 완료 조건

1. 기사쌍 3~5개 이상을 기준으로 분석한다
2. 묶이지 않은 주요 원인을 분류한다
3. 다음 단계가 무엇인지 결정한다
   - normalize 보강
   - threshold 조정
   - symbols 조건 조정
   - 현재 유지

---

## 판단 기준

좋은 분석:
- 실제 출력 기반이다
- 원인 분류가 명확하다
- 다음 수정 포인트가 작고 명확하다

좋지 않은 분석:
- 추측 위주다
- 여러 요인을 한 번에 바꾸려 한다
- 오탐 위험을 무시한다

## 분석 결과 요약

기사쌍 분석 결과, dedup v2의 중복 감소 체감이 약한 가장 큰 원인은
threshold보다 `symbols` 호환 조건의 과도한 차단에 있는 것으로 판단했다.

### 핵심 발견
1. `threshold=0.6`은 일부 근소 미달 사례가 있었지만 구조적 문제로 보이진 않았다
2. `_symbols_compatible`의 "한쪽만 symbols가 있으면 비호환" 규칙은
   실제 태깅 누락 환경에서 같은 회사 기사도 그룹핑 후보에서 제외시켰다
3. normalize 부족은 보조 요인으로 보였고, 1차 수정 우선순위는 아니다

### 다음 수정 방향
- `_symbols_compatible` 조건 완화
- 변경 원칙:
  - 둘 다 non-empty이고 서로 다른 경우만 차단
  - 한쪽만 symbols가 있는 경우는 허용