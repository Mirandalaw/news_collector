"""농산물 뉴스 → 일자·품목 피처 CSV (price-forecast 입력).

  python scripts/run_agri_signals.py --from-db --since 2026-01-01 --out agri_signals.csv
  python scripts/run_agri_signals.py --from-snapshots snapshots/ --out agri_signals.csv
  (두 번째가 폐쇄망 재현 검증용 — DB·외부 API 없이 jsonl 만 읽는다)

출력 CSV 는 price-forecast 의 data/agri_signals.csv 로 복사해 쓴다.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.signals import agri_features as AF


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-db", action="store_true")
    g.add_argument("--from-snapshots", metavar="DIR")
    ap.add_argument("--since", default="2024-01-01")
    ap.add_argument("--out", default="agri_signals.csv")
    a = ap.parse_args()

    if a.from_db:
        from app.db.connection import DatabaseConfig, managed_connection

        with managed_connection(DatabaseConfig.from_env()) as conn:
            arts = AF.read_db(conn, date.fromisoformat(a.since))
    else:
        arts = AF.read_snapshots(sorted(Path(a.from_snapshots).glob("*.jsonl")))

    rows = AF.aggregate_daily(arts)
    n = AF.write_csv(rows, Path(a.out))
    ev = sum(r["event_cnt"] for r in rows)
    print(f"기사 {len(arts)}건 → (일자,품목) {n}행, 사건 {ev}건 → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
