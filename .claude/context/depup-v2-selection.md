# DEDUP V2 REPRESENTATIVE SELECTION

## 목적

같은 그룹으로 묶인 기사 중
가장 의미 있는 대표 기사 1개를 선택한다.

---

## 현재 문제

현재는 group[0]을 대표로 사용한다.

이로 인해:
- signal 있는 기사를 놓칠 수 있음
- 정보량 적은 기사 선택 가능
- 최신 기사 반영이 안 될 수 있음

---

## 선택 기준

우선순위:

1. signal 존재 여부
2. 제목 길이 (정보량)
3. 최신 기사 (published_at)

---

## 원칙

1. 단순 비교 로직 사용
2. 복잡한 scoring 금지
3. builder 흐름 유지
4. 오탐보다 미탐 우선

---

## 출력 정책

- 그룹당 1개 기사만 유지
- 나머지는 제거

---

## 금지사항

- threshold 수정
- normalize 수정
- 그룹핑 로직 수정
- event_section 적용