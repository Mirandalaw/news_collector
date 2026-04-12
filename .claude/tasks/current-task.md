# CURRENT TASK

## 작업명
trade candidate output integration

## 목표
trade candidate report를 브리핑 또는 알림 레이어에 연결하여
최종 매매 후보를 실제 출력에서 볼 수 있게 한다.

---

## 현재 상태

- trade candidate output MVP 구현 완료
- format_text()로 텍스트 생성 가능
- 아직 상위 레이어 연결 없음

---

## 이번 단계에서 해야 할 일

1. trade candidate report 생성 위치 결정
2. briefing 또는 알림 레이어에 연결
3. 최종 후보 섹션을 출력에 추가

---

## 이번 단계에서 하지 말아야 할 일

- 주문 실행
- 시세 조회 구현
- 포지션 관리
- 가격 계산 구현
- 브리핑 구조 대규모 개편

---

## 완료 조건

1. 최종 후보 섹션이 실제 출력에 나타난다
2. 후보가 없을 때 처리 방식이 명확하다
3. 기존 브리핑 흐름이 깨지지 않는다