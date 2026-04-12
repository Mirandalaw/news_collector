# CURRENT TASK

## 작업명
trade candidate output MVP 구현

## 목표
price filter application 결과를 사람이 읽을 수 있는 형태로 요약하는 출력 함수를 구현한다.

현재 단계에서는 브리핑 구조를 크게 바꾸지 않고,
최종 매매 후보만 정리하는 별도 출력 레이어를 먼저 만든다.

---

## 현재 상태

- signal scoring 완료
- signal aggregation 완료
- signal decision 완료
- price filter 완료
- price filter application 완료

즉, 최종 후보 계산은 가능하지만
사용자에게 보여주는 출력 레이어는 없다.

---

## 이번 단계에서 해야 할 일

1. `PriceFilterApplicationResult`를 입력받는다
2. `final_candidate=True` 종목을 추린다
3. 사람이 읽을 수 있는 요약 구조를 만든다
4. 필요 시 buy/sell 구분을 유지한다

---

## 이번 단계에서 하지 말아야 할 일

- 주문 실행
- 브리핑 전체 renderer 대규모 수정
- 시세 조회 구현
- 포지션 관리
- 자동매매 엔진 연결

---

## 설계 원칙

1. 계산 로직과 출력 로직 분리
2. 기존 구조를 크게 흔들지 않음
3. 사람이 바로 읽을 수 있어야 함
4. MVP는 최종 후보 요약까지만 구현

---

## 완료 조건

1. 최종 후보 종목 요약 가능
2. buy/sell 구분 가능
3. 이후 브리핑/대시보드 연결 쉬움