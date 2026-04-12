# SIGNAL DEDUP

## 목적
한 기사에 여러 signal이 동시에 생성되는 문제를 해결한다.

---

## 현재 문제

동일 기사에서 아래와 같은 중복 발생 가능:

- earnings_beat (HIGH)
- event_earnings_beat (MEDIUM)

---

## 목표

1. 한 기사당 하나의 대표 signal만 유지
2. 중요도가 높은 signal을 우선 선택
3. 중복 signal 제거

---

## 선택 우선순위

1. importance 높은 것 우선
2. direction은 고려하지 않음
3. 동일 importance면 기존 순서 유지

---

## 적용 위치

SignalEngine 내부 또는 builder에서 적용

---

## 금지

- signal rule 수정
- importance 값 변경
- rule 제거