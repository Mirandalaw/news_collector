# CURRENT TASK

## 작업명
dedup v2 normalize 보강 - 최소 동의어/표기 정규화

## 목표
dedup v2에서 한영 혼용과 표현 차이로 인해 similarity가 과도하게 낮아지는 문제를 줄인다.

현재 단계에서는 threshold를 변경하지 않고,
실패 케이스에 직접 연결되는 최소 정규화 규칙만 추가한다.

## 우선 대상
- fed ↔ 연준
- 3q ↔ 3분기
- earnings / 어닝 / 실적발표 ↔ 실적