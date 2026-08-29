# CareerOS Product

## North star

CareerOS turns a personal goal into a realistic, personalized roadmap, always
shows the next meaningful step, records genuine progress, and builds shareable
proof of learning and achievement.

## Product promise

A user can open CareerOS, select a goal, understand where they are, and continue
learning or working with one tap. They do not need to prepare a daily plan,
commit a schedule, or reorganize missed work.

## Primary user journey

1. The user creates a goal.
2. CareerOS asks a small number of adaptive questions about the desired outcome,
   current ability, relevant context, and preferred proof of completion.
3. CareerOS generates a structured, realistic roadmap.
4. The user reviews and accepts the roadmap.
5. Selecting the goal opens its roadmap at the current step.
6. The user studies, practices, or creates an output.
7. The user records useful notes or evidence and completes the step.
8. CareerOS advances the current position and updates truthful progress.
9. The user's goal showcase grows from completed work.

## MVP capabilities

- Authentication and user-owned goals
- Simple goal creation and adaptive discovery
- Structured AI roadmap generation and review
- One active accepted roadmap per goal with preserved version history
- Mobile-first vertical roadmap path
- Current-step detail with a clear completion condition
- Verified articles, videos, and other learning resources
- Step notes, links, and lightweight evidence
- Step completion and truthful goal progress
- Progressive goal showcase
- Editable AI-generated learning summary and resume bullets
- Public sharing controlled by the user

## Product principles

### Roadmap first

The goal roadmap is the main product surface. Dashboards, feeds, calendars, and
planning screens must not sit between the user and the roadmap.

### Continue without cleanup

There is no penalty or maintenance workflow when the user takes a break. On
return, CareerOS presents the same current position and lets the user continue.

### Evidence over gamification

Motivation comes from visible progress, completed work, acquired skills, and a
growing showcase. The MVP does not use punitive streaks, artificial points, or
fabricated progress.

### AI must be trustworthy

AI output is untrusted until structurally validated. Suggested resources must be
retrieved and verified rather than accepted as invented links.

### Complexity must earn its place

A feature belongs in CareerOS only when it shortens the route to starting the
current step, improves roadmap quality, records truthful progress, or strengthens
the user's final evidence.

## Explicit non-goals

The MVP does not include:

- Today or daily-planner screens
- Daily plans or “Plan my day”
- Availability, time budgets, or required study schedules
- Carry-over, overdue, reschedule, rebalance, or calendar workflows
- Goal-specific productivity strategies
- Manual roadmap ordering
- AI mentor or general-purpose chatbot
- Social feeds, leaderboards, or competitive streaks
- Microservices or speculative infrastructure

## Progress definition

Progress is derived from completed accepted-roadmap steps. It is never inferred
from time elapsed, resources opened, AI confidence, or the user's intended
schedule.

Completed steps remain part of the accepted roadmap's history. Regeneration must
not silently rewrite completed work.

## MVP success

The MVP succeeds when a user can:

1. Describe a meaningful goal.
2. Receive a credible and personalized roadmap.
3. Start the current step without planning their day.
4. Return later without losing their place.
5. Complete steps and see truthful progress.
6. Show what they learned or produced through a shareable goal page.
