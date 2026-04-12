# TRADE CANDIDATE OUTPUT

## 목적

signal / decision / price filter application 결과를
사람이 읽을 수 있는 형태로 요약하여 브리핑 또는 대시보드에 노출한다.

현재 시스템은 최종 후보 계산까지 가능하지만,
이 결과를 사용자에게 보여주는 출력 레이어는 아직 없다.

---

## 현재 상태

- signal scoring 완료
- signal aggregation 완료
- signal decision 완료
- price filter 완료
- price filter application 완료

즉, 내부적으로는 최종 매매 후보를 계산할 수 있으나,
이 결과를 실제 브리핑이나 대시보드에 표시하는 단계가 필요하다.

---

## 목표

1. 최종 매매 후보를 사람이 읽을 수 있게 정리한다
2. 종목별 최종 후보만 요약해서 보여준다
3. 브리핑 전체를 과도하게 복잡하게 만들지 않는다

---

## 출력 대상

초기 MVP는 아래 항목만 노출한다.

- symbol
- news_decision
- price_filter_pass
- final_candidate
- reason

---

## 출력 정책

### 포함 대상
- `final_candidate = True` 인 종목 우선
- 필요 시 `final_candidate = False` 중 주요 종목만 추가 가능

### 정렬 기준
- buy_candidate 우선
- sell_candidate 다음
- symbol 기준 보조 정렬

---

## 적용 위치

초기 구현은 아래 둘 중 하나를 선택한다.

1. 브리핑 하단 별도 섹션
2. 별도 요약 함수/대시보드용 출력 함수

초기 단계에서는 브리핑 렌더러를 크게 흔들지 않는 별도 요약 함수가 더 안전하다.

---

## 설계 원칙

1. 계산 로직과 출력 로직을 분리한다
2. 기존 브리핑 구조를 크게 흔들지 않는다
3. 사람이 빠르게 읽을 수 있어야 한다
4. MVP는 최종 후보 요약까지만 한다

---

## 금지사항

- 주문 실행
- 포지션 관리
- 자동 리밸런싱
- renderer 대규모 개편