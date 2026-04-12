# CURRENT TASK

## 작업명
signal decision MVP 구현

## 목표
집계된 시장/종목 점수를 해석하여
매수 후보 / 매도 후보 / 관망 판단을 반환하는 decision 함수를 구현한다.

현재 단계에서는 차트/가격/거래량 조건 없이
점수만을 기준으로 한 1차 판단 레이어만 만든다.

---

## 현재 상태

- signal scoring MVP 구현 완료
- signal aggregation MVP 구현 완료
- market_score, by_symbol 점수 계산 가능

이제 이 결과를 사람이 이해할 수 있는 판단 형태로 변환해야 한다.

---

## 이번 단계에서 해야 할 일

1. market_score를 해석하는 함수 구현
2. by_symbol 점수를 해석하는 함수 구현
3. 반환 구조 정의
4. buy_candidate / sell_candidate / hold
   또는 bullish_bias / bearish_bias / neutral_bias 형태 반환

---

## 이번 단계에서 하지 말아야 할 일

- 자동 주문 실행
- 가격/차트 필터 결합
- 손절/익절 실행
- RSI/거래량 조건 추가
- threshold 튜닝 고도화

---

## 설계 원칙

1. 점수 계산과 판단 해석을 분리한다
2. 순수 함수 형태로 구현한다
3. 설명 가능한 규칙 기반 유지
4. 이후 차트/가격 필터가 이 결과를 받아 확장할 수 있어야 한다

---

## 완료 조건

1. 시장 bias 반환 가능
2. 종목별 decision 반환 가능
3. aggregation 결과를 입력으로 받을 수 있다
4. 다음 단계에서 차트/가격 필터를 붙일 수 있다

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `signal-scoring.md`
- `signal-aggregation.md`
- `signal-decision.md`
- `output-format.md`