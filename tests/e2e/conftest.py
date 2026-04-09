import pytest, os
from app.engines.manager import EngineManager
from app.engines.scrapling_engine import ScraplingEngine
from app.engines.opencli import OpenCLIEngine
from app.engines.bb_browser import BBBrowserEngine
from app.engines.clibrowser import CLIBrowserEngine

def pytest_collection_modifyitems(config, items):
    if not os.getenv("RUN_INTEGRATION"):
        skip = pytest.mark.skip(reason="需要设置 RUN_INTEGRATION=1")
        for item in items:
            if "integration" in str(item.fspath) or "e2e" in str(item.fspath):
                item.add_marker(skip)

@pytest.fixture
def engine_manager():
    em = EngineManager()
    em.register(ScraplingEngine())
    em.register(OpenCLIEngine())
    em.register(BBBrowserEngine())
    em.register(CLIBrowserEngine())
    return em
