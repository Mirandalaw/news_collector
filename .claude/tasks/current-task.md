# CURRENT TASK

## 작업명
simulation report MVP 구현

## 목표

SimulationResult를 입력받아
전체 성과와 종목별 결과를 요약하는 report 레이어를 구현한다.

현재 단계에서는 simulation 자체를 수정하지 않고,
그 결과를 사람이 읽기 쉽게 정리하는 출력 레이어만 만든다.

---

## 현재 상태

- trade candidate pipeline 구현 완료
- simulation.py 구현 완료
- simulation 결과는 PositionResult / SimulationResult 형태로 존재

하지만 아직 simulation 결과를 요약하는 전용 report 레이어는 없다.

---

## 이번 단계에서 해야 할 일

1. SimulationResult를 입력받는다
2. 전체 요약 지표를 계산/정리한다
3. 종목별 결과를 정렬한다
4. 사람이 읽을 수 있는 format_text()를 제공한다

---

## 이번 단계에서 하지 말아야 할 일

- simulation 로직 수정
- price history provider 수정
- 주문 실행
- 포지션 관리 확장
- 백테스트 엔진 전체 구현

---

## 출력 대상

### 전체 요약
- total_trades
- win_rate
- avg_pnl
- winners
- losers

### 종목별 결과
- symbol
- entry_price
- exit_price
- pnl
- exit_reason
- holding_days

---

## 설계 원칙

1. 계산 로직과 출력 로직 분리
2. 단순하고 읽기 쉬운 구조
3. 이후 브리핑/대시보드 연결 쉬움
4. MVP 범위 유지

---

## 완료 조건

1. simulation 결과 요약 가능
2. 종목별 정렬 출력 가능
3. format_text() 제공
4. 이후 상위 레이어에서 쉽게 호출 가능

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `simulation.md`
- `simulation-history-provider.md`
- `simulation-report.md`
- `output-format.md`