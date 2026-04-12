# SIGNAL DECISION

## 목적
집계된 시장/종목 점수를 기반으로
실제 매매 판단 후보를 생성한다.

현재 시스템은 signal 생성, 점수 계산, 집계까지 가능하다.
다음 단계는 이를 해석하여
매수 후보 / 매도 후보 / 관망 상태를 반환하는 판단 레이어를 만드는 것이다.

---

## 현재 상태

- 기사별 signal 생성 완료
- signal dedup 완료
- score_signals 구현 완료
- aggregate_signals 구현 완료

즉, 현재는 점수까지 계산 가능하며
이제 점수를 사람이 이해하고 매매에 연결할 수 있는 판단 구조가 필요하다.

---

## 목표

1. 시장 점수를 해석한다
2. 종목별 점수를 해석한다
3. buy_candidate / sell_candidate / hold 형태의 판단 결과를 만든다
4. 아직 자동매매 실행은 하지 않는다

---

## 판단 기준

### 시장
- score >= 3 → bullish_bias
- score <= -3 → bearish_bias
- 그 외 → neutral_bias

### 종목
- score >= 3 → buy_candidate
- score <= -3 → sell_candidate
- 그 외 → hold

---

## 출력 형태 예시

- market_bias
- by_symbol_decision

예:
- market_bias = bullish_bias
- by_symbol_decision["005930"] = buy_candidate

---

## 설계 원칙

1. score 해석과 score 계산을 분리한다
2. 단순 규칙 기반 유지
3. 차트/가격 조건은 아직 넣지 않는다
4. 실행 가능한 주문 신호가 아니라 "후보 판단"까지만 만든다

---

## 금지사항

- 자동 주문 실행
- 손절/익절 실행 로직
- 가격 데이터 결합
- RSI/거래량 조건 결합
- 동적 threshold 최적화