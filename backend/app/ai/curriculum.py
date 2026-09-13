"""Original, versioned CareerOS capability maps for technical roadmaps.

The maps intentionally describe capabilities and proof rather than copied course
content. They make coverage deterministic while leaving sequence and depth to the
learner's demonstrated experience.
"""

import re

from app.ai.schema import CurriculumBackbone, CurriculumCapability, CurriculumPhase


def cap(key: str, label: str, topics: list[str], proof: str, *terms: str) -> CurriculumCapability:
    return CurriculumCapability(
        key=key, label=label, topics=topics, proof=proof, coverage_terms=list(terms)
    )


def phase(
    key: str, title: str, outcome: str, *capabilities: CurriculumCapability
) -> CurriculumPhase:
    return CurriculumPhase(key=key, title=title, outcome=outcome, capabilities=list(capabilities))


PYTHON_BACKEND = CurriculumBackbone(
    key="python-backend-engineering",
    version="2026.1",
    title="Python and backend engineering",
    summary=(
        "Build production-minded Python services through sound design, APIs, data, reliability, "
        "operations, security, and a reviewable case study."
    ),
    phases=[
        phase(
            "engineering-foundations",
            "Engineering foundations",
            "Use maintainable Python and repeatable delivery practices.",
            cap(
                "python-design",
                "Python design and testing",
                ["typing", "packaging", "errors", "tests"],
                "A tested typed module with documented failure behavior.",
                "python",
                "typing",
                "testing",
            ),
            cap(
                "delivery-workflow",
                "Version control and CI",
                ["Git", "code review", "CI", "configuration"],
                "A repository with repeatable checks and contribution notes.",
                "git",
                "ci",
                "code review",
            ),
        ),
        phase(
            "service-design",
            "Service and API design",
            "Design clear service boundaries and API contracts.",
            cap(
                "web-api",
                "Web API design",
                ["HTTP", "REST", "validation", "error contracts"],
                "An API contract with validated requests and useful errors.",
                "api",
                "http",
                "rest",
            ),
            cap(
                "application-architecture",
                "Application architecture",
                ["modularity", "dependencies", "configuration", "boundaries"],
                "A component diagram and testable domain implementation.",
                "architecture",
                "dependency",
                "configuration",
            ),
        ),
        phase(
            "data-reliability",
            "Data and reliability",
            "Persist data safely and handle integration failure modes.",
            cap(
                "data-modeling",
                "Data modeling and persistence",
                ["SQL", "schema", "migrations", "transactions"],
                "A migration-backed schema with justified constraints.",
                "database",
                "sql",
                "migration",
            ),
            cap(
                "reliability",
                "Reliability and integration behavior",
                ["timeouts", "retries", "idempotency", "queues"],
                "Failure-path tests explaining retry and idempotency decisions.",
                "reliability",
                "retry",
                "idempotency",
            ),
        ),
        phase(
            "production-proof",
            "Production proof",
            "Ship, observe, secure, and explain a backend system.",
            cap(
                "operations",
                "Deployment and observability",
                ["Docker", "logs", "metrics", "health checks"],
                "A deployable service with operational notes and health evidence.",
                "deploy",
                "docker",
                "observability",
            ),
            cap(
                "security-proof",
                "Security and engineering proof",
                ["authentication", "authorization", "secrets", "threat modeling"],
                "A security review and case study showing trade-offs and results.",
                "security",
                "authentication",
                "authorization",
            ),
        ),
    ],
)

APPLIED_AI = CurriculumBackbone(
    key="applied-ai-automation",
    version="2026.1",
    title="Applied AI and automation engineering",
    summary=(
        "Build dependable AI-enabled systems by joining workflow design, LLM architecture, "
        "retrieval, evaluation, safety, operations, and credible portfolio proof."
    ),
    phases=[
        phase(
            "problem-foundation",
            "Problem and system foundation",
            "Frame the automation problem and its non-AI system boundaries.",
            cap(
                "workflow-framing",
                "Workflow framing and requirements",
                ["user workflow", "success criteria", "failure modes", "human handoff"],
                "A workflow brief with measurable success and escalation paths.",
                "workflow",
                "requirements",
                "acceptance criteria",
            ),
            cap(
                "automation-platform",
                "Automation service foundations",
                ["Python services", "APIs", "events", "state"],
                "A tested integration boundary for the surrounding system.",
                "automation",
                "api",
                "integration",
            ),
        ),
        phase(
            "llm-application-design",
            "LLM application design",
            "Build a controlled LLM workflow rather than a one-shot prompt demo.",
            cap(
                "llm-workflows",
                "LLM workflow architecture",
                ["prompt contracts", "structured output", "tool use", "state"],
                "A structured workflow handling malformed output and tool failures.",
                "llm",
                "structured output",
                "prompt",
            ),
            cap(
                "knowledge-retrieval",
                "Knowledge and retrieval design",
                ["retrieval", "chunking", "grounding", "citations"],
                "A retrieval experiment explaining relevance and grounding trade-offs.",
                "retrieval",
                "rag",
                "grounding",
            ),
        ),
        phase(
            "quality-safety",
            "Quality and safety",
            "Measure the system and control foreseeable model and workflow failures.",
            cap(
                "evaluation",
                "Evaluation and iteration",
                ["test set", "metrics", "error analysis", "regression"],
                "An evaluation report with failures and improvement decisions.",
                "evaluation",
                "metrics",
                "test set",
            ),
            cap(
                "ai-safety",
                "Safety and control boundaries",
                ["prompt injection", "permissions", "PII", "human review"],
                "Documented controls and adversarial tests for high-risk actions.",
                "safety",
                "prompt injection",
                "human review",
            ),
        ),
        phase(
            "production-proof",
            "Production and proof",
            "Operate the system and demonstrate that it is useful and dependable.",
            cap(
                "ai-operations",
                "Deployment and observability",
                ["deployment", "tracing", "cost", "latency"],
                "A deployed workflow with traces, reliability signals, and cost awareness.",
                "deployment",
                "observability",
                "tracing",
            ),
            cap(
                "ai-case-study",
                "Portfolio proof and communication",
                ["case study", "demo", "trade-offs", "limitations"],
                "A reviewable demo and case study tied to user value and evaluation evidence.",
                "portfolio",
                "case study",
                "demo",
            ),
        ),
    ],
)

DATA_ENGINEERING = CurriculumBackbone(
    key="data-engineering",
    version="2026.1",
    title="Data engineering",
    summary=(
        "Build trustworthy data products through data modeling, ingestion, transformation, "
        "orchestration, quality controls, platform operations, and documented end-to-end proof."
    ),
    phases=[
        phase(
            "data-foundations",
            "Data foundations",
            "Model analytical data and use core reproducible tooling.",
            cap(
                "sql-modeling",
                "SQL and data modeling",
                ["SQL", "normalization", "dimensional models", "query plans"],
                "A justified schema and analytical query set.",
                "sql",
                "data model",
                "schema",
            ),
            cap(
                "data-tooling",
                "Data tooling and versioned workflow",
                ["Python", "Git", "environments", "tests"],
                "A reproducible data project with dependency checks.",
                "python",
                "git",
                "testing",
            ),
        ),
        phase(
            "pipeline-building",
            "Pipeline building",
            "Ingest and transform data into dependable datasets.",
            cap(
                "ingestion",
                "Ingestion and storage",
                ["APIs", "files", "batch", "incremental loads"],
                "An ingestion job recording source, state, and failure behavior.",
                "ingestion",
                "extract",
                "load",
            ),
            cap(
                "transformation",
                "Transformation and warehouse design",
                ["ELT", "warehouse", "dbt", "lineage"],
                "Documented transformations that create tested consumer tables.",
                "transformation",
                "warehouse",
                "dbt",
            ),
        ),
        phase(
            "orchestration-quality",
            "Orchestration and quality",
            "Run pipelines predictably and detect bad data before consumers do.",
            cap(
                "orchestration",
                "Orchestration and recovery",
                ["dependencies", "backfills", "retries", "scheduling"],
                "A pipeline graph with recovery and rerun behavior.",
                "orchestration",
                "airflow",
                "workflow",
            ),
            cap(
                "data-quality",
                "Data quality and observability",
                ["assertions", "freshness", "monitoring", "incident response"],
                "Automated data checks and an issue response path.",
                "data quality",
                "freshness",
                "monitoring",
            ),
        ),
        phase(
            "platform-proof",
            "Platform and proof",
            "Deploy, secure, and explain an end-to-end data product.",
            cap(
                "data-platform",
                "Deployment, security, and cost",
                ["cloud", "access control", "secrets", "cost"],
                "A reproducible platform plan with trade-offs.",
                "deployment",
                "security",
                "cost",
            ),
            cap(
                "data-case-study",
                "Data product proof",
                ["documentation", "consumer", "case study", "lineage"],
                "A demo explaining source-to-consumer lineage and decisions.",
                "portfolio",
                "case study",
                "documentation",
            ),
        ),
    ],
)

CURRICULA = (APPLIED_AI, DATA_ENGINEERING, PYTHON_BACKEND)


def select_curriculum(goal_title: str, context: str = "") -> CurriculumBackbone | None:
    """Return only a high-confidence match; ordinary goals remain fully adaptive."""
    text = f"{goal_title} {context}".casefold()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    terms = {
        APPLIED_AI.key: ("applied ai", "ai automation", "ai engineer", "llm", "rag", "agent"),
        DATA_ENGINEERING.key: (
            "data engineer",
            "data engineering",
            "etl",
            "elt",
            "airflow",
            "dbt",
            "data pipeline",
            "warehouse",
        ),
        PYTHON_BACKEND.key: (
            "python",
            "backend",
            "fastapi",
            "django",
            "api",
            "web service",
            "software engineer",
        ),
    }
    scores = {
        key: sum(2 if " " in term else 1 for term in values if term in text or term in tokens)
        for key, values in terms.items()
    }
    key, score = max(scores.items(), key=lambda item: item[1])
    return next(item for item in CURRICULA if item.key == key) if score else None
