import importlib
import os

import pytest

from gen3discoveryai import config
from gen3discoveryai.main import _override_generated_openapi_spec
from gen3discoveryai.topic_chains.utils import get_from_cfg_metadata


def test_bad_config_metadata():
    """
    Test when invalid config is provided, an exception is raised
    """
    # change dir to the tests, so it loads the test .env
    os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/badcfg")

    with pytest.raises(Exception):
        importlib.reload(config)

    os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/..")


def test_metadata_cfg_util():
    """
    If it exists, return it
    """
    set_metadata_value = "foobar"
    metadata = {"model_name": set_metadata_value}
    retrieved_metadata_value = get_from_cfg_metadata(
        "model_name", metadata, default="gpt-3.5-turbo", type_=str
    )

    assert retrieved_metadata_value == set_metadata_value


def test_metadata_cfg_util_doesnt_exist():
    """
    If it doesn't exist, return default
    """
    default = "gpt-3.5-turbo"
    retrieved_metadata_value = get_from_cfg_metadata(
        "this_doesnt_exist", {"model_name": "foobar"}, default=default, type_=str
    )
    assert retrieved_metadata_value == default


def test_metadata_cfg_util_cant_cast():
    """
    If it doesn't exist, return default
    """
    default = "gpt-3.5-turbo"
    retrieved_metadata_value = get_from_cfg_metadata(
        "this_doesnt_exist", {"model_name": "foobar"}, default=default, type_=float
    )
    assert retrieved_metadata_value == default


@pytest.mark.parametrize("endpoint", ["/docs", "/redoc"])
def test_docs(endpoint, client):
    """
    Test FastAPI docs endpoints
    """
    assert client.get(endpoint).status_code == 200


def test_openapi():
    """
    Test our override of FastAPI's default openAPI
    """
    # change dir so the openapi.yaml is available
    os.chdir("..")

    json_data = _override_generated_openapi_spec()
    assert json_data

    # change dir so the openapi.yaml CANNOT be found
    os.chdir("./tests")

    json_data = _override_generated_openapi_spec()
    assert not json_data
