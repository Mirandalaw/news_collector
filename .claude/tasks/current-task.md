# CURRENT TASK

## 작업명
dedup v2 normalize 보강 - 숫자 토큰 제거

## 목표
dedup v2에서 similarity를 불필요하게 낮추는 수치 토큰을 normalize_title 단계에서 제거한다.

현재 단계에서는 threshold를 변경하지 않고,
normalize_title의 입력 품질만 보수적으로 개선한다.

---

## 현재 상태

- dedup v2는 builder에 적용 완료
- representative selection까지 구현 완료
- 기사쌍 분석 결과, 주요 원인은 threshold보다 normalize 부족으로 판단했다
- 특히 숫자 토큰이 합집합을 키워 similarity를 낮추는 문제가 확인되었다

---

## 이번 단계에서 해야 할 일

1. normalize_title에서 숫자 토큰 제거 규칙 추가
2. similarity 희석에 기여하는 수치형 토큰을 비교 대상에서 제외
3. 기존 normalize 흐름은 최대한 유지

예상 대상:
- 순수 숫자 토큰
- 숫자+영문/단위 형태 중 비교 의미가 낮은 토큰

---

## 이번 단계에서 하지 말아야 할 일

- threshold 변경
- builder 수정
- symbols 조건 수정
- event dedup 적용
- 대표 기사 선택 기준 수정
- 한영 동의어 사전 추가

---

## 수정 원칙

1. 최소 수정만 한다
2. 수치 토큰 제거부터 시작한다
3. 의미 있는 단어는 제거하지 않는다
4. threshold는 그대로 유지한다

---

## 완료 조건

1. normalize_title에 숫자 토큰 제거 규칙이 추가된다
2. 기존 구조는 유지된다
3. 다음 검증에서 Pair 2, 6류 similarity 개선 가능성이 생긴다