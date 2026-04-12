
---

# 2. `tasks/current-task.md`

```md
# CURRENT TASK

## 작업명
price data provider MVP 구현

## 목표

종목 코드 목록을 입력받아
`PriceFilterInput` 딕셔너리를 생성하는 price data provider를 구현한다.

현재 단계에서는 한국 종목(KRX) 기준으로
FinanceDataReader를 사용한 MVP만 구현한다.

---

## 현재 상태

- signal scoring 구현 완료
- signal aggregation 구현 완료
- signal decision 구현 완료
- price filter 구현 완료
- price filter application 구현 완료
- trade candidate output 구현 완료
- morning briefing 렌더러 연결 완료

하지만 현재는 `price_inputs={}`로 고정되어 있어
항상 "최종 매매 후보 없음 (가격 데이터 미연결)" 상태다.

---

## 이번 단계에서 해야 할 일

1. `app/signals/price_data_provider.py` 파일 생성
2. FinanceDataReader로 종목별 시세 조회
3. 아래 값 계산
   - close_price
   - ma20
   - volume
   - avg_volume
   - surge_ratio
4. `dict[str, PriceFilterInput]` 반환
5. 데이터 부족/조회 실패 종목은 skip 처리
6. `morning_briefing_service.py`에서 `price_inputs={}`를 실제 provider 호출로 교체

---

## 이번 단계에서 하지 말아야 할 일

- 주문 실행
- 포지션 관리
- 자동매매 연결
- 손절/익절 자동화
- 기술지표 확장
- 글로벌 종목(yfinance) 동시 지원

---

## 실패 처리 원칙

1. 특정 종목 조회 실패 시 전체 실패 금지
2. 조회 실패 종목은 결과 dict에서 제외
3. 브리핑 전체는 정상 생성 유지
4. 이후 `apply_price_filters(...)`가 누락 종목을 `"price data missing"`으로 처리할 수 있어야 한다

---

## 구현 원칙

1. 브리핑 생성 시점에 한 번만 조회
2. 계산 책임은 provider에 둔다
3. 필터 적용 책임은 기존 레이어에 둔다
4. 최대한 단순하게 구현한다
5. 한국 종목 기준 MVP에 집중한다

---

## 완료 조건

1. `fetch_price_inputs(...)` 구현
2. `PriceFilterInput` 자동 생성 가능
3. 실패 종목 skip 처리 가능
4. `morning_briefing_service.py`에서 실제 provider 연결 완료
5. 브리핑 하단 "매매 후보" 섹션이 실제 종목을 표시할 수 있는 상태가 된다

---

## 참고 문서

- `project-overview.md`
- `constraints.md`
- `price-filter.md`
- `price-filter-application.md`
- `trade-candidate-output.md`
- `price-data-provider.md`
- `output-format.md`

---

## 작업 판단 기준

좋은 결과:
- 단순하고 읽기 쉬움
- 실패 종목 안전 처리
- 브리핑 전체 실패 없음
- 기존 레이어와 자연스럽게 연결

좋지 않은 결과:
- 조회 실패 시 전체 예외 전파
- price filter 계산과 혼합
- 글로벌 종목 지원까지 같이 확장
- 기술지표를 과도하게 추가