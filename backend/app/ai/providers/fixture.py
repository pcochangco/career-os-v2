from app.ai.providers.base import ProviderResult
from app.ai.schema import (
    ProviderCritique,
    QualityIssue,
    RoadmapDraft,
    RoadmapDraftMilestone,
    RoadmapDraftStep,
    RoadmapGenerationInput,
)


class FixtureRoadmapProvider:
    source = "fixture"
    model = "deterministic-fixture"
    prompt_version = "roadmap-schema-1.0-fixture-1"

    def generate(self, generation_input: RoadmapGenerationInput) -> ProviderResult[RoadmapDraft]:
        outcome = generation_input.desired_outcome.rstrip(". ")
        level = generation_input.current_level.rstrip(". ")
        proof = generation_input.proof_of_completion.rstrip(". ")
        goal_title = generation_input.goal_title
        draft = RoadmapDraft(
            schema_version="1.0",
            title=f"Your path to {goal_title}",
            summary=(
                f"A focused path from your current starting point ({level}) toward {outcome}. "
                "Each stage ends with observable evidence rather than time spent."
            ),
            goal_outcome=outcome,
            starting_state_summary=(
                f"Starting level: {level}. Relevant experience: "
                f"{generation_input.existing_experience.rstrip('. ')}."
            ),
            assumptions=[
                "The path can be completed without a fixed daily schedule.",
                "Practice can use tools and materials available to the learner.",
            ],
            milestones=[
                RoadmapDraftMilestone(
                    title="Set the foundation",
                    outcome="Define success and identify the essential foundations for the goal.",
                    rationale=(
                        "A clear target and honest baseline prevent unnecessary or missing work."
                    ),
                    steps=[
                        RoadmapDraftStep(
                            stable_key="define-success",
                            kind="learn",
                            title=f"Define success for {goal_title}",
                            objective=(
                                "Turn the goal into outcomes that can be recognized and reviewed."
                            ),
                            rationale="The rest of the roadmap needs an observable destination.",
                            action=(
                                f"Write a one-page success brief for this outcome: {outcome}. "
                                "List what you will explain, do, or produce."
                            ),
                            completion_condition=(
                                "A written success brief contains at least three observable "
                                "outcomes."
                            ),
                            effort_label="Short focused session",
                            evidence_suggestion="One-page success brief",
                            prerequisite_step_keys=[],
                            resource_queries=[f"{goal_title} competency framework beginner guide"],
                        ),
                        RoadmapDraftStep(
                            stable_key="map-foundations",
                            kind="practice",
                            title="Map the essential foundations",
                            objective=(
                                "Identify the smallest set of concepts or skills used by later "
                                "work."
                            ),
                            rationale=(
                                "An explicit foundation map reveals gaps without repeating "
                                "everything."
                            ),
                            action=(
                                "Create a map of five to seven essentials. Mark existing "
                                "confidence and "
                                "one concrete gap for every item."
                            ),
                            completion_condition=(
                                "The foundation map exists and every item has a confidence and "
                                "gap note."
                            ),
                            effort_label="Several focused sessions",
                            evidence_suggestion="Annotated foundation map",
                            prerequisite_step_keys=["define-success"],
                            resource_queries=[f"{goal_title} essential concepts roadmap"],
                        ),
                    ],
                ),
                RoadmapDraftMilestone(
                    title="Build working ability",
                    outcome=(
                        "Connect the foundations in a complete workflow and apply them "
                        "independently."
                    ),
                    rationale=(
                        "Guided understanding becomes useful only after deliberate application."
                    ),
                    steps=[
                        RoadmapDraftStep(
                            stable_key="learn-workflow",
                            kind="learn",
                            title="Learn one complete workflow",
                            objective="See how the essential pieces connect from start to finish.",
                            rationale=(
                                "A complete example supplies context before independent practice."
                            ),
                            action=(
                                "Follow one credible end-to-end introduction and reproduce the "
                                "workflow "
                                "with notes explaining every major decision."
                            ),
                            completion_condition=(
                                "A complete walkthrough exists with an explanation at every "
                                "major stage."
                            ),
                            effort_label="Several focused sessions",
                            evidence_suggestion="Reproduced walkthrough with personal notes",
                            prerequisite_step_keys=["map-foundations"],
                            resource_queries=[f"{goal_title} complete practical tutorial"],
                        ),
                        RoadmapDraftStep(
                            stable_key="guided-output",
                            kind="practice",
                            title="Complete a guided practice output",
                            objective="Use the workflow without copying the original example.",
                            rationale="A changed context tests whether the workflow is understood.",
                            action=(
                                f"Create a small practice output related to {goal_title}. Apply "
                                "the stated "
                                "access and learning constraints without imposing a schedule."
                            ),
                            completion_condition=(
                                "The output works and includes a reflection describing two "
                                "corrected gaps."
                            ),
                            effort_label="Several focused sessions",
                            evidence_suggestion="Working practice output and reflection",
                            prerequisite_step_keys=["learn-workflow"],
                            resource_queries=[f"{goal_title} practice project ideas"],
                        ),
                    ],
                ),
                RoadmapDraftMilestone(
                    title="Prove the outcome",
                    outcome="Produce and explain evidence that demonstrates the target capability.",
                    rationale="Independent proof turns learning into credible, reusable evidence.",
                    steps=[
                        RoadmapDraftStep(
                            stable_key="independent-output",
                            kind="prove",
                            title="Create an independent final output",
                            objective="Demonstrate the target ability with limited guidance.",
                            rationale=(
                                "Independent work exposes the remaining gaps and proves transfer."
                            ),
                            action=f"Plan and produce the evidence you chose: {proof}.",
                            completion_condition=(
                                "The final output is complete, accessible, and reviewable by "
                                "another person."
                            ),
                            effort_label="Multi-session project",
                            evidence_suggestion=proof,
                            prerequisite_step_keys=["guided-output"],
                            resource_queries=[f"{goal_title} capstone project rubric"],
                        ),
                        RoadmapDraftStep(
                            stable_key="package-learning",
                            kind="prove",
                            title="Review, explain, and package your learning",
                            objective=(
                                "Confirm understanding and make the result useful beyond CareerOS."
                            ),
                            rationale=(
                                "Clear explanation makes the work useful for interviews and "
                                "sharing."
                            ),
                            action=(
                                "Explain the approach, key decisions, strongest result, and "
                                "remaining gap. "
                                "Package the final output with a concise summary."
                            ),
                            completion_condition=(
                                "A clear summary and final evidence artifact are ready to share."
                            ),
                            effort_label="Short focused session",
                            evidence_suggestion="Shareable summary and evidence package",
                            prerequisite_step_keys=["independent-output"],
                            resource_queries=[f"how to present {goal_title} portfolio work"],
                        ),
                    ],
                ),
            ],
        )
        return ProviderResult(value=draft)

    def critique(
        self,
        generation_input: RoadmapGenerationInput,
        draft: RoadmapDraft,
    ) -> ProviderResult[ProviderCritique]:
        del generation_input, draft
        return ProviderResult(
            value=ProviderCritique(
                passed=True,
                score=100,
                summary="The deterministic fixture satisfies the canonical quality contract.",
                issues=[],
            )
        )

    def repair(
        self,
        generation_input: RoadmapGenerationInput,
        draft: RoadmapDraft,
        issues: list[QualityIssue],
    ) -> ProviderResult[RoadmapDraft]:
        del draft, issues
        return self.generate(generation_input)
