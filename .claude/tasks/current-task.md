# CURRENT TASK

## 작업명
price filter application MVP 구현

## 목표
decision 단계의 종목별 판단 결과에 대해,
price filter를 종목별로 일괄 적용하는 상위 함수를 구현한다.

현재 단계에서는 실시간 시세 조회를 구현하지 않고,
이미 계산된 `PriceFilterInput`을 받아 종목별 결과를 반환하는 순수 함수만 만든다.

---

## 현재 상태

- signal scoring MVP 구현 완료
- signal aggregation MVP 구현 완료
- signal decision MVP 구현 완료
- price filter MVP 구현 완료

즉, 개별 종목에 대한 뉴스 판단과 가격 필터는 가능하지만,
종목 전체 후보군에 대한 일괄 적용 함수는 아직 없다.

---

## 이번 단계에서 해야 할 일

1. `DecisionResult.by_symbol_decision`을 순회한다
2. 각 종목에 대해 `price_inputs[symbol]`를 조회한다
3. `apply_price_filter(...)`를 호출한다
4. 종목별 `PriceFilterResult`를 반환한다
5. 입력 누락 종목은 안전하게 처리한다

---

## 이번 단계에서 하지 말아야 할 일

- 실시간 시세 조회 구현
- MA20 / avg_volume / surge_ratio 계산 구현
- 자동 주문 실행
- 포지션 관리
- 손절/익절 자동화
- 브리핑 렌더러 수정

---

## 누락 입력 처리 원칙

price input이 없는 종목은 예외로 전체를 중단하지 않는다.

대신:
- `price_filter_pass = False`
- `final_candidate = False`
- `reason = "price data missing"`

으로 처리한다.

---

## 설계 원칙

1. 기존 `apply_price_filter`를 재사용한다
2. 순수 함수 형태를 유지한다
3. 종목별로 독립 처리한다
4. 결과는 dict 또는 dataclass 형태로 반환한다
5. 다음 단계에서 브리핑/대시보드가 이 결과를 쉽게 사용할 수 있어야 한다

---

## 완료 조건

1. 종목별 price filter 일괄 적용 가능
2. `DecisionResult`와 `PriceFilterInput` dict를 입력으로 받을 수 있음
3. 결과를 종목별 `PriceFilterResult`로 반환
4. 입력 누락 종목도 안전하게 처리
5. 이후 브리핑/대시보드 연결이 가능

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `signal-decision.md`
- `price-filter.md`
- `price-filter-application.md`
- `output-format.md`

---

## 작업 판단 기준

좋은 결과:
- `apply_price_filter` 재사용
- 단순하고 읽기 쉬움
- 누락 입력 처리 명확
- 다음 단계 확장 쉬움

좋지 않은 결과:
- 시세 조회까지 섞음
- 가격 계산까지 넣음
- 브리핑 출력까지 한 번에 수정