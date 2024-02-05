import importlib
import os
from unittest.mock import patch

import pytest

from gen3discoveryai.main import _override_generated_openapi_spec, lifespan
from gen3discoveryai.topic_chains.utils import get_from_cfg_metadata


def test_bad_config_metadata():
    """
    Test when invalid config is provided, an exception is raised
    """
    # change dir to the tests, so it loads the test .env
    os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/badcfg")

    with pytest.raises(Exception):
        from gen3discoveryai import config

        importlib.reload(config)

    os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/..")


@pytest.mark.asyncio
@patch("gen3discoveryai.main._create_and_register_topic_chain")
async def test_bad_config_default_topic(create_and_register_topic_chain, client):
    """
    Test when config loading raises an error, it's reraised if it's the default topic
    """
    create_and_register_topic_chain.side_effect = Exception("some exception")

    with pytest.raises(Exception):
        async with lifespan(client.app, force_reload_config=True):
            pass


@pytest.mark.asyncio
@patch("gen3discoveryai.main._create_and_register_topic_chain")
async def test_bad_config_non_default_topic(create_and_register_topic_chain, client):
    """
    Test when config loading raises an error, it's NOT reraised if it's not the default topic
    """

    def _exception_if_default(*args, **kwargs):
        # simulate default topic being okay, e.g. don't raise error here
        if kwargs.get("topic") == "default":
            pass

    create_and_register_topic_chain.side_effect = _exception_if_default

    async with lifespan(client.app):
        # we don't expect an exception for non default topics
        assert True


def test_metadata_cfg_util():
    """
    If it exists, return it
    """
    set_metadata_value = "foobar"
    metadata = {"model_name": set_metadata_value}
    retrieved_metadata_value = get_from_cfg_metadata(
        "model_name", metadata, default="chat-bison", type_=str
    )

    assert retrieved_metadata_value == set_metadata_value


def test_metadata_cfg_util_doesnt_exist():
    """
    If it doesn't exist, return default
    """
    default = "chat-bison"
    retrieved_metadata_value = get_from_cfg_metadata(
        "this_doesnt_exist", {"model_name": "foobar"}, default=default, type_=str
    )
    assert retrieved_metadata_value == default


def test_metadata_cfg_util_cant_cast():
    """
    If it doesn't exist, return default
    """
    default = "chat-bison"
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
    current_dir = os.path.dirname(os.path.abspath(__file__)).rstrip("/")
    os.chdir(current_dir + "/..")

    json_data = _override_generated_openapi_spec()
    assert json_data

    # change dir so the openapi.yaml CANNOT be found
    os.chdir("./tests")

    json_data = _override_generated_openapi_spec()
    assert not json_data
