"""OpenAPI document scaffolding (Module 10).

Builds a minimal, valid OpenAPI 3.1 skeleton describing the versioned API
surface and the standard response/error envelopes. This documents the contract;
it does not implement or rewrite any endpoint.
"""

from __future__ import annotations

from typing import Any

from src.platform.api.versioning import CURRENT_VERSION


def build_openapi(title: str = "TalentMind Platform API") -> dict[str, Any]:
    """Return a minimal OpenAPI 3.1 document for the platform API."""
    return {
        "openapi": "3.1.0",
        "info": {"title": title, "version": CURRENT_VERSION.value},
        "servers": [{"url": f"/api/{CURRENT_VERSION.value}"}],
        "components": {
            "schemas": {
                "ApiError": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "object"},
                    },
                    "required": ["code", "message"],
                },
                "ApiResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "data": {},
                        "error": {"$ref": "#/components/schemas/ApiError"},
                        "meta": {"type": "object"},
                    },
                    "required": ["success"],
                },
            }
        },
        "paths": {},
    }
