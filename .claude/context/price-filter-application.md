# PRICE FILTER APPLICATION

## 목적

decision 단계에서 생성된 종목별 판단 결과에 대해,
각 종목의 가격/차트 입력값을 결합하여 price filter를 일괄 적용한다.

현재는 `apply_price_filter(symbol, news_decision, price_data)`가 개별 종목에 대해서만 동작한다.
다음 단계는 종목 전체 후보군에 대해 이를 반복 적용하는 상위 함수를 구현하는 것이다.

---

## 현재 상태

현재 시스템은 아래 단계까지 구현되어 있다.

1. 뉴스 수집
2. dedup / noise filtering
3. event 분류
4. signal 생성
5. signal dedup
6. signal scoring
7. signal aggregation
8. signal decision
9. price filter (개별 종목)

즉, 개별 종목에 대한 뉴스 기반 판단과 가격 필터는 가능하지만,
이를 종목 전체 후보군에 대해 일괄 적용하는 상위 레이어는 아직 없다.

---

## 목표

1. `DecisionResult.by_symbol_decision`을 순회한다
2. 각 종목에 대해 `PriceFilterInput`을 조회한다
3. `apply_price_filter(...)`를 호출한다
4. 종목별 결과를 하나의 구조로 반환한다
5. 이후 브리핑/대시보드/매매판단 레이어에서 재사용 가능한 형태를 만든다

---

## 입력 구조

초기 구현 입력은 아래 두 가지를 받는다.

### 1. decision
- 타입: `DecisionResult`
- 역할: 종목별 뉴스 기반 판단 제공

예:
- `decision.by_symbol_decision["005930"] = "buy_candidate"`

### 2. price_inputs
- 타입: `dict[str, PriceFilterInput]`
- 역할: 종목별 가격/거래량/이평/급등률 정보 제공

예:
- `price_inputs["005930"] = PriceFilterInput(...)`

---

## 출력 구조

초기 MVP는 아래 형태를 반환하는 것이 적절하다.

### 예시 1: dict 직접 반환
- `dict[str, PriceFilterResult]`

### 예시 2: dataclass 반환
- `PriceFilterApplicationResult`
  - `by_symbol: dict[str, PriceFilterResult]`

초기 구현은 dataclass를 사용하는 편이 이후 확장에 유리하다.

---

## 누락 입력 처리

모든 종목에 대해 `price_inputs[symbol]`가 존재하지 않을 수 있다.

이 경우 원칙:

1. 예외로 전체를 중단하지 않는다
2. 해당 종목은 `price_filter_pass = False`
3. `final_candidate = False`
4. `reason`에 `"price data missing"` 명시

---

## 설계 원칙

1. `apply_price_filter`를 재사용한다
2. 가격 입력 계산 책임은 호출자에게 둔다
3. 이 레이어는 적용만 수행한다
4. 종목별로 독립 처리한다
5. dict 기반 단순 구조로 시작한다

---

## 금지사항

- 실시간 시세 조회 구현
- MA20 / avg_volume / surge_ratio 계산 구현
- 자동 주문 실행
- 포지션 관리
- 손절/익절 자동화
- 브리핑 렌더러 직접 수정

---

## 다음 단계 연결

이 단계 다음에는 아래 순서로 확장한다.

1. 종목별 price filter application 구현
2. 결과를 브리핑/대시보드용 요약으로 변환
3. 시세 공급 레이어 연결
4. 최종적으로 자동매매 판단 레이어와 연결