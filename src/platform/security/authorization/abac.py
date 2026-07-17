"""Attribute-based access control (Module 2 — ABAC).

Evaluates :class:`AbacPolicy` objects against an :class:`AuthorizationRequest`.
A policy matches when its resource/action patterns cover the requested
permission *and* every one of its attribute conditions holds against the
request's flattened attribute bag. Matching policies are returned with their
effect so the engine can combine them (DENY overrides ALLOW).
"""

from __future__ import annotations

from src.platform.rbac import matches  # reuse M1 wildcard matching
from src.platform.security.authorization.models import (
    AbacPolicy,
    AuthorizationRequest,
    PolicyEffect,
    PolicyMatch,
)


class AbacEngine:
    """Evaluates ABAC policies against a request."""

    def _policy_targets_permission(self, policy: AbacPolicy, permission: str) -> bool:
        pattern = f"{policy.resource}:{policy.action}"
        return matches(pattern, permission)

    def _conditions_hold(self, policy: AbacPolicy, attributes: dict[str, object]) -> bool:
        return all(cond.evaluate(attributes) for cond in policy.conditions)

    def evaluate(
        self, request: AuthorizationRequest, policies: list[AbacPolicy]
    ) -> list[PolicyMatch]:
        """Return the policies that match ``request`` (highest priority first)."""
        attributes = request.attribute_bag()
        matched: list[PolicyMatch] = []
        for policy in policies:
            if not self._policy_targets_permission(policy, request.permission):
                continue
            if not self._conditions_hold(policy, attributes):
                continue
            matched.append(
                PolicyMatch(
                    policy_id=policy.id,
                    name=policy.name,
                    effect=policy.effect,
                    priority=policy.priority,
                )
            )
        matched.sort(key=lambda m: m.priority, reverse=True)
        return matched

    @staticmethod
    def combined_effect(matched: list[PolicyMatch]) -> PolicyEffect | None:
        """Combine matched effects: any DENY wins; else ALLOW if any allow."""
        if not matched:
            return None
        if any(m.effect == PolicyEffect.DENY for m in matched):
            return PolicyEffect.DENY
        return PolicyEffect.ALLOW
