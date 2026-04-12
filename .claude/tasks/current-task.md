# CURRENT TASK

## 작업명
signal scoring MVP 구현

## 목표
여러 signal을 종합하여 하나의 점수와 간단한 판단 결과를 반환하는 scoring 함수를 구현한다.

현재 단계에서는 시장/종목 전체 집계 구조까지 한 번에 구현하지 않고,
먼저 signal 리스트를 받아 score를 계산하는 순수 함수부터 만든다.

---

## 현재 상태

- 뉴스 수집 / dedup / noise filter 완료
- event 분류 완료
- signal 생성 및 dedup 완료
- 아직 signal을 종합하는 scoring 로직은 없다

즉, 현재 시스템은 기사별 signal 생성까지 가능하며,
이번 단계는 이를 매매 판단의 기초 점수로 연결하는 첫 단계다.

---

## 이번 단계에서 해야 할 일

1. signal 리스트를 입력받는다
2. importance 기반 weight를 정의한다
   - HIGH = 3
   - MEDIUM = 2
   - LOW = 1
3. direction에 따라 점수를 합산한다
   - bullish → +weight
   - bearish → -weight
   - neutral/mixed → 0
4. 최종 score를 바탕으로 간단한 판단 결과를 반환한다
   - buy_candidate
   - sell_candidate
   - hold
5. score 외에 기초 집계 정보도 함께 반환한다
   - bullish_count
   - bearish_count
   - total_signals

---

## 이번 단계에서 하지 말아야 할 일

- 시장 전체 집계 구현
- 종목별 집계 구현
- 차트/가격 필터 결합
- 자동매매 실행 로직 구현
- ML 기반 scoring
- threshold 튜닝 고도화

---

## 설계 원칙

1. 순수 함수 형태로 구현한다
2. 설명 가능한 규칙 기반을 유지한다
3. 현재 단계에서는 단순함을 우선한다
4. 이후 시장/종목 집계에 재사용 가능해야 한다

---

## 완료 조건

1. signal scoring 함수가 구현된다
2. 입력 signal 리스트에 대해 total_score 계산 가능
3. bullish/bearish 개수 계산 가능
4. buy/sell/hold 판단 결과 반환 가능
5. 다음 단계에서 종목별/시장별 집계 함수가 이 scoring 함수를 재사용할 수 있다

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `signal-scoring.md`
- `output-format.md`

---

## 작업 판단 기준

좋은 결과:
- 단순하고 읽기 쉽다
- 현재 단계 범위를 넘지 않는다
- 다음 단계로 확장하기 쉽다

좋지 않은 결과:
- 집계 구조까지 한 번에 구현한다
- 차트 조건을 섞는다
- 과도한 점수 체계를 추가한다