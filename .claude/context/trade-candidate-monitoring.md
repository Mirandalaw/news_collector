# Trade Candidate Monitoring (운영 검증 단계)

## 목표
price filter 및 signal pipeline의 실전 유효성 검증

---

## 검증 기준

### 1. 후보 개수
- 0건 지속 → 과도한 필터 (문제)
- 1~3건 → 정상 (목표)
- 5건 이상 → 과도 완화 (노이즈)

---

### 2. false positive
- 의미 없는 종목이 후보로 올라오는 경우
- 예:
  - 약한 뉴스 + 기술적으로 애매
  - 거래량 거의 없음

→ 발견 시: 필터 강화 필요

---

### 3. false negative
- 강한 signal + 정상 차트인데 탈락

→ 발견 시: 필터 완화 필요

---

## 주요 체크 포인트

### price filter
- MA20 조건
- 거래량 조건 (현재: 0.7x avg)
- surge_ratio 조건

---

### signal
- HIGH signal 여부
- rule 정확도 (earnings / geopolitics 등)

---

### decision
- buy_candidate / sell_candidate 판단 타당성

---

## 기록 방식

매일 기록:

날짜:
후보 개수:
후보 목록:
  - symbol / reason

이상 사례:
  - false positive:
  - false negative:

---

## 수정 원칙

1. 한 번에 하나만 수정
2. 최소 2~3일 데이터 후 판단
3. 감이 아니라 패턴 기반으로 수정

---

## 현재 기준 (2026-04-12)

- volume threshold: 0.7
- 결과: 1건 (정상 범위)
- false positive: 없음
- false negative: 일부 존재 (005930 경계)