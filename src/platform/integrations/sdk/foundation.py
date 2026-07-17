"""Developer SDK foundation (Module 12).

The *future package structure* for the TalentMind developer SDKs, expressed as
declarative :class:`SdkDefinition` descriptors, plus a tiny offline
:class:`RestClientFoundation` that builds standard :class:`ApiRequest` objects
and (optionally) dispatches them through the in-process
:class:`~src.platform.integrations.gateway.ApiGateway`. No SDK is published and
no network call is made — this is the scaffolding real SDK packages are
generated from.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.integrations.gateway.gateway import ApiGateway, ApiRequest
from src.platform.integrations.gateway.routing import HttpMethod


class SdkKind(str, Enum):
    """The kind of SDK a definition describes."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    REST_CLIENT = "rest_client"
    WEBHOOK = "webhook"
    PLUGIN = "plugin"
    AUTHENTICATION = "authentication"
    EXTENSION = "extension"


class SdkDefinition(PlatformModel):
    """A planned SDK package's shape (future package structure only)."""

    kind: SdkKind
    name: str
    package: str
    language: str = "python"
    description: str = ""
    modules: list[str] = Field(default_factory=list)
    status: str = "planned"


def sdk_catalog() -> list[SdkDefinition]:
    """Return the planned SDK package catalogue (foundation only)."""
    return [
        SdkDefinition(
            kind=SdkKind.PYTHON,
            name="TalentMind Python SDK",
            package="talentmind-sdk",
            language="python",
            description="Idiomatic Python client for the TalentMind Enterprise API.",
            modules=["client", "resources", "models", "pagination", "errors"],
        ),
        SdkDefinition(
            kind=SdkKind.JAVASCRIPT,
            name="TalentMind JavaScript/TypeScript SDK",
            package="@talentmind/sdk",
            language="typescript",
            description="Typed JS/TS client for browser and Node.js.",
            modules=["client", "resources", "types", "pagination", "errors"],
        ),
        SdkDefinition(
            kind=SdkKind.REST_CLIENT,
            name="REST Client",
            package="talentmind-sdk.rest",
            description="Low-level, transport-agnostic REST client foundation.",
            modules=["request", "response", "retry", "auth"],
        ),
        SdkDefinition(
            kind=SdkKind.WEBHOOK,
            name="Webhook SDK",
            package="talentmind-sdk.webhooks",
            description="Verify signatures and parse inbound webhook events.",
            modules=["verify", "events", "replay_guard"],
        ),
        SdkDefinition(
            kind=SdkKind.PLUGIN,
            name="Plugin SDK",
            package="talentmind-sdk.plugins",
            description="Author marketplace plugins against the extension seams.",
            modules=["manifest", "lifecycle", "hooks"],
        ),
        SdkDefinition(
            kind=SdkKind.AUTHENTICATION,
            name="Authentication SDK",
            package="talentmind-sdk.auth",
            description="OAuth2/OIDC and API-key credential helpers.",
            modules=["oauth", "api_key", "token_store"],
        ),
        SdkDefinition(
            kind=SdkKind.EXTENSION,
            name="Extension SDK",
            package="talentmind-sdk.extensions",
            description="Build UI/workflow extensions on the platform SDK surface.",
            modules=["registry", "capabilities", "sandbox"],
        ),
    ]


class RestClientFoundation:
    """An offline REST client foundation that speaks the standard envelope.

    It builds normalized :class:`ApiRequest` objects and, when handed an
    :class:`ApiGateway`, dispatches them in-process — the same code path a real
    HTTP client would exercise, minus the socket. Real SDKs swap the dispatch
    for an HTTP transport without changing call sites.
    """

    def __init__(
        self,
        *,
        gateway: ApiGateway | None = None,
        base_path: str = "/api",
        version: str = "v1",
        api_key: str = "",
    ) -> None:
        self._gateway = gateway
        self._base_path = base_path.rstrip("/")
        self._version = version
        self._api_key = api_key

    def build_request(
        self,
        method: HttpMethod,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
    ) -> ApiRequest:
        """Build a normalized request (auth header included when configured)."""
        headers = {"X-Api-Key": self._api_key} if self._api_key else {}
        return ApiRequest(
            method=method,
            path=path,
            version=self._version,
            headers=headers,
            query=query or {},
            body=body or {},
        )

    def request(
        self,
        method: HttpMethod,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
    ):
        """Dispatch a request through the gateway and return the envelope."""
        if self._gateway is None:
            raise RuntimeError("RestClientFoundation has no gateway bound")
        return self._gateway.handle(self.build_request(method, path, query=query, body=body))

    def get(self, path: str, *, query: dict[str, str] | None = None):
        """Convenience GET."""
        return self.request(HttpMethod.GET, path, query=query)
