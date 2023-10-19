from unittest.mock import AsyncMock, patch

import pytest

from gen3discoveryai import config
from gen3discoveryai.auth import _get_token


@pytest.mark.parametrize(
    "endpoint",
    [
        "/topics",
        "/topics/",
        "/topics/bdc",
        "/topics/bdc/",
        "/topics/default",
        "/topics/default/",
        "/_version",
        "/_version/",
        "/_status",
        "/_status/",
    ],
)
def test_debug_skip_auth_gets(monkeypatch, client, endpoint):
    previous_config = config.DEBUG_SKIP_AUTH

    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    response = client.get(endpoint)

    assert response.status_code == 200

    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)


@pytest.mark.asyncio
@pytest.mark.parametrize("token_param", [None, "something"])
@pytest.mark.parametrize("request_param", [None, "something"])
@patch("gen3discoveryai.auth.get_bearer_token", new_callable=AsyncMock)
async def test_get_token(get_bearer_token, request_param, token_param):
    """
    Test helper function returns proper token
    """
    get_bearer_token.return_value = "parsed token from request"

    output = await _get_token(token_param, request_param)

    if token_param:
        assert output == token_param
    else:
        if request_param:
            assert output == "parsed token from request"
        else:
            assert output == token_param
