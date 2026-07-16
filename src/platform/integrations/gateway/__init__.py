"""Module 7 — Enterprise API Gateway.

A REST framework layered on the Module 10 API contracts: declarative routing,
HTTP methods, version negotiation, authentication/scope hooks, rate limiting and
standardized response/error envelopes. No existing business endpoint is
rewritten — handlers are plain callables bound to declarative routes.
"""

from __future__ import annotations

from src.platform.integrations.gateway.auth import (
    ApiPrincipal,
    AuthenticationHook,
    RateLimitHook,
    StaticApiKeyAuthHook,
)
from src.platform.integrations.gateway.gateway import ApiGateway, ApiRequest
from src.platform.integrations.gateway.routing import (
    ApiRoute,
    HttpMethod,
    RegisteredRoute,
    RouteHandler,
    Router,
)

__all__ = [
    "HttpMethod",
    "ApiRoute",
    "Router",
    "RegisteredRoute",
    "RouteHandler",
    "ApiPrincipal",
    "AuthenticationHook",
    "StaticApiKeyAuthHook",
    "RateLimitHook",
    "ApiGateway",
    "ApiRequest",
]
