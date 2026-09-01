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
        domain = self._domain(goal_title)
        steps = self._steps(
            domain=domain,
            goal_title=goal_title,
            outcome=outcome,
            proof=proof,
            existing_experience=generation_input.existing_experience.rstrip(". "),
            constraints=generation_input.relevant_constraints.rstrip(". "),
        )
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
            "general": (
                "Set the foundation",
                "Define success and identify the essential foundations for the goal.",
                "Build working ability",
                "Connect the foundations in a complete workflow and apply them independently.",
                "Prove the outcome",
            ),
        }[domain]
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
                    title=foundation_title,
                    outcome=foundation_outcome,
                    rationale=(
                        "A clear target and honest baseline prevent unnecessary or missing work."
                    ),
                    steps=steps[:2],
                ),
                RoadmapDraftMilestone(
                    title=workflow_title,
                    outcome=workflow_outcome,
                    rationale=(
                        "Guided understanding becomes useful only after deliberate application."
                    ),
                    steps=steps[2:4],
                ),
                RoadmapDraftMilestone(
                    title=proof_title,
                    outcome="Produce and explain evidence that demonstrates the target capability.",
                    rationale="Independent proof turns learning into credible, reusable evidence.",
                    steps=steps[4:],
                ),
            ],
        )
        return ProviderResult(value=draft)

    @staticmethod
    def _domain(goal_title: str) -> str:
        text = goal_title.lower()
        if any(
            word in text
            for word in (
                "spanish",
                "language",
                "english",
                "french",
                "japanese",
                "german",
                "korean",
                "mandarin",
                "italian",
                "speaking",
            )
        ):
            return "language"
        if any(
            word in text
            for word in (
                "coffee",
                "business",
                "shop",
                "store",
                "sales",
                "customer",
                "startup",
                "entrepreneur",
                "marketing",
                "revenue",
            )
        ):
            return "business"
        if any(
            word in text
            for word in (
                "engineer",
                "developer",
                "python",
                "programming",
                "machine learning",
                "data science",
                "ai",
                "software",
                "code",
                "api",
            )
        ):
            return "technical"
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
            "general": [
                (
                    f"Define success for {goal_title}",
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
                    "Map the essential foundations",
                    "Identify the smallest set of concepts or skills used by later work.",
                    "An explicit foundation map reveals gaps without repeating everything.",
                    f"Create a map of five to seven essentials. Mark what your experience covers "
                    f"({existing_experience}) and one concrete gap for every remaining item.",
                    "The foundation map exists and every item has a confidence and gap note.",
                    "Annotated foundation map",
                    f"{goal_title} essential concepts roadmap",
                ),
                (
                    "Learn one complete workflow",
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
                    "Complete a guided practice output",
                    "Use the workflow without copying the original example.",
                    "A changed context tests whether the workflow is understood.",
                    f"Create a small practice output related to {goal_title}. Apply this "
                    "constraint: "
                    f"{constraints}. Record two gaps you corrected.",
                    "The output works and includes a reflection describing two corrected gaps.",
                    "Working practice output and reflection",
                    f"{goal_title} practice project ideas",
                ),
                (
                    "Create an independent final output",
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
        keys = [
            "define-success",
            "map-foundations",
            "learn-workflow",
            "guided-output",
            "independent-output",
            "package-learning",
        ]
        kinds = ["learn", "practice", "learn", "practice", "prove", "prove"]
        efforts = [
            "Short focused session",
            "Several focused sessions",
            "Several focused sessions",
            "Several focused sessions",
            "Multi-session project",
            "Short focused session",
        ]
        prerequisites = [[], [keys[0]], [keys[1]], [keys[2]], [keys[3]], [keys[4]]]
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
