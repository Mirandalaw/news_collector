# CURRENT TASK

## 작업명
simulation log MVP 구현

## 목표

simulation 결과를 날짜별/종목별로 기록할 수 있는
저장 레이어를 구현한다.

현재 단계에서는 DB 저장까지 가지 않고,
CSV 또는 단순 파일 저장 형태의 MVP만 구현한다.

---

## 현재 상태

- trade candidate pipeline 구현 완료
- simulation 구현 완료
- simulation report 구현 완료 또는 진행 중

하지만 결과를 누적 저장하는 구조는 아직 없다.

---

## 이번 단계에서 해야 할 일

1. SimulationResult를 저장 가능한 구조로 변환한다
2. 날짜/종목별 레코드 생성
3. CSV 파일 저장 함수 구현
4. 저장 실패 시 전체 흐름을 중단하지 않도록 처리

---

## 이번 단계에서 하지 말아야 할 일

- DB 저장 구현
- simulation 로직 수정
- 주문 실행
- 과도한 통계 확장
- 대시보드 구현

---

## 저장 대상

### 요약
- run_date
- total_trades
- win_rate
- avg_pnl

### 상세
- run_date
- symbol
- entry_price
- exit_price
- pnl
- exit_reason
- holding_days

---

## 설계 원칙

1. 저장 로직과 계산 로직 분리
2. CSV 중심 단순 구현
3. 실패해도 전체 시뮬레이션은 유지
4. 나중에 DB/대시보드 확장 가능해야 한다

---

## 완료 조건

1. simulation 결과를 파일로 저장 가능
2. 날짜/종목별 레코드 생성 가능
3. 저장 실패 시 graceful handling
4. 이후 성과 추세 분석에 바로 활용 가능

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `simulation.md`
- `simulation-report.md`
- `simulation-log.md`
- `output-format.md`