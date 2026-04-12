# Execution Simulation Layer

## 목표
실제 주문 없이 수익/손실 검증

---

## 역할

- 후보 진입 기록
- 가격 변화 추적
- 손절/익절 시뮬레이션

---

## 입력

- trade_candidate_report
- price_data (일별)

---

## 출력

- 포지션 결과
  - entry
  - exit
  - pnl

---

## 중요

❗ 실제 주문 절대 없음
❗ 계좌 영향 없음