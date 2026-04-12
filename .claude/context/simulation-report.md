# Simulation Report

## 목적

simulation 결과를 사람이 빠르게 해석할 수 있는 형태로 요약한다.

현재 시스템은 trade candidate를 생성하고,
price history를 기반으로 가상 진입/청산 시뮬레이션을 수행할 수 있다.

다음 단계는 그 결과를 단순 raw 데이터가 아니라
승률, 평균 손익, 종목별 성과로 정리된 리포트 형태로 제공하는 것이다.

---

## 현재 상태

- trade candidate pipeline 구현 완료
- simulation.py 구현 완료
- price history provider 구현 예정 또는 완료 직전

즉, simulation 실행 자체는 가능하거나 곧 가능하며,
이번 단계는 결과를 요약하고 출력하는 레이어를 추가하는 것이다.

---

## 목표

1. SimulationResult를 사람이 읽기 쉬운 형태로 요약한다
2. 전체 성과 지표를 계산한다
3. 종목별 결과를 정렬하여 보여준다
4. 이후 브리핑/대시보드/백테스트 로그에 쉽게 연결할 수 있게 한다

---

## 요약 대상

### 전체 지표
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

## 출력 정책

### 전체 요약
예시:
- 총 거래: 5건
- 승률: 60%
- 평균 수익률: +1.8%

### 종목별 결과
정렬 기준:
1. pnl 내림차순
2. symbol 보조 정렬

---

## 출력 형태

초기 MVP는 아래 두 가지를 제공하는 것이 적절하다.

1. 구조화된 dataclass / list
2. 사람이 읽을 수 있는 format_text()

---

## 설계 원칙

1. simulation 계산 로직과 출력 로직을 분리한다
2. 기존 SimulationResult는 수정하지 않는다
3. format_text()는 단순하고 가독성 높게 유지한다
4. 브리핑 본문을 크게 흔들지 않는 별도 요약 레이어로 둔다

---

## 금지사항

- simulation 로직 수정
- price history 조회 포함
- 주문 실행
- 포지션 관리 확장
- 과도한 통계 지표 추가