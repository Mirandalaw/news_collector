# CURRENT TASK

## 작업명
signal v2 STEP 2 검증

## 목표
event 기반 신규 signal rule이 실제 브리핑 출력에서 자연스럽게 동작하는지 확인한다.

---

## 현재 상태

- negation 기반 방향 반전 구현 완료
- event_rules.py 추가 완료
- geopolitics / earnings 규칙 registry 등록 완료

---

## 이번 단계에서 해야 할 일

1. 실제 브리핑 출력 확인
2. geopolitics bearish 발동 여부 확인
3. earnings beat/miss 발동 여부 확인
4. 기존 symbol_rules와 중복 노출 여부 확인
5. 오탐 여부 확인

---

## 이번 단계에서 하지 말아야 할 일

- importance 전체 개편
- renderer 수정
- event classifier 수정
- 새로운 규칙 추가

---

## 완료 조건

1. 실제 출력에서 신규 signal 동작 확인
2. 중복/오탐 여부 판단
3. 다음 단계 방향 결정
   - 유지
   - 중복 조정
   - importance 보정