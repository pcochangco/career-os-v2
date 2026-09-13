import re
from typing import Literal

from app.ai.schema import (
    ProviderCritique,
    QualityIssue,
    QualityReport,
    RoadmapDraft,
    RoadmapGenerationInput,
)

URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
SCHEDULE_PATTERN = re.compile(
    r"\b(daily|every day|deadline|overdue|hours? per day|days? per week|weekly schedule)\b",
    re.IGNORECASE,
)
WEAK_COMPLETION_PATTERN = re.compile(
    r"^(understand|learn|know|be familiar|feel confident)\b",
    re.IGNORECASE,
)
PERSONALIZATION_STOP_WORDS = {
    "about", "after", "already", "and", "are", "build", "from", "into", "learner",
    "learning", "need", "needed", "only", "proof", "that", "the", "their", "this",
    "through", "with", "work", "your",
}


def meaningful_terms(value: str) -> set[str]:
    return {
        term.casefold()
        for term in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{3,}", value)
        if term.casefold() not in PERSONALIZATION_STOP_WORDS
    }


def issue(
    code: str,
    message: str,
    path: str,
    repair_instruction: str,
    severity: Literal["warning", "error"] = "error",
) -> QualityIssue:
    return QualityIssue(
        severity=severity,
        code=code,
        message=message,
        path=path,
        repair_instruction=repair_instruction,
    )


def evaluate_structure(
    draft: RoadmapDraft,
    generation_input: RoadmapGenerationInput,
) -> tuple[int, list[QualityIssue]]:
    issues: list[QualityIssue] = []
    flattened = [step for milestone in draft.milestones for step in milestone.steps]
    step_positions = {step.stable_key: index for index, step in enumerate(flattened)}

    if len(flattened) < 10:
        issues.append(
            issue(
                "too_few_steps",
                "The roadmap has fewer than ten meaningful steps.",
                "milestones",
                "Add the missing prerequisite, implementation, feedback, or proof bridges so "
                "the learner can follow the path without inventing work between phases.",
            )
        )
    if len(flattened) > 24:
        issues.append(
            issue(
                "too_many_steps",
                "The roadmap is too granular for a focused path.",
                "milestones",
                "Merge repetitive or low-value steps and keep at most 24.",
            )
        )

    if len(draft.milestones) < 3:
        issues.append(
            issue(
                "too_few_capability_phases",
                "The roadmap needs at least three capability phases: foundation, application, "
                "and proof.",
                "milestones",
                "Split the path into distinct capability gates that make the learner's starting "
                "point, applied work, and credible proof visible.",
            )
        )

    for milestone_index, milestone in enumerate(draft.milestones, start=1):
        if len(milestone.steps) < 2:
            issues.append(
                issue(
                    "thin_milestone",
                    "Each capability phase needs at least two connected actions.",
                    f"milestones.{milestone_index}.steps",
                    "Add the missing bridge action so this phase has a concrete "
                    "capability-building step and an applied or evidence-producing step.",
                )
            )

    keys = [step.stable_key for step in flattened]
    if len(keys) != len(set(keys)):
        issues.append(
            issue(
                "duplicate_step_key",
                "Step keys must be unique across the roadmap.",
                "milestones",
                "Assign a unique semantic key to every step.",
            )
        )

    normalized_titles = [step.title.casefold().strip() for step in flattened]
    if len(normalized_titles) != len(set(normalized_titles)):
        issues.append(
            issue(
                "duplicate_step_title",
                "The roadmap contains repeated step titles.",
                "milestones",
                "Remove duplication or make each action meaningfully distinct.",
            )
        )

    kinds = {step.kind for step in flattened}
    for required_kind in ("practice", "prove"):
        if required_kind not in kinds:
            issues.append(
                issue(
                    f"missing_{required_kind}",
                    f"The roadmap has no {required_kind} step.",
                    "milestones",
                    f"Add a focused {required_kind} step tied to the desired outcome.",
                )
            )

    for index, step in enumerate(flattened):
        path = f"steps.{step.stable_key}"
        for prerequisite in step.prerequisite_step_keys:
            prerequisite_position = step_positions.get(prerequisite)
            if prerequisite_position is None:
                issues.append(
                    issue(
                        "unknown_prerequisite",
                        f"Prerequisite '{prerequisite}' does not identify a roadmap step.",
                        f"{path}.prerequisite_step_keys",
                        "Reference only stable keys that exist in this roadmap.",
                    )
                )
            elif prerequisite_position >= index:
                issues.append(
                    issue(
                        "forward_prerequisite",
                        f"Prerequisite '{prerequisite}' does not occur earlier in the roadmap.",
                        f"{path}.prerequisite_step_keys",
                        "Move the prerequisite earlier or correct the dependency.",
                    )
                )

        combined_text = " ".join(
            [step.title, step.objective, step.rationale, step.action, step.completion_condition]
        )
        if URL_PATTERN.search(combined_text):
            issues.append(
                issue(
                    "unverified_url",
                    "The model supplied a URL before resource verification.",
                    path,
                    "Remove URLs and provide resource search queries instead.",
                )
            )
        if SCHEDULE_PATTERN.search(combined_text):
            issues.append(
                issue(
                    "required_schedule",
                    "The step imposes a schedule or overdue framing.",
                    path,
                    "Describe sequence and approximate effort without a time commitment.",
                )
            )
        if WEAK_COMPLETION_PATTERN.search(step.completion_condition.strip()):
            issues.append(
                issue(
                    "weak_completion_condition",
                    "The completion condition describes an internal feeling instead of evidence.",
                    f"{path}.completion_condition",
                    "Require an observable explanation, result, artifact, or demonstration.",
                )
            )

    input_terms = meaningful_terms(generation_input.goal_title)
    personalized_text = f"{draft.title} {draft.summary} {draft.goal_outcome}".casefold()
    if input_terms and not any(term in personalized_text for term in input_terms):
        issues.append(
            issue(
                "weak_personalization",
                "The roadmap does not visibly connect to the user's stated goal.",
                "summary",
                "Rewrite the title, outcome, and summary around the user's actual goal.",
            )
        )

    context_terms = meaningful_terms(
        " ".join(
            [
                generation_input.current_level,
                generation_input.existing_experience,
                generation_input.relevant_constraints,
                generation_input.proof_of_completion,
                *(
                    answer.answer
                    for answer in generation_input.discovery_context
                    if not answer.skipped
                ),
            ]
        )
    )
    roadmap_text = " ".join(
        [
            draft.starting_state_summary,
            draft.strategy_summary,
            *(
                " ".join(
                    [
                        milestone.outcome,
                        milestone.rationale,
                        milestone.proof_target,
                        *(
                            " ".join(
                                [
                                    step.title,
                                    step.objective,
                                    step.action,
                                    step.completion_condition,
                                ]
                            )
                            for step in milestone.steps
                        ),
                    ]
                )
                for milestone in draft.milestones
            ),
        ]
    ).casefold()
    if context_terms and not any(term in roadmap_text for term in context_terms):
        issues.append(
            issue(
                "weak_context_personalization",
                "The roadmap does not visibly use the learner's starting experience, "
                "constraints, or proof target.",
                "starting_state_summary",
                "Make the starting state and at least one high-leverage learner-specific "
                "constraint, asset, or proof target shape the chosen actions and evidence.",
            )
        )

    curriculum = generation_input.curriculum
    if curriculum is not None:
        # A curriculum map is a coverage guardrail, not a request to reteach every topic.
        # Learners may satisfy a capability through advanced application when they already
        # have the foundation, but the accepted path must visibly address every capability.
        curriculum_text = " ".join(
            " ".join(
                [
                    milestone.title,
                    milestone.outcome,
                    milestone.rationale,
                    milestone.proof_target,
                    *(
                        " ".join(
                            [
                                step.title,
                                step.objective,
                                step.rationale,
                                step.action,
                                step.completion_condition,
                                step.evidence_suggestion,
                            ]
                        )
                        for step in milestone.steps
                    ),
                ]
            )
            for milestone in draft.milestones
        ).casefold()
        for phase in curriculum.phases:
            for capability in phase.capabilities:
                if any(term.casefold() in curriculum_text for term in capability.coverage_terms):
                    continue
                issues.append(
                    issue(
                        "missing_curriculum_capability",
                        f"The roadmap omits the essential capability '{capability.label}' "
                        f"from the {curriculum.title} backbone.",
                        "milestones",
                        "Add a learner-appropriate step or capability gate covering "
                        f"{capability.label}: {', '.join(capability.topics)}. It should lead "
                        f"to practical proof such as: {capability.proof}",
                    )
                )

    penalty = sum(14 if item.severity == "error" else 5 for item in issues)
    return max(0, 100 - penalty), issues


def combine_quality(
    structural_score: int,
    structural_issues: list[QualityIssue],
    critique: ProviderCritique,
    repair_attempts: int,
    threshold: int,
) -> QualityReport:
    issues = [*structural_issues, *critique.issues]
    final_score = round((structural_score * 0.55) + (critique.score * 0.45))
    passed = (
        structural_score >= threshold
        and critique.passed
        and final_score >= threshold
        and not any(item.severity == "error" for item in issues)
    )
    return QualityReport(
        passed=passed,
        final_score=final_score,
        structural_score=structural_score,
        critic_score=critique.score,
        repair_attempts=repair_attempts,
        issues=issues,
    )
