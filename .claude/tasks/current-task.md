# CURRENT TASK

## 작업명
dedup v2 threshold / normalize 검증

## 목표
dedup v2가 기대만큼 기사 중복을 줄이지 못하는 이유를,
threshold 후보와 normalize 상태 기준으로 분석한다.

현재 단계에서는 코드를 바로 수정하지 않고,
threshold 0.55 후보가 적절한지와 normalize 부족 여부를 먼저 판단한다.

---

## 현재 상태

- cleanup / retention 구현 완료
- event 섹션은 안정화 단계다
- dedup v2는 grouping + representative selection까지 적용 완료
- symbols 조건은 1차 완화 완료
- 실출력 기준으로 과한 병합은 없지만, 중복 감소 체감은 아직 약하다

---

## 이번 단계에서 해야 할 일

1. 실제 기사쌍 4~6개를 선정한다
2. 각 기사쌍에 대해 아래를 비교한다
   - normalize_title 결과
   - jaccard_similarity 값
   - threshold 0.6 결과
   - threshold 0.55 가정 결과
   - 실제로 묶는 것이 맞는지
3. 원인을 분류한다
   - threshold 과도
   - normalize 부족
   - 실제로 다른 이슈
4. 다음 수정 방향을 하나로 정한다

---

## 이번 단계에서 하지 말아야 할 일

- threshold 직접 수정
- normalize_title 수정
- builder 수정
- representative selection 수정
- event dedup 적용

---

## 분석 원칙

1. 실제 출력 기준으로 본다
2. 추측보다 similarity 계산 결과를 우선한다
3. 애매하면 유지한다
4. 오탐보다 미탐을 허용한다

---

## 완료 조건

1. threshold 0.55 후보 검증 완료
2. normalize 보강 필요성 판단 완료
3. 다음 수정 방향이 하나로 좁혀진다

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `dedup-v2-design.md`
- `dedup-v2-validation.md`
- `dedup-v2-tuning.md`
- `output-format.md`

---

## 작업 판단 기준

좋은 결과:
- 실제 기사쌍 기반 분석
- threshold와 normalize 원인을 구분
- 다음 액션이 명확함

좋지 않은 결과:
- 추측 위주
- 여러 수정을 한 번에 제안
- 오탐 리스크를 가볍게 봄