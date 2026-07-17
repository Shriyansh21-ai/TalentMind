"""Interview templates (Modules 1, 5).

Pure configuration (no engine / UI import) shared by the strategy engine, the
question generator and the planner:

* :data:`DEPTH_PROFILES` — interview depth presets (screen / standard / deep)
  that set length, stage count and difficulty framing (Module 1).
* :data:`ROLE_PROFILES` — role-specific interview paths (backend, frontend, ML
  engineer, data scientist, DevOps, cloud, security, product manager,
  engineering manager) with the specialized competencies each loop must cover
  (Module 5).

This is the Open/Closed heart of the studio: adding an interview depth or a role
path is a one-entry data change, never new generation code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class DepthProfile:
    """An interview-depth preset (Module 1)."""

    key: str
    name: str
    length_minutes: int
    stage_count: int
    summary: str


DEPTH_PROFILES: dict[str, DepthProfile] = {
    "screen": DepthProfile(
        key="screen",
        name="Recruiter Screen",
        length_minutes=60,
        stage_count=2,
        summary="A fast signal check — motivation, baseline depth and logistics.",
    ),
    "standard": DepthProfile(
        key="standard",
        name="Standard Loop",
        length_minutes=240,
        stage_count=5,
        summary="The full loop — technical, system design, behavioral and debrief.",
    ),
    "deep": DepthProfile(
        key="deep",
        name="Deep / Leadership Loop",
        length_minutes=330,
        stage_count=6,
        summary="An extended senior loop with architecture, leadership and a debrief.",
    ),
}

DEFAULT_DEPTH = "standard"


def get_depth(key: str) -> DepthProfile:
    """Return the depth profile for ``key`` (falls back to the default)."""
    return DEPTH_PROFILES.get((key or "").strip().lower(), DEPTH_PROFILES[DEFAULT_DEPTH])


@dataclass(frozen=True)
class RoleProfile:
    """A role-specific interview path (Module 5).

    Attributes:
        key: Stable role key.
        name: Human-readable role name.
        aliases: Title / keyword fragments that route a candidate to this role.
        competencies: The specialized competencies this loop must assess.
        technical_focus: Concrete technical topics for the role.
        system_design_focus: Architecture / design topics scaled to the role.
        coding_focus: Coding-round emphasis.
        emphasize_system_design: Whether system design is a first-class stage.
        emphasize_leadership: Whether a dedicated leadership stage applies.
    """

    key: str
    name: str
    aliases: list[str] = field(default_factory=list)
    competencies: list[str] = field(default_factory=list)
    technical_focus: list[str] = field(default_factory=list)
    system_design_focus: list[str] = field(default_factory=list)
    coding_focus: list[str] = field(default_factory=list)
    emphasize_system_design: bool = True
    emphasize_leadership: bool = False


ROLE_PROFILES: dict[str, RoleProfile] = {
    "backend": RoleProfile(
        key="backend",
        name="Backend Engineer",
        aliases=["backend", "back-end", "back end", "server", "api engineer", "platform engineer"],
        competencies=[
            "API design",
            "Data modelling",
            "Concurrency",
            "Reliability",
            "Observability",
        ],
        technical_focus=[
            "Designing clean, versioned service APIs",
            "Relational vs. non-relational data modelling trade-offs",
            "Concurrency, idempotency and transaction boundaries",
            "Caching strategies and cache invalidation",
        ],
        system_design_focus=[
            "Design a high-throughput backend service end-to-end",
            "Consistency, availability and partitioning trade-offs",
            "Queueing, backpressure and failure isolation",
        ],
        coding_focus=[
            "Implement a correct, well-tested service endpoint",
            "Reason about edge cases and error handling",
        ],
    ),
    "frontend": RoleProfile(
        key="frontend",
        name="Frontend Engineer",
        aliases=["frontend", "front-end", "front end", "ui engineer", "react", "web engineer"],
        competencies=[
            "Component architecture",
            "State management",
            "Performance",
            "Accessibility",
            "UX collaboration",
        ],
        technical_focus=[
            "Component architecture and reusable design systems",
            "State management at scale (stores, caching, hydration)",
            "Rendering performance and bundle-size budgets",
            "Accessibility (a11y) and cross-browser behavior",
        ],
        system_design_focus=[
            "Design a responsive, accessible feature end-to-end",
            "Client-side data flow, caching and optimistic updates",
            "Performance budgets and progressive loading",
        ],
        coding_focus=[
            "Build an interactive component with clean state",
            "Handle async data, loading and error states",
        ],
        emphasize_system_design=False,
    ),
    "ml_engineer": RoleProfile(
        key="ml_engineer",
        name="ML Engineer",
        aliases=[
            "ml engineer",
            "machine learning engineer",
            "mle",
            "ml eng",
            "applied scientist",
            "ai engineer",
        ],
        competencies=[
            "Modelling",
            "ML systems",
            "Data pipelines",
            "Evaluation",
            "Productionization",
        ],
        technical_focus=[
            "Model selection and the bias/variance trade-off",
            "Feature engineering and data-pipeline design",
            "Offline vs. online evaluation and metric selection",
            "Serving, latency and model monitoring in production",
        ],
        system_design_focus=[
            "Design an end-to-end ML system (training + serving)",
            "Feature store, retraining cadence and drift detection",
            "Scaling inference and controlling cost/latency",
        ],
        coding_focus=[
            "Implement a data-processing / feature transform correctly",
            "Reason about vectorized vs. iterative approaches",
        ],
    ),
    "data_scientist": RoleProfile(
        key="data_scientist",
        name="Data Scientist",
        aliases=["data scientist", "data science", "ds ", "research scientist", "statistician"],
        competencies=[
            "Statistics",
            "Experiment design",
            "Analysis",
            "Communication",
            "Business impact",
        ],
        technical_focus=[
            "Experiment / A-B test design and pitfalls",
            "Statistical inference and significance reasoning",
            "Choosing metrics that map to business outcomes",
            "Communicating findings to non-technical stakeholders",
        ],
        system_design_focus=[
            "Design an experimentation / analytics pipeline",
            "Data quality, sampling bias and validity threats",
        ],
        coding_focus=[
            "Data manipulation and analysis on a realistic dataset",
            "Translate a business question into an analysis plan",
        ],
        emphasize_system_design=False,
    ),
    "devops": RoleProfile(
        key="devops",
        name="DevOps / SRE",
        aliases=[
            "devops",
            "sre",
            "site reliability",
            "platform reliability",
            "infrastructure engineer",
        ],
        competencies=["CI/CD", "Reliability", "Automation", "Observability", "Incident response"],
        technical_focus=[
            "CI/CD pipeline design and safe deployment strategies",
            "Infrastructure as code and configuration management",
            "Observability: metrics, logging, tracing and alerting",
            "Incident response, on-call and blameless postmortems",
        ],
        system_design_focus=[
            "Design a resilient, self-healing deployment platform",
            "SLOs, error budgets and capacity planning",
            "Failure modes, recovery and disaster readiness",
        ],
        coding_focus=[
            "Automate a deployment / operational task with a script",
            "Reason about idempotency and rollback safety",
        ],
    ),
    "cloud_engineer": RoleProfile(
        key="cloud_engineer",
        name="Cloud Engineer",
        aliases=[
            "cloud engineer",
            "cloud architect",
            "aws",
            "azure",
            "gcp",
            "cloud infrastructure",
        ],
        competencies=[
            "Cloud architecture",
            "Networking",
            "Cost optimization",
            "Security",
            "Scalability",
        ],
        technical_focus=[
            "Cloud-native architecture and managed-service selection",
            "Networking, VPC design and connectivity",
            "Cost optimization and right-sizing",
            "Cloud security posture and IAM boundaries",
        ],
        system_design_focus=[
            "Design a multi-region, highly-available cloud system",
            "Trade-offs between managed services and control",
            "Scaling, resilience and cost under load",
        ],
        coding_focus=[
            "Provision infrastructure declaratively (IaC)",
            "Reason about least-privilege access",
        ],
    ),
    "security": RoleProfile(
        key="security",
        name="Security Engineer",
        aliases=["security engineer", "security", "appsec", "infosec", "cybersecurity", "pentest"],
        competencies=[
            "Threat modelling",
            "Secure design",
            "Vulnerability analysis",
            "Incident response",
            "Compliance",
        ],
        technical_focus=[
            "Threat modelling a realistic system",
            "Common vulnerability classes and mitigations (OWASP)",
            "Secure authentication, authorization and secrets handling",
            "Detection, response and forensics fundamentals",
        ],
        system_design_focus=[
            "Design a defense-in-depth architecture",
            "Trust boundaries, blast-radius containment and least privilege",
        ],
        coding_focus=[
            "Spot and fix a security flaw in a code snippet",
            "Reason about input validation and safe defaults",
        ],
    ),
    "product_manager": RoleProfile(
        key="product_manager",
        name="Product Manager",
        aliases=["product manager", "pm ", "product owner", "group product", "senior pm"],
        competencies=[
            "Product sense",
            "Prioritization",
            "Stakeholder management",
            "Metrics",
            "Execution",
        ],
        technical_focus=[
            "Product sense: defining the problem and the user",
            "Prioritization frameworks and trade-off reasoning",
            "Success metrics and how to measure impact",
            "Working with engineering on scope and feasibility",
        ],
        system_design_focus=[
            "Design a product roadmap for an ambiguous problem",
            "Balancing user value, business goals and effort",
        ],
        coding_focus=[
            "Structure a product case with clear assumptions",
            "Estimate impact and define an MVP",
        ],
        emphasize_system_design=False,
        emphasize_leadership=True,
    ),
    "engineering_manager": RoleProfile(
        key="engineering_manager",
        name="Engineering Manager",
        aliases=[
            "engineering manager",
            "em ",
            "eng manager",
            "director of engineering",
            "head of engineering",
            "manager",
        ],
        competencies=[
            "People leadership",
            "Technical direction",
            "Delivery",
            "Stakeholder management",
            "Hiring & growth",
        ],
        technical_focus=[
            "Setting and communicating technical direction",
            "Balancing delivery, quality and team health",
            "Coaching, performance management and growth",
            "Cross-functional stakeholder management",
        ],
        system_design_focus=[
            "Design a team / org structure for a mandate",
            "Technical strategy and build-vs-buy decisions",
        ],
        coding_focus=[
            "Review an engineer's design and give feedback",
            "Reason about technical trade-offs at a system level",
        ],
        emphasize_leadership=True,
    ),
    "generalist": RoleProfile(
        key="generalist",
        name="Software Engineer",
        aliases=["software engineer", "developer", "engineer", "full stack", "fullstack", "sde"],
        competencies=["Coding", "Problem solving", "System design", "Collaboration", "Ownership"],
        technical_focus=[
            "Core computer-science fundamentals",
            "Clean, testable code and design",
            "Debugging and reasoning under ambiguity",
        ],
        system_design_focus=[
            "Design a service with a clean API boundary",
            "Data modelling and basic scaling strategies",
        ],
        coding_focus=[
            "Algorithmic problem with clear reasoning",
            "Readable, correct implementation with tests",
        ],
    ),
}

DEFAULT_ROLE = "generalist"


def get_role(key: str) -> RoleProfile:
    """Return the role profile for ``key`` (falls back to the generalist path)."""
    return ROLE_PROFILES.get((key or "").strip().lower(), ROLE_PROFILES[DEFAULT_ROLE])


def detect_role(*hints: str) -> RoleProfile:
    """Infer the best-matching :class:`RoleProfile` from free-text hints.

    Checks each hint (title, JD role text, seniority) against every role's
    aliases, longest-alias-first so specific roles ("engineering manager") win
    over generic fragments ("engineer"). Deterministic and offline.
    """
    blob = " ".join(h.lower() for h in hints if h)
    if not blob.strip():
        return ROLE_PROFILES[DEFAULT_ROLE]

    # Specific roles compete on longest matched alias; the generalist is a
    # fallback only, so its generic aliases ("engineer") never beat "backend".
    best_role = ROLE_PROFILES[DEFAULT_ROLE]
    best_len = 0
    for role in ROLE_PROFILES.values():
        if role.key == DEFAULT_ROLE:
            continue
        for alias in role.aliases:
            if alias in blob and len(alias) > best_len:
                best_role = role
                best_len = len(alias)
    return best_role


def list_roles() -> list[RoleProfile]:
    """Return every registered role profile (stable order)."""
    return list(ROLE_PROFILES.values())


def list_depths() -> list[DepthProfile]:
    """Return every registered depth profile (stable order)."""
    return list(DEPTH_PROFILES.values())
