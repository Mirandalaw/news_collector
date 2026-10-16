# 소급 수집 뉴스 스냅샷 (2021~2024년 8~11월)

`output/snapshots/*.jsonl` 과 같은 형식. 웹 검색으로 수집한 5품목 수급 사건 기사 — 2021: 56건 / 2022: 64건 / 2023: 43건 / 2024: 82건.
발행일시는 기사 페이지에서 확인한 값만 썼다. 요약은 본문을 줄인 것이며 수량(톤·%·ha)은 그대로 보존했다.

```bash
python scripts/run_agri_signals.py --from-snapshots data/backfill --out agri_signals_backfill.csv
```
→ price-forecast 의 `data/agri_signals.csv` 로 복사하면 뉴스 on/off 백테스트가 돈다.
