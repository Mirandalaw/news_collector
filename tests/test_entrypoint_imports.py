"""cron 진입점이 import 단계에서 죽지 않는지 확인한다.

2026-04 시세 조회(FinanceDataReader)를 브리핑에 넣으면서 requirements.txt 에 빠뜨려
Docker 이미지에서 run_briefing / run_all 이 ModuleNotFoundError 로 매번 실패했다.
진입점이 쓰는 모듈을 전부 import 해 보면 같은 누락을 CI 에서 잡는다.
"""
import importlib

import pytest

MODULES = [
    "app.jobs.briefing_job",
    "app.services.briefing_dispatcher",
    "app.services.morning_briefing_service",
    "app.signals.price_data_provider",
    "app.signals.price_history_provider",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)
