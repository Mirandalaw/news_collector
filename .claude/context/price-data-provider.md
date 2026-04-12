# PRICE DATA PROVIDER

## 목적

trade candidate pipeline에서 필요한 `PriceFilterInput` 값을
종목별 시세 데이터로부터 자동 생성한다.

현재 시스템은 아래 단계까지 완료되어 있다.

- signal 생성
- scoring
- aggregation
- decision
- price filter
- price filter application
- trade candidate output
- morning briefing 연결

하지만 실제 가격 데이터 공급 레이어가 없어
현재는 `price_inputs={}`로 동작하며
항상 "최종 매매 후보 없음 (가격 데이터 미연결)" 상태다.

이 문서는 종목별 시세 데이터를 조회하고,
`PriceFilterInput`을 생성하는 공급 레이어의 구현 기준을 정의한다.

---

## 목표

1. 종목 코드 목록을 입력받아 시세 데이터를 조회한다
2. `PriceFilterInput`에 필요한 값을 계산한다
3. 종목별 `PriceFilterInput` 딕셔너리를 반환한다
4. 조회 실패 종목은 전체 브리핑 실패 없이 제외한다
5. 이후 `apply_price_filters(...)`에 바로 연결할 수 있어야 한다

---

## 책임 정의

### PriceDataProvider의 책임
- 입력: `list[str]` 종목 코드 목록
- 출력: `dict[str, PriceFilterInput]`
- 역할:
  - 시세 데이터 조회
  - 지표 계산
  - `PriceFilterInput` 생성

### PriceDataProvider의 비책임
- signal 계산
- decision 계산
- price filter 적용
- 주문 실행
- 포지션 관리
- 자동매매 실행

---

## 필요한 값

각 종목에 대해 아래 값을 생성해야 한다.

### 1. close_price
- 최근 거래일 종가

### 2. ma20
- 최근 20 거래일 종가 평균

### 3. volume
- 최근 거래일 거래량

### 4. avg_volume
- 최근 20 거래일 거래량 평균

### 5. surge_ratio
- 최근 N일 기준 수익률
- 기본식:
  - `(close_price - N일 전 종가) / N일 전 종가`
- MVP 기본값:
  - `N = 5`

---

## 데이터 소스 선택

### 후보 1. FinanceDataReader
장점:
- 한국 종목(KRX) 직접 지원
- 종목 코드 그대로 사용 가능
- MVP 구현 단순

단점:
- 외부 라이브러리 의존성 추가 필요

### 후보 2. yfinance
장점:
- 글로벌 종목 커버
- 범용성 높음

단점:
- 한국 종목 코드 변환 필요 (`005930.KS`)
- 현재 프로젝트에서는 불필요한 복잡도 증가

### 결정
초기 MVP는 **FinanceDataReader 사용**을 우선한다.

---

## 함수 시그니처

초기 구현은 아래 형태를 기본으로 한다.

```python
def fetch_price_inputs(
    symbols: list[str],
    lookback_days: int = 30,
    surge_window: int = 5,
) -> dict[str, PriceFilterInput]:
    ...