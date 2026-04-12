# PRICE FILTER

## 목적

뉴스 기반 decision 결과를 실제 매매 후보로 연결하기 전에,
가격/차트 조건을 통해 진입 가능 여부를 한 번 더 검증한다.

현재 시스템은 뉴스 → signal → scoring → aggregation → decision까지 완료되어 있다.
다음 단계는 decision 결과를 그대로 주문으로 연결하지 않고,
가격/차트 필터를 통해 최종 후보를 좁히는 것이다.

---

## 현재 상태

현재 시스템은 아래 단계까지 구현되어 있다.

1. 뉴스 수집
2. dedup / noise filtering
3. event 분류
4. signal 생성
5. signal dedup
6. scoring
7. aggregation
8. decision

즉, 현재는 뉴스 기반 1차 판단이 가능하며,
이번 단계는 이를 실제 진입 후보로 좁히는 가격 필터 레이어를 구현하는 것이다.

---

## 목표

1. 뉴스 판단과 가격 판단을 분리한다
2. buy_candidate / sell_candidate를 그대로 주문으로 연결하지 않는다
3. 가격/차트 조건을 만족하는 경우에만 최종 후보로 인정한다
4. 이 레이어는 순수 함수로 유지한다

---

## 입력 구조

초기 MVP 입력은 아래 값을 사용한다.

### PriceFilterInput

- `symbol: str`
- `news_decision: str`
  - `"buy_candidate"`
  - `"sell_candidate"`
  - `"hold"`
- `close_price: float`
- `ma20: float`
- `volume: float`
- `avg_volume: float`
- `surge_ratio: float`

---

## 판단 기준

### buy_candidate

아래 조건을 모두 만족해야 통과한다.

1. `close_price > ma20`
2. `volume >= avg_volume`
3. `surge_ratio <= 0.15`

해석:
- 상승 추세 위
- 거래량 뒷받침
- 과도한 급등 추격 아님

---

### sell_candidate

아래 조건을 모두 만족해야 통과한다.

1. `close_price < ma20`
2. `surge_ratio >= -0.15`

해석:
- 약세 추세
- 이미 과도한 급락 후 반등 구간은 제외

---

### hold

- 조건 검사 없이 항상 `price_filter_pass = False`

해석:
- 뉴스 판단상 보류 상태는 가격 필터로 승격시키지 않는다

---

## 출력 구조

### PriceFilterResult

- `symbol: str`
- `news_decision: str`
- `price_filter_pass: bool`
- `final_candidate: bool`
- `reason: str`

### final_candidate 규칙

아래 조건을 만족할 때만 True:

- `news_decision in ("buy_candidate", "sell_candidate")`
- `price_filter_pass is True`

---

## 설계 원칙

1. 입력값 계산 책임은 호출자에게 있다
2. 이 레이어는 계산된 입력값만 받아 판단한다
3. 가격 판단과 뉴스 판단을 분리한다
4. 조건은 단순하고 설명 가능해야 한다
5. MVP 단계에서는 이동평균 + 거래량 + 급등/급락 제한 정도만 사용한다

---

## 금지사항

- 실시간 시세 조회 구현
- 주문 실행
- 포지션 관리
- 손절/익절 자동화
- RSI / MACD / 볼린저밴드 등 과도한 지표 추가
- 동적 threshold 최적화

---

## 구현 범위

이번 단계 포함:
- `PriceFilterInput` dataclass
- `PriceFilterResult` dataclass
- `apply_price_filter(...)` 순수 함수

이번 단계 제외:
- 실제 시세 데이터 수집
- surge_ratio 계산 함수
- 종목별 일괄 적용 상위 함수
- 자동매매 연결

---

## 다음 단계 연결

이 단계 다음에는 아래 순서로 확장한다.

1. `apply_price_filter` 구현
2. `DecisionResult.by_symbol_decision`에 일괄 적용하는 상위 함수 구현
3. 이후 실시간 시세 데이터 조회 레이어 연결
4. 최종적으로 자동매매 엔진과 연결