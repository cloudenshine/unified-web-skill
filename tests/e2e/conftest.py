import pytest
from app.engines.manager import EngineManager
from app.engines.scrapling_engine import ScraplingEngine
from app.engines.opencli import OpenCLIEngine
from app.engines.bb_browser import BBBrowserEngine
from app.engines.clibrowser import CLIBrowserEngine


@pytest.fixture
def engine_manager():
    em = EngineManager()
    em.register(ScraplingEngine())
    em.register(OpenCLIEngine())
    em.register(BBBrowserEngine())
    em.register(CLIBrowserEngine())
    return em
