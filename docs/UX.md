# CareerOS UX

## Experience statement

CareerOS should feel calm, focused, and easy to resume. The user should rarely
need to decide where to navigate next.

## Navigation

The baseline navigation contains:

- **Goals** — owned goals and truthful progress
- **Current goal** — the selected goal's roadmap and current position
- **Profile** — account, privacy, and optional notification preferences

“New goal” is an action from Goals, not a permanent destination.

There is no dashboard or Today destination.

## App opening behavior

- With no goals, show a calm goal-creation empty state.
- With one active goal, open its roadmap directly.
- With several active goals, restore the last opened goal when available;
  otherwise show Goals.
- Selecting a goal always opens that goal's roadmap.

## Goal creation

Discovery uses one question at a time and asks only what materially changes the
roadmap. Typical information includes:

- Desired real-world outcome
- Current starting level
- Existing experience or completed prerequisites
- Relevant constraints other than a required schedule
- Preferred proof of completion

Questions are adaptive. CareerOS should not ask the user to choose an algorithm,
planning strategy, activity count, or time commitment.

## Roadmap screen

Use a mobile-first vertical path inspired by a guided learning journey:

- Completed steps remain visible behind the current position.
- The current step is visually prominent and available in one tap.
- Future steps are visible enough to make the journey understandable.
- Milestones group steps without becoming separate management screens.
- A compact header shows goal title and truthful completion progress.

Avoid Gantt charts, horizontal timelines, dense dashboards, and duplicate lists.

## Roadmap states

- **Completed** — genuinely completed by the user
- **Current** — the next normally actionable step
- **Upcoming** — accepted future work
- **Blocked** — a future step whose prerequisite is incomplete

The user may review completed and upcoming steps. The UI must not imply that
opening a resource completes a step.

## Step experience

Opening a step presents one focused surface with:

- Step title and purpose
- What the user should understand or produce
- One recommended primary resource or action
- Optional supporting resources
- A practice or application task
- A concrete completion condition
- Optional notes and evidence
- **Complete step**

Approximate effort may be shown as guidance, but never as a commitment,
deadline, or source of overdue status.

External resources show available metadata such as source, content type,
thumbnail, and duration or reading length. Resource previews must not crowd the
primary action.

## Completion

Completing a step:

1. Requires the user to confirm the concrete completion condition was met.
2. Preserves notes and evidence.
3. Updates goal progress.
4. Advances the current position to the next unblocked step.
5. Provides a restrained confirmation and a direct way to continue.

No streak celebration, schedule repair, or missed-day warning is required.

Notes, an output summary, and an optional web link can be saved before
completion. They remain attached to the exact accepted-roadmap step if the step
is completed or reopened. Saving or opening evidence never completes a step.

## Goal showcase

The showcase is available throughout the goal and grows as work is completed.
It can contain:

- Goal and outcome
- Skills demonstrated
- Completed milestones and steps
- Resources the user chose to retain
- Notes and reflections selected by the user
- Projects, links, documents, screenshots, or other evidence
- Editable learning summary
- Editable resume bullets

The showcase is private by default. The user deliberately enables a public
share link. Public presentation must not expose private notes or evidence unless
explicitly selected.

## Notifications

Notifications are not part of the first roadmap vertical slice. When added,
they must:

- Be opt-in
- Use calm language
- Deep-link to the exact current step
- Avoid guilt, streak loss, or “overdue” framing
- Stop when the goal is paused or completed
- Respect quiet hours and platform permissions

## Accessibility and responsive behavior

- Design from 320px width upward.
- Use at least 44px interactive targets.
- Support keyboard navigation and visible focus.
- Do not communicate state through color alone.
- Avoid horizontal page scrolling.
- Preserve readable titles and resource metadata at narrow widths.
- Use semantic status text for progress and generation states.
