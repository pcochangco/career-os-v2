# CareerOS AI Roadmap Specification

## Objective

Generate a realistic, personalized, explainable sequence that can move a user
from their current state to a defined real-world outcome while producing useful
evidence along the way.

The AI roadmap is CareerOS's core product capability. It is not a generic task
list and must not depend on daily scheduling.

## Required discovery input

Generation requires enough information to establish:

- Goal statement
- Desired outcome and success condition
- Starting level and relevant prior experience
- Known prerequisites already completed
- Important constraints that affect content or feasibility
- Desired proof, project, credential, or demonstrable capability

The system may record explicit user facts and clearly labeled assumptions.
Material assumptions must be reviewable before generation.

## Generation pipeline

1. **Normalize the goal** — turn the user's wording into a clear target without
   replacing their intent.
2. **Model the gap** — identify the knowledge, skills, practice, and evidence
   separating the starting state from the outcome.
3. **Build prerequisites** — order concepts and capabilities by dependency.
4. **Create milestones** — define meaningful checkpoints with observable
   outcomes.
5. **Create steps** — divide each milestone into focused learn, practice, and
   prove actions.
6. **Retrieve resources** — search trusted or appropriate sources for material
   matching each step.
7. **Verify resources** — validate URL reachability and capture reliable
   metadata before presenting a resource.
8. **Critique the roadmap** — check realism, sequencing, gaps, duplication,
   personalization, and evidence quality.
9. **Repair when necessary** — revise failed quality checks within a bounded
   number of attempts.
10. **Validate structure** — accept only output matching the versioned schema.
11. **Persist a draft version** — retain generation provenance for review.

## Roadmap structure

A roadmap contains:

- Goal outcome
- Starting-state summary
- Assumptions
- Ordered milestones
- Ordered steps
- Prerequisite relationships
- Completion evidence expected from the overall goal
- Generation and schema version metadata

A milestone contains:

- Title
- Outcome
- Rationale
- Ordered steps

A step contains:

- Title
- Type: `learn`, `practice`, or `prove`
- Objective
- Rationale
- Concrete instructions
- Completion condition
- Optional approximate effort guidance
- Optional prerequisite step references
- Verified resource references
- Suggested evidence type when relevant

## Quality contract

A valid roadmap must be:

- **Personalized** — reflects the user's stated starting point and outcome
- **Realistic** — avoids impossible jumps and unnecessary breadth
- **Sequential** — prerequisites precede dependent work
- **Actionable** — every step states what to do next
- **Verifiable** — every step has an observable completion condition
- **Evidence-producing** — important capabilities lead to practice or proof
- **Concise** — avoids filler steps and repeated explanations
- **Grounded** — presented resources are retrieved and verified
- **Stable** — identical test inputs can use deterministic fixtures without a
  live provider

## Resource policy

The language model must not be trusted to provide final resource URLs from
memory. It may describe a resource need or produce a search query. CareerOS then
retrieves candidates and verifies:

- URL and canonical URL
- Title and source
- Content type
- Accessibility at verification time
- Available thumbnail
- Available duration or reading metadata
- Relevance to the step

A failed or unavailable resource must not block the roadmap itself. The step can
remain actionable without it and may receive a replacement later.

## Review and acceptance

Generated roadmaps begin as drafts. The user may:

- Accept
- Regenerate with feedback
- Reject

Accepting a roadmap makes it the active version for the goal. Regeneration does
not overwrite an accepted historical version.

## Regeneration after progress

Completed steps are historical facts and must not be silently changed or
deleted. Later adaptation may revise the unfinished future portion while
preserving completed step identity, evidence, and completion records.

## Provider independence

Application code depends on a roadmap-generation interface, not a particular
model vendor. Provider responses are parsed into the canonical schema and
treated as untrusted input.

Tests must run without network or live model calls using deterministic fixtures.

## Evaluation

Before production expansion, maintain a representative evaluation set covering:

- Beginner and experienced users with the same goal
- Career, learning, project, and credential goals
- Narrow and overly broad goals
- Missing prerequisites
- Conflicting or unrealistic expectations
- Resource-rich and resource-scarce topics
- Attempts to inject instructions through user content or retrieved pages

Quality measurements should include schema validity, prerequisite correctness,
goal coverage, actionable-step rate, completion-condition quality, resource
validity, duplication, and human reviewer usefulness.
