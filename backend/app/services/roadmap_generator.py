from dataclasses import dataclass

from app.api.schemas import DiscoveryWrite


@dataclass(frozen=True)
class FixtureStep:
    kind: str
    title: str
    objective: str
    action: str
    completion_condition: str
    effort_label: str


@dataclass(frozen=True)
class FixtureMilestone:
    title: str
    outcome: str
    steps: tuple[FixtureStep, ...]


@dataclass(frozen=True)
class FixtureRoadmap:
    title: str
    summary: str
    milestones: tuple[FixtureMilestone, ...]


def generate_fixture_roadmap(goal_title: str, discovery: DiscoveryWrite) -> FixtureRoadmap:
    outcome = discovery.desired_outcome.rstrip(". ")
    proof = discovery.proof_of_completion.rstrip(". ")
    level = discovery.current_level.rstrip(". ")

    return FixtureRoadmap(
        title=f"Your path to {goal_title}",
        summary=(
            f"A focused path from your current starting point ({level}) toward {outcome}. "
            "Each stage ends with something observable rather than time spent."
        ),
        milestones=(
            FixtureMilestone(
                title="Set the foundation",
                outcome=(
                    "Understand the target, the essential concepts, and your true starting point."
                ),
                steps=(
                    FixtureStep(
                        kind="learn",
                        title=f"Define what good looks like for {goal_title}",
                        objective=(
                            "Turn the goal into a concrete outcome you can recognize in practice."
                        ),
                        action=(
                            f"Write a one-page success brief for this outcome: {outcome}. "
                            "Include what "
                            "you will be able to explain, do, or produce."
                        ),
                        completion_condition=(
                            "A success brief exists with at least three observable outcomes."
                        ),
                        effort_label="Short focused session",
                    ),
                    FixtureStep(
                        kind="practice",
                        title="Map the essential foundations",
                        objective=(
                            "Identify the smallest set of concepts or skills that "
                            "everything else uses."
                        ),
                        action=(
                            "Create a foundation map with five to seven essentials. "
                            "Mark what you already "
                            f"know based on this experience: {discovery.existing_experience}."
                        ),
                        completion_condition=(
                            "The foundation map is written and every item has a confidence note."
                        ),
                        effort_label="One or two sessions",
                    ),
                ),
            ),
            FixtureMilestone(
                title="Build working ability",
                outcome="Apply the foundations repeatedly and correct the gaps that appear.",
                steps=(
                    FixtureStep(
                        kind="learn",
                        title="Learn one complete workflow",
                        objective="See how the essential pieces connect from start to finish.",
                        action=(
                            "Follow one credible end-to-end introduction and reproduce its key "
                            "workflow "
                            "in your own words or environment."
                        ),
                        completion_condition=(
                            "A complete walkthrough exists with your own notes at each stage."
                        ),
                        effort_label="A few focused sessions",
                    ),
                    FixtureStep(
                        kind="practice",
                        title="Complete a guided practice output",
                        objective="Use the workflow without merely copying the example.",
                        action=(
                            f"Create a small practice output related to {goal_title}. "
                            "Respect this context: "
                            f"{discovery.relevant_constraints}."
                        ),
                        completion_condition=(
                            "The practice output works and includes a short reflection on two gaps."
                        ),
                        effort_label="Several sessions",
                    ),
                ),
            ),
            FixtureMilestone(
                title="Prove the outcome",
                outcome=(
                    "Produce convincing evidence that the goal has moved from intention to ability."
                ),
                steps=(
                    FixtureStep(
                        kind="prove",
                        title="Create an independent final output",
                        objective="Demonstrate the target ability with limited guidance.",
                        action=f"Plan and produce the evidence you chose: {proof}.",
                        completion_condition=(
                            "The final output is complete, accessible, and can be reviewed "
                            "by another "
                            "person."
                        ),
                        effort_label="Multi-session project",
                    ),
                    FixtureStep(
                        kind="prove",
                        title="Review, explain, and package your learning",
                        objective=(
                            "Confirm understanding and make the result useful beyond the app."
                        ),
                        action=(
                            "Explain your approach, decisions, strongest result, and "
                            "remaining gap. "
                            "Package "
                            "the final output with a concise summary."
                        ),
                        completion_condition=(
                            "A clear summary and final evidence link or artifact are ready "
                            "to share."
                        ),
                        effort_label="One focused session",
                    ),
                ),
            ),
        ),
    )
