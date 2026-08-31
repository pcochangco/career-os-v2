from app.ai.providers.base import DiscoveryProvider, ProviderResult
from app.ai.schema import DiscoveryContextAnswer, DiscoveryOption, DiscoveryQuestionDraft

MAX_DISCOVERY_QUESTIONS = 6
MIN_DISCOVERY_QUESTIONS = 3


class DiscoveryValidationError(RuntimeError):
    """The provider returned a discovery turn that cannot safely be shown."""


class AdaptiveDiscoveryService:
    def __init__(self, provider: DiscoveryProvider) -> None:
        self.provider = provider

    def next_question(
        self,
        *,
        goal_title: str,
        answers: list[DiscoveryContextAnswer],
        used_question_keys: list[str],
    ) -> ProviderResult[DiscoveryQuestionDraft]:
        if len(answers) >= MAX_DISCOVERY_QUESTIONS:
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=True,
                    completion_reason="You have given enough detail to shape a focused roadmap.",
                )
            )

        result = self.provider.next_question(
            goal_title=goal_title,
            answers=answers,
            used_question_keys=used_question_keys,
        )
        question = result.value
        if question.is_complete:
            if len(answers) < MIN_DISCOVERY_QUESTIONS:
                raise DiscoveryValidationError(
                    "Discovery completed before enough context was gathered"
                )
            return result

        self._validate_question(question, used_question_keys)
        return result

    @staticmethod
    def _validate_question(
        question: DiscoveryQuestionDraft,
        used_question_keys: list[str],
    ) -> None:
        if not question.question_key or question.question_key in used_question_keys:
            raise DiscoveryValidationError("Discovery question key must be new and non-empty")
        if len(question.question.strip()) < 8 or len(question.help_text.strip()) < 8:
            raise DiscoveryValidationError(
                "Discovery question must include helpful learner-facing copy"
            )
        if len(question.options) < 3:
            raise DiscoveryValidationError(
                "Discovery question must include at least three answer options"
            )
        if len({option.key for option in question.options}) != len(question.options):
            raise DiscoveryValidationError("Discovery question options must have unique keys")
        if any(not option.label.strip() for option in question.options):
            raise DiscoveryValidationError("Discovery question options must have labels")


class FixtureDiscoveryProvider:
    """A deterministic local preview of adaptive discovery, never used in strict live mode."""

    def next_question(
        self,
        *,
        goal_title: str,
        answers: list[DiscoveryContextAnswer],
        used_question_keys: list[str],
    ) -> ProviderResult[DiscoveryQuestionDraft]:
        del goal_title, used_question_keys
        if not answers:
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=False,
                    question_key="focus-area",
                    question="Which part of this goal matters most to you right now?",
                    help_text="Choose the direction that would make the roadmap most useful.",
                    selection_mode="multiple",
                    options=[
                        DiscoveryOption(key="practical-project", label="Build a practical project"),
                        DiscoveryOption(key="career-change", label="Prepare for a career move"),
                        DiscoveryOption(key="deeper-expertise", label="Build deeper expertise"),
                        DiscoveryOption(
                            key="solve-current-work", label="Solve a current work problem"
                        ),
                    ],
                    placeholder="Describe the result you want in your own words…",
                )
            )
        if len(answers) == 1:
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=False,
                    question_key="starting-point",
                    question="What have you already tried or built that relates to this?",
                    help_text=(
                        "This keeps your roadmap from sending you back through familiar basics."
                    ),
                    selection_mode="multiple",
                    options=[
                        DiscoveryOption(key="work-experience", label="Used it at work"),
                        DiscoveryOption(key="personal-project", label="Built a personal project"),
                        DiscoveryOption(key="courses", label="Completed courses or tutorials"),
                        DiscoveryOption(key="starting-fresh", label="I am starting fresh"),
                    ],
                    placeholder="Add tools, projects, or experience…",
                )
            )
        if len(answers) == 2:
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=False,
                    question_key="biggest-gap",
                    question="What is the biggest thing holding you back?",
                    help_text="Pick the gap the roadmap should solve first.",
                    selection_mode="multiple",
                    options=[
                        DiscoveryOption(
                            key="know-what-to-learn", label="Knowing what to learn next"
                        ),
                        DiscoveryOption(key="real-practice", label="Getting real practice"),
                        DiscoveryOption(key="confidence", label="Confidence explaining my work"),
                        DiscoveryOption(key="proof", label="Creating strong proof of my skills"),
                    ],
                    placeholder="Describe another obstacle…",
                )
            )
        return ProviderResult(
            value=DiscoveryQuestionDraft(
                is_complete=True,
                completion_reason="You have shared enough to create a focused first roadmap.",
            )
        )
