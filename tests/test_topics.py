from unittest.mock import AsyncMock, patch

import pytest

from gen3discoveryai import config
from gen3discoveryai.factory import Factory
from gen3discoveryai.main import lifespan


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/topics", "/topics/"])
@patch("gen3discoveryai.routes.authorize_request")
async def test_topics_list_all(_, endpoint, client):
    """
    Test listing all topics.
    """
    async with lifespan(client.app, force_reload_config=True):
        response = client.get(endpoint)
        assert response.status_code == 200
        topics = response.json().get("topics")
        assert topics is not None

        expected_topics = [
            "default",
            "bdc",
            "usedefault",
            "ollama"
            # add new ones here
        ]

        for expected_topic in expected_topics:
            assert expected_topic in topics

        assert len(topics) == len(expected_topics)

        # the actual content here is checked in other tests
        assert topics["default"].get("topic_chain") is not None
        assert topics["default"].get("description") is not None
        assert topics["default"].get("system_prompt") is not None
        assert topics["default"].get("metadata") is not None

        assert topics["bdc"].get("topic_chain") is not None
        assert topics["bdc"].get("description") is not None
        assert topics["bdc"].get("system_prompt") is not None
        assert topics["bdc"].get("metadata") is not None

        assert topics["usedefault"].get("topic_chain") is not None
        assert topics["usedefault"].get("description") is not None
        assert topics["usedefault"].get("system_prompt") is not None
        assert topics["usedefault"].get("metadata") is not None

        assert topics["ollama"].get("topic_chain") is not None
        assert topics["ollama"].get("description") is not None
        assert topics["ollama"].get("system_prompt") is not None
        assert topics["ollama"].get("metadata") is not None


@pytest.mark.parametrize("endpoint", ["/topics", "/topics/"])
def test_topics_no_token(endpoint, client):
    """
    Test accessing topics without a token.
    """
    response = client.get(endpoint)
    assert response.status_code == 401
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/topics", "/topics/"])
@patch("gen3discoveryai.auth.arborist", new_callable=AsyncMock)
def test_topics_unauthorized(arborist, endpoint, client):
    """
    Test unauthorized access to topics.
    """
    # Simulate an unauthorized request
    arborist.auth_request.return_value = False

    headers = {"Authorization": "Bearer ofbadnews"}
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 403
    assert response.json().get("detail")


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/topics/bdc", "/topics/bdc/"])
@patch("gen3discoveryai.routes.authorize_request")
async def test_topics_specific_topic_with_configured_overrides(_, endpoint, client):
    """
    Test accessing a specific topic that has been configured with overrides to default configuration
    """
    async with lifespan(client.app, force_reload_config=True):
        response = client.get(endpoint)
        assert response.status_code == 200
        topic_data = response.json().get("topics", {}).get("bdc")
        assert topic_data

        # since we specify an override in the config, this should NOT be the default
        assert topic_data["topic_chain"] != config.DEFAULT_CHAIN_NAME

        assert (
            topic_data["description"]
            == "Ask about available datasets, powered by public dataset metadata like study descriptions"
        )
        assert (
            topic_data["system_prompt"]
            == "You answer questions about datasets that are available in BioData Catalyst. You'll be given relevant "
            "dataset descriptions for every dataset that's been ingested into BioData Catalyst. You are acting as a "
            "search assistant for a biomedical researcher (who will be asking you questions). The researcher is likely "
            "trying to find datasets of interest for a particular research question. You should recommend datasets that "
            "may be of interest to that researcher."
        )

        # this is parsed from the string in the config
        assert topic_data["metadata"] == {
            "model_name": "gpt-3.5-turbo",
            "max_output_tokens": "512",
            "model_temperature": "0.45",
            "num_similar_docs_to_find": "5",
            "similarity_score_threshold": "0.75",
        }


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/topics/usedefault", "/topics/usedefault/"])
@patch("gen3discoveryai.routes.authorize_request")
async def test_topics_specific_topic_with_defaults(_, endpoint, client):
    """
    Test accessing a specific topic that has NOT been configured with overrides. So default configuration should exist
    """
    async with lifespan(client.app, force_reload_config=True):
        response = client.get(endpoint)
        assert response.status_code == 200
        topic_data = response.json().get("topics", {}).get("usedefault")
        assert topic_data

        assert topic_data["topic_chain"] == config.DEFAULT_CHAIN_NAME
        assert topic_data["description"] == config.DEFAULT_DESCRIPTION
        assert topic_data["system_prompt"] == config.DEFAULT_SYSTEM_PROMPT
        assert topic_data["metadata"] == config.DEFAULT_METADATA


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint", ["/topics/non_existent_topic", "/topics/non_existent_topic/"]
)
@patch("gen3discoveryai.routes.authorize_request")
async def test_topics_specific_topic_doesnt_exist(_, endpoint, client):
    """
    Test accessing a non-existent topic.
    """
    async with lifespan(client.app, force_reload_config=True):
        response = client.get(endpoint)
        assert response.status_code == 404
        assert response.json().get("detail")


def test_topic_chain_factory():
    """
    Test that factory class can register classes and retrieve them
    """

    class TestClassA:
        """
        Test class
        """

        def __init__(self, some_arg):
            self.some_arg = some_arg

    factory = Factory()
    factory.register("TestClassA", TestClassA)

    test_class = factory.get("TestClassA", some_arg="foobar")

    assert isinstance(test_class, TestClassA)
    assert test_class.some_arg == "foobar"


def test_topic_chain_factory_doesnt_exist():
    """
    Test that factory class can register classes and retrieve them
    """

    class TestClassA:
        """
        Test class
        """

        def __init__(self, some_arg):
            self.some_arg = some_arg

    factory = Factory()
    factory.register("TestClassA", TestClassA)

    with pytest.raises(ValueError):
        factory.get("DOESNTEXIST", some_arg="foobar")
