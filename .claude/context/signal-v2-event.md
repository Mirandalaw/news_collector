# SIGNAL V2 EVENT LINKING

## 목적
event_type 정보를 signal 판단에 더 직접적으로 반영한다.

---

## 현재 한계

- event 섹션은 존재하지만 signal 방향과의 연결이 약하다
- 금리 / 유가 / 지정학 이벤트가 signal에 충분히 반영되지 않을 수 있다

---

## 목표

1. event_type별 기본 방향 규칙을 정리한다
2. 기존 keyword signal과 충돌하지 않도록 보수적으로 반영한다
3. 시장 전체 영향이 큰 이벤트의 중요도를 더 일관되게 만든다

---

## 대상 event_type

- rate
- oil
- earnings
- policy
- geopolitics

---

## 기본 방향 예시

### rate
- 금리 인하 → bullish
- 금리 인상 → bearish

### oil
- 유가 상승 / 공급 차질 → bearish
- 유가 안정 / 하락 → bullish

### geopolitics
- 전쟁 / 분쟁 / 봉쇄 / 제재 강화 → bearish

### policy
- 경기 부양 / 규제 완화 → bullish
- 규제 강화 / 관세 확대 → bearish

---

## 원칙

1. keyword rule 위에 덧씌우지 않고 보조적으로 연결한다
2. 과도한 자동 추론 금지
3. event_type이 명확한 기사부터 적용한다
4. 애매하면 기존 signal 유지

---

## 금지사항

- ML 모델 도입
- 복잡한 scoring
- event_type 전체를 무조건 signal로 변환