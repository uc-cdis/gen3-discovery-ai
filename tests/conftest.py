import importlib
import os

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    from gen3discoveryai import config
    from gen3discoveryai.main import get_app

    # change dir to the tests, so it loads the test .env
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    importlib.reload(config)

    with TestClient(get_app()) as client:
        yield client
