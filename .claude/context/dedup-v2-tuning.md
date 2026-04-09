# DEDUP V2 TUNING

## 목적

dedup v2가 실제 브리핑에서 기대만큼 중복을 줄이지 못하는 원인을 바탕으로,
threshold 및 normalize 보정 방향을 검토한다.

현재 단계에서는 바로 코드를 수정하지 않고,
실제 기사쌍을 기준으로 threshold 후보와 normalize 부족 여부를 먼저 검증한다.

---

## 현재 상태

- dedup v2는 builder의 market_section, symbol_section에 적용 완료
- representative selection까지 구현 완료
- event_section은 기존 동작 유지
- 실출력 기준으로 과한 병합은 없지만 중복 감소 체감은 아직 약하다

---

## 현재 관찰된 문제

1. symbol_section 기사 수가 여전히 많다
2. 같은 회사/유사 이슈 기사들이 여러 개 남아 있다
3. representative selection은 들어갔지만, 애초에 같은 그룹으로 충분히 묶이지 않는 케이스가 있다
4. threshold가 너무 보수적인지, normalize가 약한지 추가 검증이 필요하다

---

## 현재까지 확인된 원인

### 1. symbols 조건 과도함
- 한쪽만 symbols가 있는 경우를 허용하도록 이미 완화 완료
- 이 단계는 1차 보정이 끝난 상태다

### 2. threshold 경계 사례 존재
- similarity가 0.583처럼 0.6 바로 아래인 케이스가 확인됨
- threshold가 약간만 낮아져도 묶일 수 있는 사례가 존재한다

### 3. normalize 부족 가능성
- 동의어, 표현 차이, 수치 토큰, 영문/한글 혼용 등으로 유사도가 낮아질 수 있다
- 예:
  - 실적 / 어닝
  - Fed / 연준
  - 새 AI 성능 / 공개 / 참전
  - 숫자 토큰(15, 122 등)

---

## 이번 단계 목표

1. threshold 후보(특히 0.55)가 실제로 적절한지 검증한다
2. normalize 부족이 threshold보다 더 큰 문제인지 구분한다
3. 다음 수정 방향을 하나로 좁힌다
   - threshold 조정
   - normalize 보강
   - 현재 유지

---

## 검증 대상

우선 아래 유형 기사쌍을 중심으로 본다.

1. 같은 회사 + 같은 이슈로 보이는 기사
   - 메타
   - 쿠팡
   - 삼성/삼성전자
   - 엔비디아
2. 같은 회사 + 다른 이슈 기사
3. market 기사 중 같은 거시 이슈 기사
4. market 기사 중 실제로 다른 이슈 기사

---

## 검증 방식

각 기사쌍에 대해 아래를 확인한다.

1. 원본 제목
2. normalize_title 결과
3. jaccard_similarity 값
4. symbols 값
5. 현재 threshold=0.6 결과
6. 후보 threshold=0.55 결과
7. 실제로 묶는 것이 맞는지 판단

---

## 판단 기준

### threshold 조정이 맞는 경우
- 0.55에서 자연스럽게 묶이는 케이스가 늘어난다
- 다른 이슈가 잘못 묶이는 사례는 거의 없다
- normalize를 크게 바꾸지 않아도 개선 효과가 있다

### normalize 보강이 먼저인 경우
- similarity가 여전히 너무 낮다
- 0.55로 낮춰도 충분히 안 묶인다
- 표현 차이(동의어, 수치, 영문/한글)가 주요 원인이다

### 현재 유지가 맞는 경우
- 0.55에서 과한 병합이 생긴다
- 실제 출력 품질 개선보다 오탐 리스크가 더 크다

---

## 이번 단계에서 하지 말아야 할 일

- threshold 즉시 변경
- normalize_title 즉시 수정
- builder 로직 수정
- event dedup 적용
- 대표 기사 선택 기준 수정

이번 단계는 분석과 판단만 수행한다.

---

## 설계 원칙

1. 추측으로 threshold를 바꾸지 않는다
2. 실제 기사쌍 기준으로 판단한다
3. 애매하면 유지한다
4. 오탐보다 미탐을 허용한다

---

## 완료 조건

1. threshold 0.55 후보의 적절성을 검토한다
2. normalize 부족 여부를 구분한다
3. 다음 수정 방향을 하나로 좁힌다

## 분석 결론 요약

기사쌍 분석 결과, dedup v2의 주요 한계는 threshold보다 normalize 부족에 더 가깝다고 판단했다.

### 핵심 발견
1. threshold 0.55로 해결되는 사례는 제한적이다
2. 실제 미탐의 주요 원인은 수치 토큰, 한영 혼용, 표현 차이로 인한 normalize 부족이다
3. threshold를 먼저 낮추는 것보다 normalize를 먼저 보강하는 편이 정확도 개선 폭이 크고 오탐 위험이 낮다

### 다음 수정 방향
- `normalize_title`에서 수치 토큰 제거를 우선 적용한다
- threshold는 현재 0.6을 유지한다