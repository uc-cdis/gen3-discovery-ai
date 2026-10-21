import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from jwt.algorithms import RSAAlgorithm
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

from gen3discoveryai import auth, config
from gen3discoveryai.auth import _get_token, get_user_id

KEY_ID = "test-key"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
# Not served by the issuer, so a token it signs fails signature verification.
UNKNOWN_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


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
    """
    Test that DEBUG_SKIP_AUTH configuration allows access to endpoints without auth
    """
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


@pytest.mark.asyncio
async def test_authorize_request_arborist_failure_500() -> None:
    """
    Test that a failed call to arborist gives a 500 error.
    """
    arborist_error = ConnectionError("arborist is unreachable")
    token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="some-token")

    with (
        # The user_id lookup is only for the debug log
        patch.object(auth, "get_user_id", new_callable=AsyncMock, return_value="42"),
        patch.object(
            auth.arborist,
            "auth_request",
            new_callable=AsyncMock,
            side_effect=arborist_error,
        ) as auth_request,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await auth.authorize_request(token=token)

    auth_request.assert_awaited_once()
    assert exc_info.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    # `raise ... from exc` keeps the original failure available for debugging.
    assert exc_info.value.__cause__ is arborist_error


@pytest.fixture(scope="module")
def issuer() -> Iterator[str]:
    """
    Serve OIDC discovery and a JWKS for SIGNING_KEY from a local issuer.

    Bound to a free port, so each run gets an issuer URL nothing else has used. authutils caches
    public keys per issuer for the life of the process, and a fresh URL keeps that cache from
    carrying over between runs in the same worker.

    Yields:
        str: The issuer URL, as it appears in a token's `iss` claim.
    """
    jwk = json.loads(RSAAlgorithm.to_jwk(SIGNING_KEY.public_key()))
    jwk.update(kid=KEY_ID, alg="RS256", use="sig")
    server = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    issuer_url = f"http://127.0.0.1:{server.server_port}/user"

    class IssuerHandler(BaseHTTPRequestHandler):
        """Answers the two requests authutils makes to find an issuer's keys."""

        def do_GET(
            self,
        ) -> None:  # noqa: N802 # pylint: disable=invalid-name
            """
            Return the discovery document or the key set, depending on the path.

            The name is fixed by BaseHTTPRequestHandler, which dispatches GET requests to `do_GET`.
            """
            if self.path.endswith("/.well-known/openid-configuration"):
                body = {"issuer": issuer_url, "jwks_uri": f"{issuer_url}/jwt/keys"}
            else:
                body = {"keys": [jwk]}
            payload = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(
            self, format: str, *args: Any
        ) -> None:  # noqa: A002 - overridden signature
            """Keep request lines out of the test output."""

    server.RequestHandlerClass = IssuerHandler
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield issuer_url
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def enforce_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every test validate its token, whatever the environment sets."""
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
    monkeypatch.setattr(config, "ALLOW_ANONYMOUS_ACCESS", False)


@pytest.fixture
def request_context() -> Request:
    """
    A bare request, with no Authorization header.

    get_user_id only checks the audience when it is given a request, so tests that exercise
    audience validation need one. The token is passed in directly, so the request is never read.
    """
    return Request({"type": "http", "headers": []})


def make_token(
    issuer: str, key: rsa.RSAPrivateKey = SIGNING_KEY, **claims: Any
) -> HTTPAuthorizationCredentials:
    """
    Build a bearer token shaped like a Gen3 access token.

    Args:
        issuer (str): Value for the `iss` claim.
        key (rsa.RSAPrivateKey): Key to sign with.
        **claims (Any): Claims to add or override.

    Returns:
        HTTPAuthorizationCredentials: The token as FastAPI's bearer dependency would hand it over.
    """
    now = int(time.time())
    payload = {
        "iss": issuer,
        "sub": "42",
        "aud": ["gen3"],
        "scope": ["user", "openid"],
        "pur": "access",
        "iat": now,
        "exp": now + 300,
        "jti": "test-jti",
        "context": {"user": {"name": "test-user"}},
    }
    payload.update(claims)
    encoded = jwt.encode(payload, key, algorithm="RS256", headers={"kid": KEY_ID})
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=encoded)


@pytest.mark.asyncio
async def test_valid_token_yields_user_id(
    issuer: str, request_context: Request
) -> None:
    """A valid access token resolves to its `sub` claim."""
    assert await auth.get_user_id(make_token(issuer), request_context) == "42"


@pytest.mark.parametrize(
    ("case", "overrides"),
    [
        ("wrong purpose", {"pur": "refresh"}),
        ("missing scope", {"scope": ["user"]}),
        ("wrong audience", {"aud": ["not-gen3"]}),
        ("expired", {"iat": int(time.time()) - 600, "exp": int(time.time()) - 300}),
        ("unknown signing key", {"key": UNKNOWN_KEY}),
    ],
)
@pytest.mark.asyncio
async def test_invalid_token_is_rejected(
    issuer: str, request_context: Request, case: str, overrides: dict[str, Any]
) -> None:
    """A token failing any one validation check is answered with a 401."""
    token = make_token(issuer, **overrides)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_user_id(token, request_context)

    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED, case


@pytest.mark.asyncio
async def test_token_is_rejected_without_request(issuer: str) -> None:
    """
    Current behavior: with no request the expected audience is None, and PyJWT rejects any
    token that carries an `aud` claim when it is not given an audience to check against.

    Every real Gen3 access token has an `aud` claim, so get_user_id can only validate a token
    when it is also handed the request. This pins existing behavior rather than a requirement;
    delete or flip it if get_user_id is changed to fall back to the `gen3` audience.
    """
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_user_id(make_token(issuer))

    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_token_without_sub_is_rejected() -> None:
    """Claims that validate but carry no `sub` can't identify a user, so they are a 401."""
    with patch.object(auth, "_get_token_claims", new_callable=AsyncMock) as get_claims:
        get_claims.return_value = {"scope": ["user", "openid"]}

        with pytest.raises(HTTPException) as exc_info:
            await auth.get_user_id(make_token("unused"))

    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_missing_token_is_rejected() -> None:
    """With no token and no request to read one from, the caller is unauthenticated."""
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_user_id()

    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_debug_skip_auth_without_token_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With DEBUG_SKIP_AUTH on and no token, validation is skipped and no user id is returned."""
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)

    assert await auth.get_user_id() is None


@pytest.mark.asyncio
async def test_debug_skip_auth_still_validates_a_provided_token(
    issuer: str, request_context: Request, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DEBUG_SKIP_AUTH only applies when no token is given; a bad token is still rejected."""
    monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)
    token = make_token(issuer, key=UNKNOWN_KEY)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_user_id(token, request_context)

    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
