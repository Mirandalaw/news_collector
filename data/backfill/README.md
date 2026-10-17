# 소급 수집 뉴스 스냅샷 (2015~2024년 8~11월)

`output/snapshots/*.jsonl` 과 같은 형식. 웹 검색으로 수집한 5품목 수급 사건 기사 — 2015: 29 / 2016: 36 / 2017: 25 / 2018: 31 / 2019: 6 / 2020: 21 / 2021: 56 / 2022: 64 / 2023: 43 / 2024: 82 (합계 393건).
2015~2020 은 검색엔진의 최신 기사 편향 때문에 수율이 낮다(특히 2019). 양파·마늘 단독 사건은 농민신문·농어민신문 등 접근 불가 매체에만 있어 거의 비어 있다.
발행일시는 기사 페이지에서 확인한 값만 썼다. 요약은 본문을 줄인 것이며 수량(톤·%·ha)은 그대로 보존했다.

```bash
python scripts/run_agri_signals.py --from-snapshots data/backfill --out agri_signals_backfill.csv
```
→ price-forecast 의 `data/agri_signals.csv` 로 복사하면 뉴스 on/off 백테스트가 돈다.
