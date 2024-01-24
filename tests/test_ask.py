from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

import langchain.schema
import pytest
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_429_TOO_MANY_REQUESTS, HTTP_503_SERVICE_UNAVAILABLE

from gen3discoveryai import config
from gen3discoveryai.routes import (
    raise_if_global_ai_limit_exceeded,
    raise_if_user_exceeded_limits,
)

get_bearer_token = HTTPBearer(auto_error=False)


@pytest.mark.parametrize("skip_auth", [True, False])
@pytest.mark.parametrize("conversation_id", [None, "", "foobar"])
@pytest.mark.parametrize("topic", [None, "default", "bdc"])
@pytest.mark.parametrize("endpoint", ["/ask", "/ask/"])
@pytest.mark.parametrize(
    "user_query",
    [
        "do you have covid 19 data?",
        "HELLO",
        "!@#$%^&*()-(){}]][[^",
        "exec(sys.exit(1))",
        "",
        None,
    ],
)
@patch("gen3discoveryai.routes.config")
@patch("gen3discoveryai.auth.access_token")
@patch("gen3discoveryai.auth._get_token")
@patch("gen3discoveryai.auth.arborist", new_callable=AsyncMock)
def test_ask(
    arborist,
    get_token,
    access_token,
    mock_config,
    user_query,
    endpoint,
    topic,
    conversation_id,
    skip_auth,
    client,
    monkeypatch,
    mock_google_ai,
):
    """
    Test the ask endpoint given variable valid input from the user.
    """
    # setup
    if skip_auth:
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    headers = {"Authorization": "Bearer a.valid.token"}
    arborist.auth_request.return_value = True
    get_token.return_value = HTTPAuthorizationCredentials(
        scheme="bearer", credentials="valid creds"
    )
    access_token.return_value = AsyncMock(return_value={"sub": 0})

    topic_chain_response = "yes"

    test_a = langchain.schema.Document(
        page_content="fooA", metadata={"row": 120, "source": "phs000001.v1.p1.c1"}
    )
    test_b = langchain.schema.Document(
        page_content="barB", metadata={"row": 59, "source": "phs000002.v2.p2.c2"}
    )

    source_documents = [
        test_a,
        test_b,
    ]

    mock_topic_chain = MagicMock()
    mock_topic_chain.run.return_value = {
        "result": topic_chain_response,
        "source_documents": source_documents,
    }
    mock_config.topics = MagicMock()
    mock_config.topics.get.return_value = {"topic_chain": mock_topic_chain}
    mock_config.topics.__getitem__.return_value = {"topic_chain": mock_topic_chain}

    endpoint_string = f"{endpoint}"
    query_params = {}
    if topic:
        query_params["topic"] = topic
    if conversation_id is not None:
        query_params["conversation_id"] = conversation_id

    # call endpoint
    body = {"query": user_query}
    endpoint_string = f"{endpoint_string}?{urlencode(query_params)}"

    response = client.post(
        endpoint_string,
        headers=headers,
        json=body,
    )

    # make assertions about endpoint response
    if user_query:
        assert response.status_code == 200

        assert mock_topic_chain.run.called
        assert "query" in mock_topic_chain.run.call_args.kwargs
        assert mock_topic_chain.run.call_args.kwargs["query"] == user_query

        assert "response" in response.json()
        assert "documents" in response.json()

        assert response.json()["response"] == topic_chain_response
        assert response.json()["documents"]

        for doc in response.json()["documents"]:
            assert doc.get("page_content") in ["fooA", "barB"]
            assert doc.get("metadata", {}).get("row") in [120, 59]
            assert doc.get("metadata", {}).get("source") in [
                "phs000001.v1.p1.c1",
                "phs000002.v2.p2.c2",
            ]
    else:
        # if no user query, except an error
        assert response.status_code == 400
        assert not mock_topic_chain.run.called
        assert response.json().get("detail")
        assert "response" not in response.json()
        assert "documents" not in response.json()

    # cleanup

    if skip_auth:
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)


@pytest.mark.parametrize("get_token_returns_none", [True, False])
@pytest.mark.parametrize("access_token_raises_error", [True, False])
@pytest.mark.parametrize("topic", [None, "default", "bdc"])
@pytest.mark.parametrize("endpoint", ["/ask", "/ask/"])
@pytest.mark.parametrize(
    "user_query",
    [
        "do you have covid 19 data?",
    ],
)
@patch("gen3discoveryai.auth.access_token")
@patch("gen3discoveryai.auth._get_token")
@patch("gen3discoveryai.auth.arborist", new_callable=AsyncMock)
def test_ask_invalid_token(
    arborist,
    get_token,
    access_token,
    user_query,
    endpoint,
    topic,
    access_token_raises_error,
    get_token_returns_none,
    client,
    mock_google_ai,
):
    """
    Test the ask endpoint when provided an invalid token.
    """
    # setup
    headers = {"Authorization": "Bearer a.valid.token"}
    arborist.auth_request.return_value = True

    if get_token_returns_none:
        get_token.return_value = None
    else:
        get_token.return_value = HTTPAuthorizationCredentials(
            scheme="bearer", credentials="valid creds"
        )

    if access_token_raises_error:
        access_token.side_effect = Exception()
    else:
        access_token.return_value = AsyncMock(return_value={"NOSUB": 0})

    endpoint_string = f"{endpoint}"

    if topic:
        endpoint_string = f"{endpoint_string}?topic={topic}"

    # call endpoint
    response = client.post(
        endpoint_string,
        headers=headers,
        json={"query": user_query},
    )

    # if no user query, except an error
    assert response.status_code == 401
    assert response.json().get("detail")
    assert "response" not in response.json()
    assert "documents" not in response.json()


@pytest.mark.parametrize("endpoint", ["/ask", "/ask/"])
@pytest.mark.parametrize("topic", ["invalid", "!@(#*&$^&", "sys.exit(1)"])
def test_ask_invalid_topic(topic, endpoint, client, monkeypatch, mock_google_ai):
    """
    Test ask with invalid topics and ensure error
    """
    previous_config = config.DEBUG_SKIP_AUTH
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    # call endpoint
    endpoint_string = f"{endpoint}"
    query_params = {}
    if topic:
        query_params["topic"] = topic

    body = {"query": "how do I make a pumpkin pie?"}
    endpoint_string = f"{endpoint_string}?{urlencode(query_params)}"

    response = client.post(
        endpoint_string,
        headers={"Authorization": "bearer this.is.valid"},
        json=body,
    )

    assert response.status_code == 404
    assert response.json().get("detail")
    assert "response" not in response.json()
    assert "documents" not in response.json()

    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)


@pytest.mark.parametrize("endpoint", ["/ask", "/ask/"])
@patch("gen3discoveryai.routes.config")
def test_ask_invalid_response_from_chain(
    mock_config, endpoint, client, monkeypatch, mock_google_ai
):
    """
    Test that when the chain returns an error, the ask endpoint returns service unavailable
    """
    previous_config = config.DEBUG_SKIP_AUTH
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    mock_topic_chain = MagicMock()
    mock_topic_chain.run.side_effect = Exception("something bad happened!!")

    mock_config.topics = MagicMock()
    mock_config.topics.get.return_value = {"topic_chain": mock_topic_chain}
    mock_config.topics.__getitem__.return_value = {"topic_chain": mock_topic_chain}

    # call endpoint
    body = {"query": "do you have covid data?"}
    response = client.post(
        f"{endpoint}",
        headers={"Authorization": "bearer this.is.valid"},
        json=body,
    )

    assert response.status_code == 503
    assert response.json().get("detail")
    assert "response" not in response.json()
    assert "documents" not in response.json()

    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)


@pytest.mark.parametrize("endpoint", ["/ask", "/ask/"])
@pytest.mark.parametrize(
    "post_body",
    [
        None,
        {},
        {"not_query": "not a query"},
        {"!@(*#&(%$*&": "!@(*#&$%(^*"},
        {"sys.exit(1)": "sys.exit(1)"},
        {"a": "foo", "b": "bar"},
    ],
)
def test_invalid_post_body(post_body, endpoint, client, monkeypatch, mock_google_ai):
    """
    Test when ask is sent with a body that doesn't appropriately contain
    the `query`, we get an error
    """
    previous_config = config.DEBUG_SKIP_AUTH
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    # call endpoint
    endpoint_string = f"{endpoint}"

    response = client.post(
        endpoint_string,
        headers={"Authorization": "bearer this.is.valid"},
        json=post_body,
    )

    assert response.status_code in [400, 422]
    assert response.json().get("detail")
    assert "response" not in response.json()
    assert "documents" not in response.json()

    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)


@pytest.mark.parametrize("headers", [{}, {"NotAuthorization": "asdfasdf"}])
@pytest.mark.parametrize(
    "endpoint",
    [
        "/ask",
        "/ask/",
        "/ask?topic=default",
        "/ask/?topic=default",
        "/ask?topic=bdc",
        "/ask/?topic=bdc",
    ],
)
def test_ask_no_token(endpoint, headers, client, mock_google_ai):
    """
    Test that the ask endpoint returns a 401 with details when no token is provided
    """
    response = client.post(
        endpoint, headers=headers, json={"query": "do you have covid data?"}
    )
    assert response
    assert response.status_code == 401
    assert response.json().get("detail")


@pytest.mark.parametrize(
    "endpoint",
    [
        "/ask",
        "/ask/",
        "/ask?topic=default",
        "/ask/?topic=default",
        "/ask?topic=bdc",
        "/ask/?topic=bdc",
    ],
)
@patch("gen3discoveryai.auth.access_token")
@patch("gen3discoveryai.auth.get_user_id")
@patch("gen3discoveryai.auth._get_token")
@patch("gen3discoveryai.auth.arborist", new_callable=AsyncMock)
def test_ask_unauthorized(
    arborist, get_token, get_user_id, access_token, endpoint, client, mock_google_ai
):
    """
    Test accessing the endpoint when authorized
    """
    # setup
    arborist.auth_request.return_value = False
    get_token.return_value = HTTPAuthorizationCredentials(
        scheme="bearer", credentials="valid creds"
    )
    get_user_id.return_value = 0
    access_token.return_value = AsyncMock(return_value={"sub": 0})

    # call endpoint
    headers = {"Authorization": "Bearer of.bad.news"}
    response = client.post(
        endpoint, json={"query": "do you have covid data?"}, headers=headers
    )

    # assertions
    assert response.status_code == 403
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/ask", "/ask/"])
def test_ask_too_many_requests(endpoint, client, monkeypatch, mock_google_ai):
    """
    Tests the ask endpoint when a user exceeds request limits, expecting a 429 response.
    """
    previous_config = config.DEBUG_SKIP_AUTH
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    async def _override_raise_if_user_exceeded_limits():
        raise HTTPException(status_code=HTTP_429_TOO_MANY_REQUESTS)

    # ensure overriding for Depends() on routes
    client.app.dependency_overrides[
        raise_if_user_exceeded_limits
    ] = _override_raise_if_user_exceeded_limits

    # call endpoint
    endpoint_string = f"{endpoint}"

    response = client.post(
        endpoint_string,
        headers={"Authorization": "bearer this.is.valid"},
        json={"query": "something"},
    )

    assert response.status_code == 429
    assert response.json().get("detail")
    assert "response" not in response.json()
    assert "documents" not in response.json()

    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    # this reverts the override
    client.app.dependency_overrides = {}


@pytest.mark.parametrize("endpoint", ["/ask", "/ask/"])
def test_ask_service_unavailable_due_to_global_limit(
    endpoint, client, monkeypatch, mock_google_ai
):
    """
    Tests the ask endpoint when a global limit has been exceeded, expecting a 503 response.
    """
    previous_config = config.DEBUG_SKIP_AUTH
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    async def _override_raise_if_global_ai_limit_exceeded():
        raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE)

    # ensure overriding for Depends() on routes
    client.app.dependency_overrides[
        raise_if_global_ai_limit_exceeded
    ] = _override_raise_if_global_ai_limit_exceeded

    # call endpoint
    endpoint_string = f"{endpoint}"

    response = client.post(
        endpoint_string,
        headers={"Authorization": "bearer this.is.valid"},
        json={"query": "something"},
    )

    assert response.status_code == 503
    assert response.json().get("detail")
    assert "response" not in response.json()
    assert "documents" not in response.json()

    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    # this reverts the override
    client.app.dependency_overrides = {}
