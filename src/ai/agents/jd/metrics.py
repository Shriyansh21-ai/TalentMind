"""JD metrics (Modules 3, 7, 9, 11).

Deterministic, evidence-derived measurements over a :class:`JDDocument`:
technology categorization, JD-quality **dimensions** (0-100), and offline
**market heuristics**. These numbers describe *job-description quality* and
market posture only; they must never influence candidate ranking (Module 11).

Everything here is a transparent function of what the JD contains — reproducible
and explainable, no model and no randomness. The technology taxonomy is local to
this package so the JD agent stays independent of the Resume agent (Module 15).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.ai.agents.jd.extractors import JDDocument

# -- technology taxonomy (local, transparent, editable) ---------------------

LANGUAGES = {
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "golang",
    "rust",
    "c++",
    "c#",
    "kotlin",
    "swift",
    "scala",
    "ruby",
    "php",
    "sql",
}
FRAMEWORKS = {
    "react",
    "angular",
    "vue",
    "next.js",
    "django",
    "flask",
    "fastapi",
    "spring",
    "spring boot",
    "node",
    "node.js",
    "express",
    ".net",
    "rails",
    "svelte",
}
CLOUD = {
    "aws",
    "gcp",
    "azure",
    "cloud",
    "lambda",
    "ec2",
    "s3",
    "cloudformation",
    "gke",
    "eks",
    "aks",
}
AI_ML = {
    "machine learning",
    "deep learning",
    "ml",
    "nlp",
    "llm",
    "rag",
    "pytorch",
    "tensorflow",
    "transformers",
    "computer vision",
    "scikit",
    "ai",
    "genai",
    "generative ai",
}
DEVOPS = {
    "docker",
    "kubernetes",
    "terraform",
    "ci/cd",
    "jenkins",
    "ansible",
    "helm",
    "prometheus",
    "grafana",
    "gitops",
    "argocd",
}
DATA = {
    "spark",
    "airflow",
    "kafka",
    "snowflake",
    "hadoop",
    "databricks",
    "dbt",
    "etl",
    "bigquery",
    "redshift",
    "warehouse",
}
SECURITY = {
    "security",
    "oauth",
    "iam",
    "encryption",
    "owasp",
    "penetration",
    "compliance",
    "soc2",
    "gdpr",
    "zero trust",
}
INFRA = {
    "microservices",
    "distributed systems",
    "high availability",
    "scalability",
    "load balancing",
    "message queue",
    "grpc",
    "graphql",
    "rest",
    "api gateway",
}
ARCHITECTURE = {
    "architecture",
    "system design",
    "design patterns",
    "event-driven",
    "domain-driven",
    "ddd",
    "cqrs",
    "monolith",
    "serverless",
}

MODERN_TECH = {
    "go",
    "rust",
    "typescript",
    "kubernetes",
    "terraform",
    "llm",
    "rag",
    "pytorch",
    "fastapi",
    "next.js",
    "graphql",
    "genai",
    "databricks",
    "grpc",
}
DATED_TECH = {
    "jquery",
    "perl",
    "cobol",
    "vb6",
    "flash",
    "silverlight",
    "soap",
    "coldfusion",
    "svn",
    "angularjs",
    "struts",
    "jsp",
}

BIAS_TERMS = {
    "young",
    "energetic",
    "recent graduate",
    "digital native",
    "native speaker",
    "cultural fit",
    "rockstar",
    "ninja",
    "guru",
    "he/him",
    "she/her",
    "aggressive",
    "fresh graduate",
}
VAGUE_TERMS = {
    "etc",
    "and more",
    "various",
    "other duties",
    "as needed",
    "wear many hats",
    "fast-paced",
    "self-starter",
    "wears many hats",
}

# Coarse demand/scarcity heuristics for market intelligence (offline only).
HIGH_DEMAND = {
    "llm",
    "rag",
    "genai",
    "kubernetes",
    "rust",
    "go",
    "ml",
    "machine learning",
    "pytorch",
    "terraform",
    "distributed systems",
}
SCARCE = {
    "llm",
    "rag",
    "genai",
    "rust",
    "distributed systems",
    "kubernetes",
    "compiler",
    "cryptography",
}

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.\-/]*")


@dataclass
class JDMetrics:
    """A bundle of deterministic JD measurements + quality dimensions."""

    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    cloud: list[str] = field(default_factory=list)
    ai_ml: list[str] = field(default_factory=list)
    devops: list[str] = field(default_factory=list)
    data: list[str] = field(default_factory=list)
    security: list[str] = field(default_factory=list)
    infrastructure: list[str] = field(default_factory=list)
    architecture: list[str] = field(default_factory=list)
    all_technologies: list[str] = field(default_factory=list)
    modern_tech: list[str] = field(default_factory=list)
    dated_tech: list[str] = field(default_factory=list)
    tech_count: int = 0
    requirement_count: int = 0
    responsibility_count: int = 0
    bias_terms: list[str] = field(default_factory=list)
    vague_terms: list[str] = field(default_factory=list)
    dimensions: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict of the metrics."""
        return {
            "languages": self.languages,
            "frameworks": self.frameworks,
            "cloud": self.cloud,
            "ai_ml": self.ai_ml,
            "devops": self.devops,
            "data": self.data,
            "security": self.security,
            "infrastructure": self.infrastructure,
            "architecture": self.architecture,
            "all_technologies": self.all_technologies,
            "modern_tech": self.modern_tech,
            "dated_tech": self.dated_tech,
            "tech_count": self.tech_count,
            "requirement_count": self.requirement_count,
            "responsibility_count": self.responsibility_count,
            "bias_terms": self.bias_terms,
            "vague_terms": self.vague_terms,
            "dimensions": {k: round(v, 1) for k, v in self.dimensions.items()},
        }


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp ``value`` into ``[low, high]``."""
    return max(low, min(high, value))


def _present(blob: str, vocab: set, tokens: set) -> list[str]:
    """Return the vocab terms present in ``blob`` (sorted, deduped).

    Single-word alphanumeric technologies are matched against the tokenized blob
    (word-boundary) so e.g. ``"scala"`` does NOT match inside ``"scalable"``.
    Multi-word phrases and terms with special characters (``c++``, ``ci/cd``,
    ``node.js``) fall back to substring matching.
    """
    out = []
    for term in vocab:
        if " " not in term and "+" not in term and "#" not in term and term.isalnum():
            hit = term in tokens or (term + "s") in tokens  # tolerate simple plurals (LLMs)
        else:
            hit = term in blob
        if hit:
            out.append(term)
    return sorted(out)


def compute_metrics(doc: JDDocument) -> JDMetrics:
    """Compute the full metric bundle for ``doc``."""
    m = JDMetrics()
    blob = doc.all_text()
    tokens = set(_WORD_RE.findall(blob))

    m.languages = _present(blob, LANGUAGES, tokens)
    m.frameworks = _present(blob, FRAMEWORKS, tokens)
    m.cloud = _present(blob, CLOUD, tokens)
    m.ai_ml = _present(blob, AI_ML, tokens)
    m.devops = _present(blob, DEVOPS, tokens)
    m.data = _present(blob, DATA, tokens)
    m.security = _present(blob, SECURITY, tokens)
    m.infrastructure = _present(blob, INFRA, tokens)
    m.architecture = _present(blob, ARCHITECTURE, tokens)

    all_tech = set()
    for group in (
        m.languages,
        m.frameworks,
        m.cloud,
        m.ai_ml,
        m.devops,
        m.data,
        m.security,
        m.infrastructure,
        m.architecture,
    ):
        all_tech.update(group)
    m.all_technologies = sorted(all_tech)
    m.modern_tech = _present(blob, MODERN_TECH, tokens)
    m.dated_tech = _present(blob, DATED_TECH, tokens)
    m.tech_count = len(m.all_technologies)

    m.requirement_count = len(doc.requirements)
    m.responsibility_count = len(doc.responsibilities)
    m.bias_terms = _present(blob, BIAS_TERMS, tokens)
    m.vague_terms = _present(blob, VAGUE_TERMS, tokens)

    m.dimensions = _dimensions(doc, m, blob)
    return m


def _dimensions(doc: JDDocument, m: JDMetrics, blob: str) -> dict[str, float]:
    """Compute the JD-quality dimensions (0-100). JD quality ONLY."""
    present = len(doc.sections_present)
    structure = _clamp(35 + present * 6)

    # Technical clarity: some tech named, categorized, not a giant undifferentiated dump.
    categories = sum(
        bool(g) for g in (m.languages, m.frameworks, m.cloud, m.ai_ml, m.devops, m.data)
    )
    technical_clarity = _clamp(
        30 + categories * 10 + min(m.tech_count, 8) * 2 - max(0, m.tech_count - 15) * 3
    )

    # Role clarity: responsibilities present + seniority/title signal + low vagueness.
    role_clarity = _clamp(
        35
        + min(m.responsibility_count, 6) * 7
        + (10 if doc.years_experience is not None else 0)
        - len(m.vague_terms) * 5
    )

    # Requirement quality: has requirements + a preferred/nice-to-have split.
    split_bonus = 15 if doc.preferred else 0
    requirement_quality = _clamp(
        30 + min(m.requirement_count, 8) * 6 + split_bonus - max(0, m.requirement_count - 12) * 2
    )

    # Business context: company info + why-the-role signal words.
    context_words = sum(
        1
        for w in ("mission", "growth", "scale", "customers", "team", "build", "launch")
        if w in blob
    )
    business_context = _clamp(25 + (25 if doc.company_info else 0) + context_words * 6)

    # Hiring readiness: compensation + benefits + responsibilities + requirements all present.
    hiring_readiness = _clamp(
        20
        + (20 if doc.compensation else 0)
        + (15 if doc.benefits else 0)
        + (20 if doc.responsibilities else 0)
        + (15 if doc.requirements else 0)
        + (10 if doc.location or doc.remote_policy else 0)
    )

    # Market alignment: modern tech vs dated tech.
    market_alignment = _clamp(50 + len(m.modern_tech) * 6 - len(m.dated_tech) * 8)

    # Organization clarity: department + company info + employment type.
    organization_clarity = _clamp(
        30
        + (25 if doc.company_info else 0)
        + (20 if doc.department else 0)
        + (15 if doc.employment_type else 0)
    )

    overall = _clamp(
        structure * 0.12
        + technical_clarity * 0.16
        + role_clarity * 0.16
        + requirement_quality * 0.14
        + business_context * 0.12
        + hiring_readiness * 0.12
        + market_alignment * 0.08
        + organization_clarity * 0.10
    )

    return {
        "overall": overall,
        "structure": structure,
        "technical_clarity": technical_clarity,
        "role_clarity": role_clarity,
        "requirement_quality": requirement_quality,
        "business_context": business_context,
        "hiring_readiness": hiring_readiness,
        "market_alignment": market_alignment,
        "organization_clarity": organization_clarity,
    }


# ---------------------------------------------------------------------------
# Market heuristics (Module 9) — offline, deterministic, confidence-tagged
# ---------------------------------------------------------------------------


def market_estimates(doc: JDDocument, m: JDMetrics) -> list[dict[str, object]]:
    """Return deterministic market estimates, each with a confidence."""
    blob = doc.all_text()
    tokens = set(_WORD_RE.findall(blob))
    high_demand = _present(blob, HIGH_DEMAND, tokens)
    scarce = _present(blob, SCARCE, tokens)
    years = doc.years_experience or 0

    def est(dimension: str, assessment: str, confidence: float) -> dict[str, object]:
        return {
            "dimension": dimension,
            "assessment": assessment,
            "confidence": round(confidence, 1),
        }

    estimates: list[dict[str, object]] = []

    demand = "High" if len(high_demand) >= 2 else ("Moderate" if high_demand else "Standard")
    estimates.append(
        est(
            "skill_demand",
            f"{demand} (drivers: {', '.join(high_demand) or 'none'})",
            65 if high_demand else 45,
        )
    )

    scarcity = "High" if len(scarce) >= 2 else ("Moderate" if scarce else "Low")
    estimates.append(est("talent_scarcity", scarcity, 60 if scarce else 45))

    difficulty = (
        "Hard"
        if (len(scarce) >= 2 or years >= 8 or m.tech_count >= 12)
        else ("Moderate" if m.tech_count >= 6 else "Manageable")
    )
    estimates.append(est("hiring_difficulty", difficulty, 55))

    availability = "Limited" if scarcity in ("High", "Moderate") else "Healthy"
    estimates.append(est("candidate_availability", availability, 50))

    competitiveness = "Competitive" if high_demand else "Average"
    estimates.append(est("market_competitiveness", competitiveness, 55 if high_demand else 45))

    # Salary competitiveness is only stated when the JD provides comp — never invented.
    if doc.compensation:
        estimates.append(
            est(
                "salary_competitiveness", "Comp disclosed in JD; benchmark against market bands", 40
            )
        )
    else:
        estimates.append(
            est("salary_competitiveness", "No compensation disclosed — cannot assess", 30)
        )

    popularity = (
        "Trending" if m.modern_tech else ("Mainstream" if m.all_technologies else "Unclear")
    )
    estimates.append(
        est(
            "technology_popularity",
            f"{popularity} ({', '.join(m.modern_tech[:5]) or 'n/a'})",
            60 if m.modern_tech else 40,
        )
    )

    return estimates
