# Simulation Price History Provider

## 목적
시뮬레이션에 필요한 과거 가격 데이터를 제공한다.

---

## 입력

- symbols: list[str]
- lookback_days: int (기본 30)

---

## 출력

- dict[str, list[DayBar]]

---

## DayBar 구조

- date
- open
- high
- low
- close
- volume

---

## 데이터 기준

- 일봉 기준 (Daily)
- 최근 lookback_days 만큼 조회

---

## 처리 규칙

- 데이터가 부족한 종목은 제외
- 조회 실패 종목은 skip (예외 전파 금지)

---

## 제약

- 실제 주문 없음
- 외부 API 의존 (FinanceDataReader)
- 시뮬레이션용 데이터만 제공