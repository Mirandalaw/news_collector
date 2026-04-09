# CURRENT TASK

## 작업명
event classifier 오분류 보정

## 목표
event 섹션에서 발생하는 잘못된 event_type 분류를 줄인다.

## 현재 상태
- builder 레이어에서 event 재분류 구현 완료
- event_section 정상 출력됨 (빈 섹션 문제 해결됨)
- event_type:
  - rate / oil / earnings / policy / geopolitics
- classify_event_type(title) 기반 substring 매칭 사용
- 일부 기사에서 잘못된 event_type이 붙는 문제 발생

## 확인된 문제

### 1. oil 오분류
- 예:
  "日 학생 5000명 방울 달고 등교..." → [유가]
- 실제로는 유가와 무관한 기사
- substring 매칭이 너무 넓게 잡혀 있을 가능성

### 2. geopolitics 과매칭
- 예:
  "전쟁추경..." → [지정학]
- 실제로는 정책/재정 성격이 더 강함

### 3. keyword 기반 분류 한계
- 짧은 키워드 또는 일반 단어 포함 시 오분류 발생 가능

## 이번 단계에서 해야 할 일

1. `event_classifier.py`의 keyword 목록 점검
2. 특히 아래 타입 집중 분석
   - oil
   - policy
   - geopolitics

3. 오분류를 유발할 가능성이 높은 keyword 식별

4. 최소 수정으로 keyword 보정
   - 너무 일반적인 단어 제거
   - 의미가 명확한 키워드로 교체
   - 필요 시 키워드 축소

## 이번 단계에서 하지 말아야 할 일

- builder 로직 수정 금지
- DB 구조 변경 금지
- event_type 구조 변경 금지
- 다중 event_type 허용 금지
- classifier 구조 변경 금지 (substring 방식 유지)
- config 외부화 금지

## 수정 원칙

- 보수적으로 수정한다
- 오탐 감소를 우선한다
- 일부 누락보다 오분류 제거가 더 중요하다
- 최소 변경으로 효과를 낸다

## 완료 조건

- 명백한 오분류 케이스 제거
- oil / geopolitics 오탐 감소
- 기존 정상 분류 케이스는 유지
- 수정 후 재실행 시 event 섹션 품질 개선 확인

## 검증 방법

1. `docker compose --profile jobs run --rm all` 실행
2. event 섹션 확인

체크리스트:
- [ ] 의미 없는 기사에 event_type이 붙지 않음
- [ ] 금리 / 유가 / 지정학 기사만 남음
- [ ] event 개수 과도하지 않음
- [ ] market과 완전 동일 리스트가 아님