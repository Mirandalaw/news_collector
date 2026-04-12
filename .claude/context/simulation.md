# Simulation Layer

## 목적
Trade candidate의 성능 검증

---

## 입력

- TradeCandidateReport
- 가격 데이터 (일별 OHLCV)

---

## 출력

- 포지션 결과
  - entry_price
  - exit_price
  - pnl

---

## 규칙

- 실제 주문 없음
- 가상 진입만 수행

---

## 진입 조건

- trade_candidate_report.final_candidate == True

---

## 종료 조건

- 손절 or 익절
- 일정 기간 경과 (예: 5일)

---

## 손절

- -3%

## 익절

- +5%

---

## 제약

- 단순 규칙 기반
- 복잡한 전략 금지