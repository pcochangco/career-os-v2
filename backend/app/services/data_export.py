"""Portable copy of everything a person has created in CareerOS.

Includes the account, goals, discovery answers, roadmaps (milestones and steps), progress,
learning records, evidence links, daily practice, and issue reports. Internal operational data
(sessions, AI usage accounting, provider metadata, prompts) is deliberately left out.
"""

from datetime import UTC, datetime
from typing import Any

from app.db.models import User
from app.services.entitlements import is_premium

EXPORT_FORMAT_VERSION = 1


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


def build_account_export(user: User) -> dict[str, Any]:
    work_by_step = {record.step_id: record for record in user.step_work}
    completed_by_step = {record.step_id: record.completed_at for record in user.step_progress}
    practice_by_roadmap: dict[Any, list[dict[str, Any]]] = {}
    for completion in user.practice_completions:
        practice_by_roadmap.setdefault(completion.roadmap_id, []).append(
            {
                "date": completion.practice_date.isoformat(),
                "completed_at": _iso(completion.completed_at),
            }
        )

    goals = []
    for goal in sorted(user.goals, key=lambda item: item.created_at):
        questions = {
            (question.revision, question.question_key): question.question
            for question in goal.discovery_questions
        }
        goals.append(
            {
                "title": goal.title,
                "status": goal.status,
                "created_at": _iso(goal.created_at),
                "discovery_answers": [
                    {
                        "question": questions.get(
                            (answer.revision, answer.question_key), answer.question_key
                        ),
                        "answer": answer.answer,
                        "answered_at": _iso(answer.created_at),
                    }
                    for answer in sorted(goal.discovery_answers, key=lambda item: item.created_at)
                ],
                "roadmaps": [
                    {
                        "title": roadmap.title,
                        "status": roadmap.status,
                        "version": roadmap.version,
                        "summary": roadmap.summary,
                        "goal_outcome": roadmap.goal_outcome,
                        "starting_point": roadmap.starting_state_summary,
                        "milestones": [
                            {
                                "position": milestone.position,
                                "title": milestone.title,
                                "outcome": milestone.outcome,
                                "steps": [
                                    {
                                        "position": step.position,
                                        "title": step.title,
                                        "objective": step.objective,
                                        "action": step.action,
                                        "complete_when": step.completion_condition,
                                        "completed_at": _iso(completed_by_step.get(step.id)),
                                        "learning_record": "\n\n".join(
                                            value
                                            for value in (
                                                work_by_step[step.id].notes,
                                                work_by_step[step.id].evidence_summary,
                                            )
                                            if value
                                        )
                                        if step.id in work_by_step
                                        else "",
                                        "evidence_link": work_by_step[step.id].evidence_url
                                        if step.id in work_by_step
                                        else "",
                                    }
                                    for step in sorted(milestone.steps, key=lambda s: s.position)
                                ],
                            }
                            for milestone in sorted(roadmap.milestones, key=lambda m: m.position)
                        ],
                        "daily_practice": sorted(
                            practice_by_roadmap.get(roadmap.id, []), key=lambda item: item["date"]
                        ),
                    }
                    for roadmap in sorted(goal.roadmaps, key=lambda item: item.version)
                ],
            }
        )

    return {
        "format": "careeros-account-export",
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "account": {
            "email": next((i.email for i in user.identities if i.email), ""),
            "sign_in_methods": sorted(identity.provider for identity in user.identities),
            "plan": "premium" if is_premium(user) else "free",
            "created_at": _iso(user.created_at),
        },
        "goals": goals,
        "issue_reports": [
            {
                "category": report.category,
                "message": report.message,
                "created_at": _iso(report.created_at),
            }
            for report in sorted(user.issue_reports, key=lambda item: item.created_at)
        ],
    }
