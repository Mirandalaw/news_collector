# CURRENT TASK

## 목표
Simulation에 사용할 price history provider 구현

---

## 해야 할 것

1. DayBar 리스트 생성
2. FinanceDataReader로 OHLCV 조회
3. DataFrame → DayBar 변환
4. 종목별 dict 형태로 반환

---

## 입력

- symbols: list[str]

---

## 출력

- dict[str, list[DayBar]]

---

## 제약

- 조회 실패 종목 skip
- 최소 2일 이상 데이터 필요
- 시뮬레이션 외 로직 포함 금지

---

## 성공 기준

- run_simulation에 바로 넣을 수 있는 데이터 생성