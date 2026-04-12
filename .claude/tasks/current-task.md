# CURRENT TASK

## 작업명
signal aggregation MVP 구현

## 목표
시장 및 종목 단위로 signal을 집계하고,
기존 score_signals를 재사용하여 각각의 점수를 계산한다.

---

## 현재 상태

- 기사별 signal 생성 가능
- signal dedup 완료
- score_signals(signals) 구현 완료

이제 실제 사용 단위인 시장/종목 기준 집계가 필요하다.

---

## 이번 단계에서 해야 할 일

1. 시장 signal 집계 함수 구현
2. 종목별 signal 집계 함수 구현
3. score_signals를 재사용한다
4. 결과를 dictionary 또는 dataclass 형태로 반환한다

---

## 이번 단계에서 하지 말아야 할 일

- 자동매매 실행 로직
- 차트/가격 필터 결합
- 주문 조건 추가
- threshold 튜닝 고도화

---

## 완료 조건

1. 시장 점수 계산 가능
2. 종목별 점수 계산 가능
3. score_signals 재사용 구조 유지
4. 다음 단계에서 매매 판단 로직이 이 결과를 사용할 수 있다