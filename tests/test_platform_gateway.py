"""Module 7 tests — Enterprise API Gateway.

Exercises routing/resolution, version negotiation, the authentication and scope
pipeline, rate limiting and the standard response/error envelopes — without
rewriting any existing business endpoint.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.integrations.gateway import (
    ApiGateway,
    ApiPrincipal,
    ApiRequest,
    ApiRoute,
    HttpMethod,
    Router,
    StaticApiKeyAuthHook,
)


def _gateway_with_route(**gw_kwargs) -> ApiGateway:
    router = Router()
    router.add(
        ApiRoute(
            method=HttpMethod.GET,
            path="/integrations/{id}",
            name="get_integration",
            scopes=["integrations:read"],
        ),
        handler=lambda ctx: {"id": ctx["params"]["id"]},
    )
    router.add(
        ApiRoute(
            method=HttpMethod.GET,
            path="/health",
            name="health",
            auth_required=False,
        ),
        handler=lambda ctx: {"status": "ok"},
    )
    return ApiGateway(router=router, **gw_kwargs)


def _authed_gateway() -> ApiGateway:
    auth = StaticApiKeyAuthHook()
    auth.register_key(
        "key-1",
        ApiPrincipal(principal_id="u1", tenant_id="t1", scopes=["integrations:read"]),
    )
    return _gateway_with_route(auth_hook=auth, clock=FrozenClock())


# -- routing ----------------------------------------------------------------


def test_route_matches_and_captures_params():
    route = ApiRoute(method=HttpMethod.GET, path="/integrations/{id}", name="r")
    assert route.matches("/integrations/abc") == {"id": "abc"}
    assert route.matches("/other") is None
    assert route.path_params() == ["id"]


def test_router_resolves_by_method_and_path():
    gw = _authed_gateway()
    resolved = gw.router.resolve(HttpMethod.GET, "/integrations/xyz")
    assert resolved is not None
    registered, params = resolved
    assert registered.route.name == "get_integration"
    assert params == {"id": "xyz"}


# -- pipeline ---------------------------------------------------------------


def test_authenticated_scoped_request_succeeds():
    gw = _authed_gateway()
    resp = gw.handle(
        ApiRequest(
            method=HttpMethod.GET,
            path="/integrations/i1",
            headers={"X-Api-Key": "key-1"},
        )
    )
    assert resp.success
    assert resp.data == {"id": "i1"}
    assert gw.http_status(resp) == 200
    assert resp.meta.api_version == "v1"


def test_missing_credentials_returns_401():
    gw = _authed_gateway()
    resp = gw.handle(ApiRequest(method=HttpMethod.GET, path="/integrations/i1"))
    assert not resp.success
    assert resp.error.code == "authentication_failed"
    assert gw.http_status(resp) == 401


def test_missing_scope_returns_403():
    auth = StaticApiKeyAuthHook()
    auth.register_key(
        "key-2", ApiPrincipal(principal_id="u2", tenant_id="t1", scopes=["other:read"])
    )
    gw = _gateway_with_route(auth_hook=auth, clock=FrozenClock())
    resp = gw.handle(
        ApiRequest(
            method=HttpMethod.GET,
            path="/integrations/i1",
            headers={"X-Api-Key": "key-2"},
        )
    )
    assert not resp.success
    assert resp.error.code == "permission_denied"
    assert gw.http_status(resp) == 403


def test_unauthenticated_public_route_allowed():
    gw = _authed_gateway()
    resp = gw.handle(ApiRequest(method=HttpMethod.GET, path="/health"))
    assert resp.success and resp.data == {"status": "ok"}


def test_unknown_route_returns_404():
    gw = _authed_gateway()
    resp = gw.handle(ApiRequest(method=HttpMethod.GET, path="/nope"))
    assert not resp.success and resp.error.code == "not_found"


def test_rate_limit_exceeded_returns_429():
    from src.platform.api.ratelimit import TokenBucketRateLimiter

    clock = FrozenClock()
    limiter = TokenBucketRateLimiter(requests_per_minute=1, clock=clock)
    auth = StaticApiKeyAuthHook()
    auth.register_key(
        "key-3", ApiPrincipal(principal_id="u3", tenant_id="t1", scopes=["integrations:read"])
    )
    gw = _gateway_with_route(auth_hook=auth, rate_limiter=limiter, clock=clock)
    req = ApiRequest(
        method=HttpMethod.GET, path="/integrations/i1", headers={"X-Api-Key": "key-3"}
    )
    assert gw.handle(req).success  # first consumes the only token
    second = gw.handle(req)
    assert not second.success and second.error.code == "quota_exceeded"
    assert gw.http_status(second) == 429
