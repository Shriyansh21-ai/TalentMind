"""Enterprise API Gateway (Module 7).

Composes the existing Module 10 API contracts (response/error envelopes,
versioning, rate limiting, pagination) with the Module 7 routing/auth seams into
one dispatchable gateway. A request flows through a fixed, auditable pipeline:

    negotiate version → authenticate → authorize scopes → rate-limit →
    dispatch handler → wrap in a standard ApiResponse

No existing business endpoint is rewritten: handlers are plain callables the
platform registers against declarative :class:`ApiRoute` s. The gateway only
standardises the cross-cutting concerns around them.
"""

from __future__ import annotations

from pydantic import Field

from src.platform.api.errors import http_status_for, to_response
from src.platform.api.ratelimit import RateLimiter, TokenBucketRateLimiter
from src.platform.api.responses import ApiResponse, ResponseMeta, fail, ok
from src.platform.api.versioning import negotiate
from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import (
    AuthenticationError,
    PermissionDeniedError,
    PlatformError,
    QuotaExceededError,
)
from src.platform.common.ids import generate_id
from src.platform.common.models import PlatformModel
from src.platform.integrations.gateway.auth import AuthenticationHook, ApiPrincipal
from src.platform.integrations.gateway.routing import HttpMethod, Router


class ApiRequest(PlatformModel):
    """A normalized inbound API request the gateway dispatches."""

    method: HttpMethod
    path: str
    version: str = "v1"
    headers: dict[str, str] = Field(default_factory=dict)
    query: dict[str, str] = Field(default_factory=dict)
    body: dict[str, object] = Field(default_factory=dict)


class ApiGateway:
    """Dispatches :class:`ApiRequest` s through the standard pipeline."""

    def __init__(
        self,
        *,
        router: Router | None = None,
        auth_hook: AuthenticationHook | None = None,
        rate_limiter: RateLimiter | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.router = router or Router()
        self.auth_hook = auth_hook
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(clock=self._clock)

    def handle(self, request: ApiRequest) -> ApiResponse:
        """Run ``request`` through the full pipeline and return an envelope."""
        version = negotiate(request.version)
        meta = ResponseMeta(request_id=generate_id("req"), api_version=version.value)
        try:
            resolved = self.router.resolve(request.method, request.path)
            if resolved is None:
                return fail("not_found", f"no route for {request.method.value} {request.path}", meta=meta)
            registered, params = resolved
            route = registered.route

            principal = self._authenticate(request, route)
            self._authorize(principal, route)
            self._rate_limit(principal, request)

            if registered.handler is None:
                # Architecture-only route: report it is declared but unbound.
                return ok(
                    {"route": route.name, "declared": True, "bound": False},
                    meta=meta,
                )
            context = {
                "params": params,
                "query": request.query,
                "body": request.body,
                "principal": principal.model_dump() if principal else None,
            }
            result = registered.handler(context)
            return ok(result, meta=meta)
        except PlatformError as exc:
            return to_response(exc, meta=meta)

    # -- pipeline stages ----------------------------------------------------

    def _authenticate(self, request: ApiRequest, route) -> ApiPrincipal | None:
        if not route.auth_required:
            return None
        if self.auth_hook is None:
            raise AuthenticationError("no authentication hook configured")
        principal = self.auth_hook.authenticate(request.headers)
        if principal is None or not principal.authenticated:
            raise AuthenticationError("invalid or missing credentials")
        return principal

    def _authorize(self, principal: ApiPrincipal | None, route) -> None:
        if not route.scopes:
            return
        if principal is None:
            raise PermissionDeniedError("authentication required for scoped route")
        missing = [s for s in route.scopes if not principal.has_scope(s)]
        if missing:
            raise PermissionDeniedError(f"missing required scopes: {missing}")

    def _rate_limit(self, principal: ApiPrincipal | None, request: ApiRequest) -> None:
        key = principal.principal_id if principal else f"anon:{request.path}"
        result = self.rate_limiter.check(key)
        if not result.allowed:
            raise QuotaExceededError(
                f"rate limit exceeded (limit={result.limit}/min)"
            )

    def http_status(self, response: ApiResponse) -> int:
        """Return the HTTP status a response maps to (200 on success)."""
        if response.success:
            return 200
        error = PlatformError(response.error.message if response.error else "")
        error.code = response.error.code if response.error else "platform_error"
        return http_status_for(error)
