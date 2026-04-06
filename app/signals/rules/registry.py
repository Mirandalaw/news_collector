"""시그널 규칙 레지스트리.

DEFAULT_RULES : 엔진이 기본으로 사용하는 규칙 전체 목록.

규칙 추가 방법:
  1. market_rules.py 또는 symbol_rules.py에 KeywordSignalRule 인스턴스 추가
  2. 이 파일의 DEFAULT_RULES 리스트에 추가

규칙 비활성화:
  - 해당 규칙의 enabled=False 설정 (삭제 없이 비활성화)
  - 또는 DEFAULT_RULES에서 제거
"""

from app.signals.rules import market_rules, symbol_rules
from app.signals.rules.base import SignalRule

DEFAULT_RULES: list[SignalRule] = [
    # ── 거시경제 / 시장 전체 ──────────────────────────────────────
    market_rules.FED_RATE_CUT,
    market_rules.FED_RATE_HIKE,
    market_rules.FED_HOLD_UNCERTAIN,
    market_rules.INFLATION_HOT,
    market_rules.INFLATION_COOL,
    market_rules.RECESSION_RISK,
    market_rules.RATE_CYCLE_PIVOT,
    market_rules.OIL_SURGE,
    market_rules.OIL_DROP,
    market_rules.DOLLAR_STRONG,
    market_rules.MARKET_RALLY,
    market_rules.MARKET_CRASH,
    market_rules.VIX_SPIKE,
    # ── 종목 / 기업 ───────────────────────────────────────────────
    symbol_rules.EARNINGS_BEAT,
    symbol_rules.EARNINGS_MISS,
    symbol_rules.GUIDANCE_RAISE,
    symbol_rules.GUIDANCE_CUT,
    symbol_rules.REGULATORY_RISK,
    symbol_rules.CAPEX_EXPANSION,
    symbol_rules.ANALYST_UPGRADE,
    symbol_rules.ANALYST_DOWNGRADE,
    symbol_rules.MA_DEAL,
    symbol_rules.CONTRACT_WIN,
    symbol_rules.DIVIDEND_INCREASE,
    symbol_rules.PARTNERSHIP_STRATEGIC,
]
