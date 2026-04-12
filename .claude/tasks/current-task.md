# CURRENT TASK

## 작업명
signal v2 STEP 2 - event 기반 규칙 추가

## 목표
event 성격이 강한 기사 중 기존 규칙이 충분히 커버하지 못하는 영역에
최소한의 신규 signal rule을 추가한다.

---

## 현재 상태

- signal v2 STEP 1로 negation 기반 방향 반전 구현 완료
- 기존 규칙은 rate / oil을 상당 부분 커버하고 있다
- 신규 가치가 큰 영역은 geopolitics, earnings로 판단했다

---

## 이번 단계에서 해야 할 일

1. `app/signals/rules/event_rules.py` 신규 생성
2. `GEOPOLITICS_BEARISH` 규칙 추가
3. `EARNINGS_BEAT` 규칙 추가
4. `EARNINGS_MISS` 규칙 추가
5. registry.py에 등록

---

## 이번 단계에서 하지 말아야 할 일

- policy 규칙 추가
- oil / rate 신규 규칙 추가
- event_type DTO 추가
- renderer 수정
- importance 전체 개편

---

## 구현 원칙

1. 기존 `KeywordSignalRule` 재사용
2. 최소 규칙만 추가
3. geopolitics 규칙에는 negation 반전을 넣지 않는다
4. earnings는 실적 키워드 + 방향 키워드 동시 존재 시에만 발동한다

---

## 완료 조건

1. 신규 event_rules 파일 생성
2. geopolitics / earnings 규칙 등록 완료
3. 기존 signal 구조와 충돌 없이 동작
4. 오탐 위험이 큰 policy 영역은 제외 유지