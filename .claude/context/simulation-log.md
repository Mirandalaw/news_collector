# SIMULATION LOG

## 목적

simulation 결과를 날짜별/종목별로 기록하여
전략 성능을 누적 검증할 수 있게 한다.

현재 시스템은 trade candidate를 생성하고,
simulation 결과를 계산하고,
simulation report로 요약할 수 있다.

다음 단계는 이 결과를 일회성 출력으로 끝내지 않고
누적 저장 가능한 로그 구조로 정리하는 것이다.

---

## 현재 상태

- trade candidate pipeline 구현 완료
- simulation.py 구현 완료
- simulation report MVP 구현 예정 또는 완료 직전

즉, 개별 실행 결과는 확인할 수 있지만,
이를 날짜 단위로 누적 저장하는 구조는 아직 없다.

---

## 목표

1. simulation 결과를 저장 가능한 구조로 변환한다
2. 날짜/종목 기준으로 누적 기록이 가능해야 한다
3. 이후 CSV / JSON / DB 저장 중 어느 방식으로도 확장 가능해야 한다
4. 초기 단계는 파일 저장 중심으로 단순하게 시작한다

---

## 기록 대상

### 실행 메타 정보
- run_date
- since
- until
- total_trades
- win_rate
- avg_pnl

### 종목별 상세 결과
- symbol
- entry_price
- exit_price
- pnl
- exit_reason
- holding_days

---

## 저장 형식

초기 MVP는 아래 중 하나로 단순하게 시작한다.

### 1. JSON Lines
- 한 실행(run)당 한 파일 또는 한 줄 저장 가능
- 구조 보존이 쉬움

### 2. CSV
- 사람이 바로 열어보기 쉬움
- 단순 테이블 구조에 적합

초기 추천:
- **CSV 우선**
- 이유: 검토/필터/엑셀 확인이 쉬움

---

## 출력 구조 예시

### 실행 요약
- run_date
- total_trades
- win_rate
- avg_pnl

### 상세 레코드
- run_date
- symbol
- entry_price
- exit_price
- pnl
- exit_reason
- holding_days

---

## 설계 원칙

1. simulation 계산 로직과 저장 로직을 분리한다
2. 저장 실패가 전체 브리핑/시뮬레이션 실패를 유발하지 않게 한다
3. 초기 단계는 CSV 기반 단순 구조로 유지한다
4. 나중에 DB 저장으로 확장 가능해야 한다

---

## 금지사항

- simulation 로직 수정
- 주문 실행
- DB 스키마 바로 추가
- 과도한 통계 계산