import logging

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, DbSession
from app.api.schemas import IssueReportRead, IssueReportWrite
from app.db.models import IssueReport

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/issue-reports", tags=["issue-reports"])


@router.post("", response_model=IssueReportRead, status_code=status.HTTP_201_CREATED)
def create_issue_report(
    payload: IssueReportWrite,
    user: CurrentUser,
    db: DbSession,
) -> IssueReportRead:
    report = IssueReport(
        user_id=user.id,
        category=payload.category,
        message=payload.message,
        request_reference=payload.request_reference,
        platform=payload.platform,
        app_version=payload.app_version,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    reference = f"CAR-{str(report.id)[:8].upper()}"
    logger.info(
        "Issue report received report_reference=%s category=%s platform=%s",
        reference,
        report.category,
        report.platform,
    )
    return IssueReportRead(
        id=report.id,
        reference=reference,
        category=report.category,
        created_at=report.created_at,
    )
