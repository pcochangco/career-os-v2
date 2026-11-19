import re

from app.ai.providers.base import ProviderResult
from app.ai.schema import (
    ADAPTIVE_INSTRUCTION_PREFIX,
    DiscoveryContextAnswer,
    ProviderCritique,
    QualityIssue,
    RoadmapDraft,
    RoadmapDraftMilestone,
    RoadmapDraftStep,
    RoadmapGenerationInput,
    RoadmapPracticeTask,
)

# Checked in order; whole words only, so "ai" never matches "paint" and "api" never "capital".
DOMAIN_PATTERNS: list[tuple[str, str]] = [
    (
        "language",
        r"\b(spanish|language|english|french|japanese|german|korean|mandarin|chinese|italian|"
        r"portuguese|tagalog|speaking|conversational|fluent|fluency)\b",
    ),
    (
        "business",
        r"\b(business|coffee|shop|store|bakery|sales|customers?|clients?|startup|entrepreneur\w*|"
        r"marketing|revenue|freelanc\w*|side hustle)\b",
    ),
    # Leadership goals need the general roadmap, even in technical fields.
    ("general", r"\b(manager|management|leader\w*|lead a team|promot\w*|executive|ceo)\b"),
    (
        "fitness",
        r"\b(marathon|half-marathon|5k|10k|running|runner|jog\w*|fitness|workouts?|gym|"
        r"strength|weight ?lifting|lose weight|weight loss|triathlon|cycling|swim\w*|yoga|"
        r"pilates|push-?ups?|pull-?ups?)\b",
    ),
    (
        "technical",
        r"\b(engineer|developer|programming|programmer|coding|code|software|python|javascript|"
        r"sql|machine learning|data science|data engineer\w*|ai|api|devops|cloud)\b",
    ),
    (
        "creative",
        r"\b(paint\w*|watercolou?rs?|draw\w*|sketch\w*|illustrat\w*|art|artist|music\w*|guitar|"
        r"piano|violin|drums?|sing\w*|songs?|songwriting|photograph\w*|novel|poe\w+|writ\w*|"
        r"film\w*|animation|pottery|ceramics|knit\w*|crochet)\b",
    ),
]


# Adaptive discovery picks its own question keys, so answers are recognised by meaning.
PROOF_QUESTION = r"\b(proof|prove|show|evidence|success|look like|count as|finish line)\b"
TIME_QUESTION = r"\b(time|hours?|minutes?|schedule|how often|per week|available|commit)\b"
TIME_ANSWER = (
    r"\b(\d+\s*(min|mins|minutes|hours?|hrs?)|weekends?|evenings?|mornings?|commute|"
    r"daily|every day|per week|a week|days a week|lunch breaks?)\b"
)
LEVEL_QUESTION = (
    r"\b(already|experience|tried|built|starting|level|background|familiar|done before)\b"
)
BEGINNER_ANSWER = (
    r"\b(beginner|starting fresh|new to|never|no experience|just starting|from scratch)\b"
)
EXPERIENCED_ANSWER = (
    r"\b(\d+\+? years?|years of|professional(ly)?|at work|advanced|senior|experienced|"
    r"shipped|built a)\b"
)


def read_answers(context: list[DiscoveryContextAnswer]) -> dict[str, str]:
    """Pick out the starting level, available time and wanted proof from free-form answers.

    Returns "level" ("beginner", "experienced" or ""), "experience", "schedule" and "proof";
    each is "" when no answer clearly says it.
    """
    found = {"level": "", "experience": "", "schedule": "", "proof": ""}
    for item in context:
        answer = item.answer.strip().rstrip(". ")
        if item.skipped or not answer:
            continue
        question, text = item.question.casefold(), answer.casefold()
        if not found["proof"] and re.search(PROOF_QUESTION, question):
            found["proof"] = answer
        elif not found["schedule"] and (
            re.search(TIME_QUESTION, question) or re.search(TIME_ANSWER, text)
        ):
            found["schedule"] = answer
        elif not found["experience"] and re.search(LEVEL_QUESTION, question):
            found["experience"] = answer
            if re.search(BEGINNER_ANSWER, text):
                found["level"] = "beginner"
            elif re.search(EXPERIENCED_ANSWER, text):
                found["level"] = "experienced"
    return found


def mid_sentence_label(label: str) -> str:
    """'Data tooling' -> 'data tooling', but keep acronyms: 'SQL and modeling' stays."""
    return label if label[1:2].isupper() else label[:1].lower() + label[1:]


class FixtureRoadmapProvider:
    source = "fixture"
    model = "deterministic-fixture"
    prompt_version = "roadmap-schema-1.0-fixture-1"

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        """Shorten text to ``limit`` characters at a word boundary, marking the cut."""
        if len(text) <= limit:
            return text
        cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
        return f"{cut}…"

    @staticmethod
    def _mid_sentence(goal_title: str) -> str:
        """Lower-case a goal's first letter for use mid-sentence, keeping acronyms intact."""
        title = goal_title.strip().rstrip(". ")
        if len(title) > 1 and title[0].isupper() and not title[1].isupper():
            return title[0].lower() + title[1:]
        return title

    @staticmethod
    def _learner_facts(generation_input: RoadmapGenerationInput) -> dict[str, str]:
        """Return learner-facing wording for the deterministic draft.

        Adaptive discovery passes model instructions (``ADAPTIVE_INSTRUCTION_PREFIX``) in the
        structured fields and the learner's real answers in ``discovery_context``. Those
        instructions must never be shown to the learner, so the fallback builds its copy from
        the answers instead.
        """
        goal_title = FixtureRoadmapProvider._mid_sentence(generation_input.goal_title)
        if not generation_input.current_level.startswith(ADAPTIVE_INSTRUCTION_PREFIX):
            level = generation_input.current_level.rstrip(". ")
            experience = generation_input.existing_experience.rstrip(". ")
            outcome = generation_input.desired_outcome.rstrip(". ")
            return {
                "outcome": outcome,
                "proof": generation_input.proof_of_completion.rstrip(". "),
                "experience": experience,
                "constraints": generation_input.relevant_constraints.rstrip(". "),
                "summary_lead": (
                    f"A focused path from your current starting point ({level}) toward {outcome}."
                ),
                "starting_state": f"Starting level: {level}. Relevant experience: {experience}.",
            }

        # Answers can be up to 1,200 characters each; clip them so the composed copy always
        # fits the draft's field limits (starting state 1,000, step action 1,600).
        title = generation_input.goal_title.strip().rstrip(". ")
        answers = [
            FixtureRoadmapProvider._clip(answer.answer.strip().rstrip(". "), 160)
            for answer in generation_input.discovery_context
            if not answer.skipped and answer.answer.strip()
        ]
        shared = read_answers(generation_input.discovery_context)
        clip = FixtureRoadmapProvider._clip
        if answers:
            summary_lead = f"A focused roadmap for “{title}”, shaped by what you shared."
            if shared["level"] == "experienced":
                summary_lead += " The first steps are a quick review, since you have experience."
            elif shared["level"] == "beginner":
                summary_lead += " It starts from the basics."
            starting_state = f"What you shared: {'; '.join(answers[:3])}."
            experience = (
                "anything you've picked up so far"
                if shared["level"] == "beginner"
                else clip(shared["experience"], 160) or "; ".join(answers[:2])
            )
        else:
            summary_lead = f"A focused roadmap for “{title}”."
            starting_state = (
                "You skipped the starting questions, so this roadmap begins with the foundations. "
                "Note anything you already know in each step's learning record."
            )
            experience = "what you already know"
        return {
            # goal_outcome needs at least 12 characters; short goals ("Become CEO") get a frame.
            "outcome": title if len(title) >= 12 else f"Reach this goal: {title}",
            "proof": clip(shared["proof"], 160) if answers and shared["proof"] else (
                f"a concrete piece of work that shows real progress toward {goal_title}"
            ),
            "experience": experience,
            "constraints": (clip(shared["schedule"], 160) if answers else "")
            or "the time, tools, and preferences you have right now",
            "schedule": clip(shared["schedule"], 160) if answers else "",
            "level": shared["level"] if answers else "",
            "summary_lead": summary_lead,
            "starting_state": starting_state,
        }

    def generate(self, generation_input: RoadmapGenerationInput) -> ProviderResult[RoadmapDraft]:
        facts = self._learner_facts(generation_input)
        outcome = facts["outcome"]
        proof = facts["proof"]
        goal_title = generation_input.goal_title
        domain = self._domain(goal_title)
        steps = self._steps(
            domain=domain,
            goal_title=goal_title,
            outcome=outcome,
            proof=proof,
            existing_experience=facts["experience"],
            constraints=facts["constraints"],
        )
        if facts.get("level") == "experienced":
            steps = [
                step.model_copy(update={"effort_label": "Quick review"}) if index < 3 else step
                for index, step in enumerate(steps)
            ]
        foundation_title, foundation_outcome, workflow_title, workflow_outcome, proof_title = {
            "language": (
                "Build usable language foundations",
                "Understand and use the vocabulary, grammar, and listening patterns needed for "
                "real situations.",
                "Use the language in real situations",
                "Hold increasingly independent conversations and handle practical communication "
                "tasks.",
                "Demonstrate real communication",
            ),
            "business": (
                "Clarify the offer and customer",
                "Define a focused offer, customer need, and simple way to test demand.",
                "Run and improve the operating loop",
                "Serve customers, track what works, and improve the next decision using real "
                "evidence.",
                "Prove a repeatable result",
            ),
            "technical": (
                "Build on the right technical base",
                "Identify the tools, concepts, and existing strengths needed for a real "
                "implementation.",
                "Build and test a working system",
                "Create a usable implementation and improve it through deliberate testing.",
                "Demonstrate an engineering outcome",
            ),
            "creative": (
                "Build your creative foundations",
                "Know what you want to make and the techniques it takes.",
                "Make work regularly",
                "Turn techniques into finished pieces, with less guidance each time.",
                "Finish and share your work",
            ),
            "fitness": (
                "Set a safe starting point",
                "Know your baseline, your target, and a routine your body can keep up with.",
                "Train consistently",
                "Build fitness week by week and adjust based on how training actually goes.",
                "Reach the target",
            ),
            "general": (
                "Set the foundation",
                "Define success and identify the essential foundations for the goal.",
                "Build working ability",
                "Connect the foundations in a complete workflow and apply them independently.",
                "Prove the outcome",
            ),
        }[domain]
        draft = RoadmapDraft(
            schema_version="1.2",
            title=f"Your roadmap to {self._mid_sentence(goal_title)}",
            summary=(
                f"{facts['summary_lead']} "
                "Each milestone ends with observable evidence rather than time spent."
            ),
            strategy_summary=(
                "Build only the capabilities that close the gap between what you can already do "
                "and the evidence required for this outcome. Each milestone turns learning into a "
                "visible artifact before you move on."
            ),
            suggested_rhythm=[
                *(
                    [f"Fit the work into the time you have: {facts['schedule']}."]
                    if facts.get("schedule")
                    else []
                ),
                "Use learning sessions to unlock the next concrete build or practice task.",
                "Return to the current step until its completion condition has real evidence.",
                "After each milestone, keep your strongest work and explain what it proves.",
            ],
            practice_tasks=self._practice_tasks(domain=domain, steps=steps),
            goal_outcome=outcome,
            starting_state_summary=facts["starting_state"],
            assumptions=[
                "You can follow this roadmap without a fixed daily schedule.",
                "Practice can use the tools and materials you already have.",
            ],
            milestones=[
                self._milestone(
                    position=1,
                    title=foundation_title,
                    outcome=foundation_outcome,
                    rationale=(
                        "A clear target and honest baseline prevent unnecessary or missing work."
                    ),
                    steps=steps[:3],
                ),
                self._milestone(
                    position=2,
                    title=workflow_title,
                    outcome=workflow_outcome,
                    rationale=(
                        "Guided understanding becomes useful only after deliberate application."
                    ),
                    steps=steps[3:7],
                ),
                self._milestone(
                    position=3,
                    title=proof_title,
                    outcome="Produce and explain evidence that demonstrates the target capability.",
                    rationale="Independent proof turns learning into credible, reusable evidence.",
                    steps=steps[7:],
                ),
            ],
        )
        if generation_input.curriculum is not None:
            curriculum_steps_by_phase = self._curriculum_steps_by_phase(generation_input)
            curriculum_steps = [
                step for phase_steps in curriculum_steps_by_phase for step in phase_steps
            ]
            draft.practice_tasks = self._practice_tasks(domain="technical", steps=curriculum_steps)
            self._apply_curriculum_backbone(
                draft,
                generation_input.curriculum,
                curriculum_steps_by_phase,
            )
        return ProviderResult(value=draft)

    @classmethod
    def _apply_curriculum_backbone(cls, draft: RoadmapDraft, curriculum, steps_by_phase) -> None:
        """Present deterministic maps as capability-specific, end-to-end roadmaps."""
        milestones: list[RoadmapDraftMilestone] = []
        for position, (phase, phase_steps) in enumerate(
            zip(curriculum.phases, steps_by_phase, strict=True), start=1
        ):
            milestones.append(
                cls._milestone(
                    position=position,
                    title=phase.title,
                    outcome=phase.outcome,
                    rationale=(
                        "This capability gate follows the CareerOS curriculum backbone while "
                        "adapting the work to the learner's stated goal and experience."
                    ),
                    steps=phase_steps,
                )
            )
        draft.milestones = milestones

    @staticmethod
    def _curriculum_steps_by_phase(
        generation_input: RoadmapGenerationInput,
    ) -> list[list[RoadmapDraftStep]]:
        """Expand each curriculum capability into an applied step and proof step.

        This keeps the offline fallback useful when live generation is unavailable and
        gives tests a realistic baseline: a curriculum map is not merely relabelled
        generic content.
        """
        curriculum = generation_input.curriculum
        assert curriculum is not None
        steps_by_phase: list[list[RoadmapDraftStep]] = []
        previous_key: str | None = None
        capability_index = 0
        for phase in curriculum.phases:
            phase_steps: list[RoadmapDraftStep] = []
            for capability in phase.capabilities:
                capability_key = capability.key
                study_key = f"{capability_key}-apply"
                topics = ", ".join(capability.topics)
                apply_step = RoadmapDraftStep(
                    stable_key=study_key,
                    kind="learn",
                    title=f"Learn {mid_sentence_label(capability.label)}",
                    objective=(
                        f"Use {topics} in the context of {generation_input.goal_title}, building "
                        "on demonstrated experience instead of repeating basic theory."
                    ),
                    rationale=(
                        f"{capability.label} is a necessary bridge to the learner's stated outcome."
                    ),
                    action=(
                        f"Choose one realistic part of your target system and implement or analyze "
                        f"it through {capability.label.lower()}. Record the design decision, one "
                        "failure mode, and the check that would catch it."
                    ),
                    completion_condition=(
                        f"A reviewable artifact explains how {topics} was applied to one concrete "
                        "part of the target system."
                    ),
                    effort_label="Several focused sessions",
                    evidence_suggestion=f"Applied {capability.label} design note or implementation",
                    prerequisite_step_keys=(
                        [
                            f"{prerequisite}-evidence"
                            for prerequisite in capability.prerequisite_capability_keys
                        ]
                        or ([previous_key] if previous_key else [])
                    ),
                    resource_queries=[
                        f"{generation_input.goal_title} {capability.label} practical tutorial"
                    ],
                )
                proof_key = f"{capability_key}-evidence"
                proof_kind = "prove" if capability_index % 2 else "practice"
                proof_step = RoadmapDraftStep(
                    stable_key=proof_key,
                    kind=proof_kind,
                    title=f"Put {mid_sentence_label(capability.label)} to the test",
                    objective=(
                        f"Turn the {capability.label.lower()} work into evidence another engineer "
                        "could inspect, test, or review."
                    ),
                    rationale="A capability is credible only when it survives a practical check.",
                    action=(
                        f"Run a changed scenario, test, review, or comparison for the artifact. "
                        f"Use this proof target as the standard: {capability.proof}"
                    ),
                    completion_condition=(
                        f"The evidence shows the result, one limitation or trade-off, and why it "
                        f"supports {capability.label.lower()}."
                    ),
                    effort_label="Several focused sessions",
                    evidence_suggestion=capability.proof,
                    prerequisite_step_keys=[study_key],
                    resource_queries=[
                        f"{generation_input.goal_title} {capability.label} testing case study"
                    ],
                )
                phase_steps.extend([apply_step, proof_step])
                previous_key = proof_key
                capability_index += 1
            steps_by_phase.append(phase_steps)
        return steps_by_phase

    @staticmethod
    def _practice_tasks(*, domain: str, steps: list[RoadmapDraftStep]) -> list[RoadmapPracticeTask]:
        domain_prompts = {
            "technical": [
                (
                    "Solve one focused implementation problem",
                    "Choose a small problem related to the current capability and write a "
                    "working solution with one edge-case check.",
                    "Keep the solution and note the trade-off you made.",
                ),
                (
                    "Explain one design decision",
                    "Sketch the inputs, outputs, and failure cases for a small part of your "
                    "current build before changing code.",
                    "Save a short design note or diagram.",
                ),
            ],
            "language": [
                (
                    "Use the language in context",
                    "Write or say a short response about a real situation using the vocabulary "
                    "from your current step.",
                    "Keep the response and mark one phrase to improve.",
                ),
                (
                    "Practice comprehension",
                    "Use one short authentic clip or text and capture the main idea plus two "
                    "useful expressions.",
                    "Record the summary and expressions.",
                ),
            ],
            "business": [
                (
                    "Test one customer assumption",
                    "Write one precise question that would test an assumption in your current "
                    "offer or workflow.",
                    "Save the question and the evidence you would look for.",
                ),
                (
                    "Improve one decision",
                    "Review one small customer or operating signal and write the next decision "
                    "it supports.",
                    "Record the signal and decision in one note.",
                ),
            ],
            "creative": [
                (
                    "Make a ten-minute sketch",
                    "Make a quick, rough piece using the technique from your current step. "
                    "Don't fix anything; just finish it.",
                    "Keep the piece, however rough.",
                ),
                (
                    "Study one detail",
                    "Look closely at one piece you admire and copy a single small detail.",
                    "Save the copy and one line on what you noticed.",
                ),
            ],
            "fitness": [
                (
                    "Do an easy movement session",
                    "Do 15 to 20 minutes of easy movement related to your goal at a pace where "
                    "you could still talk.",
                    "Log the time and how it felt.",
                ),
                (
                    "Practise form for five minutes",
                    "Spend five minutes on the form or warm-up from your current step.",
                    "Note one thing that improved.",
                ),
            ],
            "general": [
                (
                    "Rehearse the current capability",
                    "Take one small piece of the current roadmap step and perform it without "
                    "following a tutorial.",
                    "Keep a short artifact or note showing what you did.",
                ),
                (
                    "Explain your current learning",
                    "Teach back one key idea from the current phase in plain language.",
                    "Save the explanation and one remaining question.",
                ),
            ],
        }[domain]
        step_prompts = [
            (
                f"Start small: {step.title}",
                f"Choose one contained part of this step: {step.objective}",
                f"Leave evidence that moves this step forward: {step.evidence_suggestion}",
            )
            for step in steps[:3]
        ]
        prompts = [*domain_prompts, *step_prompts]
        return [
            RoadmapPracticeTask(
                title=FixtureRoadmapProvider._clip(title, 160),
                instruction=FixtureRoadmapProvider._clip(instruction, 500),
                completion_signal=FixtureRoadmapProvider._clip(signal, 300),
            )
            for title, instruction, signal in prompts[:5]
        ]

    @staticmethod
    def _milestone(
        *,
        position: int,
        title: str,
        outcome: str,
        rationale: str,
        steps: list[RoadmapDraftStep],
    ) -> RoadmapDraftMilestone:
        focus_areas = [step.title for step in steps[:3]]
        final_step = steps[-1]
        return RoadmapDraftMilestone(
            title=title,
            outcome=outcome,
            rationale=rationale,
            focus_areas=focus_areas if len(focus_areas) > 1 else [title, final_step.objective],
            proof_target=(
                f"Phase {position} proof: {final_step.evidence_suggestion.rstrip('. ')}."
            ),
            success_signal=final_step.completion_condition,
            steps=steps,
        )

    @staticmethod
    def _domain(goal_title: str) -> str:
        text = goal_title.casefold()
        for domain, pattern in DOMAIN_PATTERNS:
            if re.search(pattern, text):
                return domain
        return "general"

    @staticmethod
    def _steps(
        *,
        domain: str,
        goal_title: str,
        outcome: str,
        proof: str,
        existing_experience: str,
        constraints: str,
    ) -> list[RoadmapDraftStep]:
        templates = {
            "language": [
                (
                    "Define the conversations you want to handle",
                    "Turn the language goal into specific situations and observable communication.",
                    "A real conversation target keeps vocabulary and grammar work relevant.",
                    "List three situations where you want to use the language. For each one, "
                    "write what you need to understand, say, and accomplish.",
                    "Three conversation scenarios each include an intended result and observable "
                    "speaking or listening behavior.",
                    "Conversation target brief",
                    f"{goal_title} conversational ability framework",
                ),
                (
                    "Map the language needed for those situations",
                    "Identify the phrases, vocabulary, grammar, and listening patterns that unlock "
                    "the target conversations.",
                    "A focused language map prevents broad study that never reaches real use.",
                    f"Build a five-to-seven-part language map for the target situations. Mark what "
                    f"your current experience already covers ({existing_experience}) and one gap "
                    "for each remaining part.",
                    "The language map covers phrases, vocabulary, grammar, and listening, with "
                    "each "
                    "item marked as known or needing practice.",
                    "Annotated language map",
                    f"{goal_title} essential phrases grammar listening guide",
                ),
                (
                    "Study and shadow one complete conversation",
                    "Connect listening, meaning, pronunciation, and response choices in context.",
                    "A complete exchange shows how isolated language pieces work together.",
                    "Use one credible dialogue with audio or a transcript. Annotate each turn, "
                    "then "
                    "shadow or reproduce it while explaining why each response fits.",
                    "An annotated dialogue and a recorded or written reproduction cover every turn "
                    "without copying unexplained lines.",
                    "Annotated dialogue and reproduction",
                    f"{goal_title} practical dialogue audio transcript",
                ),
                (
                    "Complete a guided role-play",
                    "Use the target language in a changed situation rather than reciting an "
                    "example.",
                    "A varied scenario tests whether the language can transfer to real use.",
                    f"Run a role-play based on one target situation, changing at least two "
                    "details. "
                    f"Work within this preference or constraint: {constraints}. Record or "
                    "transcribe "
                    "the exchange, then correct two unclear moments.",
                    "The role-play reaches its practical result and includes two explained "
                    "corrections.",
                    "Role-play recording or transcript with corrections",
                    f"{goal_title} guided speaking role play prompts",
                ),
                (
                    "Hold an independent practical conversation",
                    "Demonstrate useful communication with limited preparation or prompting.",
                    "Independent conversation proves transfer beyond rehearsed material.",
                    "Plan and complete the chosen evidence in a realistic target situation: "
                    f"{proof}.",
                    "The conversation evidence is complete, reviewable, and shows whether the "
                    "intended practical result was reached.",
                    proof,
                    f"{goal_title} conversation proficiency rubric",
                ),
                (
                    "Review and package your communication evidence",
                    "Explain what you can now handle and identify the most important remaining "
                    "gap.",
                    "A concise review turns practice into credible proof and a clear continuation "
                    "point.",
                    "Select the strongest conversation evidence. Add a short explanation of the "
                    "situation, what worked, one corrected mistake, and the next communication "
                    "gap.",
                    "A shareable evidence package includes the conversation, context, correction, "
                    "and next gap.",
                    "Shareable communication evidence package",
                    f"how to assess and present {goal_title} speaking progress",
                ),
            ],
            "business": [
                (
                    "Define the offer and target customer",
                    "Connect the business goal to one customer need and a testable offer.",
                    "A focused offer makes customer feedback and operating decisions meaningful.",
                    f"Write a one-page offer brief for this outcome: {outcome}. Name the customer, "
                    "their need, the offer, the buying reason, and the result you will measure.",
                    "The offer brief identifies one customer, one need, one offer, and one "
                    "measurable "
                    "result.",
                    "Customer and offer brief",
                    f"{goal_title} customer value proposition examples",
                ),
                (
                    "Map the smallest repeatable operating loop",
                    "Identify how the offer moves from preparation through sale, delivery, and "
                    "feedback.",
                    "A visible operating loop reveals the few constraints that affect "
                    "repeatability.",
                    "Map five to seven stages from preparing the offer to collecting feedback. "
                    "Mark "
                    f"what your existing experience covers ({existing_experience}) and one risk or "
                    "unknown at every stage.",
                    "The operating map covers preparation, customer acquisition, sale, delivery, "
                    "and "
                    "feedback, with an owner or risk note for each stage.",
                    "Annotated operating-loop map",
                    f"{goal_title} small business operating process checklist",
                ),
                (
                    "Study one complete customer cycle",
                    "See how a comparable small offer moves from customer need to fulfilled order.",
                    "A complete example provides useful decisions to test without copying a "
                    "business.",
                    "Analyze one credible example from offer through feedback. Record the "
                    "customer, sales channel, delivery steps, costs or constraints, and "
                    "improvement decision.",
                    "A customer-cycle analysis explains every major stage and at least three "
                    "decisions.",
                    "Customer-cycle analysis",
                    f"{goal_title} customer journey small business case study",
                ),
                (
                    "Run a small offer test",
                    "Collect real evidence about demand and delivery before expanding the "
                    "operation.",
                    "A bounded test replaces assumptions with customer and operating evidence.",
                    f"Offer one small version to a clearly defined customer group. Apply this "
                    f"constraint: {constraints}. Record responses, completed sales or commitments, "
                    "delivery issues, and one change for the next run.",
                    "The test log records the audience, responses, result, delivery issues, and "
                    "one "
                    "evidence-based change.",
                    "Offer-test log and reflection",
                    f"{goal_title} minimum viable offer test guide",
                ),
                (
                    "Run and evaluate an independent sales cycle",
                    "Demonstrate that the offer can be sold and delivered through the mapped loop.",
                    "An independently run cycle is credible evidence of practical business "
                    "ability.",
                    f"Plan and produce the chosen business evidence: {proof}. Capture the result "
                    "from "
                    "customer contact through delivery and feedback.",
                    "The business evidence is complete, reviewable, and includes customer "
                    "response, "
                    "delivery result, and an outcome measure.",
                    proof,
                    f"{goal_title} small business experiment scorecard",
                ),
                (
                    "Turn the result into a simple playbook",
                    "Preserve the decisions that worked and the next improvement to test.",
                    "A concise playbook makes the result repeatable without adding management "
                    "overhead.",
                    "Summarize the offer, customer, operating steps, strongest evidence, failed "
                    "assumption, and the single next improvement in a reusable one-page playbook.",
                    "A shareable playbook includes the operating loop, evidence, lesson, and next "
                    "test.",
                    "One-page operating playbook and evidence package",
                    f"how to document a repeatable {goal_title} operating process",
                ),
            ],
            "technical": [
                (
                    "Define the system and acceptance criteria",
                    "Translate the technical goal into behavior, boundaries, and observable "
                    "quality.",
                    "Clear acceptance criteria prevent a technically interesting build from "
                    "missing "
                    "the real outcome.",
                    f"Write a one-page system brief for this outcome: {outcome}. Include users or "
                    "callers, inputs, outputs, failure behavior, quality constraints, and "
                    "evidence.",
                    "The system brief contains at least three testable behaviors plus failure and "
                    "quality criteria.",
                    "System brief and acceptance criteria",
                    f"{goal_title} requirements and acceptance criteria example",
                ),
                (
                    "Map the architecture and technical gaps",
                    "Identify the components, interfaces, risks, and missing knowledge needed for "
                    "the build.",
                    "An architecture map uses existing strengths while exposing only the gaps that "
                    "block implementation.",
                    f"Draw a component and data-flow map. Mark what your experience already covers "
                    f"({existing_experience}), then attach one risk, unknown, or test to each "
                    "boundary.",
                    "The architecture map shows components, interfaces, data flow, and a risk or "
                    "test "
                    "for every boundary.",
                    "Annotated architecture and gap map",
                    f"{goal_title} architecture patterns practical guide",
                ),
                (
                    "Reproduce one end-to-end reference workflow",
                    "Understand how the chosen components work together under success and failure.",
                    "A reproduced reference creates implementation context before independent "
                    "design.",
                    "Follow one credible end-to-end reference and rebuild the smallest working "
                    "path. "
                    "Add notes for each interface, major decision, and one simulated failure.",
                    "The reference workflow runs end to end and the notes explain every interface, "
                    "decision, and simulated failure.",
                    "Working reference implementation with notes",
                    f"{goal_title} end to end implementation tutorial",
                ),
                (
                    "Build and test a constrained prototype",
                    "Apply the architecture to a changed use case without copying the reference.",
                    "A constrained prototype tests design judgment before the final system grows.",
                    f"Build the smallest prototype that exercises the critical path. Apply this "
                    f"constraint: {constraints}. Test normal behavior, one boundary case, and one "
                    "failure path, then record two corrected gaps.",
                    "The prototype passes documented normal, boundary, and failure checks and "
                    "includes "
                    "two explained corrections.",
                    "Working prototype, checks, and reflection",
                    f"{goal_title} prototype testing project ideas",
                ),
                (
                    "Build and evaluate the independent system",
                    "Demonstrate the target engineering capability through a reviewable "
                    "implementation.",
                    "Independent implementation and evaluation prove transfer beyond tutorials.",
                    f"Plan, build, and evaluate the chosen technical evidence: {proof}. Compare "
                    "the "
                    "result with the acceptance criteria and record limitations.",
                    "The system is runnable or inspectable, its evaluation covers every acceptance "
                    "criterion, and known limitations are documented.",
                    proof,
                    f"{goal_title} engineering project evaluation rubric",
                ),
                (
                    "Document the engineering decisions and evidence",
                    "Make the implementation understandable, credible, and reusable beyond "
                    "CareerOS.",
                    "Clear technical explanation demonstrates judgment as well as working code.",
                    "Package the architecture, setup, key decisions, tests, strongest result, and "
                    "remaining limitation in a concise technical case study.",
                    "A reviewer can inspect the system, reproduce the main result, and understand "
                    "its "
                    "tradeoffs from the evidence package.",
                    "Technical case study and evidence package",
                    f"how to present {goal_title} engineering portfolio project",
                ),
            ],
            "creative": [
                (
                    "Choose what you want to make",
                    "Turn the creative goal into a specific kind of piece you can picture.",
                    "A concrete target makes it obvious which techniques to practise first.",
                    f"Collect three to five examples of work like what you want to make for this "
                    f"goal: {outcome}. For each, note one thing you love and one thing you'd do "
                    "differently.",
                    "A short reference board with at least three examples and a note on each.",
                    "Reference board with notes",
                    f"{goal_title} inspiration examples for beginners",
                ),
                (
                    "Map the techniques it takes",
                    "Name the few techniques your target pieces depend on.",
                    "Practising the right techniques beats practising everything.",
                    f"List five to seven techniques your reference pieces use. Mark which ones you "
                    f"already have ({existing_experience}) and pick the one that would make the "
                    "biggest difference first.",
                    "A technique list with each item marked as comfortable or to practise.",
                    "Technique map",
                    f"{goal_title} essential techniques",
                ),
                (
                    "Study one finished piece closely",
                    "See how an experienced maker puts the techniques together.",
                    "Copying a small part of real work teaches decisions a tutorial skips.",
                    "Pick one piece you admire. Recreate a small section of it as a study, and "
                    "write down three choices the maker made and why they work.",
                    "A study piece plus three noted choices.",
                    "Study piece with notes",
                    f"{goal_title} step by step tutorial",
                ),
                (
                    "Make a guided practice piece",
                    "Create a small piece of your own using what the study taught you.",
                    "Small finished pieces build skill faster than one big unfinished one.",
                    "Make one small, complete piece in your own subject or style, working within "
                    f"this: {constraints}. Note two things you'd fix next time.",
                    "One finished small piece and two notes on what to improve.",
                    "Practice piece and notes",
                    f"{goal_title} practice exercises",
                ),
                (
                    "Create an original piece on your own",
                    "Make the kind of work you set out to make, with no tutorial to follow.",
                    "An original piece shows the skill is yours, not borrowed from a guide.",
                    f"Plan and finish the piece you chose as proof: {proof}.",
                    "The piece is finished and ready for someone else to look at, read, or hear.",
                    proof,
                    f"{goal_title} project ideas",
                ),
                (
                    "Share the work and get feedback",
                    "Put the work in front of real people and learn from their response.",
                    "Feedback from others shows what lands, which practice alone can't.",
                    "Share your strongest piece with at least two people or one community. Ask "
                    "one specific question, then write down what you'll keep and what you'll "
                    "change in the next piece.",
                    "The work has been shared and the feedback is noted with a next step.",
                    "Shared piece and feedback notes",
                    f"where to share {goal_title} work for feedback",
                ),
            ],
            "fitness": [
                (
                    "Set your target and baseline",
                    "Know exactly where you are now and what you're training toward.",
                    "Training is easier to plan, and safer, when it starts from your real level.",
                    f"Write down the target ({outcome}) and do one easy baseline test: a timed "
                    "distance, a set count, or a session you can finish comfortably. If you "
                    "have a health condition or injury, check with a professional first.",
                    "A written target and one recorded baseline result.",
                    "Target and baseline record",
                    f"{goal_title} beginner baseline test",
                ),
                (
                    "Plan a gradual weekly routine",
                    "Lay out a week of training that builds up slowly and includes rest.",
                    "Gradual increases prevent most injuries and keep training sustainable.",
                    f"Plan one week that fits your schedule ({constraints}). Include easy days, "
                    "one harder session, and at least one rest day. Build on what you already "
                    f"do ({existing_experience}).",
                    "A one-week plan with session types, durations, and rest days.",
                    "Weekly training plan",
                    f"{goal_title} beginner training plan",
                ),
                (
                    "Learn good form and recovery",
                    "Understand the technique, warm-up, and recovery your training needs.",
                    "Good form and recovery keep you training week after week.",
                    "Learn the correct form for your main exercise and a simple warm-up and "
                    "cool-down. Film or check one session against a reliable guide.",
                    "A warm-up and cool-down you use, and one form check done.",
                    "Form check and warm-up routine",
                    f"{goal_title} proper form and recovery",
                ),
                (
                    "Complete your first full training week",
                    "Follow the plan for a whole week and see how it really goes.",
                    "A completed week shows whether the plan fits your life and body.",
                    "Do every planned session for one week. After each one, log how it felt "
                    "(easy, right, too hard) and adjust next week if needed.",
                    "A week of logged sessions with one adjustment noted.",
                    "Training log for one week",
                    f"{goal_title} how to track training progress",
                ),
                (
                    "Do a practice run toward the target",
                    "Try a shorter or easier version of your target to see where you stand.",
                    "A practice run shows what's ready and what still needs training.",
                    f"Do a scaled-down version of your target ({proof}). Note what held up, "
                    "what was hard, and how you felt the next day.",
                    "A practice run is done and logged with notes on what to work on.",
                    "Practice run log",
                    f"{goal_title} practice run tips",
                ),
                (
                    "Review progress and plan what's next",
                    "Compare where you started with where you are, and decide how to keep going.",
                    "A clear review keeps the habit going after the goal is reached.",
                    "Compare your baseline with your latest results. Note what worked, what "
                    "you'd change, and the next target to keep the habit going.",
                    "A before-and-after comparison and a next target.",
                    "Progress review and next target",
                    f"after {goal_title} what next",
                ),
            ],
            "general": [
                (
                    "Define what success looks like",
                    "Turn the goal into outcomes that can be recognized and reviewed.",
                    "The rest of the roadmap needs an observable destination.",
                    f"Write a one-page success brief for this outcome: {outcome}. List what you "
                    "will "
                    "explain, do, or produce.",
                    "A written success brief contains at least three observable outcomes.",
                    "One-page success brief",
                    f"{goal_title} competency framework beginner guide",
                ),
                (
                    "Map what you know and what's missing",
                    "Identify the smallest set of concepts or skills used by later work.",
                    "An explicit foundation map reveals gaps without repeating everything.",
                    f"Create a map of five to seven essentials. Mark what your experience covers "
                    f"({existing_experience}) and one concrete gap for every remaining item.",
                    "The foundation map exists and every item has a confidence and gap note.",
                    "Annotated foundation map",
                    f"{goal_title} essential concepts roadmap",
                ),
                (
                    "Learn from one complete example",
                    "See how the essential pieces connect from start to finish.",
                    "A complete example supplies context before independent practice.",
                    "Follow one credible end-to-end introduction and reproduce the workflow with "
                    "notes "
                    "explaining every major decision.",
                    "A complete walkthrough exists with an explanation at every major stage.",
                    "Reproduced walkthrough with personal notes",
                    f"{goal_title} complete practical tutorial",
                ),
                (
                    "Try it once with guidance",
                    "Use the workflow without copying the original example.",
                    "A changed context tests whether the workflow is understood.",
                    "Create a small practice output related to your goal. Apply this "
                    "constraint: "
                    f"{constraints}. Record two gaps you corrected.",
                    "The output works and includes a reflection describing two corrected gaps.",
                    "Working practice output and reflection",
                    f"{goal_title} practice project ideas",
                ),
                (
                    "Do it on your own",
                    "Demonstrate the target ability with limited guidance.",
                    "Independent work exposes the remaining gaps and proves transfer.",
                    f"Plan and produce the evidence you chose: {proof}.",
                    "The final output is complete, accessible, and reviewable by another person.",
                    proof,
                    f"{goal_title} capstone project rubric",
                ),
                (
                    "Review, explain, and package your learning",
                    "Confirm understanding and make the result useful beyond CareerOS.",
                    "Clear explanation makes the work useful for interviews and sharing.",
                    "Explain the approach, key decisions, strongest result, and remaining gap. "
                    "Package "
                    "the final output with a concise summary.",
                    "A clear summary and final evidence artifact are ready to share.",
                    "Shareable summary and evidence package",
                    f"how to present {goal_title} portfolio work",
                ),
            ],
        }[domain]
        templates = [
            *templates[:5],
            (
                "Review your first solo result",
                "Compare the independent result against the intended outcome and identify the "
                "few gaps that matter most.",
                "A deliberate review prevents a finished-looking artifact from hiding a weak "
                "capability.",
                f"Review the independent result against this proof target: {proof}. Record the "
                "three strongest parts, the highest-risk gap, and one concrete revision that "
                "would make the evidence more credible.",
                "A review note identifies the strongest evidence, one high-impact gap, and one "
                "specific revision tied to the proof target.",
                "Evidence review and revision plan",
                f"{goal_title} self review rubric practical project",
            ),
            (
                "Fix the biggest gap",
                "Improve the part of the work that most limits the target capability.",
                "Targeted revision turns feedback into stronger evidence instead of starting a "
                "disconnected new exercise.",
                "Implement the single revision from your review plan. Show the before-and-after "
                "behavior, decision, or artifact, and explain why the revision improves the "
                "outcome.",
                "The revised result includes a visible before-and-after comparison and an "
                "explanation of the improvement.",
                "Revision comparison and explanation",
                f"{goal_title} improvement case study examples",
            ),
            (
                "Try it in a new situation",
                "Show that the capability survives a realistic variation rather than only one "
                "rehearsed example.",
                "A changed scenario distinguishes repeatable skill from a one-off successful "
                "artifact.",
                "Use the improved work in one changed but relevant scenario. Keep the same "
                "outcome while changing an input, constraint, audience, edge case, or "
                "requirement. Capture what transferred and what required adjustment.",
                "The changed scenario reaches a reviewable result and records one justified "
                "adjustment or trade-off.",
                "Transfer test and trade-off note",
                f"{goal_title} realistic scenario test examples",
            ),
            (
                "Prepare to show your result",
                "Assemble the exact evidence a reviewer would need to judge the target capability.",
                "A deliberate demonstration connects the finished work to the learner's intended "
                "outcome and proof.",
                f"Choose the strongest version of the work and prepare a concise demonstration "
                f"against: {proof}. Include the outcome, approach, evidence, limitation, and "
                "what you would improve next.",
                "A reviewer can follow the demonstration, inspect the evidence, and understand "
                "one limitation without needing extra context.",
                "Final demonstration outline and evidence set",
                f"{goal_title} portfolio demonstration rubric",
            ),
            templates[5],
        ]
        keys = [
            "define-success",
            "map-foundations",
            "learn-workflow",
            "guided-output",
            "independent-output",
            "review-independent-result",
            "strengthen-key-gap",
            "test-transfer",
            "prepare-final-demonstration",
            "package-learning",
        ]
        kinds = [
            "learn",
            "practice",
            "learn",
            "practice",
            "prove",
            "practice",
            "practice",
            "prove",
            "prove",
            "prove",
        ]
        efforts = [
            "Short focused session",
            "Several focused sessions",
            "Several focused sessions",
            "Several focused sessions",
            "Multi-session project",
            "Short focused session",
            "Several focused sessions",
            "Several focused sessions",
            "Short focused session",
            "Short focused session",
        ]
        prerequisites = [[]] + [[keys[index - 1]] for index in range(1, len(keys))]
        return [
            RoadmapDraftStep(
                stable_key=keys[index],
                kind=kinds[index],
                title=template[0],
                objective=template[1],
                rationale=template[2],
                action=template[3],
                completion_condition=template[4],
                effort_label=efforts[index],
                evidence_suggestion=template[5],
                prerequisite_step_keys=prerequisites[index],
                resource_queries=[template[6]],
            )
            for index, template in enumerate(templates)
        ]

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
