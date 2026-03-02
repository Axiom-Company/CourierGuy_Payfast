import json
import logging
import uuid
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.domain.models.user import Profile
from app.database import get_db
from app.domain.models.email_log import EmailLog
from app.domain.models.email_webhook_event import EmailWebhookEvent
from app.domain.schemas.email import (
    EmailLogsResponse, EmailLogItem,
    WebhookEventsResponse, WebhookEventItem,
    EmailStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-webhooks", tags=["Email Webhooks"])


# ── ZeptoMail webhook receiver (unauthenticated — ZeptoMail requirement) ─────

@router.post("/zeptomail")
async def zeptomail_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives POST from ZeptoMail for bounce, open, click, and feedback events.
    Must return 200 immediately. No auth required (ZeptoMail constraint).
    """
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=200)

    event_names = body.get("event_name", [])
    event_messages = body.get("event_message", [])

    for event_name in event_names:
        for msg in event_messages:
            email_info = msg.get("email_info", {})

            # Extract recipient from the to field
            to_list = email_info.get("to", [])
            recipient_email = ""
            if to_list:
                first = to_list[0] if isinstance(to_list, list) else to_list
                if isinstance(first, dict):
                    ea = first.get("email_address", {})
                    recipient_email = ea.get("address", "") if isinstance(ea, dict) else str(ea)
                else:
                    recipient_email = str(first)

            subject = email_info.get("subject", "") or body.get("subject", "")
            email_reference = body.get("email_reference", "") or email_info.get("email_reference", "")

            bounce_type = None
            bounce_reason = None
            if event_name in ("softbounce", "hardbounce"):
                bounce_type = "soft" if event_name == "softbounce" else "hard"
                bounce_reason = msg.get("reason", "") or msg.get("description", "")

            event = EmailWebhookEvent(
                id=str(uuid.uuid4()),
                event_type=event_name,
                recipient_email=recipient_email,
                subject=subject[:500] if subject else None,
                email_reference=email_reference or None,
                bounce_type=bounce_type,
                bounce_reason=bounce_reason,
                raw_payload=json.dumps(body)[:4000],
            )
            db.add(event)

    try:
        await db.flush()
    except Exception as e:
        logger.error(f"[WEBHOOK] Failed to save ZeptoMail event: {e}")

    return Response(status_code=200)


# ── Admin endpoints (protected) ──────────────────────────────────────────────

@router.get("/admin/logs", response_model=EmailLogsResponse)
async def get_email_logs(
    admin: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    email_type: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
):
    """Get paginated email send logs for admin panel."""
    q = select(EmailLog)
    count_q = select(func.count()).select_from(EmailLog)

    if email_type:
        q = q.where(EmailLog.email_type == email_type)
        count_q = count_q.where(EmailLog.email_type == email_type)
    if status:
        q = q.where(EmailLog.status == status)
        count_q = count_q.where(EmailLog.status == status)
    if search:
        like = f"%{search}%"
        q = q.where(EmailLog.user_email.ilike(like) | EmailLog.subject.ilike(like))
        count_q = count_q.where(EmailLog.user_email.ilike(like) | EmailLog.subject.ilike(like))

    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(EmailLog.sent_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return EmailLogsResponse(
        logs=[
            EmailLogItem(
                id=r.id,
                user_email=r.user_email,
                email_type=r.email_type,
                subject=r.subject,
                status=r.status,
                error_message=r.error_message,
                sent_at=r.sent_at.isoformat() if r.sent_at else "",
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/events", response_model=WebhookEventsResponse)
async def get_webhook_events(
    admin: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    event_type: str | None = Query(None),
    search: str | None = Query(None),
):
    """Get paginated webhook events for admin panel."""
    q = select(EmailWebhookEvent)
    count_q = select(func.count()).select_from(EmailWebhookEvent)

    if event_type:
        q = q.where(EmailWebhookEvent.event_type == event_type)
        count_q = count_q.where(EmailWebhookEvent.event_type == event_type)
    if search:
        like = f"%{search}%"
        q = q.where(
            EmailWebhookEvent.recipient_email.ilike(like) | EmailWebhookEvent.subject.ilike(like)
        )
        count_q = count_q.where(
            EmailWebhookEvent.recipient_email.ilike(like) | EmailWebhookEvent.subject.ilike(like)
        )

    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(EmailWebhookEvent.received_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return WebhookEventsResponse(
        events=[
            WebhookEventItem(
                id=r.id,
                event_type=r.event_type,
                recipient_email=r.recipient_email,
                subject=r.subject,
                email_reference=r.email_reference,
                bounce_type=r.bounce_type,
                bounce_reason=r.bounce_reason,
                received_at=r.received_at.isoformat() if r.received_at else "",
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    admin: Profile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate email delivery stats for admin dashboard."""
    # Counts from email_logs
    sent_q = select(func.count()).select_from(EmailLog).where(EmailLog.status == "sent")
    failed_q = select(func.count()).select_from(EmailLog).where(EmailLog.status == "failed")
    total_sent = (await db.execute(sent_q)).scalar() or 0
    total_failed = (await db.execute(failed_q)).scalar() or 0

    # Counts from webhook events
    soft_q = select(func.count()).select_from(EmailWebhookEvent).where(
        EmailWebhookEvent.event_type == "softbounce"
    )
    hard_q = select(func.count()).select_from(EmailWebhookEvent).where(
        EmailWebhookEvent.event_type == "hardbounce"
    )
    open_q = select(func.count()).select_from(EmailWebhookEvent).where(
        EmailWebhookEvent.event_type == "open"
    )
    click_q = select(func.count()).select_from(EmailWebhookEvent).where(
        EmailWebhookEvent.event_type == "click"
    )

    total_soft = (await db.execute(soft_q)).scalar() or 0
    total_hard = (await db.execute(hard_q)).scalar() or 0
    total_opens = (await db.execute(open_q)).scalar() or 0
    total_clicks = (await db.execute(click_q)).scalar() or 0
    total_bounces = total_soft + total_hard

    denominator = total_sent or 1

    return EmailStatsResponse(
        total_sent=total_sent,
        total_failed=total_failed,
        total_bounces=total_bounces,
        total_soft_bounces=total_soft,
        total_hard_bounces=total_hard,
        total_opens=total_opens,
        total_clicks=total_clicks,
        bounce_rate=round(total_bounces / denominator * 100, 2),
        open_rate=round(total_opens / denominator * 100, 2),
        click_rate=round(total_clicks / denominator * 100, 2),
    )
