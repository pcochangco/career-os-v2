import logging
import re

from app.ai.providers.base import DiscoveryProvider, ProviderResult, RoadmapProviderError
from app.ai.providers.fixture import domain_of
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


logger = logging.getLogger(__name__)


class FallbackDiscoveryService:
    """Live discovery first; if the AI call fails (retired model, outage, rate limit), use the
    built-in goal check and questions so creating a goal never fails because of the AI."""

    def __init__(self, primary: AdaptiveDiscoveryService, fallback: AdaptiveDiscoveryService):
        self.primary = primary
        self.fallback = fallback
        self.provider = primary.provider

    def assess_goal(self, *, goal_title: str) -> ProviderResult[GoalIntentAssessment]:
        try:
            return self.primary.assess_goal(goal_title=goal_title)
        except RoadmapProviderError as error:
            self._log("assess_goal", error)
            return self.fallback.assess_goal(goal_title=goal_title)

    def next_question(self, **kwargs) -> ProviderResult[DiscoveryQuestionDraft]:
        try:
            return self.primary.next_question(**kwargs)
        except (RoadmapProviderError, DiscoveryValidationError) as error:
            self._log("next_question", error)
            return self.fallback.next_question(**kwargs)

    @staticmethod
    def _log(operation: str, error: Exception) -> None:
        logger.warning(
            "Live discovery failed; using built-in fallback operation=%s failure_code=%s",
            operation,
            getattr(error, "diagnostic_code", type(error).__name__),
        )


class FixtureDiscoveryProvider:
    """A deterministic local preview of adaptive discovery, never used in strict live mode."""

    source = "fixture"
    model = "deterministic-fixture"

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
        if len(answers) >= len(FALLBACK_QUESTIONS):
            return ProviderResult(
                value=DiscoveryQuestionDraft(
                    is_complete=True,
                    completion_reason="You have shared enough to create a focused first roadmap.",
                )
            )
        key, question, help_text, placeholder = FALLBACK_QUESTIONS[len(answers)]
        labels = FALLBACK_OPTIONS[domain_of(goal_title)][key]
        return ProviderResult(
            value=DiscoveryQuestionDraft(
                is_complete=False,
                question_key=key,
                question=question.format(goal=goal_title),
                help_text=help_text,
                selection_mode="multiple",
                options=[DiscoveryOption(key=option_key(label), label=label) for label in labels],
                placeholder=placeholder.format(goal=goal_title),
            )
        )


def option_key(label: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", label.casefold()))


# (key, question, help text, placeholder) for the fixed fallback questions, asked in order.
FALLBACK_QUESTIONS = [
    (
        "focus-area",
        'For "{goal}", what would make the biggest difference right now?',
        "Choose the direction that would make this particular roadmap most useful.",
        'What would meaningful progress in "{goal}" look like to you?',
    ),
    (
        "starting-point",
        "What have you already tried or done that relates to this?",
        "This keeps your roadmap from sending you back through familiar basics.",
        "Add what you have tried, made or learned…",
    ),
    (
        "biggest-gap",
        "What is the biggest thing holding you back?",
        "Pick the gap the roadmap should solve first.",
        "Describe another obstacle…",
    ),
]

# Answer options per goal topic. Each starting-point list has a beginner and an experienced
# option worded so the fallback roadmap can read the learner's level from them.
FALLBACK_OPTIONS: dict[str, dict[str, list[str]]] = {
    "technical": {
        "focus-area": [
            "Build a practical project",
            "Prepare for a career move",
            "Build deeper expertise",
            "Solve a current work problem",
        ],
        "starting-point": [
            "Used it at work",
            "Built a personal project",
            "Completed courses or tutorials",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Knowing what to learn next",
            "Getting real practice",
            "Confidence explaining my work",
            "Creating strong proof of my skills",
        ],
    },
    "language": {
        "focus-area": [
            "Hold everyday conversations",
            "Travel or move abroad",
            "Use it at work",
            "Pass an exam or certificate",
        ],
        "starting-point": [
            "Took classes or used an app",
            "Can get by in simple conversations",
            "Used it at work",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Speaking without freezing",
            "Understanding native speakers",
            "Vocabulary and grammar",
            "Practising regularly",
        ],
    },
    "business": {
        "focus-area": [
            "Test whether the idea works",
            "Win my first customers",
            "Grow sales",
            "Run things more smoothly",
        ],
        "starting-point": [
            "Researched or planned it",
            "Sold things on the side",
            "Worked in this industry for years",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Knowing where to start",
            "Finding customers",
            "Money and pricing",
            "Time to work on it",
        ],
    },
    "fitness": {
        "focus-area": [
            "Finish an event or race",
            "Build a regular habit",
            "Get stronger or faster",
            "Feel healthier day to day",
        ],
        "starting-point": [
            "Exercise now and then",
            "Done an event like this before",
            "Trained regularly for years",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Staying consistent",
            "Knowing what to do each session",
            "Avoiding injury",
            "Finding the time",
        ],
    },
    "creative": {
        "focus-area": [
            "Learn the fundamentals",
            "Finish a piece I'm proud of",
            "Find my own style",
            "Share or sell my work",
        ],
        "starting-point": [
            "Followed tutorials or classes",
            "Made pieces on my own",
            "Practised it for years",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Knowing what to practise",
            "Finishing what I start",
            "Confidence in my work",
            "Finding the time",
        ],
    },
    "exams": {
        "focus-area": [
            "Pass on the first try",
            "Reach a target score",
            "Retake and do better",
            "Study efficiently around work",
        ],
        "starting-point": [
            "Looked at the syllabus",
            "Taken a practice test",
            "Studied this subject for years",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Knowing what to study",
            "Remembering what I learn",
            "Running out of time in the exam",
            "Staying consistent",
        ],
    },
    "cooking": {
        "focus-area": [
            "Cook everyday meals",
            "Master a dish or cuisine",
            "Cook for friends or family",
            "Eat healthier",
        ],
        "starting-point": [
            "Can follow a simple recipe",
            "Cook a few dishes regularly",
            "Cooked for years",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Knowing what to cook",
            "Basic techniques",
            "Getting a whole meal ready together",
            "Finding the time",
        ],
    },
    "games": {
        "focus-area": [
            "Reach a rating or level",
            "Beat the people I play with",
            "Play in a tournament",
            "Understand the game deeply",
        ],
        "starting-point": [
            "Know the rules",
            "Play casually now and then",
            "Played competitively for years",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Spotting patterns and tactics",
            "Planning ahead",
            "Learning from my games",
            "Staying focused in long games",
        ],
    },
    # Anything else, including leadership goals.
    "general": {
        "focus-area": [
            "Learn the basics properly",
            "Work on a real project",
            "Go deeper than I am now",
            "Use it in my job or studies",
        ],
        "starting-point": [
            "Read or watched tutorials",
            "Tried it a few times",
            "Done it for years",
            "I am starting fresh",
        ],
        "biggest-gap": [
            "Knowing what to learn next",
            "Getting real practice",
            "Staying consistent",
            "Finding the time",
        ],
    },
}
