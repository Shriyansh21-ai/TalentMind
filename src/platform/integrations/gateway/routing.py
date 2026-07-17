"""API routing primitives (Module 7).

A lightweight REST routing layer: HTTP methods, declarative route/endpoint
descriptors and a :class:`Router` that resolves an incoming
``(method, path, version)`` to a registered :class:`ApiRoute`. This is the
framework the future public API is expressed in — it does **not** rewrite any
existing business endpoint; handlers are plain callables the platform binds
later.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.integrations.common.errors import ProviderConfigurationError

#: A route handler receives a request context dict and returns any JSON-safe value.
RouteHandler = Callable[[dict], object]

_PARAM = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class HttpMethod(str, Enum):
    """Supported HTTP verbs."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ApiRoute(PlatformModel):
    """A declarative description of a single API endpoint.

    Attributes:
        method: The HTTP verb.
        path: A version-relative path template, e.g. ``/integrations/{id}``.
        name: Stable operation id (used in OpenAPI / docs).
        summary: Human summary.
        auth_required: Whether an authenticated principal is required.
        scopes: Permission scopes the caller must hold.
        paginated: Whether the endpoint returns a paginated collection.
    """

    method: HttpMethod
    path: str
    name: str
    summary: str = ""
    auth_required: bool = True
    scopes: list[str] = Field(default_factory=list)
    paginated: bool = False
    tags: list[str] = Field(default_factory=list)

    def path_params(self) -> list[str]:
        """Return the ``{param}`` names declared in the path."""
        return _PARAM.findall(self.path)

    def matches(self, path: str) -> dict[str, str] | None:
        """Return captured params if ``path`` matches this route, else ``None``."""
        pattern = "^" + _PARAM.sub(r"(?P<\1>[^/]+)", self.path) + "$"
        match = re.match(pattern, path)
        return match.groupdict() if match else None


class RegisteredRoute:
    """A route bound to its (optional) handler inside a router."""

    def __init__(self, route: ApiRoute, handler: RouteHandler | None = None) -> None:
        self.route = route
        self.handler = handler


class Router:
    """Registers routes and resolves an incoming request to one of them."""

    def __init__(self) -> None:
        self._routes: list[RegisteredRoute] = []

    def add(self, route: ApiRoute, handler: RouteHandler | None = None) -> RegisteredRoute:
        """Register ``route`` (optionally with a handler)."""
        for existing in self._routes:
            if existing.route.method == route.method and existing.route.path == route.path:
                raise ProviderConfigurationError(
                    f"duplicate route {route.method.value} {route.path}"
                )
        registered = RegisteredRoute(route, handler)
        self._routes.append(registered)
        return registered

    def routes(self) -> list[ApiRoute]:
        """Return every registered route descriptor."""
        return [r.route for r in self._routes]

    def resolve(
        self, method: HttpMethod, path: str
    ) -> tuple[RegisteredRoute, dict[str, str]] | None:
        """Return the matching route + captured params, or ``None``."""
        for registered in self._routes:
            if registered.route.method != method:
                continue
            params = registered.route.matches(path)
            if params is not None:
                return registered, params
        return None
