import re

from app.ai.providers.base import DiscoveryProvider, ProviderResult
from app.ai.schema import (
    DiscoveryContextAnswer,
    DiscoveryOption,
    DiscoveryQuestionDraft,
    GoalIntentAssessment,
)

MAX_DISCOVERY_QUESTIONS = 6
MIN_DISCOVERY_QUESTIONS = 3

_QUESTION_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "do",
    "does",
    "for",
    "in",
    "is",
    "of",
    "or",
    "the",
    "to",
    "what",
    "which",
    "with",
    "you",
    "your",
}
_QUESTION_WORD_ALIASES = {
    "intended": "intend",
    "planning": "plan",
    "planned": "plan",
    "pursuing": "pursue",
    "targeting": "target",
}


def question_terms(question: str) -> set[str]:
    return {
        _QUESTION_WORD_ALIASES.get(word, word)
        for word in re.findall(r"[a-z0-9]+", question.lower())
        if word not in _QUESTION_STOP_WORDS
    }


def questions_are_similar(first: str, second: str) -> bool:
    first_terms = question_terms(first)
    second_terms = question_terms(second)
    overlap = first_terms & second_terms
    union = first_terms | second_terms
    return len(overlap) >= 3 and bool(union) and len(overlap) / len(union) >= 0.72


def deduplicate_context(
    answers: list[DiscoveryContextAnswer],
) -> list[DiscoveryContextAnswer]:
    unique: list[DiscoveryContextAnswer] = []
    for answer in answers:
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(unique)
                if questions_are_similar(existing.question, answer.question)
            ),
            None,
        )
        if duplicate_index is None:
            unique.append(answer)
            continue
        existing = unique[duplicate_index]
        if (existing.skipped and not answer.skipped) or (
            existing.skipped == answer.skipped and len(answer.answer) > len(existing.answer)
        ):
            unique[duplicate_index] = answer
    return unique


class DiscoveryValidationError(RuntimeError):
    """The provider returned a discovery turn that cannot safely be shown."""


class AdaptiveDiscoveryService:
    def __init__(self, provider: DiscoveryProvider) -> None:
        self.provider = provider

    def assess_goal(self, *, goal_title: str) -> ProviderResult[GoalIntentAssessment]:
        return self.provider.assess_goal(goal_title=goal_title)

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

        if any(questions_are_similar(question.question, answer.question) for answer in answers):
            if len(answers) >= MIN_DISCOVERY_QUESTIONS:
                return ProviderResult(
                    value=DiscoveryQuestionDraft(
                        is_complete=True,
                        completion_reason=(
                            "You have given enough detail to shape a focused roadmap."
                        ),
                    ),
                    response_id=result.response_id,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                )
            raise DiscoveryValidationError("Discovery question repeats an earlier topic")

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

    def assess_goal(self, *, goal_title: str) -> ProviderResult[GoalIntentAssessment]:
        normalized = " ".join(goal_title.split())
        words = re.findall(r"[a-z]+", normalized.lower())
        letters_only = "".join(words)
        keyboard_patterns = ("qwerty", "asdf", "zxcv", "poiuy", "lkjh")
        known_fixture_gibberish = {"havduwh", "wozzle"}
        vowels = sum(character in "aeiou" for character in letters_only)
        looks_invented = (
            not words
            or any(pattern in letters_only for pattern in keyboard_patterns)
            or any(word in known_fixture_gibberish for word in words)
            or bool(re.fullmatch(r"(.)\1{2,}", letters_only))
            or (len(letters_only) >= 6 and vowels == 0)
            or all(
                len(word) >= 6 and sum(character in "aeiou" for character in word) <= 1
                for word in words
            )
        )
        return ProviderResult(
            value=GoalIntentAssessment(
                is_meaningful=not looks_invented,
                normalized_title=normalized if not looks_invented else "",
                reason="meaningful" if not looks_invented else "nonsense",
            )
        )

    def next_question(
        self,
        *,
        goal_title: str,
        answers: list[DiscoveryContextAnswer],
        used_question_keys: list[str],
    ) -> ProviderResult[DiscoveryQuestionDraft]:
        del used_question_keys
        if not answers:
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=False,
                    question_key="focus-area",
                    question=(
                        f'For "{goal_title}", what would make the biggest difference right now?'
                    ),
                    help_text=(
                        "Choose the direction that would make this particular roadmap most useful."
                    ),
                    selection_mode="multiple",
                    options=[
                        DiscoveryOption(key="practical-project", label="Build a practical project"),
                        DiscoveryOption(key="career-change", label="Prepare for a career move"),
                        DiscoveryOption(key="deeper-expertise", label="Build deeper expertise"),
                        DiscoveryOption(
                            key="solve-current-work", label="Solve a current work problem"
                        ),
                    ],
                    placeholder=(
                        f'What would meaningful progress in "{goal_title}" look like to you?'
                    ),
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
