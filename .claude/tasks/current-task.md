# CURRENT TASK

## 작업명
price filter MVP 구현

## 목표
뉴스 기반 decision 결과를 가격/차트 조건으로 한 번 더 검증하는
price filter 순수 함수를 구현한다.

현재 단계에서는 시세 조회나 주문 실행을 구현하지 않고,
입력값이 주어졌을 때 통과 여부를 판단하는 순수 함수만 만든다.

---

## 현재 상태

- signal scoring MVP 구현 완료
- signal aggregation MVP 구현 완료
- signal decision MVP 구현 완료
- price filter 설계 완료

즉, 현재는 뉴스 기반 판단이 가능하며,
이번 단계는 이를 실제 진입 후보로 좁히는 가격 필터를 구현하는 단계다.

---

## 이번 단계에서 해야 할 일

1. `PriceFilterInput` dataclass 구현
2. `PriceFilterResult` dataclass 구현
3. `apply_price_filter(...)` 순수 함수 구현
4. buy_candidate / sell_candidate / hold 기준에 따라 통과 여부를 판단한다
5. 사람이 읽을 수 있는 `reason` 문자열을 반환한다

---

## 판단 기준

### buy_candidate
아래 조건을 모두 만족해야 통과

- `close_price > ma20`
- `volume >= avg_volume`
- `surge_ratio <= 0.15`

### sell_candidate
아래 조건을 모두 만족해야 통과

- `close_price < ma20`
- `surge_ratio >= -0.15`

### hold
- 항상 `price_filter_pass = False`

---

## 이번 단계에서 하지 말아야 할 일

- 실시간 시세 조회 구현
- surge_ratio 계산 구현
- 종목별 일괄 적용 상위 함수 구현
- 주문 실행
- 포지션 관리
- 손절/익절 자동화
- 기술적 지표 확장

---

## 설계 원칙

1. 순수 함수로 구현한다
2. 입력값 계산 책임은 호출자에게 둔다
3. 뉴스 판단과 가격 판단을 분리한다
4. 설명 가능한 규칙 기반을 유지한다
5. 단순함을 우선한다

---

## 완료 조건

1. `PriceFilterInput` 구현
2. `PriceFilterResult` 구현
3. `apply_price_filter(...)` 구현
4. buy/sell/hold에 대한 판단이 정상 동작
5. `reason`을 통해 통과/탈락 이유 확인 가능

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `signal-scoring.md`
- `signal-aggregation.md`
- `signal-decision.md`
- `price-filter.md`
- `output-format.md`

---

## 작업 판단 기준

좋은 결과:
- 순수 함수 형태
- 단순하고 읽기 쉬움
- 다음 단계 확장 쉬움

좋지 않은 결과:
- 시세 조회까지 같이 구현
- 주문/포지션 로직 섞음
- 지표를 과도하게 늘림