import importlib
import os

import pytest
from starlette.testclient import TestClient
from unittest.mock import patch

from gen3discoveryai import config
from gen3discoveryai.main import get_app


@pytest.fixture(scope="session")
def mock_google_ai():
    """
    Mock the Google Topic Chain AI and Embeddings
    """
    mocked_embeddings = patch(
        "gen3discoveryai.topic_chains.question_answer_google.VertexAIEmbeddings"
    ).start()
    mocked_vertex_ai = patch(
        "gen3discoveryai.topic_chains.question_answer_google.ChatVertexAI"
    ).start()
    mocked_retrieval = patch(
        "gen3discoveryai.topic_chains.question_answer_google.RetrievalQA"
    ).start()

    yield {
        "gen3discoveryai.topic_chains.question_answer_google.VertexAIEmbeddings": mocked_embeddings,
        "gen3discoveryai.topic_chains.question_answer_google.ChatVertexAI": mocked_vertex_ai,
        "gen3discoveryai.topic_chains.question_answer_google.RetrievalQA": mocked_retrieval,
    }

    mocked_embeddings.stop()
    mocked_vertex_ai.stop()
    mocked_retrieval.stop()


@pytest.fixture(scope="session")
def client():
    """
    Set up and yield a test client to send HTTP requests.
    """
    # change dir to the tests, so it loads the test .env
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    importlib.reload(config)

    with TestClient(get_app()) as test_client:
        yield test_client
